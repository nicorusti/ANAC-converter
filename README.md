# AVCP-ANAC
script per la conversione da xml a json dei file di contratti pubblici relativi alla legge 190/2012
La struttura dell'output in  json ricalca quella indicata  nelle [specifiche tecniche AVCP](http://www.anticorruzione.it/portal/rest/jcr/repository/collaboration/Digital%20Assets/pdf/AllCom27.05.13SpecificeTecnichev1.0.pdf )
		
#Correzione e validazione dei dati
* L'aggiudicatario di una gara viene aggiunto anche tra i partecipanti, qualora non fosse già presente. 
* Conversione in maiuscolo e pulizia da caratteri non alfanumerici di cig e codici fiscali/p.iva. Controllo della corrispondenza di cig e codice fiscale /p.iva alle specifiche. (cig=10 char alfanumerici). Controllo che cig, c.f./p.iva non siano valorizzati rispettivamente con "0000000000" e "00000000000". 
* Partecipanti/aggiudicatari privi di dati validi (né intestazione né p.iva/c.f.) non vengono aggiunti al json 
* In un raggruppamento, se la stringa relativa al ruolo non corrisponde alle specifiche dello [schema XSD](http://dati.avcp.it/schema/TypesL190.xsd), viene inserita la stringa più simile tra quelle previste dallo schema. in questo caso, la stringa originale viene inserita comunque con la chiave "ruoloOriginal". 
* Nello stesso modo viene processato il campo sceltaContraente: sceltaContraenteOriginal viene aggiunto se esso non corrisponde al suddetto [schema XSD](http://dati.avcp.it/schema/TypesL190.xsd)
		
#Aggiunta di campi aggiuntivi ed hash: 
+ Per ciascun partecipante/agiudicatario: campo "type", valorizzato con  "partecipante" o  "raggruppamento", in modo da poter trattare i dati del partecipante o raggruppamento in modo diverso. 
+ Per ciascuna gara con CIG non valido o nullo (casi di gare per le quali non è prevista l'assegnazione del cig): campo "cigHash"  in forma di stringa esadecimale [sha1](http://en.wikipedia.org/wiki/SHA-1), costruito in base a: 
	* Codice Fiscale della struttura proponente
	* Importo Aggiudicazione
	* Scelta Contraente (tipo di procedura di aggiudicazione) 
	* Codice Fiscale(di seguito C.F.)/p.iva dell'aggiudicatario. Nel caso l'aggiudicatario sia un raggruppamento, l'hash è costruito in base ai C.F./p.iva in ordine alfabetico
+ Per ciascun raggruppamento: campo "groupHash" in forma di stringa esadecimale [sha1](http://en.wikipedia.org/wiki/SHA-1), costruito in base a: 
	* C.F./p.iva, in ordine alfabetico, dei membri del raggruppamento. 
	* cig o cigHash. Per ogni gara, quindi, un raggruppamento formato dalle stesse aziende, ottiene hash diversi. Questo affinché il raggruppamento corrisponde alla definizione giuridica di Associazione Temporanea di Impresa

	
#Istruzioni: 
Usare le seguenti funzioni presenti in main():

	getFileNameFromCommandLine()
	
> Converte singoli file xml, già presenti nella stessa cartella dove viene eseguito lo script, in formato json


	downloadAndParseEverything("http://url_file_indice.xml")
	
> Scarica e parsifica il file di indice e tutti i file da esso linkati.
Passare alla funzione l'url del file xml di indice. I file xml e json sono salvati nella cartella download\nome_istituzione\anno , dove nome_istituzione ed anno sono presi dal 	file di indice. 
Qualora esista già il percorso download\nome_istituzione\anno, i file presenti non sono sovrascritti ma salvati nella cartella download\nome_istituzione\anno_1 



