from xml.dom.minidom import parse
import xml.dom.minidom
import json
import sys

#funzione per lavorare con un membro di tipo singolo
def companyParse(membro, tipoAzienda):
    ragioneSociale=membro.getElementsByTagName("ragioneSociale")[0].childNodes[0].data
    if membro.getElementsByTagName("codiceFiscale").length!=0: 
        codiceFiscale=membro.getElementsByTagName("codiceFiscale")[0].childNodes[0].data
        italiano = True
    if membro.getElementsByTagName("identificativoFiscaleEstero").length!=0:
        codiceFiscale=membro.getElementsByTagName("identificativoFiscaleEstero")[0].childNodes[0].data
        italiano = False
    return newCompany(codiceFiscale,ragioneSociale,italiano, tipoAzienda)

#funzione per lavorare con un membro di tipo aggregato (per i raggruppamenti)
def companyGroupParse(group, tipoAzienda):
    membri=group.getElementsByTagName("membro")
    raggruppamentoObj=dict()
    #aggiunta di un campo type per descrivere se si tratta di raggruppamento, aggiudicatarioRaggruppamento, raggruppamento o aggiudicatarioRaggruppamento
    raggruppamentoObj["type"]=tipoAzienda
    groupParticipantObj=[]
    for membro in membri:
        ragioneSociale=membro.getElementsByTagName("ragioneSociale")[0].childNodes[0].data
        ruolo=membro.getElementsByTagName("ruolo")[0].childNodes[0].data
        if membro.getElementsByTagName("codiceFiscale").length!=0: 
            codiceFiscale=membro.getElementsByTagName("codiceFiscale")[0].childNodes[0].data
            italiano=True 
        if membro.getElementsByTagName("identificativoFiscaleEstero").length!=0:
            codiceFiscale=membro.getElementsByTagName("identificativoFiscaleEstero")[0].childNodes[0].data
            italiano=False
        groupParticipantObj.append(newCompanyGroupElement(codiceFiscale,ragioneSociale,italiano, ruolo))
    raggruppamentoObj["raggruppamento"]=groupParticipantObj
    return raggruppamentoObj


#funzione per creare oggetto contenente dati di un partecipante/aggiudicatario singolo
def newCompany(codiceFiscale,ragioneSociale, italiano, tipoAzienda):
    participant=dict()
    #aggiunta di un campo type per descrivere se si tratta di partecipante, aggiudicatario, raggruppamento, aggiudicatarioRaggruppamento
    participant['type']=tipoAzienda
    if italiano:
        participant['codiceFiscale']=codiceFiscale
    else:
        participant['identificativoFiscaleEstero']=codiceFiscale
    participant['ragioneSociale']=ragioneSociale
    return participant

#funzione per creare oggetto contenente dati di un partecipante/aggiudicatario parte di un raggruppamento
def newCompanyGroupElement(codiceFiscale,ragioneSociale, italiano, ruolo):
    participant=dict()
    if italiano:
        participant['codiceFiscale']=codiceFiscale
    else:
        participant['identificativoFiscaleEstero']=codiceFiscale
    participant['ragioneSociale']=ragioneSociale
    participant['ruolo']=ruolo
    return participant

#funzioone per creare dizionario di una struttura proponente 
def newProposingStructure(codiceFiscale,denominazione):
    proposingStructure=dict()
    proposingStructure['codiceFiscale']=codiceFiscale
    proposingStructure['denominazione']=denominazione
    return proposingStructure

#funzione per creare dizionario relativo a tempi completamento
def newCompletionTime(dataInizio,dataUltimazione):
    completionTime=dict()
    if len(dataInizio)!=0:
        completionTime['dataInizio']=dataInizio
    if len(dataUltimazione)!=0:
        completionTime['dataUltimazione']=dataUltimazione
    return completionTime


#funzione che restituisce un oggetto contentente la lista dei dizionari dei lotti 
def lottiToObject(rootNode):
    tenders =[]
    nLotti=0
    lotti=rootNode.getElementsByTagName("lotto")
    if lotti.length!=0:
        for lotto in lotti:
            gara = dict()
            nLotti=nLotti+1
            #LETTURA CIG
            gara['cig']=lotto.getElementsByTagName("cig")[0].childNodes[0].data         

            #LETTURA STRUTTURA PROPONENTE
            strutturaProponenteObj=[]
            struttureProponenti=lotto.getElementsByTagName("strutturaProponente")   
            for strutturaProponente in struttureProponenti:                         
                codiceFiscaleProp=strutturaProponente.getElementsByTagName("codiceFiscaleProp")[0].childNodes[0].data
                denominazione=strutturaProponente.getElementsByTagName("denominazione")[0].childNodes[0].data
                strutturaProponenteObj.append(newProposingStructure(codiceFiscaleProp,denominazione))
            gara['strutturaProponente']=strutturaProponenteObj
            
            #LETTURA OGGETTO BANDO
            gara['oggetto']=lotto.getElementsByTagName("oggetto")[0].childNodes[0].data                         
          
            #LETTURA SCELTA CONTRAENTE
            gara['sceltaContraente']=lotto.getElementsByTagName("sceltaContraente")[0].childNodes[0].data       
           
            #LETTURA DEI PARTECIPANTI ALLA GARA 
            partecipanti=lotto.getElementsByTagName("partecipanti")                              
            partecipantiObj=[]
            partecipantiSingoli=partecipanti[0].getElementsByTagName("partecipante")                       #caso in cui vi siano dei partecipanti singoli
            if partecipantiSingoli.length!=0:                                                               
                for partecipante in partecipantiSingoli:
                    partecipantiObj.append(companyParse(partecipante, "partecipante"))                #aggiunge il diz di un partecipante alla lista dei partecipanti singoli     
            raggruppamenti=partecipanti[0].getElementsByTagName("raggruppamento")                          #caso in cui vi siano dei raggruppamenti
            if raggruppamenti.length!=0:
                for raggruppamento in raggruppamenti:
                    partecipantiObj.append(companyGroupParse(raggruppamento, "raggruppamento"))
            gara['partecipanti']=partecipantiObj    

            #LETTURA DEGLI AGGIUDICATARI DELLA GARA     
            aggiudicatari=lotto.getElementsByTagName("aggiudicatari")                                       
            aggiudicatariObj=[]
            aggiudicatariSingoli=aggiudicatari[0].getElementsByTagName("aggiudicatario")                       #caso in cui vi siano aggiudicatari singoli
            aggiudicatariRaggruppamenti=aggiudicatari[0].getElementsByTagName("aggiudicatarioRaggruppamento")    #caso in cui vi siano aggiudicatari raggruppamenti
            if aggiudicatariSingoli.length!=0:
                for aggiudicatario in aggiudicatariSingoli:
                    aggiudicatariObj.append(companyParse(aggiudicatario, "aggiudicatario"))          
            if aggiudicatariRaggruppamenti.length!=0:
                for aggiudicatarioRaggruppamento in aggiudicatariRaggruppamenti:
                    aggiudicatariObj.append(companyGroupParse(aggiudicatarioRaggruppamento, "aggiudicatarioRaggruppamento"))
            gara['aggiudicatari']=aggiudicatariObj

            #LETTURA IMPORTO AGGIUDICAZIONE
            if lotto.getElementsByTagName("importoAggiudicazione")[0].childNodes[0].length!=0:
                gara['importoAggiudicazione']=lotto.getElementsByTagName("importoAggiudicazione")[0].childNodes[0].data

            #LETTURA TEMPI COMPLETAMENTO
            tempiCompletamento=lotto.getElementsByTagName("tempiCompletamento")
            for tempoCompletamento in tempiCompletamento:                                                       
                dataInizio=""
                if tempoCompletamento.getElementsByTagName("dataInizio").length!=0:
                    dataInizio=tempoCompletamento.getElementsByTagName("dataInizio")[0].childNodes[0].data
                dataUltimazione=""
                if tempoCompletamento.getElementsByTagName("dataUltimazione").length!=0:
                    dataUltimazione=tempoCompletamento.getElementsByTagName("dataUltimazione")[0].childNodes[0].data
                tempiCompletamentoObj=newCompletionTime(dataInizio,dataUltimazione)
            gara['tempiCompletamento']=tempiCompletamentoObj
            
            #LETTURA SOMME LIQUIDATE
            if lotto.getElementsByTagName("importoSommeLiquidate")[0].childNodes[0].length!=0:
                gara['importoSommeLiquidate']=lotto.getElementsByTagName("importoSommeLiquidate")[0].childNodes[0].data                   

            #CREAZIONE DIZIONARIO DEI LOTTI 
            tenders.append(gara)

            #decommentare per stampare i C.F nulli (uguali a 00000000000 )
            #codiceFiscaleCheck(lot)
        print ("trovati ", nLotti, "lotti")
        lottiObj=dict()
        lottiObj["lotto"]=tenders
    return lottiObj

#funzione che restituisce un dizionario con i metadati del file xml 
def metadataToObject(rootNode):
    metadata=rootNode.getElementsByTagName("metadata")[0]
    metadataObj=dict()

    #i file xml contengono il campo dataPubbicazioneDataset , l'italiano è sbagliato ma le specifiche dicono proprio "Pubbicazione"
    compulsoryMetadataFields=['dataPubbicazioneDataset', 'entePubblicatore','annoRiferimento', 'urlFile']
    optionalMetadataFields=['titolo', 'abstract','dataUltimoAggiornamentoDataset', 'licenza']
    #lettura campi opzionali 
    for metadataField in optionalMetadataFields:
        if metadata.getElementsByTagName(metadataField)[0].childNodes[0].length!=0: 
            content=metadata.getElementsByTagName(metadataField)[0].childNodes[0].data
            metadataObj[metadataField]=content

    #lettura  campi obbligatori (ma controllo sulla loro presenza aggiunto comunque 
    for metadataField in compulsoryMetadataFields:
        if metadata.getElementsByTagName(metadataField)[0].childNodes[0].length!=0: 
            content=metadata.getElementsByTagName(metadataField)[0].childNodes[0].data
            metadataObj[metadataField]=content        
    return metadataObj

#funzione che scrive il file contenente i dati dei contratti in formato json 
def dataXmlToJson(fIn):
    print("converting ", fIn, "to json")
    if fIn.endswith('.xml'):
        fOutName = fIn[:-4]+".json"
        f = open(fOutName, 'w')
    json.dump(parseXmlDataset(fIn), f, indent=4)
    f.close()
    print ("file ", fOutName, "creato correttamente")

#funzione che scrive il file di indice dei contratti in formato json
def indexXmlToJson(fIn):
    print("converting ", fIn, "to json")
    if fIn.endswith('.xml'):
        fOutName= fIn[:-4]+".json"
        f = open(fOutName, 'w')
    json.dump(parseIndexDataset(fIn), f, indent=4)
    f.close()
    print ("file ", fOutName, "creato correttamente")

#funzione che scrive il file dei dati dei contratti in formato json
def parseXmlDataset(fileName): 
    DOMTree=xml.dom.minidom.parse(fileName)
    legge190=DOMTree.documentElement
    pubblicazione=dict()
    pubblicazione["metadata"]=metadataToObject(legge190)
    pubblicazione["data"]=lottiToObject(legge190)
    return pubblicazione

#funzione che ritorna un dizionario con dati e metadati del file di indice
def parseIndexDataset(fileName):
    DOMTree=xml.dom.minidom.parse(fileName)
    legge190=DOMTree.documentElement
    pubblicazione=dict()
    pubblicazione["metadata"]=indexMetadataToObject(legge190)
    pubblicazione["indice"]=indexDataToObject(legge190)
    return pubblicazione

#funzione che ritorna un oggetto con i metadati del file di indice
def indexMetadataToObject(rootNode):
    metadata=rootNode.getElementsByTagName("metadata")[0]
    metadataObj=dict()

    compulsoryMetadataFields=['dataPubblicazioneIndice', 'entePubblicatore','annoRiferimento', 'urlFile']
    optionalMetadataFields=['titolo', 'abstract','dataUltimoAggiornamentoIndice', 'licenza']
    #lettura campi opzionali 
    for metadataField in optionalMetadataFields:
        if metadata.getElementsByTagName(metadataField)[0].childNodes[0].length!=0: 
            content=metadata.getElementsByTagName(metadataField)[0].childNodes[0].data
            metadataObj[metadataField]=content

    #lettura  campi obbligatori (ma controllo sulla loro presenza aggiunto comunque 
    for metadataField in compulsoryMetadataFields:
        if metadata.getElementsByTagName(metadataField)[0].childNodes[0].length!=0: 
            metadataObj[metadataField]=metadata.getElementsByTagName(metadataField)[0].childNodes[0].data        
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

#funzione di prova per stampare tutti i partecipanti e gli aggiudicatari con codicaFiscale = 00000000000 )
def codiceFiscaleCheck(lotto):
    partecipanti=lotto['partecipanti']
    aggiudicatari=lotto['aggiudicatari']
    for aggiudicatario in aggiudicatari:
        if "codiceFiscale" in aggiudicatario:
            if aggiudicatario['codiceFiscale']=="00000000000":
                print ("aggiudicatario errato:" , lotto["cig"], " ", aggiudicatario["codiceFiscale"], " ", aggiudicatario["ragioneSociale"])
            if "identificativoFiscaleEstero" in aggiudicatario:
                if aggiudicatario['identificativoFiscaleEstero']=="00000000000":
                    print ("aggiudicatario estero errato: ",lotto['cig'], " " ,aggiudicatario['identificativoFiscaleEstero'], " ",aggiudicatario['ragioneSociale'])  
    for partecipante in partecipanti:
        if "codiceFiscale" in partecipante:
            if partecipante["codiceFiscale"]=="00000000000":
                print ("partecipante errato:  " , lotto["cig"], " ", partecipante["codiceFiscale"], " ", partecipante["ragioneSociale"])
                print()
        if "identificativoFiscaleEstero" in partecipante:
            if partecipante["identificativoFiscaleEstero"]=="00000000000":
                print ("partecipante estero errato: ",lotto['cig'], " " ,partecipante['identificativoFiscaleEstero'], " ",partecipante['ragioneSociale'])
                print()
   
def main():
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
            



main()


