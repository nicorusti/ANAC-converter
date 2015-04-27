from xml.dom.minidom import parse
import xml.dom.minidom
import json
import sys
import urllib.request
import urllib.parse
import os
import hashlib
from  xml.parsers.expat import ExpatError
import re
from difflib import SequenceMatcher
from operator import itemgetter

#------------------------------TENDER DATA/METADATA PARSING FUNCTIONS-------------------------------------------

#returns a  dictionary for a single company (which may be a bidder or a winner)
#dictionary  has entry participant['type']="partecipante"  or participant['type']="aggiudicatario"
#if company has an invalid partita Iva or Codice Fiscale, the hash participant['companyHash'] is added based on "ragioneSociale"
#if company has nor a ragioneSociale nor a valid vatId, None is returned
def companyParse(membro, tipoAzienda):
    participant=dict()
    hasFiscalId=False
    participant['type']=tipoAzienda
    if checkDataTag(membro.getElementsByTagName("ragioneSociale")):
        participant['ragioneSociale']=membro.getElementsByTagName("ragioneSociale")[0].childNodes[0].data
    else:
        print("PARSE ERROR:  "+tipoAzienda + " company name not found!")
    if checkDataTag(membro.getElementsByTagName("codiceFiscale")): 
        participant['codiceFiscale']=toUpperAlfanumeric (membro.getElementsByTagName("codiceFiscale")[0].childNodes[0].data)
        hasFiscalId=codiceFiscaleCheck(participant['codiceFiscale'])
        if len(re.sub(r'[^0-9]', '', participant['codiceFiscale']))==11:   #if vatId is a partitaIva, clear also literals
            participant['codiceFiscale']=re.sub(r'[^0-9]', '', participant['codiceFiscale'])
    if checkDataTag(membro.getElementsByTagName("identificativoFiscaleEstero")):
        participant['identificativoFiscaleEstero']=toUpperAlfanumeric(membro.getElementsByTagName("identificativoFiscaleEstero")[0].childNodes[0].data)
        hasFiscalId=True
    if hasFiscalId==False:
        #print("PARSE ERROR:  "+tipoAzienda + " company fiscal id not found!")
        if 'ragioneSociale' in participant.keys():
            participant["companyHash"]=hashlib.sha1(participant['ragioneSociale'].upper().encode('utf-8')).hexdigest()
        else:
            #print("PARSE ERROR:  "+tipoAzienda + " nor VatId nor Denominazione found")
            return None
    return participant


        
#returns a list of dictionaries for a group of companies (Associazione Temporanea d'Impresa / consorzio)
#each dictionary has the entry participant['type']="raggruppamento"  or participant['type']="aggiudicatarioRaggruppamento"
#if company has an invalid partita Iva or Codice Fiscale, the hash participant['companyHash'] is added based on "ragioneSociale"
#if company has nor a ragioneSociale nor a valid vatId, it is not added to group
#if group has no companies, None is returned
#if participant has role NOT complying with AVCP xsd schema, the most similar role is inserted
#the original role string is preserved under participant['ruoloOriginal']
def companyGroupParse(group, tipoAzienda):
    membri=group.getElementsByTagName("membro")
    raggruppamentoObj=dict()
    raggruppamentoObj["type"]=tipoAzienda
    groupParticipantObj=[]
    for membro in membri:
        participant=dict()
        hasFiscalId=False
        if checkDataTag(membro.getElementsByTagName("ragioneSociale")):
            participant['ragioneSociale']=membro.getElementsByTagName("ragioneSociale")[0].childNodes[0].data
        else:
            print("PARSE ERROR: "+tipoAzienda + " company name not found!")
        if checkDataTag(membro.getElementsByTagName("ruolo")):
            #check compliance of ruolo with XSD schema 
            ruolo=membro.getElementsByTagName("ruolo")[0].childNodes[0].data
            participant['ruolo']=mostSimilarRole(ruolo)
            if ruolo!= participant['ruolo']:
                participant['ruoloOriginal']=ruolo
                #print("PARSE ERROR: role not compliant to XSD schema")
        else:
            print("PARSE ERROR: "+tipoAzienda + " company role in a group not found!")
        if checkDataTag(membro.getElementsByTagName("codiceFiscale")): 
            participant['codiceFiscale']=toUpperAlfanumeric (membro.getElementsByTagName("codiceFiscale")[0].childNodes[0].data)
            hasFiscalId=codiceFiscaleCheck(participant['codiceFiscale'])
            if len(re.sub(r'[^0-9]', '', participant['codiceFiscale']))==11:   #if vatId is a partitaIva, clear also literals
                participant['codiceFiscale']=re.sub(r'[^0-9]', '', participant['codiceFiscale'])
        if checkDataTag(membro.getElementsByTagName("identificativoFiscaleEstero")):
            participant['identificativoFiscaleEstero']=membro.getElementsByTagName("identificativoFiscaleEstero")[0].childNodes[0].data
            hasFiscalId=True
        if hasFiscalId==False:
            #print("PARSE ERROR: "+tipoAzienda+" company fiscal id not found!")
            if 'ragioneSociale' in participant.keys():
                participant["companyHash"]=hashlib.sha1(participant['ragioneSociale'].upper().encode('utf-8')).hexdigest()
                groupParticipantObj.append(participant)
            else:
                #print("PARSE ERROR:  "+tipoAzienda + " nor VatId nor Denominazione found")
                return None
        else: 
            groupParticipantObj.append(participant)
    if len(groupParticipantObj)!=0: 
        raggruppamentoObj[tipoAzienda]=groupParticipantObj
        return raggruppamentoObj
    else:
        return None

        
                    

#returns a list of dictionaries containing all information about tenders
#if some fields are not found, they are ignored and not added to the list/dictionary
def lottiToObject(rootNode):
    tenders =[]
    metrics=dict()
    metrics['nLotti']=0
    metrics['nLotti']=0



    
    lotti=rootNode.getElementsByTagName("lotto")
    
    if (lotti.length!=0):
        for lotto in lotti:
            gara = dict()
            metrics['nLotti']+=1
            
            #READING PROPOSING AUTHORITY(IES) INFORMATION
            proposingStructureList=[]
            struttureProponenti=lotto.getElementsByTagName("strutturaProponente")
            if len(struttureProponenti)!=0:             
                for strutturaProponente in struttureProponenti:
                    proposingStructureObj=dict()
                    if checkDataTag(strutturaProponente.getElementsByTagName("codiceFiscaleProp")): 
                        proposingStructureObj['codiceFiscaleProp']=toUpperAlfanumeric(strutturaProponente.getElementsByTagName("codiceFiscaleProp")[0].childNodes[0].data)
                        if codiceFiscaleCheck(proposingStructureObj['codiceFiscaleProp'])==False:
                            print ("PARSE ERROR: proposing Structure codiceFiscale not valid!")
                    else:
                        print ("PARSE ERROR: proposing Structure codiceFiscale not found!")
                    if checkDataTag(strutturaProponente.getElementsByTagName("denominazione")): 
                        proposingStructureObj['denominazione']=strutturaProponente.getElementsByTagName("denominazione")[0].childNodes[0].data
                    else: 
                        print ("PARSE ERROR: proposing Structure name not found!")
                    proposingStructureList.append(proposingStructureObj)
                gara['strutturaProponente']=proposingStructureList
            else:
                print ("PARSE ERROR: proposing Structure information not found!")
            
            #READ TENDER OBJECT
            if checkDataTag(lotto.getElementsByTagName("oggetto")):
                gara['oggetto']=lotto.getElementsByTagName("oggetto")[0].childNodes[0].data
            else:
                print ("PARSE ERROR: oggetto (tender description)  not found!")


            #READ TENDER AWARD PROCEDURE
            if checkDataTag(lotto.getElementsByTagName("sceltaContraente")):
                sceltaContraente=lotto.getElementsByTagName("sceltaContraente")[0].childNodes[0].data
                gara['sceltaContraente']=mostSimilarProcedure(sceltaContraente)
                ##check compliance of award procedure with XSD schema 
                if gara['sceltaContraente']!=sceltaContraente:
                    gara['sceltaContraenteOriginal']=sceltaContraente
                    print("PARSE ERROR: award procedure (sceltaContraente) not compliant to XSD schema")
            else:
                print ("PARSE ERROR: sceltaContraente tender award procedure  not found!")


            #READ COMPLETION TIME (optional fields)
            if len(lotto.getElementsByTagName("tempiCompletamento"))!=0:
                tempoCompletamento=lotto.getElementsByTagName("tempiCompletamento")[0]
                completionTimeObj=dict()
                if checkDataTag(tempoCompletamento.getElementsByTagName("dataInizio")):
                    completionTimeObj['dataInizio']=toDate(tempoCompletamento.getElementsByTagName("dataInizio")[0].childNodes[0].data)
                    if dateCheck(completionTimeObj['dataInizio'])== False:
                        a= None 
                if checkDataTag(tempoCompletamento.getElementsByTagName("dataUltimazione")):
                    completionTimeObj['dataUltimazione']=toDate(tempoCompletamento.getElementsByTagName("dataUltimazione")[0].childNodes[0].data)
                    if dateCheck(completionTimeObj['dataUltimazione'])==False:
                        a= None  
                gara['tempiCompletamento']=completionTimeObj


            #READ AGREED PRICE (optional field) 
            if checkDataTag(lotto.getElementsByTagName("importoAggiudicazione")):
                gara['importoAggiudicazione']=toAmount(lotto.getElementsByTagName("importoAggiudicazione")[0].childNodes[0].data)               
            
            #READ PAID AMOUNT (optional field)
            if checkDataTag(lotto.getElementsByTagName("importoSommeLiquidate")):
                gara['importoSommeLiquidate']=toAmount(lotto.getElementsByTagName("importoSommeLiquidate")[0].childNodes[0].data)

            #READ TENDER WINNER    
            aggiudicatari=lotto.getElementsByTagName("aggiudicatari")
            if len(aggiudicatari)!=0: 
                aggiudicatariObj=[]
                aggiudicatariSingoli=aggiudicatari[0].getElementsByTagName("aggiudicatario")
                for aggiudicatario in aggiudicatariSingoli:
                    aggiudicatarioObj=companyParse(aggiudicatario, "aggiudicatario")
                    if aggiudicatarioObj!=None:
                        aggiudicatariObj.append(aggiudicatarioObj)
                    
                aggiudicatariRaggruppamenti=aggiudicatari[0].getElementsByTagName("aggiudicatarioRaggruppamento")
                for aggiudicatarioRaggruppamento in aggiudicatariRaggruppamenti:
                    aggiudicatarioRaggruppamentoObj=companyGroupParse(aggiudicatarioRaggruppamento, "aggiudicatarioRaggruppamento")
                    if aggiudicatarioRaggruppamentoObj!=None:
                        aggiudicatariObj.append(aggiudicatarioRaggruppamentoObj)
                gara['aggiudicatari']=aggiudicatariObj

                #if no valid bidder is found, key "aggiudicatari" is removed
                if len(gara['aggiudicatari'])==0:            
                    del gara['aggiudicatari']
                    print ("PARSE ERROR: no tender winners found!")
            else:
                print ("PARSE ERROR: no tender winners found!")

           
            #READ BIDDER TO TENDER  
            partecipanti=lotto.getElementsByTagName("partecipanti")
            partecipantiObj=[]
            if len(partecipanti)!=0:
                partecipantiSingoli=partecipanti[0].getElementsByTagName("partecipante")                                                                        
                for partecipante in partecipantiSingoli:
                    partecipanteObj=companyParse(partecipante, "partecipante")
                    if partecipanteObj!= None:
                        
                        partecipantiObj.append(partecipanteObj)             

                raggruppamenti=partecipanti[0].getElementsByTagName("raggruppamento")              
                for raggruppamento in raggruppamenti:
                    raggruppamentoObj=companyGroupParse(raggruppamento, "raggruppamento")
                    if raggruppamentoObj!=None:
                        partecipantiObj.append(raggruppamentoObj)
            gara['partecipanti']=partecipantiObj
                
             
            #READ, VALIDATE CIG, EVENTUALLY ADD AN HASH IF CIG IS INVALID
            if checkDataTag(lotto.getElementsByTagName("cig")):     
                gara['cig']=toUpperAlfanumeric(lotto.getElementsByTagName("cig")[0].childNodes[0].data)
                gara['cigValid']=cigCheck(gara['cig'])
            else:
                gara['cigValid']=False
                
            if gara['cigValid']==False:         
                gara['cigHash']=cigHash(gara)
                print("PARSE ERROR: invalid cig: "+gara['cig']+ " hashed with "+gara['cigHash'] )
                
            #ADD HASH TO EACH GROUP (used for URI minting in triplification)
            groupHash(gara)

            #ADD WINNER TO BIDDERS (if not present)
            if 'aggiudicatari' in gara.keys(): 
                addWinnerToBidders(gara['partecipanti'], gara['aggiudicatari'])
            #if no valid bidder is found, key "partecipanti" is removed
            if len(gara['partecipanti'])==0:            
                    del gara['partecipanti']
                    print ("PARSE ERROR: no bidders nor winners found to tender!")


            
            #appends a tender to the list of tenders
            tenders.append(gara)

            
            
        print ("trovati ", metrics['nLotti'], "lotti")
        lottiObj=dict()
        lottiObj["lotto"]=tenders
        outFileDict=dict()
        outFileDict['metrics']=metrics
        outFileDict['data']=lottiObj
        return outFileDict
    else:
        print ("PARSE ERROR: lotti information not found!")
        return ""

#returns a dictionary containing all metadata
#if some fields are not found, they are ignored and not added to the dictionary
def metadataToObject(rootNode, metadataType):
    if len(rootNode.getElementsByTagName("metadata"))!=0: 
        metadata=rootNode.getElementsByTagName("metadata")[0]
        metadataObj=dict()
        #NOTE: the xml files, according to AVCP xsd schema, have the tag "dataPubbicazioneDataset"
        #it is wrong according to Italian grammar, but there is really the field  "Pubbicazione"
        if metadataType=="indexMetadata":
            compulsoryMetadataFields=['dataPubblicazioneDataset', 'entePubblicatore','annoRiferimento', 'urlFile']
            optionalMetadataFields=['titolo', 'abstract','dataUltimoAggiornamentoDataset', 'licenza']
        if metadataType=="contractsMetadata":
            optionalMetadataFields=['titolo', 'abstract','dataUltimoAggiornamentoIndice', 'licenza']
            compulsoryMetadataFields=['dataPubbicazioneDataset', 'entePubblicatore','annoRiferimento', 'urlFile']
            
        #read optional metadata fields 
        for metadataField in optionalMetadataFields:
            if checkDataTag(metadata.getElementsByTagName(metadataField)): 
                content=metadata.getElementsByTagName(metadataField)[0].childNodes[0].data
                metadataObj[metadataField]=content

        #read compulsory metadata fields
        for metadataField in compulsoryMetadataFields:
            if checkDataTag(metadata.getElementsByTagName(metadataField)): 
                content=metadata.getElementsByTagName(metadataField)[0].childNodes[0].data
                metadataObj[metadataField]=content
            else:
                metadataObj[metadataField]=""
                print ("PARSE ERROR: no "+metadataField+" found!")
        metadataObj['annoRiferimento']=re.sub(r'[^0-9]', '', metadataObj['annoRiferimento'])
    else:
         print ("PARSE ERROR: no metadata found!")   
    return metadataObj


#funzione che ritorna un oggetto con i dati del file di indice
def indexDataToObject(rootNode):
    datasets=rootNode.getElementsByTagName("dataset")
    datasetObj=[]
    if datasets.length!=0:
        for dataset in datasets:
            datasetDict=dict()
            datasetDict["linkDataset"]=dataset.getElementsByTagName("linkDataset")[0].childNodes[0].data 
            datasetDict["dataUltimoAggiornamento"]=dataset.getElementsByTagName("dataUltimoAggiornamento")[0].childNodes[0].data 
            datasetObj.append(datasetDict)
    return datasetObj

#------------------------------DATA CHECK, CORRECTION, HASHING FUNCTIONS-------------------------------------------

#Check that a node contains some data
def checkDataTag (tag):
    if len(tag)!=0:
        try:
            tag[0].childNodes[0].data
            return True
        except:
            return False 
    return False

def dateCheck(dateStr):
    date=dateStr.split("-") 
    if int(date[0])<2999 and int(date[0])>1000 and int(date[1])<13 and int(date[1])>0 and int(date[2])<32 and int(date[2])>0: 
        return True
    else:
        return False 

#returns True in case of  compliance of codice fiscale / p.iva with Italian standards.
#returns False elsewhere, or if p.iva is "00000000000"
#REM: correspondence of last char (controlo code) with control code algorythm NOT done!
def codiceFiscaleCheck(cf):
    PATTERN = "^[A-Za-z]{6}[0-9]{2}([A-Ea-e]|[HLMPRSThlmprst])[0-9]{2}[A-Za-z][0-9]{3}[A-Za-z]$"
    if re.match(PATTERN, cf)!=None:
        return True
    else:
        partitaIva=re.sub(r'[^0-9]', '', cf)
        if len(partitaIva)==11 and partitaIva!= "00000000000":
            return True 
        return False


def cigCheck (cig):
    return (cig.isalnum()and len(cig)==10 and cig!="0000000000")

#checks wether winner is also a bidder. If not, winner is added to participants. 
def addWinnerToBidders(partecipanti, aggiudicatari):
    for aggiudicatario in aggiudicatari: #case of a single winner
        winnerId=""
        winnerPresent=False 
        if aggiudicatario['type']== "aggiudicatario":
            if 'companyHash' in aggiudicatario.keys():
                winnerId=aggiudicatario['companyHash']
            else:
                if 'codiceFiscale' in aggiudicatario.keys():
                    winnerId=aggiudicatario['codiceFiscale']
                if 'identificativoFiscaleEstero' in aggiudicatario.keys():
                    winnerId=aggiudicatario['identificativoFiscaleEstero']
            for partecipante in partecipanti:
                bidderId=""
                if partecipante['type']== "partecipante":
                    if 'companyHash' in partecipante.keys():
                        bidderId=partecipante['companyHash']
                    else:
                        if 'codiceFiscale' in partecipante.keys():
                            bidderId=partecipante['codiceFiscale']
                        if 'identificativoFiscaleEstero' in partecipante.keys():
                            bidderId=partecipante['identificativoFiscaleEstero']
                if bidderId==winnerId:
                    winnerPresent=True
            if winnerPresent==False:
                newParticipant=aggiudicatario.copy()
                newParticipant['type']="partecipante"
                partecipanti.append(newParticipant)

           

        if aggiudicatario['type']== "aggiudicatarioRaggruppamento":
            if 'groupHash' in aggiudicatario.keys():
                winnerId=aggiudicatario['groupHash']
            for partecipante in partecipanti:

                bidderId=""
                if partecipante['type']== "raggruppamento":
                    if 'groupHash' in partecipante.keys():
                        bidderId=partecipante['groupHash']
                if bidderId==winnerId:
                    winnerPresent=True
            if winnerPresent==False:
                newParticipant=aggiudicatario.copy()
                newParticipant['type']="raggruppamento"
                newParticipant["raggruppamento"]=newParticipant["aggiudicatarioRaggruppamento"]
                del newParticipant["aggiudicatarioRaggruppamento"]
                partecipanti.append(newParticipant)


                

#returns a sha1 hexadecimal string hash in cases in which cig is not present. Hash based on: 
def cigHash (gara):
    cigHashBase=""
    vatIdList=[]
    if 'strutturaProponente' in gara.keys(): 
        if (len(gara['strutturaProponente'])>0):
            if 'codiceFiscaleProp' in gara['strutturaProponente'][0].keys(): 
                cigHashBase+=gara['strutturaProponente'][0]['codiceFiscaleProp']    #proposing structure fiscal id
    if 'importoAggiudicazione' in gara.keys():                                      #agreed price 
        cigHashBase+=gara['importoAggiudicazione']
    if 'sceltaContraente' in gara.keys():                                           #tender award procedure
        cigHashBase+=gara['sceltaContraente']
    if 'aggiudicatari' in gara.keys():                                              #winner(s) vat Id (ordered)
        for aggiudicatario in gara['aggiudicatari']:
            if aggiudicatario['type']=="aggiudicatario":
                if 'codiceFiscale' in aggiudicatario.keys():
                    vatIdList.append(aggiudicatario['codiceFiscale'])
                if 'identificativoFiscaleEstero' in aggiudicatario.keys():
                    vatIdList.append(aggiudicatario['identificativoFiscaleEstero'])
            if aggiudicatario['type']=='aggiudicatarioRaggruppamento':
                for membro in  aggiudicatario['aggiudicatarioRaggruppamento']:
                    if 'codiceFiscale' in membro.keys():
                        vatIdList.append(membro['codiceFiscale'])
                    if 'identificativoFiscaleEstero' in membro.keys():
                        vatIdList.append(membro['identificativoFiscaleEstero'])

    vatIdList.sort()
    for vatId in vatIdList:
        cigHashBase+=vatId                 
    return hashlib.sha1(cigHashBase.encode('utf-8')).hexdigest()

#adds a sha1 hexadecimal string hash to the groups
#hash is based on cig/cig Hash and on ordered vat id of group members 
def groupHash(gara):
    if gara['cigValid']==True:
        cigId=gara['cig']
    else:
        cigId=gara['cigHash']
    if 'aggiudicatari' in gara.keys():                                              
        for aggiudicatario in gara['aggiudicatari']:
            if aggiudicatario!=None: 
                if aggiudicatario['type']=='aggiudicatarioRaggruppamento':
                    vatIdList=[]
                    for membro in  aggiudicatario['aggiudicatarioRaggruppamento']:
                        if 'codiceFiscale' in membro.keys():
                            vatIdList.append(membro['codiceFiscale'])
                        if 'identificativoFiscaleEstero' in membro.keys():
                            vatIdList.append(membro['identificativoFiscaleEstero'])
                    vatIdList.sort()
                    groupHashBase=cigId
                    for vatId in vatIdList:
                        groupHashBase+=vatId                 
                    aggiudicatario['groupHash']=hashlib.sha1(groupHashBase.encode('utf-8')).hexdigest()

                
    if 'partecipanti' in gara.keys():                                              
        for partecipante in gara['partecipanti']:
            if partecipante!= None: 
                if partecipante['type']=='raggruppamento':
                    vatIdList=[]
                    for membro in  partecipante['raggruppamento']:
                        if 'codiceFiscale' in membro.keys():
                            vatIdList.append(membro['codiceFiscale'])
                        if 'identificativoFiscaleEstero' in membro.keys():
                            vatIdList.append(membro['identificativoFiscaleEstero'])
                    vatIdList.sort()
                    groupHashBase=cigId
                    for vatId in vatIdList:
                        groupHashBase+=vatId                 
                    partecipante['groupHash']=hashlib.sha1(groupHashBase.encode('utf-8')).hexdigest()
                    #print(partecipante['groupHash'])
                   

#clear any non alfanumeric char from a string
#return cleared string
def toUpperAlfanumeric (string):
    return re.sub(r'[^a-zA-Z0-9]', '', string).upper()

#clear any non numeric part, convert "," to "." and leave only last occurrency of "."
#return cleared string
def toAmount(string):
    string=re.sub(r'[^,.0-9]', '', string)
    string=re.sub(r',', '.', string)
    count=string.count(".")-1
    string=string.replace('.','',count)
    return string

#clear any non allowed char by xsd:date, cut timezone information 
def toDate(string):
    #string=string.decode('unicode').encode('ascii', 'replace')
    #print (bytes(string, 'ascii'))
    #print (string.encode())
    #string=repr(string).replace("\\", "-")
    count=string.count("+")-1
    string=string.replace('+','',count)
    string=string.split( "+")[0]
    #string=string.replace('--','-')    
    #string=re.sub(r'[^-0-9]', '', string)
    return string
    
#returns a string, from the xsd schema, of the most similar role to the given one
def mostSimilarRole(string):
    ruoli =['01-MANDANTE', '02-MANDATARIA', '03-ASSOCIATA', '04-CAPOGRUPPO',  '05-CONSORZIATA']
    similarity=[]
    for ruolo in ruoli:
        similarity.append([-SequenceMatcher(None, string.upper(), ruolo).ratio(), ruolo])
    similarity=sorted(similarity, key=itemgetter(0))
    return similarity[0][1]

#returns a string, from the xsd schema, of the most similar procedure to the given one
def mostSimilarProcedure(string):
    procedures =['01-PROCEDURA APERTA',
                 '02-PROCEDURA RISTRETTA',
                 '03-PROCEDURA NEGOZIATA PREVIA PUBBLICAZIONE DEL BANDO',
                 '04-PROCEDURA NEGOZIATA SENZA PREVIA PUBBLICAZIONE DEL BANDO',
                 '05-DIALOGO COMPETITIVO',
                 '06-PROCEDURA NEGOZIATA SENZA PREVIA INDIZIONE DI  GARA ART. 221 D.LGS. 163/2006',
                 '07-SISTEMA DINAMICO DI ACQUISIZIONE',
                 '08-AFFIDAMENTO IN ECONOMIA - COTTIMO FIDUCIARIO',
                 '14-PROCEDURA SELETTIVA EX ART 238 C.7, D.LGS. 163/2006',
                 '17-AFFIDAMENTO DIRETTO EX ART. 5 DELLA LEGGE N.381/91',
                 '21-PROCEDURA RISTRETTA DERIVANTE DA AVVISI CON CUI SI INDICE LA GARA',
                 '22-PROCEDURA NEGOZIATA DERIVANTE DA AVVISI CON CUI SI INDICE LA GARA',
                 '23-AFFIDAMENTO IN ECONOMIA - AFFIDAMENTO DIRETTO',
                 "24-AFFIDAMENTO DIRETTO A SOCIETA' IN HOUSE",
                 "25-AFFIDAMENTO DIRETTO A SOCIETA' RAGGRUPPATE/CONSORZIATE O CONTROLLATE NELLE CONCESSIONI DI LL.PP",
                 '26-AFFIDAMENTO DIRETTO IN ADESIONE AD ACCORDO QUADRO/CONVENZIONE',
                 '27-CONFRONTO COMPETITIVO IN ADESIONE AD ACCORDO QUADRO/CONVENZIONE',  
                 '28-PROCEDURA AI SENSI DEI REGOLAMENTI DEGLI ORGANI COSTITUZIONALI',
                 ]
    similarity=[]
    for procedure in procedures:
        similarity.append([-SequenceMatcher(None, string.upper(), procedure).ratio(), procedure])
    similarity=sorted(similarity, key=itemgetter(0))
    return similarity[0][1]


#------------------------------FILE DOWNLOAD / MANAGEMENT-------------------------------------------  

#writes the parsed contracts filename.xml into filename.json
#Existing filename.json file is overwritten
def dataXmlToJson(fIn):
    print("converting ", fIn, "to json")
    base = os.path.splitext(fIn)[0]
    fOutName = base+".json"
    f = open(fOutName, 'w', encoding='utf-8')
    json.dump(parseXmlDataset(fIn), f, indent=4, ensure_ascii=False, sort_keys=True)
    f.close()
    print ("file ", fOutName, "creato correttamente")


#funzione che scrive il file di indice dei contratti in formato json, più un file downloadInfo.json con informazioni sul download del file 
def indexXmlToJson(fIn):
    print("converting ", fIn, "to json")
    try:
        if fIn.endswith('.xml'):
            fOutName= fIn[:-4]+".json"
            f = open(fOutName, 'w', encoding='utf-8')
        else:
            fOutName="defaultIndex.json"
            f = open(fOutName, 'w', encoding='utf-8')
        indexData=parseIndexDataset(fIn)
        json.dump(indexData, f, indent=4)
        f.close()
        
        
        indexInfoFileName="download/temp/downloadInfo.json"
        f = open(indexInfoFileName, 'w', encoding='utf-8')
        downloadInfo=indexData['indice']
        for dataset in downloadInfo:
            try: 
                dataset['anno']=re.sub(r'[^0-9]', '', indexData['metadata']['annoRiferimento'])
            except:
                dataset['anno']=""
        json.dump(downloadInfo, f, indent=4)
        f.close()
        
        print ("file ", fOutName,   " e " ,indexInfoFileName, "creato correttamente")
    except:
        print ("ERRORE: file ", fOutName, " e " ,indexInfoFileName, "non creati")
    return [fOutName, indexInfoFileName, re.sub(r'[^0-9]', '', indexData['metadata']['annoRiferimento']), indexData['metadata']['entePubblicatore'],]

#funzione che scrive il file dei dati dei contratti in formato json
def parseXmlDataset(fileName):
    pubblicazione=dict()
    try:
        DOMTree=xml.dom.minidom.parse(fileName)
        #exception raised in case of bad xml syntax
    except:
        print("ERRORE generico nel parsing di "+ fileName+" , il file .json è stato creato vuoto" )
        return pubblicazione
    legge190=DOMTree.documentElement
    pubblicazione=lottiToObject(legge190)
    if len(pubblicazione["data"])==0:
        pubblicazione.pop("data", None)
    pubblicazione["metadata"]=metadataToObject(legge190, "contractsMetadata")
    if len(pubblicazione["metadata"])==0:
        pubblicazione.pop("metadata", None)
   
    return pubblicazione

#funzione che ritorna un dizionario con dati e metadati del file di indice
def parseIndexDataset(fileName):
    pubblicazione=dict()
    try: 
        DOMTree=xml.dom.minidom.parse(fileName)
    except:
        print("ERRORE generico nel parsing di "+ fileName+" , il file .json è stato creato vuoto" )
        return pubblicazione 
    legge190=DOMTree.documentElement    
    pubblicazione["metadata"]=metadataToObject(legge190, "indexMetadata" )
    if len(pubblicazione["metadata"])==0:
        pubblicazione.pop("metadata", None)
    pubblicazione["indice"]=indexDataToObject(legge190)
    if len(pubblicazione["indice"])==0:
        pubblicazione.pop("indice", None)
    return pubblicazione




def download(url, filename):
    try:
        result=urllib.request.urlretrieve(url, filename)
        print (result[1])
    except urllib.error.URLError:
        print("error while downloading the file", url)
    except urllib.error.ContentTooShortError(msg, content):
        print ("error, data not fully downloaded")

    #scarica e parsifica, nel percorso download/ente_pubblicatore/anno
    # -->file di indice
    # -->tutti i dataset linkati nel file di indice
    #inoltre vi salva un file downloadInfo.json contenente informazioni sull'esito dei download e dei parsing 
def downloadAndParseEverything(url):
    if  os.path.exists("download/")==False:
        os.mkdir("download/") 
    xmlFileName = url.split('/')[-1].split('#')[0].split('?')[0]
    tempDirectory="download/temp/"
    xmlFileTempPath=tempDirectory+xmlFileName
    try:
        os.stat(tempDirectory)
    except:
        os.mkdir(tempDirectory)
    download(url, xmlFileTempPath)
    
    try:
          indexFileInfo=indexXmlToJson(xmlFileTempPath)
    except FileNotFoundError:
            print("errore, file ", xmlFileTempPath , "non parsificato")
            
    #creazione della directory definitive download/nome_istituzione/anno
    #XXXXXXX CHANGE!!!! Usa la p.iva presente nel dataset ANAC
    defInstitutionDirectory ="download/"+toUpperAlfanumeric(indexFileInfo[3])+"/"
    if  os.path.exists(defInstitutionDirectory)==False:
        os.mkdir(defInstitutionDirectory) 

    
    defDirectory =defInstitutionDirectory+indexFileInfo[2]+"/"
    i=0
    while os.path.exists(defDirectory)==True:
        i=i+1
        print("controllo di ", defDirectory)        
        defDirectory =defInstitutionDirectory+indexFileInfo[2]+"_"+str(i)+"/"
    os.mkdir(defDirectory)    
    #spostamento dei file nella directory definitive
    print("spostandi i file")
    xmlFileDefPath=defDirectory+xmlFileTempPath.split('/')[-1]
    jsonFileDefPath=defDirectory+indexFileInfo[0].split('/')[-1]
    downloadInfoFileDefPath=defDirectory+indexFileInfo[1].split('/')[-1]
    os.rename(xmlFileTempPath, xmlFileDefPath)
    os.rename(indexFileInfo[0], jsonFileDefPath)
    os.rename( indexFileInfo[1], downloadInfoFileDefPath)

    #lettura del file con le informazioni du download e parsing dei dataset
    f = open(downloadInfoFileDefPath, 'r')
    downloadInfo=json.loads(f.read())
    f.close()
    #downbload e parsing dei dataset linkati dal file di indice
    for dataset in downloadInfo:
        url=dataset['linkDataset']
        xmlDatasetFileName = url.split('/')[-1].split('#')[0].split('?')[0]
        xmlDatasetFilePath=defDirectory+xmlDatasetFileName
        try: 
            download(url, xmlDatasetFilePath)
            dataset['downloaded']="True"
        except:
            dataset['downloaded']="False"
        try:
            indexFileInfo=dataXmlToJson(xmlDatasetFilePath)
            dataset['parsed']="True"
        except:
            dataset['parsed']="False"
    f = open(downloadInfoFileDefPath, 'w', encoding='utf-8')       
    json.dump(downloadInfo, f, indent=4)
    f.close()

#trasforma in json file già presenti in locale nella stessa cartella dello script
    #ELIMINARE 
def getFileNameFromCommandLine():
    fileOk=False
    while fileOk== False: 
        try:
            indice=input('Inserire il nome del file di indice, invio per saltare\n' )
            if len(indice)!=0:
                indexXmlToJson(indice)
                fileOk=True
            else:
                fileOk=True 
        except FileNotFoundError:
            print("errore, file ", indice , "non trovato")

    fileOk=False
    while fileOk== False: 
        try:
            dati=input('Inserire il nome del file di dati, invio per saltare\n' )
            if len(dati)!=0:
                dataXmlToJson(dati)
                fileOk=True
            else:
                fileOk=True 
        except FileNotFoundError:
            print("errore, file ", indice , "non trovato")


            
def main ():
    #decommentare per elaborare file già presenti in locale, nella stessa cartella dove si trova lo script

    #getFileNameFromCommandLine()

    #decommentare per scaircare e parsificare tutti i file linkati dall'indice
    #downloadAndParseEverything("http://www.swas.polito.it/services/avcp/avcpIndice2013.xml")
    
    #decommentare per convertire in json un solo filename.xml presente nella stessa cartella dove si esegue il programma
    #dataXmlToJson("polito2012.xml")
    





main()


 
