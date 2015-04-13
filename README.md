# AVCP
programma per la conversione da xml a json dei file di contratti pubblici relativi alla legge 190/2012

ISTRUZIONI: 
Usare le seguenti funzioni presenti in main():

getFileNameFromCommandLine()

Converte singoli file xml, già presenti nella stessa cartella dove viene eseguito lo script, in formato json

downloadAndParseEverything("http:\\url_file_indice.xml")

Scarica e parsifica tutti i file (indice compreso) linkati dal file di indice. Passare alla funzione l'url del file di indice. 


Il programma converte i file dei contratti pubblici in formato json. La struttura dei json ricalca fedelmente quella indicata  nel specifiche tecniche AVCP: http://www.anticorruzione.it/portal/rest/jcr/repository/collaboration/Digital%20Assets/pdf/AllCom27.05.13SpecificeTecnichev1.0.pdf 
Viene aggiunto per ciascun partecipante/agiudicatario, inoltre, il campo "type", valorizzato con  "partecipante" o  "raggruppamento", in modo da poter trattare i dati del partecipante o raggruppamento in modo diverso. 
