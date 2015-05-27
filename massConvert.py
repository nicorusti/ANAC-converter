from xmlToJson import toJson
from download import INFO_FILE
from download import DOWN_DIR
from download import XML_SUBDIR
from xmlToJson import PROCTYPES
import re
import os
import json
from collections import Counter
import timeit

DOWNLOAD_STATS="downloadStats.json"
JSON_SUBDIR="json/"
STATS_FILE="stats.json"

def main():
    convertAll()
    #stats()
    #aggregatedStats()
    
    #reset()
    input("press enter to exit")

def aggregatedStats():
    print("computing aggregated download stats.... ")
    stats=dict()
    stats["nDataset"]=0
    stats["nParseableDataset"]=0
    stats["downloadErrors"]=dict()
    stats["nSuccessAnacLink"]=0
    stats["nFailAnacLink"]=0

    try: 
        fIn=open(INFO_FILE, 'r')
        downloadInfo=json.load(fIn)
        fIn.close()
    except Exception:
        print("GENERAL ERROR: download downloadInformation.json is corrupted!")
        return

    #compute stats about information by ANAC and your information abopud dataset parseability
    try: 
        for mainDataset in downloadInfo["data"]:
            cf= mainDataset["CodiceFiscale"]
            if mainDataset["EsitoUltimoTentativoAccessoUrl"] not in stats.keys():
                stats[mainDataset["EsitoUltimoTentativoAccessoUrl"]]=1
            else: 
                stats[mainDataset["EsitoUltimoTentativoAccessoUrl"]]+=1
            if len(mainDataset["files"])>0: 
                if len(mainDataset["files"])>1 or mainDataset["files"][0]["parseable"]==True:
                    stats["nSuccessAnacLink"]+=1
                else:
                    stats["nFailAnacLink"]+=1
            else: 
                stats["nFailAnacLink"]+=1
                
            if mainDataset["CodiceFiscale"] not in mainDataset.keys():
                stats[cf]=dict()
                stats[cf]["nDataset"]=0
                stats[cf]["nParseableDataset"]=0

            for file in mainDataset["files"]:
                stats["nDataset"]+=1
                stats[cf]["nDataset"]+=1
                #print (file)
                if file["parseable"]==True:
                    stats[mainDataset["CodiceFiscale"]]["nParseableDataset"]+=1
                    stats["nParseableDataset"]+=1
                error=file["downloaded"]
                if error!=True: 
                    if "HTTP Error" in error:
                        error=error[:14]
                    if "urlopen error" in error:
                        error=error[15:]
                    if "timed out" in error:
                        error="timed out"

                    if error not in stats["downloadErrors"].keys():
            
                        stats["downloadErrors"][error]=1
                    else:
                        stats["downloadErrors"][error]+=1
        for cf in stats.keys():
            if not cf.isalpha() and " " not in cf: 
                correctness=computeCorrectness(DOWN_DIR+cf+"/"+STATS_FILE)
                stats[cf]["nValidFields"]=correctness[0]
                stats[cf]["nTotalFields"]=correctness[1]
        correctness=computeCorrectness(DOWN_DIR+STATS_FILE)
        stats["nValidFields"]=correctness[0]
        stats["nTotalFields"]=correctness[1]
    except Exception:
        print (Exception)
        print(mainDataset)
    fOut = open(DOWN_DIR+DOWNLOAD_STATS, 'w', encoding='utf-8')       
    json.dump(stats, fOut, indent=4, ensure_ascii=False, sort_keys=True)      
    fOut.close()

    #returns total number of correct fields / wrong or missing fields in stats.json
def computeCorrectness(filePath):
    nValidFields=0
    nTotalFields=0
    try: 
        fIn=open(filePath, 'r')
        stats=json.load(fIn)
        fIn.close()
    except Exception:
        #print(filePath, " not found")
        return [0, 0]
    for proctype in PROCTYPES:
        if proctype in stats.keys(): 
            nTotalFields+=stats[proctype]["nValid"]+stats[proctype]["nInvalid"]
            nValidFields+=stats[proctype]["nValid"]
    nTotalFields+=stats["unknownProcType"]["nValid"]
    fields=['cig',  'proposingStructureCF', 'awardedPrice', 'paidPrice', 'role', 'companyCF', 'companyName','tenderObject']
    for field in fields:
        if field in stats.keys(): 
            nTotalFields+=stats[field]["nValid"]+stats[field]["nInvalid"]+stats[field]["nAbsent"]
            nValidFields+=stats[field]["nValid"]
    optFields=['startDate', 'endDate']
    for field in optFields:
        if field in stats.keys(): 
            nTotalFields+=stats[field]["nValid"]+stats[field]["nInvalid"]
            nValidFields+=stats[field]["nValid"]
    return [nValidFields,nTotalFields]

def reset():
    try: 
        fIn=open(INFO_FILE, 'r')
        downloadInfo=json.load(fIn)
        fIn.close()
    except Exception:
        print("GENERAL ERROR: download informations json is corrupted or absent!")
    print ("resetting...")
    nLoop=0
    for dataset in downloadInfo["data"]:
        nLoop+=1
        if "files"  in dataset.keys():
            for file in dataset["files"]:
                
                if "convertedToJson" in file.keys():
                    file["convertedToJson"]=False
                    file["convertedToRdf"]=False

            
    fOut = open(INFO_FILE, 'w', encoding='utf-8')       
    json.dump(downloadInfo, fOut, indent=4, ensure_ascii=False, sort_keys=True)      
    fOut.close()
                       

    
"""
batch converts all the xml files according if they were not converted before.
If "convertedToJson"==False in INFO_FILE, dataset is converted
press CTRL+c safely interrupts conversion 
"""
def convertAll():
    dataset=dict()
    nXmlFiles=0
    previousFile=dict()
    start_time = timeit.default_timer()
    try: 
        fIn=open(INFO_FILE, 'r')
        downloadInfo=json.load(fIn)
        fIn.close()
    except Exception:
        print("GENERAL ERROR: download informations json is corrupted or absent!")
        return False

    try: 
        for dataset in downloadInfo["data"]:
            if "CodiceFiscale" in dataset.keys():
                administrationId= re.sub(r'[^a-zA-Z0-9]', '', dataset["CodiceFiscale"]).upper()
                if "files"  in dataset.keys():
                    previousFile=dataset["files"].copy()
                    for file in dataset["files"]:
                        if "downloaded" in file.keys():
                            alreadyParsed=False
                            if "convertedToJson" in file.keys():
                                alreadyParsed=file["convertedToJson"]
                            parseable=True
                            if "parseable" in file.keys():
                                parseable=file["parseable"]
                                alreadyParsed=file["convertedToJson"]
                            if file["downloaded"]==True and alreadyParsed==False and parseable==True: 
                                xmlFileName=DOWN_DIR+administrationId+"/"+XML_SUBDIR+file["fileName"]
                                jsonPath=DOWN_DIR+administrationId+"/"+JSON_SUBDIR
                                if  os.path.exists(jsonPath)==False:
                                    os.makedirs(jsonPath) 
                                try: 
                                    file["convertedToJson"]=toJson(xmlFileName, jsonPath)
                                    if file["convertedToJson"]==True:
                                        file["convertedToRdf"]=False 
                                    nXmlFiles+=1
                                    if (nXmlFiles%1000)==0:
                                        print("Converted ", nXmlFiles, " datasets")
                                except Exception:
                                    print("exception raised in convertAll()")
                                    file["convertedToRdf"]=False 
                                    file["convertedToJson"]=False
                                    file["parseable"]=False
    except KeyboardInterrupt:
        print()
        #restore previous file list if interrupt was called 
        if "files" in dataset.keys():
            dataset["files"]=previousFile               
        if "RagioneSociale" in dataset.keys():
            print("KEYBOARD INTERRUPT: while converting "+dataset["RagioneSociale"])
        else:
            print("KEYBOARD INTERRUPT")
        print("Writing final downloadInfo.json")
        print("DO NOT TERMINATE NOW to avoid database corruption!")
        print("please wait...")
        fOut = open(INFO_FILE, 'w', encoding='utf-8')       
        json.dump(downloadInfo, fOut, indent=4, ensure_ascii=False, sort_keys=True)      
        fOut.close()
        elapsed = (timeit.default_timer() - start_time)/60
        print ("Converted %s xml datasets" %nXmlFiles)
        print("process terminated after %s minutes" %elapsed)
        return False 

    print("Writing final downloadInfo.json")
    print("DO NOT TERMINATE NOW to avoid database corruption!")
    print("please wait...")
    fOut = open(INFO_FILE, 'w', encoding='utf-8')       
    json.dump(downloadInfo, fOut, indent=4, ensure_ascii=False, sort_keys=True)      
    fOut.close()
    elapsed = (timeit.default_timer() - start_time)/60
    print ("Converted %s xml datasets" %nXmlFiles)
    print("process terminated after %s minutes" %elapsed)    

    return True
    
"""
saves in each public administration folder a file stats.json with the sum of all metrics in the administration's file
furthermore, in download directory, saves another stats.json with sum of stats for all institutions
Field "nDataset" is added, and expresses number of data datasets published. 
"""
def stats():
    print("Computing stats... DO NOT INTERRUPT NOW")
    start_time = timeit.default_timer()
    globalStats=Counter()
    globalStats["nContractsDatasets"]=0
    administrationIds=os.listdir(DOWN_DIR)
    for administrationId in administrationIds:
        if os.path.isfile(DOWN_DIR+administrationId)==False:
            if  os.path.exists(DOWN_DIR+administrationId+"/"+JSON_SUBDIR)==True:
                jsonFileList=os.listdir(DOWN_DIR+administrationId+"/"+JSON_SUBDIR)
                nDatasetAdministration=0
                administrationStats=Counter()
                for jsonFileName in jsonFileList:
                    if os.path.isfile(DOWN_DIR+administrationId+"/"+JSON_SUBDIR+jsonFileName):
                        #try:
                        try: 
                            fIn=open(DOWN_DIR+administrationId+"/"+JSON_SUBDIR+jsonFileName, 'r',encoding='utf-8' )
                            dataset=json.load(fIn)
                            fIn.close()
                        except Exception:
                            print("problem opening "+DOWN_DIR+administrationId+"/"+JSON_SUBDIR+jsonFileName)
                        if "metrics" in dataset.keys():
                            administrationStats["nContractsDatasets"]+=1
                            globalStats["nContractsDatasets"]+=1
                            for key in dataset["metrics"].keys():
                                if isinstance(dataset["metrics"][key], dict):
                                    if administrationStats[key]==0:
                                        administrationStats[key]=Counter()
                                    if globalStats[key]==0:
                                        globalStats[key]=Counter()
                                    globalStats[key].update(Counter(dataset["metrics"][key]))    
                                    administrationStats[key].update(Counter(dataset["metrics"][key]))
                                if isinstance(dataset["metrics"][key], int ):
                                    administrationStats.update(Counter({key :  dataset["metrics"][key]}))
                                    globalStats.update(Counter({key :  dataset["metrics"][key]}))
                        '''except Exception:
                            print(Exception)
                            print("exeption raised in stats")
                        pass'''
                        
                fOut = open(DOWN_DIR+administrationId+"/"+STATS_FILE, 'w', encoding='utf-8')       
                json.dump(administrationStats, fOut, indent=4, ensure_ascii=False, sort_keys=True)      
                fOut.close()

    fOut = open(DOWN_DIR+STATS_FILE, 'w', encoding='utf-8')       
    json.dump(globalStats, fOut, indent=4, ensure_ascii=False, sort_keys=True)      
    fOut.close()
    elapsed = (timeit.default_timer() - start_time)/60
    print("stats computed in %s minutes" %elapsed)     

def createBusinessEntities():

    start_time = timeit.default_timer()
    try: 
        fIn=open(INFO_FILE, 'r')
        downloadInfo=json.load(fIn)
        fIn.close()
    except Exception:
        print("GENERAL ERROR: download informations json is corrupted or absent!")
        return False
    companies=dict()
    try: 
        for dataset in downloadInfo["data"]:
            if "CodiceFiscale" in dataset.keys():
                administrationId= re.sub(r'[^a-zA-Z0-9]', '', dataset["CodiceFiscale"]).upper()
                if "files"  in dataset.keys():
                    for file in dataset["files"]:
                        if "convertedToJson" in file.keys() and "downloaded"  in file.keys():
                            if file["downloaded"]==True and file["convertedToJson"]==True:
                                xmlFileName=DOWN_DIR+administrationId+"/"+XML_SUBDIR+file["fileName"]
                                jsonPath=DOWN_DIR+administrationId+"/"+JSON_SUBDIR
                                if  os.path.exists(jsonPath)==True:
                                    try: 
                                        fIn=open(INFO_FILE, 'r')
                                        contractFile=json.load(fIn)
                                        fIn.close()
                                    except Exception:
                                        pass
                                    for lotto in contractFile["data"]["lotto"] :
                                        for partecipante in lotto["partecipati"]:
                                            if "raggruppamento" in partecipante.keys():
                                                for member in partecipante["raggruppamento"]:
                                                    if "companyHash" in member.keys():
                                                        vatId=member["companyHash"]
                                                        ###continua 
                                        
                                    


    except Exception:
        print("errore")
                                                                
                                    







    


main()
