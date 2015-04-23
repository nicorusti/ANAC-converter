# AVCP-ANAC
script per la conversione da xml a json dei file di contratti pubblici relativi alla legge 190/2012
La struttura dell'output in  json ricalca quella indicata  nelle [specifiche tecniche AVCP](http://www.anticorruzione.it/portal/rest/jcr/repository/collaboration/Digital%20Assets/pdf/AllCom27.05.13SpecificeTecnichev1.0.pdf )
		
#Correzione e validazione dei dati
* L'aggiudicatario di una gara viene aggiunto anche tra i partecipanti, qualora non fosse già presente. 
* Pulizia da caratteri non alfanumerici di cig, codici fiscali/p.iva, e converisone in maiuscolo. Controllo della rispondenza di cig e codice fiscale /p.iva alle specifiche. (cig=10 char alfanumerici)
		
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



