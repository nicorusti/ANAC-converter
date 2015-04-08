# AVCP
programma per la conversione da xml a json dei file di contratti pubblici relativi alla legge 190/2012

Il programma, ricevuto come input il file di indice o il file di dati, restituisce un json la cui struttura ricalca fedelmente quella specificata nel specifiche tecniche AVCP: http://www.anticorruzione.it/portal/rest/jcr/repository/collaboration/Digital%20Assets/pdf/AllCom27.05.13SpecificeTecnichev1.0.pdf 
Viene aggiunto, inoltre, il campo "type", valorizzato con  "partecipante" o  "raggruppamento", in modo da poter trattare i dati del partecipante o raggruppamento in modo diverso. 
