# L. 190 Public Contracts dataset processing 
Codice testato ed eseguito su python 3.4.2
Codice e documentazione in fase di sviluppo!

#### Project: 
These scripts are intended for use with Italian public contracts xml datasets, in compliance with the Transparency Act, L.190/2012. 

#### Functionalities 
Scripts are able to download, keep updated and convert to json all Italian public contracts xml. 

#### Instructions: 
Download and run the scripts in the same folder. 
To download and convert to json all Italy's public contracts, run, in following order:

	checkUpdates("http://dati.anticorruzione.it/data/L190.json") 	#in script download.py
	convertAll()							#in script massConvert.py
	stats()								#in script massConvert.py

Be careful! the amount of data processed is massive as download/processing time!

To convert a single xml dataset (both index or data typr) run: 

	toJson("foldername/filename.xml", "outputfolder/myNewJson/")	#in script xmlToJson.py

#### For detailed instructions check the project [wiki](https://github.com/nicorusti/ANAC-converter/wiki)






