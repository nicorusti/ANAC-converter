import urllib.request
import urllib.parse
import json
from xml.dom.minidom import parse
import xml.dom.minidom
from xmlToJson import codiceFiscaleCheck
from xmlToJson import indexDataToObject
import re
import os
import hashlib
import sys
import email.utils
import time
import timeit

import socket


#LOCAL FILES PATHS. CHANGE ONLY BEFORE FIRST EXECUTION!
DOWN_DIR="download/"
ANAC_FILE=DOWN_DIR+"datasetANAC.json"
INFO_FILE=DOWN_DIR+"downloadInfo.json"

PROPOSING_STRUCTURES_FILE=DOWN_DIR+"proposingStructures.json"
TEMP_DIR=DOWN_DIR+"temp/"
XML_SUBDIR="xml/"
JUNK_SUBDIR="junk/"
TIMEOUT=10 #timeout for connections
USER_AGENT='Mozilla/5.0'

#for a correctly downloaded and parseable file, sets the time (in seconds) after which http header
#is checked again for updates and interval after which a not downloaded/parseable file is downloaded again
#1 day= 86400
HEADER_CHECK_INTERVAL=86400*3
DOWNLOAD_INTERVAL=86400*3


            
            

#download file from remote to local,
#return True if download successful,otherwise return a String with error message
def download(remote, local, fileInfo):
    try:
        #add http:// if not present  (otherwise urllib raises Exception!)
        if len( urllib.parse.urlparse(remote).scheme)==0:
           remote = "http://"+remote
        opener = urllib.request.build_opener()
        opener.addheaders = [('User-agent', 'Mozilla/5.0')]
        urllib.request.install_opener(opener)
        fileInfo["lastHeaderCheck"]=time.mktime(time.gmtime())
        socket.setdefaulttimeout(TIMEOUT) 
        local_filename, headers=urllib.request.urlretrieve(remote, local)
        try:
            fileInfo["sizeServer"]=int(headers.__getitem__("Content-Length"))
        except Exception:
            fileInfo["sizeServer"]=-1
        try: 
            fileInfo["lastUpdateServer"]=time.mktime(email.utils.parsedate(headers.__getitem__("Last-Modified")))
        except Exception:
            fileInfo["lastUpdateServer"]=-1

    except urllib.error.URLError as err:
        fileInfo["sizeServer"]=-1
        fileInfo["lastUpdateServer"]=-1
        return str(err)
    except urllib.error.HTTPError as err:
        fileInfo["sizeServer"]=-1
        fileInfo["lastUpdateServer"]=-1
        return str(err)
    except urllib.error.ContentTooShortError as err:
        fileInfo["sizeServer"]=-1
        fileInfo["lastUpdateServer"]=-1
        return str(err)
    except socket.timeout as err:
        fileInfo["sizeServer"]=-1
        fileInfo["lastUpdateServer"]=-1
        return str(err)
    except Exception:
        fileInfo["sizeServer"]=-1
        fileInfo["lastUpdateServer"]=-1
        return "Unknown error"
    return True


"""
check and eventually updates a single dataset
dataset file is replaced with downloaded one if: 
    -in http header, last update field or content size field are bigger than previously stored value
    -if http header has none of these fields, if downloaded file is bigger
    -"downlaoded" field was not true due to some previous errors
    -file is new
dataset["downloaded"]=if dataset is correctly downloaded (may be downloaded to junk folder if not parseable!)

returns True if a readable ANAC xml is saved,
False otherwise

"""
def updateSingleDataset(url, fileInfo, administrationId):
    toBeUpdated=False
    headerChecked=False
    #check if exsisting  dataset was not downloaded correctly or is not parseable 
    if "downloaded" in fileInfo.keys() and "parseable" in fileInfo.keys():
        if fileInfo["downloaded"]!=True or fileInfo["parseable"]!=True:
            toBeUpdated=True
    #check if dataset was never downloaded before
    else:
        toBeUpdated=True
            
    #Check if existing file is up to date (check url http header fields last-updated and size)
    #Check header again only if 
    if "sizeServer" in fileInfo.keys() and "lastHeaderCheck" in fileInfo.keys() and "downloaded" in fileInfo.keys() and "lastUpdateServer" in fileInfo.keys():
        if fileInfo["downloaded"]==True and(time.mktime(time.gmtime())-fileInfo["lastHeaderCheck"])>HEADER_CHECK_INTERVAL: 
            httpInfo=checkUrl(url)
            fileInfo["lastHeaderCheck"]=time.mktime(time.gmtime())
            headerChecked=True
            if fileInfo["sizeServer"]<httpInfo[0] or fileInfo["lastUpdateServer"]<httpInfo[1] or( httpInfo[0]==-1 and   httpInfo[1]==-1): 
                toBeUpdated=True
            
    else:     #case in which some of the fields are missing due to a keyboard interrupt
        toBeUpdated=True
        
    #block donwload if it was performed less than DOWNLOAD_INTERVAL s ago 
    if "lastDownloadTry" in  fileInfo.keys():
        if (time.mktime(time.gmtime())-fileInfo["lastDownloadTry"])<DOWNLOAD_INTERVAL:
            toBeUpdated=False
            
    if toBeUpdated==True:
        print()
        print("Downloading", url)
        #save whether file was previously converted to json
        previouslyConverted=False
        if "convertedToJson" in fileInfo.keys():
            previouslyConverted=fileInfo["convertedToJson"]
        if "convertedToRdf" in fileInfo.keys():
            previouslyRdfized=fileInfo["convertedToRdf"]   

        moveToJunk=False

        fileHash=hashlib.sha1(url.encode('utf-8')).hexdigest()
        fileInfo["fileName"]=fileHash+".xml"
        xmlFileTempPath=TEMP_DIR+fileInfo["fileName"]
        fileInfo["downloaded"]=download(url, xmlFileTempPath, fileInfo)
        fileInfo['URL']=url
        fileInfo["lastDownloadTry"]=time.mktime(time.gmtime())
        
        #operations moved in downloat to avoid doubled http request
        #if headerChecked==False: 
         #   httpInfo=checkUrl(url)
          #  fileInfo["lastHeaderCheck"]=time.mktime(time.gmtime())
        #fileInfo["sizeServer"]=httpInfo[0]
        #fileInfo["lastUpdateServer"]=httpInfo[1]
        fileInfo["convertedToJson"]=False
        fileInfo["convertedToRdf"]=False
        fileInfo["type"]="unknown"
        fileInfo["parseable"]=False
        #if file was correctly downloaded
        if fileInfo["downloaded"]==True:                    
            try: 
                fileInfo["sizeLocal"]=os.stat(xmlFileTempPath).st_size
            except Exception:
                fileInfo["sizeLocal"]=-2
            try:
                legge190=xml.dom.minidom.parse(xmlFileTempPath).documentElement
                fileInfo["parseable"]=True
            except Exception:
                fileInfo["parseable"]=False
                fileInfo["type"]="unknown"
                moveToJunk=True
                
            if fileInfo["parseable"]==True:
                try: 
                    indiceContent=legge190.getElementsByTagName("indice") #check wether xml has some fields from ANAC schema 
                    lotti=legge190.getElementsByTagName("lotto")
                    if len(indiceContent)!=0:
                        fileInfo["type"]="index"
                        fileInfo["fileName"]=fileHash+"_index.xml"
                    elif len(lotti)!=0:
                        fileInfo["type"]="data"
                    else:
                        fileInfo["type"]="unknown"
                        fileInfo["parseable"]=False
                        moveToJunk=True
                except Exception:
                    fileInfo["type"]="unknown"
                    fileInfo["parseable"]=False
                    moveToJunk=True
                
        else:
            print(fileInfo["downloaded"])
            moveToJunk=True
                


                
        if fileInfo["downloaded"]==True and (fileInfo["parseable"]==False or fileInfo["type"]=="unknown"):
            print("Not L.190 xml standard")
            moveToJunk=True
    
        #FILE WRITING
        
        #create definitive directory download/CF_istituzione/
        defInstitutionDirectory =DOWN_DIR+administrationId+"/"+XML_SUBDIR 
        if  os.path.exists(defInstitutionDirectory)==False:
            os.makedirs(defInstitutionDirectory) 
           
       
        xmlFileDefPath =defInstitutionDirectory+fileInfo["fileName"]
        #if no httpInfo available, check existing file size!
        if fileInfo["downloaded"]==True and fileInfo["parseable"]==True and fileInfo["sizeServer"]==-1 and   fileInfo["lastUpdateServer"]==-1 and os.path.exists(xmlFileDefPath)==True and os.path.exists(xmlFileTempPath)==True:
            if os.stat(xmlFileTempPath).st_size<os.stat(xmlFileDefPath).st_size:
                print("trovato file con risposta -1 -1 http header")
                moveToJunk=True                                #if downloaded file smaller than already existing one, move to junk
                fileInfo["convertedToJson"]=previouslyConverted
                fileInfo["convertedToRdf"]=previouslyRdfized
            else:
                moveToJunk=False

                    
        #move to destination directory                                                 
        if moveToJunk==False:
            try: 
                if os.path.exists(xmlFileDefPath)==True:
                    os.remove(xmlFileDefPath)
                os.rename(xmlFileTempPath, xmlFileDefPath)
                return True
            except Exception:
                print(xmlFileTempPath, xmlFileDefPath)
                print(str(Exception))
                
        #move to junk       
        else: 
            junkDirectory=DOWN_DIR+administrationId+"/"+JUNK_SUBDIR
            if  os.path.exists(junkDirectory)==False:
                os.makedirs(junkDirectory)
            try:
                if os.path.exists(junkDirectory+fileInfo["fileName"])==True:
                   os.remove(junkDirectory+fileInfo["fileName"])
                if os.path.exists(xmlFileTempPath):
                    os.rename(xmlFileTempPath, junkDirectory+fileInfo["fileName"])  #and move to destination directory
                    
                #erases xml and junk folders in case they are empty (happens, for ex. in case of 404 error)
                if os.path.exists(junkDirectory): 
                    if len(os.listdir(junkDirectory))==0:
                        os.rmdir(junkDirectory)
                if os.path.exists(defInstitutionDirectory): 
                    if len(os.listdir(defInstitutionDirectory))==0:
                        os.rmdir(defInstitutionDirectory)
            except Exception:
                print("exception raised in junk removal!")
                fileInfo["downloaded"]==False
            
        if os.path.exists(xmlFileTempPath)==True:
            print("ERROR FILE IN TEMP LEFT", xmlFileTempPath)
            #os.remove(xmlFileTempPath)    
    return False


    #scarica e parsifica, nel percorso download/CF/
    # -->file di indice
    # -->tutti i dataset linkati nel file di indice
    #files are named with a sha1 hash on their url
    #scrive nella lista datasets di vocabolari con le informazioni sul download
def downloadAllIndexedDatasets(url, administrationId, fileInfoList):
    nFileDownloaded=0
    mainUpdated=False
    mainAlreadyPresent=False
    #check and update all already present datasets, find the main one if present
    for fileInfo in fileInfoList:
        if "URL" in fileInfo.keys():
            updated=updateSingleDataset(fileInfo["URL"], fileInfo, administrationId)
            if fileInfo["URL"]==url:
                mainAlreadyPresent=True
                mainUpdated=updated
                mainFileInfo=fileInfo
            if updated==True:
                nFileDownloaded+=1
     
    #download a new main dataset (the one at url)
    if mainAlreadyPresent==False:
        mainFileInfo=dict()
        updated=updateSingleDataset(url, mainFileInfo, administrationId)
        mainUpdated=updated
        fileInfoList.append(mainFileInfo)

    #check again if linked datasets were present after index dataset was updated
    #if not, add and update them 
    if mainUpdated==True:
        nFileDownloaded+=1
        if mainFileInfo["parseable"]==True and mainFileInfo["type"]=="index":
            try:
                mainFilePath=DOWN_DIR+administrationId+"/"+XML_SUBDIR+mainFileInfo["fileName"]
                legge190=xml.dom.minidom.parse(mainFilePath).documentElement
                indice=indexDataToObject(legge190);
            except Exception:
                print("errore nel leggere file di indice")
                mainFileInfo["type"]="unknown"
                mainFileInfo["parseable"]=False
                indice=[]
            
            for dataset in indice:
                alreadyPresent=False
                for fileInfo in fileInfoList:
                    if dataset["linkDataset"]==fileInfo["URL"]:
                        alreadyPresent=True
                        break
                if alreadyPresent==False:
                    newFileInfo=dict()
                    linkDataset=dataset["linkDataset"]


                    ##remove!
                    print(linkDataset)
                    ##
                    
                    if len(linkDataset)>2048:
                        linkDataset="too long url"
                    updated=updateSingleDataset(linkDataset, newFileInfo, administrationId)
                    if updated==True:
                        nFileDownloaded+=1
                    fileInfoList.append(newFileInfo)
           
    return nFileDownloaded

"""
takes url of dataset from ANAC's Registro comunicazioni
If http header on ANAC website has changed, downloads file from ANAC Registro delle Comunicazioni into  DOWN_DIR/datasetANAC.json  
updates downloadInfo.json  adding any new information from datasetANAC.json and check updates in all listed datasets
Furthermore writes a DOWN_DIR/PROPOSING_STRUCTURES_FILE with a list of all the fiscalid of the Public administrations
(useful for linking with the Indice delle pubbliche amministrazioni)
"""
def checkUpdates(urlANAC):
    nUrlProcessed=0
    nUrl=1
    dataset=dict()
    nXmlFiles=0
    #check that files downloadInfo.json exists (run only first time)
    print("Checking ANAC dataset...")
    if  os.path.exists(DOWN_DIR)==False:
        os.makedirs(DOWN_DIR)
    if  os.path.exists(TEMP_DIR)==False:
        os.makedirs(TEMP_DIR)
    if os.path.isfile(INFO_FILE)==False: 
        newDonwloadInfoFile= open(INFO_FILE, 'w', encoding='utf-8')
        downloadInfo=dict()
        downloadInfo["sizeServer"]=0
        downloadInfo["lastUpdateServer"]=0
        downloadInfo["data"]=[]
        json.dump(downloadInfo, newDonwloadInfoFile, indent=4, ensure_ascii=False, sort_keys=True)
        newDonwloadInfoFile.close()
    try: 
        fIn=open(INFO_FILE, 'r')
        downloadInfo=json.load(fIn)
        fIn.close()
    except Exception:
        print("GENERAL ERROR: download downloadInformation.json is corrupted!")
        return False

    start_time = timeit.default_timer()

    #update datasetANAC.json and copies new URL to downloadInfo.json
    #copies all the CF to proposingStructures.jon (for LOD linking purposes)
    proposingStructuresDict= dict()
    httpInfo=checkUrl(urlANAC)
    if  True==True or downloadInfo["sizeServer"]<httpInfo[0] or downloadInfo["lastUpdateServer"]<httpInfo[1] or os.path.isfile(ANAC_FILE)==False or( httpInfo[0]==-1 and   httpInfo[1]==-1):
        print("Updating ANAC dataset... may take 2-3 min.")
        downloadInfo["URL"]=urlANAC
        downloadInfo["sizeServer"]=httpInfo[0]
        downloadInfo["lastUpdateServer"]=httpInfo[1]
        downloadInfo["donwloaded"]=download(urlANAC, ANAC_FILE, downloadInfo)
        if os.path.isfile(INFO_FILE)==True:
            downloadInfo["sizeLocal"]=os.stat(ANAC_FILE).st_size
        downloadInfo["lastDownloadTry"]=time.mktime(time.gmtime())
        fIn=open(ANAC_FILE, 'r')
        anacDataset=json.load(fIn)
        fIn.close()
        count=0
        for element in anacDataset:
            if "CodiceFiscale" in element.keys(): 
                if codiceFiscaleCheck(element["CodiceFiscale"])==True:
                    proposingStructuresDict[element["CodiceFiscale"]]=element["RagioneSociale"]
            found=False
            for dataset in downloadInfo["data"]:
                if "URL" in dataset.keys() and "URL" in element.keys():
                    if dataset["URL"]==element["URL"]:
                        found=True
                        break
            if found==False:    #if url is not in downloadInfo.json, add it!
                count+=1
                downloadInfo["data"].append(element)
             
        proposingStructures=list()
        for key in proposingStructuresDict.keys():
            newStructure=dict()
            newStructure["name"]=proposingStructuresDict[key]
            newStructure["vatId"]=key
            proposingStructures.append(newStructure)
        elapsed = (timeit.default_timer() - start_time) /60  
        print ("Added %s new links from ANAC dataset in %s seconds" %(count, elapsed))
        #Write proposingStructures.json 
        fOut = open(PROPOSING_STRUCTURES_FILE, 'w', encoding='utf-8')       
        json.dump( proposingStructures, fOut, indent=4, ensure_ascii=False)      
        fOut.close()
   
    else:
        print("Your ANAC dataset is already up to date!")

        
    #update of datasets files
    try: 
        print("Looking for new contracts datasets...")
        nUrl=len(downloadInfo["data"])
        for dataset in downloadInfo["data"]:
            administrationId=""
            nUrlProcessed+=1
            if "CodiceFiscale" in dataset.keys():
                administrationId= re.sub(r'[^a-zA-Z0-9]', '', dataset["CodiceFiscale"]).upper()
            if codiceFiscaleCheck(administrationId)==False and "RagioneSociale" in dataset.keys():
                print("ERROR, administration ", dataset["RagioneSociale"], "has invalid fiscal id")
                administrationId=hashlib.sha1(dataset["RagioneSociale"].encode('utf-8')).hexdigest()
                dataset["CodiceFiscale"]=administrationId
            elif codiceFiscaleCheck(administrationId)==False:
                administrationId="INVALID"
                #print("ERROR, administration ", dataset["RagioneSociale"], "has invalid fiscal id nor demonimation")
            if "URL" in dataset.keys():
                if "files" not in dataset.keys():
                    dataset["files"]=[]    
                nXmlFiles+=downloadAllIndexedDatasets(dataset["URL"], administrationId, dataset["files"])
        print ("Downloaded or updated %s xml datasets" %nXmlFiles)
        perCent=(nUrlProcessed/nUrl)*100
        print("Processed %s url in ANAC dataset %s %%" %(nUrlProcessed, perCent)) 
        print("Writing final downloadInfo.json. DO NOT TERMINATE NOW to avoid database corruption!")
        #write downloadInfo.json 
        fOut = open(INFO_FILE, 'w', encoding='utf-8')       
        json.dump(downloadInfo, fOut, indent=4, ensure_ascii=False, sort_keys=True)      
        fOut.close()
    except KeyboardInterrupt:
        print()
        #clear any downloaded data for dataset where interrupt was called 
        if "files" in dataset.keys():
            dataset["files"]=[]
        if "RagioneSociale" in dataset.keys():
            print("KEYBOARD INTERRUPT: while checking "+dataset["RagioneSociale"])
        else:
            print("KEYBOARD INTERRUPT")
        perCent=(nUrlProcessed/nUrl)*100
        print("Processed %s url in ANAC dataset %s %%" %(nUrlProcessed, perCent)) 
        print("Writing final downloadInfo.json")
        print("DO NOT TERMINATE NOW to avoid database corruption!")
        print("please wait...")
        fOut = open(INFO_FILE, 'w', encoding='utf-8')       
        json.dump(downloadInfo, fOut, indent=4, ensure_ascii=False, sort_keys=True)      
        fOut.close()
        elapsed = (timeit.default_timer() - start_time)/60
        print ("Downloaded or updated %s xml datasets" %nXmlFiles)
        print("process terminated after %s minutes" %elapsed)
    except:
        print()
        print("UNKNOWN ERROR IN checkUpdates()! writing errrorDownloadInfo.json")
        fOut = open(DOWN_DIR+"errorDownloadInfo.json", 'w', encoding='utf-8')       
        json.dump(downloadInfo, fOut, indent=4, ensure_ascii=False, sort_keys=True)      
        fOut.close()

def addDataset(url, pIva, nome):
    try: 
        fIn=open(PROPOSING_STRUCTURES_FILE, 'r')
        proposingStructures=json.load(fIn)
        fIn.close()
    except Exception:
        print("GENERAL ERROR: proposing structure file reading error!")
    try: 
        fIn=open(INFO_FILE, 'r')
        downloadInfo=json.load(fIn)
        fIn.close()
    except Exception:
        print("GENERAL ERROR: download downloadInformation.json is corrupted!")
        return False
    newDataset=dict()
    newDataset
    newDataset["CodiceFiscale"]= pIva
    newDataset["DataAggiornamento"]= ""
    newDataset["DataUltimoTentativoAccessoUrl"]= ""
    newDataset["EsitoUltimoTentativoAccessoUrl"]= "MANUALE"
    newDataset["IdentificativoPEC"]=""
    newDataset["RagioneSociale"]= nome
    newDataset["URL"]=url
    downloadInfo["data"].append(newDataset)

    found=False
    for structure in proposingStructures:
        if structure["vatId"]==pIva: 
            found=True
    newStructure=dict()
    newStructure["name"]=nome
    newStructure["vatId"]=pIva
    if found==False: 
        proposingStructures.append(newStructure)
        fOut = open(PROPOSING_STRUCTURES_FILE, 'w', encoding='utf-8')       
        json.dump( proposingStructures, fOut, indent=4, ensure_ascii=False)      
        fOut.close()
    
    
    fOut = open(INFO_FILE, 'w', encoding='utf-8')       
    json.dump(downloadInfo, fOut, indent=4, ensure_ascii=False, sort_keys=True)      
    fOut.close()

def removeDataset(pIva):
    try: 
        fIn=open(INFO_FILE, 'r')
        downloadInfo=json.load(fIn)
        fIn.close()
    except Exception:
        print("GENERAL ERROR: download downloadInformation.json is corrupted!")
        return False
    for element in downloadInfo["data"]:
            if "CodiceFiscale" in element.keys(): 
                if element["CodiceFiscale"]==pIva:
                    downloadInfo["data"].remove(element)
                    print ("removed")

    
    fOut = open(INFO_FILE, 'w', encoding='utf-8')       
    json.dump(downloadInfo, fOut, indent=4, ensure_ascii=False, sort_keys=True)      
    fOut.close()
    
    
    

""" returns  two float values from http header:
[Content-Length,  Last-Modified]
dates are converted into a float which expresses time since the point where the time starts
WARNING! Value may change on different systems!
Following date format are supported 
    Sun, 06 Nov 1994 08:49:37 GMT  ; RFC 822, updated by RFC 1123
    Sunday, 06-Nov-94 08:49:37 GMT ; RFC 850, obsoleted by RFC 1036
    Sun Nov  6 08:49:37 1994       ; ANSI C's asctime() format
in case of error or if a field absent, it has value -1 """   
def checkUrl(url):
    result=[-1, -1]
    try:
        socket.setdefaulttimeout(TIMEOUT)
        f=urllib.request.urlopen(url)
        length=f.getheader("Content-Length", default="")
        lastUpdate=f.getheader("Last-Modified", default="")
    except (urllib.error.URLError, urllib.error.HTTPError, urllib.error.ContentTooShortError) as err:
        #print("CheckUrl ERROR: %s unaccessible for: %s " %( url, str(err)))
        length=""
        lastUpdate=""
    except Exception:
        #print("CheckUrl ERROR while opening %s Unknown error!!!" %url)
        length=""
        lastUpdate=""
        #print(str(sys.exc_info()))
        
    try:
        result[0]=int(length)
    except Exception:
        pass
    try:
        result[1]=time.mktime(email.utils.parsedate(lastUpdate))
    except Exception:
        pass
    return result


if __name__ == '__main__':
    checkUpdates("http://dati.anticorruzione.it/data/L190.json")


    
  
    #input("press enter to exit")
  
