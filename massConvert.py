from xmlToJson import toJson
from download import INFO_FILE
from download import DOWN_DIR
from download import XML_SUBDIR
import re
import os
import json
from collections import Counter

JSON_SUBDIR="json/"
STATS_FILE="stats.json"

def main():
    convertAll()
    stats()



def convertAll():
    try: 
        fIn=open(INFO_FILE, 'r')
        downloadInfo=json.load(fIn)
        fIn.close()
    except:
        print("GENERAL ERROR: download informations json is corrupted!")
        return False

    
    for dataset in downloadInfo["data"]:
        if "CodiceFiscale" in dataset.keys():
            administrationId= re.sub(r'[^a-zA-Z0-9]', '', dataset["CodiceFiscale"]).upper()
            if "files"  in dataset.keys():
                for file in dataset["files"]:
                    if "downloaded" in file.keys():
                        alreadyParsed=False
                        if "convertedToJson" in file.keys():
                            alreadyParsed=file["convertedToJson"]
                        if file["downloaded"]==True and alreadyParsed==False: 
                            xmlFileName=DOWN_DIR+administrationId+"/"+XML_SUBDIR+file["fileName"]
                            jsonPath=DOWN_DIR+administrationId+"/"+JSON_SUBDIR
                            if  os.path.exists(jsonPath)==False:
                                os.makedirs(jsonPath) 
                            try: 
                                file["convertedToJson"]=toJson(xmlFileName, jsonPath)
                            except:
                                file["convertedToJson"]=False
                                file["parseable"]=False

    fOut = open(INFO_FILE, 'w', encoding='utf-8')       
    json.dump(downloadInfo, fOut, indent=4, ensure_ascii=False, sort_keys=True)      
    fOut.close()
    
"""
saves in each public administration folder a file stats.json with the sum of all metrics in the administration's file
furthermore, in download directory, saves another stats.json with sum of stats for all institutions
Field "nDataset" is added, and expresses number of data datasets published. 
"""
def stats():
    globalStats=Counter()
    globalStats["nDatasets"]=0
    administrationIds=os.listdir(DOWN_DIR)
    for administrationId in administrationIds:
        if os.path.isfile(DOWN_DIR+administrationId)==False:
            if  os.path.exists(DOWN_DIR+administrationId+"/"+JSON_SUBDIR)==True:
                jsonFileList=os.listdir(DOWN_DIR+administrationId+"/"+JSON_SUBDIR)
                nDatasetAdministration=0
                administrationStats=Counter()
                for jsonFileName in jsonFileList:
                    if os.path.isfile(DOWN_DIR+administrationId+"/"+JSON_SUBDIR+jsonFileName):
                        try:
                            fIn=open(DOWN_DIR+administrationId+"/"+JSON_SUBDIR+jsonFileName, 'r',encoding='utf-8' )
                            dataset=json.load(fIn)
                            fIn.close()
                            if "metrics" in dataset.keys():
                                administrationStats["nDatasets"]+=1
                                globalStats["nDatasets"]+=1
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
                        except:
                            print("exeption raised in stats")
                            pass
                        
                fOut = open(DOWN_DIR+administrationId+"/"+STATS_FILE, 'w', encoding='utf-8')       
                json.dump(administrationStats, fOut, indent=4, ensure_ascii=False, sort_keys=True)      
                fOut.close()

    fOut = open(DOWN_DIR+STATS_FILE, 'w', encoding='utf-8')       
    json.dump(globalStats, fOut, indent=4, ensure_ascii=False, sort_keys=True)      
    fOut.close()
        









    


main()
