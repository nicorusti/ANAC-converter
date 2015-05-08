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


#LOCAL FILES PATHS. CHANGE ONLY BEFORE FIRST EXECUTION!
DOWN_DIR="download/"
ANAC_FILE=DOWN_DIR+"datasetANAC.json"
INFO_FILE=DOWN_DIR+"downloadInfo.json"
PROPOSING_STRUCTURES_FILE=DOWN_DIR+"proposingStructures.json"
TEMP_DIR=DOWN_DIR+"temp/"
XML_SUBDIR="xml/"

#for a correctly downloaded and parseable file, sets the time (in seconds) after which header
#is checked again for updates
#1 day= 86400
HEADER_CHECK_INTERVAL=86400*3
    

#download file from remote to local,
#return True if download successful,otherwise return a String with error message
def download(remote, local):
    try:
        #add http:// if not present  (otherwise urllib raises Exception!)
        if len( urllib.parse.urlparse(remote).scheme)==0:
           remote = "http://"+remote
        u = urllib.request.urlopen(remote)
        h = u.info()
        try: 
            totalSize = int(h["Content-Length"])
            totalSizeKB=totalSize/1024
        except Exception:
            totalSizeKB = "unknown Size"
            totalSize=0
        urllib.request.urlretrieve(remote, local)


        if totalSize!=os.stat(local).st_size and totalSize!=0:
            return "Downloaded file size different from http header size"
    except urllib.error.URLError as err:
        return str(err)
    except urllib.error.HTTPError as err:
        return str(err)
    except urllib.error.ContentTooShortError as err:
        return str(err)
    except Exception:
        return "Unknown error"
    return True


"""
check and eventually updates a single dataset
dataset file is replaced with downloaded one if: 
    -in http header, last update field or content size field are bigger than previously stored value
    -if http header has none of these fields, if downloaded file is bigger
    -"downlaoded" field was not true due to some previous errors
    -file is new 

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

            
    if toBeUpdated==True:
        print()
        print("Downloading", url)
        fileHash=hashlib.sha1(url.encode('utf-8')).hexdigest()
        fileInfo["fileName"]=fileHash+".xml"
        xmlFileTempPath=TEMP_DIR+fileInfo["fileName"]
        fileInfo["downloaded"]=download(url, xmlFileTempPath)
        fileInfo['URL']=url
        fileInfo["lastDownloadTry"]=time.mktime(time.gmtime())
        if headerChecked==False: 
            httpInfo=checkUrl(url)
            fileInfo["lastHeaderCheck"]=time.mktime(time.gmtime())
        fileInfo["sizeServer"]=httpInfo[0]
        fileInfo["lastUpdateServer"]=httpInfo[1]
        previouslyConverted=False
        if "convertedToJson" in fileInfo.keys():
            previouslyConverted=fileInfo["convertedToJson"]
        fileInfo["convertedToJson"]=False
        if fileInfo["downloaded"]==True:
            try: 
                fileInfo["sizeLocal"]=os.stat(xmlFileTempPath).st_size
            except Exception:
                fileInfo["sizeLocal"]=-2
        else:
            print(str(fileInfo["downloaded"]))
        try:
            legge190=xml.dom.minidom.parse(xmlFileTempPath).documentElement
            fileInfo["parseable"]=True
        except Exception:
            fileInfo["parseable"]=False
            fileInfo["type"]="unknown"
        if fileInfo["parseable"]==True:
            try: 
                indiceContent=legge190.getElementsByTagName("dataset")
                lotti=legge190.getElementsByTagName("lotto")
                if len(indiceContent)!=0:
                    fileInfo["type"]="index"
                    fileInfo["fileName"]=fileHash+"_index.xml"
                elif len(lotti)!=0:
                    fileInfo["type"]="data"
                else:
                    fileInfo["type"]="unknown"
            except Exception:
                fileInfo["type"]="unknown"
                
        if fileInfo["downloaded"]==True and (fileInfo["parseable"]==False or fileInfo["type"]=="unknown"):
            print("Not L.190 xml standard")
                
        #create definitive directory download/CF_istituzione/
        defInstitutionDirectory =DOWN_DIR+administrationId+"/"+XML_SUBDIR 
        if  os.path.exists(defInstitutionDirectory)==False:
            os.makedirs(defInstitutionDirectory) 
            
        #move file to destination directory
        xmlFileDefPath =defInstitutionDirectory+fileInfo["fileName"]
        if fileInfo["downloaded"]==True:
            if httpInfo[0]==-1 and   httpInfo[1]==-1:
                if os.path.exists(xmlFileDefPath)==True and os.path.exists(xmlFileTempPath)==True:
                    if os.stat(xmlFileTempPath).st_size<os.stat(xmlFileDefPath).st_size:
                         os.remove(xmlFileTempPath)
                         fileInfo["convertedToJson"]=previouslyConverted
                    else: 
                         os.rename(xmlFileTempPath, xmlFileDefPath)
            else:
                try: 
                    os.remove(xmlFileDefPath)
                except Exception:
                    pass
        
                
                if os.path.exists(xmlFileDefPath)==True:
                    os.remove(xmlFileDefPath)
                try: 
                    os.rename(xmlFileTempPath, xmlFileDefPath)
                except Exception:
                    fileInfo["downloaded"]==False
                return True
        #erase temp file if not downloaded correctly 
        if os.path.exists(xmlFileTempPath)==True:
            os.remove(xmlFileTempPath)    
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
                    updated=updateSingleDataset(dataset["linkDataset"], newFileInfo, administrationId)
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
    proposingStructures= set()
    httpInfo=checkUrl(urlANAC)
    if downloadInfo["sizeServer"]<httpInfo[0] or downloadInfo["lastUpdateServer"]<httpInfo[1] or os.path.isfile(ANAC_FILE)==False or( httpInfo[0]==-1 and   httpInfo[1]==-1):
        print("Updating ANAC dataset... may take 2-3 min.")
        downloadInfo["URL"]=urlANAC
        downloadInfo["sizeServer"]=httpInfo[0]
        downloadInfo["lastUpdateServer"]=httpInfo[1]
        downloadInfo["donwloaded"]=download(urlANAC, ANAC_FILE)
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
                    proposingStructures.add(element["CodiceFiscale"])
            found=False
            for dataset in downloadInfo["data"]:
                if "URL" in dataset.keys() and "URL" in element.keys():
                    if dataset["URL"]==element["URL"]:
                        found=True
                        break
            if found==False:    #if url is not in downloadInfo.json, add it!
                count+=1
                downloadInfo["data"].append(element)
        elapsed = (timeit.default_timer() - start_time) /60       
        print ("Added %s new links from ANAC dataset in %s seconds" %(count, elapsed))         

        #Write proposingStructures.json 
        fOut = open(PROPOSING_STRUCTURES_FILE, 'w', encoding='utf-8')       
        json.dump( list(proposingStructures), fOut, indent=4, ensure_ascii=False)      
        fOut.close()

        
    else:
        print("Your ANAC dataset is already up to date!")
        
    #update of datasets files
    try: 
        print("Looking for new contracts datasets...")
        for dataset in downloadInfo["data"]:
            administrationId=""
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
        print("Writing final downloadInfo.json. DO NOT TERMINATE NOW to avoid database corruption!")
        #write fileInfo.json 
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
