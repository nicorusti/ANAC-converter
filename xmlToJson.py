from xml.dom.minidom import parse
import xml.dom.minidom
import json
import sys
import os
import hashlib
#from  xml.parsers.expat import ExpatError
import re
from difflib import SequenceMatcher
from operator import itemgetter

#strings of procedure types and roles according to xsd schema 
PROCTYPES        =['01-PROCEDURA APERTA',
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
ROLES =['01-MANDANTE', '02-MANDATARIA', '03-ASSOCIATA', '04-CAPOGRUPPO',  '05-CONSORZIATA']

#------------------------------TENDER DATA/METADATA PARSING FUNCTIONS-------------------------------------------

#returns a  dictionary for a single company (which may be a bidder or a winner)
#dictionary  has entry participant['type']="partecipante"  or participant['type']="aggiudicatario"
#if company has an invalid partita Iva or Codice Fiscale, the hash participant['companyHash'] is added based on "ragioneSociale"
#if company has nor a ragioneSociale nor a valid vatId, None is returned
def companyParse(membro, tipoAzienda, metrics):
    participant=dict()
    hasFiscalId=False
    participant['type']=tipoAzienda
    if checkDataTag(membro.getElementsByTagName("ragioneSociale")):
        participant['ragioneSociale']=membro.getElementsByTagName("ragioneSociale")[0].childNodes[0].data
        if len(participant['ragioneSociale'])>1:
            metrics['companyName']['nValid']+=1
        else:
            metrics['companyName']['nInvalid']+=1
    else:
        metrics['companyName']['nAbsent']+=1
        #print("PARSE ERROR:  "+tipoAzienda + " company name not found!")
        
        
    if checkDataTag(membro.getElementsByTagName("codiceFiscale")): 
        participant['codiceFiscale']=toUpperAlfanumeric (membro.getElementsByTagName("codiceFiscale")[0].childNodes[0].data)
        hasFiscalId=codiceFiscaleCheck(participant['codiceFiscale'])
        if hasFiscalId==True:
            metrics['companyCF']['nValid']+=1
        else:
            metrics['companyCF']['nInvalid']+=1
        if len(re.sub(r'[^0-9]', '', participant['codiceFiscale']))==11:   #if vatId is a partitaIva, clear also literals
            participant['codiceFiscale']=re.sub(r'[^0-9]', '', participant['codiceFiscale'])
    if checkDataTag(membro.getElementsByTagName("identificativoFiscaleEstero")):
        participant['identificativoFiscaleEstero']=toUpperAlfanumeric(membro.getElementsByTagName("identificativoFiscaleEstero")[0].childNodes[0].data)
        metrics['companyCF']['nValid']+=1
        hasFiscalId=True
    if hasFiscalId==False:
        metrics['companyCF']['nAbsent']+=1
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
def companyGroupParse(group, tipoAzienda, metrics):
    membri=group.getElementsByTagName("membro")
    raggruppamentoObj=dict()
    raggruppamentoObj["type"]=tipoAzienda
    groupParticipantObj=[]
    for membro in membri:
        participant=dict()
        hasFiscalId=False
        if checkDataTag(membro.getElementsByTagName("ragioneSociale")):
            participant['ragioneSociale']=membro.getElementsByTagName("ragioneSociale")[0].childNodes[0].data
            if len(participant['ragioneSociale'])>1:
                metrics['companyName']['nValid']+=1
            else:
                metrics['companyName']['nInvalid']+=1
        else:
            metrics['companyName']['nAbsent']+=1
            #print("PARSE ERROR: "+tipoAzienda + " company name not found!")
        if checkDataTag(membro.getElementsByTagName("ruolo")):
            #check compliance of ruolo with XSD schema 
            ruolo=membro.getElementsByTagName("ruolo")[0].childNodes[0].data
            participant['ruolo']=mostSimilarRole(ruolo)
            if ruolo!= participant['ruolo']:
                metrics['role']['nInvalid']+=1
                participant['ruoloOriginal']=ruolo
                #print("PARSE ERROR: role not compliant to XSD schema")
            else:
                metrics['role']['nValid']+=1
        else:
            metrics['role']['nAbsent']+=1
            #print("PARSE ERROR: "+tipoAzienda + " company role in a group not found!")
        if checkDataTag(membro.getElementsByTagName("codiceFiscale")): 
            participant['codiceFiscale']=toUpperAlfanumeric (membro.getElementsByTagName("codiceFiscale")[0].childNodes[0].data)
            hasFiscalId=codiceFiscaleCheck(participant['codiceFiscale'])
            if hasFiscalId==True:
                metrics['companyCF']['nValid']+=1
            else:
                metrics['companyCF']['nInvalid']+=1
            if len(re.sub(r'[^0-9]', '', participant['codiceFiscale']))==11:   #if vatId is a partitaIva, clear also literals
                participant['codiceFiscale']=re.sub(r'[^0-9]', '', participant['codiceFiscale'])
        if checkDataTag(membro.getElementsByTagName("identificativoFiscaleEstero")):
            participant['identificativoFiscaleEstero']=membro.getElementsByTagName("identificativoFiscaleEstero")[0].childNodes[0].data
            metrics['companyCF']['nValid']+=1
            hasFiscalId=True
        if hasFiscalId==False:
            metrics['companyCF']['nAbsent']+=1
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
    metrics=metricsInit()
    outFileDict=dict()
    lotti=rootNode.getElementsByTagName("lotto")    
    if (lotti.length!=0):
        for lotto in lotti:
            gara = dict()
            error=dict()
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
                            metrics['proposingStructureCF']['nInvalid']+=1
                        else:
                            metrics['proposingStructureCF']['nValid']+=1
                    else:
                        metrics['proposingStructureCF']['nAbsent']+=1
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
                if len(gara['oggetto'])>1:
                    metrics['tenderObject']['nValid']+=1
                else:
                    metrics['tenderObject']['nInvalid']+=1
            else:
                metrics['tenderObject']['nAbsent']+=1
                #print ("PARSE ERROR: oggetto (tender description)  not found!")


            #READ COMPLETION TIME (optional fields)
            if len(lotto.getElementsByTagName("tempiCompletamento"))!=0:
                tempoCompletamento=lotto.getElementsByTagName("tempiCompletamento")[0]
                completionTimeObj=dict()
                if checkDataTag(tempoCompletamento.getElementsByTagName("dataInizio")):
                    completionTimeObj['dataInizio']=toDate(tempoCompletamento.getElementsByTagName("dataInizio")[0].childNodes[0].data)
                    if dateCheck(completionTimeObj['dataInizio'])== False:
                        metrics['startDate']['nInvalid']+=1
                    else:
                        metrics['startDate']['nValid']+=1
                else:
                    metrics['startDate']['nAbsent']+=1
                if checkDataTag(tempoCompletamento.getElementsByTagName("dataUltimazione")):
                    completionTimeObj['dataUltimazione']=toDate(tempoCompletamento.getElementsByTagName("dataUltimazione")[0].childNodes[0].data)
                    if dateCheck(completionTimeObj['dataUltimazione'])==False:
                        metrics['endDate']['nInvalid']+=1
                    else:
                        metrics['endDate']['nValid']+=1
                else:
                    metrics['endDate']['nAbsent']+=1
                gara['tempiCompletamento']=completionTimeObj


            #READ AWARDED PRICE (optional field)
            awardedPrice=0
            if checkDataTag(lotto.getElementsByTagName("importoAggiudicazione")):
                gara['importoAggiudicazione']=toAmount(lotto.getElementsByTagName("importoAggiudicazione")[0].childNodes[0].data)
                try:
                    awardedPrice=float(gara['importoAggiudicazione'])
                    metrics['awardedPrice']['nValid']+=1
                except:
                    awardedPrice=0
                    metrics['awardedPrice']['nInvalid']+=1
                metrics['awardedPrice']['totalAmount']+=awardedPrice
            else:
                metrics['awardedPrice']['nAbsent']+=1
            
            #READ PAID AMOUNT (optional field)
            paidPrice=0
            if checkDataTag(lotto.getElementsByTagName("importoSommeLiquidate")):
                gara['importoSommeLiquidate']=toAmount(lotto.getElementsByTagName("importoSommeLiquidate")[0].childNodes[0].data)
                try:
                    paidPrice=float(gara['importoSommeLiquidate'])
                    metrics['paidPrice']['nValid']+=1
                except:
                    paidPrice=0
                    metrics['paidPrice']['nInvalid']+=1
                metrics['paidPrice']['totalAmount']+=paidPrice
            else:
                metrics['paidPrice']['nAbsent']+=1


            #READ TENDER AWARD PROCEDURE
            if checkDataTag(lotto.getElementsByTagName("sceltaContraente")):
                sceltaContraente=lotto.getElementsByTagName("sceltaContraente")[0].childNodes[0].data
                gara['sceltaContraente']=mostSimilarProcedure(sceltaContraente)
                metrics[gara['sceltaContraente']]['totalAwardedPrice']+=awardedPrice
                metrics[gara['sceltaContraente']]['totalPaidPrice']+=paidPrice
                
                ##check compliance of award procedure with XSD schema 
                if gara['sceltaContraente']!=sceltaContraente:
                    gara['sceltaContraenteOriginal']=sceltaContraente
                    metrics[gara['sceltaContraente']]['nInvalid']+=1
                    #print("PARSE ERROR: award procedure (sceltaContraente) not compliant to XSD schema")
                else:
                    metrics[gara['sceltaContraente']]['nValid']+=1
                    
            else:
                metrics[gara['unknownProcType']]['nValid']+=1
                metrics[gara['unknownProcType']]['totalAwardedPrice']+=awardedPrice
                metrics[gara['unknownProcType']]['totalPaidPrice']+=paidPrice
                #print ("PARSE ERROR: sceltaContraente tender award procedure  not found!")


            #READ TENDER WINNER    
            aggiudicatari=lotto.getElementsByTagName("aggiudicatari")
            if len(aggiudicatari)!=0: 
                aggiudicatariObj=[]
                aggiudicatariSingoli=aggiudicatari[0].getElementsByTagName("aggiudicatario")
                for aggiudicatario in aggiudicatariSingoli:
                    aggiudicatarioObj=companyParse(aggiudicatario, "aggiudicatario", metrics)
                    if aggiudicatarioObj!=None:
                        aggiudicatariObj.append(aggiudicatarioObj)
                        metrics['single']['nWinners']+=1
                        metrics['single']['totalAwardedPrice']+=awardedPrice
                        metrics['single']['totalPaidPrice']+=paidPrice
                    
                aggiudicatariRaggruppamenti=aggiudicatari[0].getElementsByTagName("aggiudicatarioRaggruppamento")
                for aggiudicatarioRaggruppamento in aggiudicatariRaggruppamenti:
                    aggiudicatarioRaggruppamentoObj=companyGroupParse(aggiudicatarioRaggruppamento, "aggiudicatarioRaggruppamento", metrics)
                    if aggiudicatarioRaggruppamentoObj!=None:
                        aggiudicatariObj.append(aggiudicatarioRaggruppamentoObj)
                        metrics['group']['nWinners']+=1
                        metrics['group']['totalAwardedPrice']+=awardedPrice
                        metrics['group']['totalPaidPrice']+=paidPrice
                gara['aggiudicatari']=aggiudicatariObj

                #if no valid bidder is found, key "aggiudicatari" is removed
                if len(gara['aggiudicatari'])==0:            
                    del gara['aggiudicatari']
                    #print ("PARSE ERROR: no tender winners found!")
            else:
                print ("PARSE ERROR: no tender winners found!")

           
            #READ BIDDER TO TENDER  
            partecipanti=lotto.getElementsByTagName("partecipanti")
            partecipantiObj=[]
            if len(partecipanti)!=0:
                partecipantiSingoli=partecipanti[0].getElementsByTagName("partecipante")                                                                        
                for partecipante in partecipantiSingoli:
                    partecipanteObj=companyParse(partecipante, "partecipante", metrics)
                    if partecipanteObj!= None:
                        metrics['single']['nParticipants']+=1
                        partecipantiObj.append(partecipanteObj)             

                raggruppamenti=partecipanti[0].getElementsByTagName("raggruppamento")              
                for raggruppamento in raggruppamenti:
                    raggruppamentoObj=companyGroupParse(raggruppamento, "raggruppamento", metrics)
                    if raggruppamentoObj!=None:
                        partecipantiObj.append(raggruppamentoObj)
                        metrics['group']['nParticipants']+=1
            gara['partecipanti']=partecipantiObj
                
             
            #READ, VALIDATE CIG, EVENTUALLY ADD AN HASH IF CIG IS INVALID
            if checkDataTag(lotto.getElementsByTagName("cig")):     
                gara['cig']=toUpperAlfanumeric(lotto.getElementsByTagName("cig")[0].childNodes[0].data)
                gara['cigValid']=cigCheck(gara['cig'])
            else:
                gara['cigValid']=False
                metrics['cig']['nAbsent']+=1
                
            if gara['cigValid']==False:
                metrics['cig']['nInvalid']+=1
                gara['cigHash']=cigHash(gara)
                #print("PARSE ERROR: invalid cig: "+gara['cig']+ " hashed with "+gara['cigHash'] )
            else:
                metrics['cig']['nValid']+=1
                
            #ADD HASH TO EACH GROUP (used for URI minting in triplification)
            groupHash(gara)

            #CHECK AND ADD WINNER TO BIDDERS (if not present)
            if 'aggiudicatari' in gara.keys(): 
                addWinnerToBidders(gara['partecipanti'], gara['aggiudicatari'], metrics)
            #if no valid bidder is found, key "partecipanti" is removed
            if len(gara['partecipanti'])==0:            
                    del gara['partecipanti']
                    #print ("PARSE ERROR: no bidders nor winners found to tender!")

            
            #appends a tender to the list of tenders
            tenders.append(gara)

            
            
        print ("trovati ", metrics['nLotti'], "lotti")
        lottiObj=dict()
        lottiObj["lotto"]=tenders
        outFileDict['metrics']=metrics
        outFileDict['data']=lottiObj
    else:
        print ("PARSE ERROR: lotti information not found!")
    return outFileDict

#returns a dictionary containing all metadata
#if some fields are not found, they are ignored and not added to the dictionary
def metadataToObject(rootNode, metadataType):
    metadataObj=dict()
    if len(rootNode.getElementsByTagName("metadata"))!=0: 
        metadata=rootNode.getElementsByTagName("metadata")[0]   #controlla!!!!! TODO TODO 
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


#returnd a list of dictionaries with dataset link and date.
#if no link is present, datased is discarded 
def indexDataToObject(rootNode):
    datasets=rootNode.getElementsByTagName("dataset")
    datasetObj=[]
    if datasets.length!=0:
        for dataset in datasets:
            datasetDict=dict()
            if checkDataTag(dataset.getElementsByTagName("dataUltimoAggiornamento")):   
                datasetDict["dataUltimoAggiornamento"]=dataset.getElementsByTagName("dataUltimoAggiornamento")[0].childNodes[0].data 
            if checkDataTag(dataset.getElementsByTagName("linkDataset")): 
                datasetDict["linkDataset"]=dataset.getElementsByTagName("linkDataset")[0].childNodes[0].data
                datasetObj.append(datasetDict)
            
    return datasetObj

#------------------------------DATA CHECK, CORRECTION, HASHING FUNCTIONS, METRICS INITIALIZATON-------------------------------------------
#initialize all the metrics for a single xml file 
def metricsInit():
    metrics=dict()
    metrics['nLotti']=0
    metrics['nWinnerNotParticipant']=0
    metrics['single']=dict()
    metrics['single']['nParticipants']=0
    metrics['single']['nWinners']=0
    metrics['single']['totalAwardedPrice']=0
    metrics['single']['totalPaidPrice']=0
    metrics['group']=dict()
    metrics['group']=metrics['single'].copy()

    fields=['cig', 'startDate', 'endDate', 'proposingStructureCF', 'awardedPrice', 'paidPrice', 'role', 'companyCF', 'companyName','tenderObject']
    for field in fields:
        metrics[field]=dict()
        metrics[field]['nValid']=0
        metrics[field][ 'nAbsent']=0
        metrics[field]['nInvalid']=0
    metrics['awardedPrice']['totalAmount']=0
    metrics['paidPrice']['totalAmount']=0
    for procedure in PROCTYPES: 
        metrics[procedure]=dict()
        metrics[procedure]['totalAwardedPrice']=0
        metrics[procedure]['totalPaidPrice']=0
        metrics[procedure]['nValid']=0
        metrics[procedure]['nInvalid']=0
    metrics['unknownProcType']=dict()    
    metrics['unknownProcType']['totalAwardedPrice']=0
    metrics['unknownProcType']['totalPaidPrice']=0
    metrics['unknownProcType']['nValid']=0   
    return metrics


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
def addWinnerToBidders(partecipanti, aggiudicatari, metrics):
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
                metrics['nWinnerNotParticipant']+=1
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
                metrics['nWinnerNotParticipant']+=1
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
    count=string.count("+")-1
    string=string.replace('+','',count)
    string=string.split( "+")[0]
    string=string.replace("/", "-") 
    string=string.replace('--','-')
    result = []
    #print("before", [char for char in string])
    for char in string:
        if (char.isdigit() or char=='-'):
            result.append(char)
        elif char == "\\":
            result.append(char)
        else:
            result.extend({
                "\12": ["\\", "12"],
                "\0": ["\\", "0"],
                "\1": ["\\", "1"],
                "\10": ["\\", "10"],
                "\11": ["\\", "11"],
                "\12": ["\\", "12"],
                "\2": ["\\", "2"],
                "\3": ["\\", "3"],
                "\4": ["\\", "4"],
                "\5": ["\\", "5"],
                "\6": ["\\", "6"],
                "\7": ["\\", "7"],
                "\20": ["\\", "20"],
                "\200": ["\\", "200"],
                "\201": ["\\", "201"],
                "\202": ["\\", "202"],
            }.get(char, ""))
        #print("cur", result)
    #print("after", result)
    result = "".join(result).replace("\\", "-")
    result = [x for x in result.split("-")]
    result = "-".join(result)
    result=result.replace('--','-')
    #string=re.sub(r'[^-0-9]', '', string)
    return result
    
#returns a string, from the xsd schema, of the most similar role to the given one
def mostSimilarRole(string):
    similarity=[]
    for ruolo in ROLES:
        similarity.append([-SequenceMatcher(None, string.upper(), ruolo).ratio(), ruolo])
    similarity=sorted(similarity, key=itemgetter(0))
    return similarity[0][1]

#returns a string, from the xsd schema, of the most similar procedure to the given one
def mostSimilarProcedure(string):
    similarity=[]
    for procedure in PROCTYPES:
        similarity.append([-SequenceMatcher(None, string.upper(), procedure).ratio(), procedure])
    similarity=sorted(similarity, key=itemgetter(0))
    return similarity[0][1]


#------------------------------FILE  MANAGEMENT-------------------------------------------  

#writes the parsed contracts filename.xml into filename.json
#Existing filename.json file is overwritten
def dataXmlToJson(fIn):
    print("converting ", fIn, "to json")
    base = os.path.splitext(fIn)[0]
    fOutName = base+".json"
    f = open(fOutName, 'w', encoding='utf-8')    
    try:
        DOMTree=xml.dom.minidom.parse(fIn)
    except:
        print("ERRORE generico nel parsing di "+ fIn+" , il file .json è stato creato vuoto" )
        #TO DO return control for parsing dictionary
    legge190=DOMTree.documentElement
    pubblicazione=dict()
    pubblicazione=lottiToObject(legge190)
    if len(pubblicazione["data"])==0:
        pubblicazione.pop("data", None)
    pubblicazione["metadata"]=metadataToObject(legge190, "contractsMetadata")
    if len(pubblicazione["metadata"])==0:
        pubblicazione.pop("metadata", None)
    json.dump(pubblicazione, f, indent=4, ensure_ascii=False, sort_keys=True)
    f.close()
    print ("file ", fOutName, "creato correttamente")


#funzione che scrive il file di indice dei contratti in formato json, più un file downloadInfo.json con informazioni sul download del file 
def indexXmlToJson(fIn, writeFile):
    print("converting ", fIn, "to json")
    
    pubblicazione=dict()
    try: 
        DOMTree=xml.dom.minidom.parse(fIn)
    except:
        print("ERRORE generico nel parsing di "+ fIn+" , il file .json è stato creato vuoto" )
        return pubblicazione
    
    legge190=DOMTree.documentElement    
    pubblicazione["metadata"]=metadataToObject(legge190, "indexMetadata" )
    if len(pubblicazione["metadata"])==0:
        pubblicazione.pop("metadata", None)
    pubblicazione["indice"]=indexDataToObject(legge190)
    if len(pubblicazione["indice"])==0:
        pubblicazione.pop("indice", None)

    if writeFile==True: 
        try:
            base = os.path.splitext(fIn)[0]
            fOutName = base+".json"
            print("converting ", fIn, "to ", fOutName)
            f = open(fOutName, 'w', encoding='utf-8')
            json.dump(pubblicazione, f, indent=4)
            f.close()
            print ("file ", fOutName,  "creato correttamente")
        except:
            print ("ERRORE: file ", fOutName, "non creato")
        #return [fOutName, indexInfoFileName, re.sub(r'[^0-9]', '', indexData['metadata']['annoRiferimento']), indexData['metadata']['entePubblicatore'],]
    return pubblicazione

def toJson(fIn):
    xmlReadable=False
    try:
        legge190=xml.dom.minidom.parse(fIn).documentElement
        xmlReadable=True
    except:
        print("ERROR, ", fIn, " unreadable! There may be errors in xml structure, or file is nonexixtent!")
    if xmlReadable==True: 
        dataset=legge190.getElementsByTagName("dataset")
        lotto=legge190.getElementsByTagName("lotto")
        if len(dataset)!=0:
            indexXmlToJson(fIn, True)
        elif len(lotto)!=0:
            dataXmlToJson(fIn)
        else:
            print("error ", fIn, " doesn't contain valid fields")




            
def main ():
    #decommentare per elaborare  un file già presente in locale, nella stessa cartella dove si trova lo script
    #il file può essere sia di indice che un dataset di bandi
    toJson("polito2012.xml")   


main()


