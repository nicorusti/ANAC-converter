# AVCP-ANAC
Codice testato ed eseguito su python 3.4.2
Codice e documentazione in fase di sviluppo!

Script per la conversione da xml a json dei file di contratti pubblici relativi alla legge 190/2012
La struttura dell'output in  json ricalca quella indicata  nelle [specifiche tecniche AVCP](http://www.anticorruzione.it/portal/rest/jcr/repository/collaboration/Digital%20Assets/pdf/AllCom27.05.13SpecificeTecnichev1.0.pdf )
![schema](https://cloud.githubusercontent.com/assets/11498717/7343336/afb74876-ecc0-11e4-8ca5-9fedcda4c178.png)
Il json creato si divide in tre sezioni:

	"data" 
	"metadata"
	"metrics"
* "data" contiene i dati dei contratti riutilizzando, ove possibile, la semantica dello schema AVCP
* "metadata" contiene i metadati del file xml, seguendo precisamente la semantica dello schema AVCP
* "metrics" contiene alcune statistiche sui dati contenuti nel file xml e sulla loro validità, come specificato nell'apposita sezione

#Correzione dei dati
* L'**aggiudicatario** di una gara viene aggiunto anche tra i partecipanti, qualora non fosse già presente. 
* Conversione in maiuscolo e pulizia da caratteri non alfanumerici di **cig** e **codici fiscali/p.iva**. Controllo della corrispondenza di cig e codice fiscale /p.iva alle specifiche (cig=10 char alfanumerici, p.iva=11 cifre, c.f.=lettere/numeri secondo specifiche). Controllo che cig, c.f./p.iva non siano valorizzati rispettivamente con "0000000000" e "00000000000". NON viene eseguito alcun check sulla correttezza del carattere di controllo di c.f. e P.Iva. 
* **Partecipanti/aggiudicatari** privi di dati validi ( intestazione e p.iva/c.f vuoti.) non vengono aggiunti al json 
* In un raggruppamento, se la stringa relativa al **ruolo** non corrisponde alle specifiche dello [schema XSD](http://dati.avcp.it/schema/TypesL190.xsd), viene inserita la stringa più simile tra quelle previste dallo schema. in questo caso, la stringa originale viene inserita comunque nel json con la chiave "ruoloOriginal". 
* Nello stesso modo viene processato il campo **sceltaContraente**: sotto la chiave "sceltaContraente" viene inserita la stringa più simile tra quelle previste dallo schema xsd, la chiave  "sceltaContraenteOriginal", contenente la stringa originale, viene aggiunta se essa non risponde alle specifiche del suddetto [schema XSD](http://dati.avcp.it/schema/TypesL190.xsd)
* Il campo **data** viene ripulito dai caratteri non numerici o non "/", inoltre viene ripossa la parte relativa al fuso orario, ove presente, di modo che la data sia conforme a xsd:date --> "yyyy-mm-dd"
* I campi contenenti un **importo** vengono ripuliti dai caratteri non numerici o non '.' e ',' e la ',' viene convertita in '.'
		
#Aggiunta di campi aggiuntivi in caso di campi errati/mancanti: 
+ Per ciascun partecipante/agiudicatario: campo **"type"**, valorizzato con  "partecipante" o  "raggruppamento", in modo da poter trattare i dati del partecipante o raggruppamento in modo diverso. 
+ Per ciascuna gara, è presente il campo **"cigValid"** valorizzato con true / false
+ Per ciascuna gara con CIG non valido o nullo (casi di gare per le quali non è prevista l'assegnazione del cig): campo **"cigHash"**  in forma di stringa esadecimale [sha1](http://en.wikipedia.org/wiki/SHA-1), costruito in base a: 
	* Codice Fiscale della struttura proponente
	* Importo Aggiudicazione
	* Scelta Contraente (tipo di procedura di aggiudicazione) 
	* Codice Fiscale(di seguito C.F.)/p.iva dell'aggiudicatario. Nel caso l'aggiudicatario sia un raggruppamento, l'hash è costruito in base ai C.F./p.iva in ordine alfabetico
+ Per ciascun raggruppamento: campo **"groupHash"** in forma di stringa esadecimale [sha1](http://en.wikipedia.org/wiki/SHA-1), costruito in base a: 
	* C.F./p.iva, in ordine alfabetico, dei membri del raggruppamento. 
	* cig o cigHash. Per ogni gara, quindi, un raggruppamento formato dalle stesse aziende, ottiene hash diversi. Questo affinché il raggruppamento corrisponde alla definizione giuridica di Associazione Temporanea di Impresa
* Aggiunta campi **"sceltaContraenteOriginal"** e  **"ruoloOriginal"** nei casi in cui questi campi nel xml siano valorizzati con stringhe non previste dallo  [schema XSD](http://dati.avcp.it/schema/TypesL190.xsd)
 
#Conteggi e metriche: 
Per ciascun file xml, sotto la chiave **"metrics"** sono disponibili delle metriche per i seguenti campi: 
* ciascuno dei possibili campi "sceltaContraente" presenti nello  [schema XSD](http://dati.avcp.it/schema/TypesL190.xsd)
	esempio: 

		"01-PROCEDURA APERTA": {
            "nInvalid": 0,
            "nValid": 0,
            "totalAwardedPrice": 0,
            "totalPaidPrice": 0
            }
	* **"nValid"** indica il n. delle gare in cui il campo sceltaContrante è presente e risponce allo schema xsd
	* **"nInvalid"** indica le occorrenze in cui il campo sceltaContraente è simile ad uno dei campi nello schema xsd. In questo caso il campo scelto è quello con similitudine maggiore 
	* **"totalAwardedPrice"** indica la somma degli importi aggiudicati per singolo tipo di procedura di aggiudicazione
	* **"totalPaidPrice"** indica la somma degli importi liquidati per singolo tipo di procedura di aggiudicazione 
 Qualora il campo sceltaContraente sia assente, le seguenti misure sono riportate: 
	esempio:

		"unknownProcType": {
            "nValid": 0,
            "totalAwardedPrice": 0,
            "totalPaidPrice": 0
            }
* per ciascuno dei campi campi **"awardedPrice"**, **"cig"**, **"companyCF"**, **"companyName"** (ragione sociale), **"endDate"**, **"paidPrice"** (importo somme liquidate), **"proposingStructureCF"**, **"role"** (ruolo in un raggruppamento),  **"startDate"**,  **"tenderObject"**  sono disponibili i seguenti contatori, come da esempio: 

        	"cig": {
            "nAbsent": 0,
            "nInvalid": 1,
            "nValid": 2
        }
        
       * **"nAbsent"** indica il n. delle occorrenze in cui il dato é assente 
       * **"nInvalid"** indica il n. delle occorrenze in cui il dato è presente ma non valido. Oggetto di una gara e regione sociale di un'azienda sono considerati invalidi se lunghi meno di 2 caratteri. Importo di aggiudicazione e somme liquidate sono considerate invalide se, una volta ripulite di caratteri non numerici e non ',' o '.'  non sono convertibili in float. Le date sono considerate invalide se, una volta ripulite, non soddisfano il formato yyy-mm-dd o se yyyy<1000 o yyyy>2999, se i mesi e i igorni sono inesistenti. cig e c.f./p.iva sono considerati invalidi se non corrispondenti alle specifiche. Role è invalido se diverso dalle stringhe specificate dallo  [schema XSD](http://dati.avcp.it/schema/TypesL190.xsd)
       * **"nValid"**  indica il n. delle occorrenze in cui il campo è presente e valido

* per i campi **"awardedPrice"** e **"paidPrice"** è presente anche il campo **"totalAmount"** che contiene la somma degli importi di aggiudicazione o delle somme liquidate nell'intero file xml.
* I campi **"single"** e **"group"** contengono le seguenti metriche: 
		
		"single": {
            "nParticipants": 10,
            "nParticipants": 2,
            "totalAwardedPrice": 32952.8,
            "totalPaidPrice": 24283.4
        }
	* **"nParticipants"** indica, per tutto il file xml,  il numero di partecipanti di tipo singolo / raggruppamento (esclusi eventuali aggiudicatari non partecipanti, aggiunti tra i partecipanti dallo script)
	* **"nParticipants"** indica il numero degli aggiudicatari
	* **"totalAwardedPrice"** e **"totalPaidPrice"** indicano la somma degli importi di aggiudicazione / delle somme liquidate per ciascun tipo di partecipante (singolo o raggruppamento)
***"nWinnerNotParticipant"** indica il numero dei vincitori non presente tra i partecipanti. 
* **"nLotti"** indica il numero di gare presenti nel file xml 


#Istruzioni: 
Usare le seguenti funzioni presenti in main():

	toJson("filename.xml")
	
> Converte  filename.xml, che deve essere presente nella stessa cartella dove viene eseguito lo script, in formato json. Funziona sia con i file di indice che con i file di dati






