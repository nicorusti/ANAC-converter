# AVCP
programma per la conversione da xml a json dei file di contratti pubblici relativi alla legge 190/2012
Il programma converte i file dei contratti pubblici in formato json. La struttura dei json ricalca fedelmente quella indicata  nel [specifiche tecniche AVCP](http://www.anticorruzione.it/portal/rest/jcr/repository/collaboration/Digital%20Assets/pdf/AllCom27.05.13SpecificeTecnichev1.0.pdf )

Viene aggiunto per ciascun partecipante/agiudicatario, inoltre, il campo "type", valorizzato con  "partecipante" o  "raggruppamento", in modo da poter trattare i dati del partecipante o raggruppamento in modo diverso. 


ISTRUZIONI: 
Usare le seguenti funzioni presenti in main():
	
	
	getFileNameFromCommandLine()

Converte singoli file xml, già presenti nella stessa cartella dove viene eseguito lo script, in formato json



	downloadAndParseEverything("http://url_file_indice.xml")

Scarica e parsifica il file di indice e tutti i file da esso linkati.
Passare alla funzione l'url del file xml di indice. I file xml e json sono salvati nella cartella download\nome_istituzione\anno , dove nome_istituzione ed anno sono presi dal 	file di indice. 
Qualora esista già il percorso download\nome_istituzione\anno, i file presenti non sono sovrascritti ma salvati nella cartella download\nome_istituzione\anno_1 



