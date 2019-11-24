# GeoSearch - GreenLabs

#### Correr el script
1) Descomprimir el zip 
2) Ejecutar ``` ./geosearch.sh create ```
3) Copiar el json con las credenciales en la carpeta creds (nombrar el archivo como *credentials.json*) or si posee un token de acceso copiarlo con el nombre *token.pickle*
4) En *geosearch.py* cambiar el valor de la variable **DRIVE_DIR** con el id de la carpeta padre donde comenzara la busqueda (ultima valor alfanumerico encontrado en la url en drive: *drive.google.com/drive/u/0/folders/**15aZijgdBWQ5WCmSaemTNsb9z9vOVbo6B**)*
5) Ejecutar el script con: ```./geosearch.sh run latitud longitud metros```
ejemplo:
```
./geosearch.sh run -34.42187777 -58.872108333 100
```

**NOTAS**:  
Tambien puede llamar al script con los siguientes argumentos:  
**-a** (all_images): traera todas las imagenes encontradas en dentro de la carpeta y subcarpetas  
**-v** (vervose) : imprimira en consola las imagenes encontradas  
**--no-recursive** : realizara la busqueda solo en la carpeta apuntada por la variable **DRIVE_DIR**  
ejemplo:  
```
./geosearch.sh run --no-recursive -v -32.17722166  -64.481199194  100
```

##### Output:
El json de salida se guarda en la carpeta *data/* y posee los siguientes campos por cada imagen encontrada:
1) **id**: *id del archivo el drive*
2) **name**: *nombre del archivo en drive*
3) **mimeType**: *tipo de archivo*
4) **webContentLink**: *link para descargar la imagen desde drive*
5) **webViewLink**: *link para ver la imagen ampiada en drive*
6) **thumbnailLink**: *link para ver la imagen en miniatura en drive*
7) **latitude**: *latitud de la imagen*
8) **longitude**: *longitud de la imagen*

**NOTA**: El archivo json posee el formato de *'images_data_24-12-19_23-59-59.json'*
donde los numeron son la fecha y hora de ejecucion del script.

##### Links de interes:
[Busqueda de archivo con API drive](https://developers.google.com/drive/api/v3/search-files)  
[Busqueda recursiva con API drive](https://stackoverflow.com/questions/41741520/how-do-i-search-sub-folders-and-sub-sub-folders-in-google-drive)  
[Metadatos en drive](https://googleapis.github.io/google-api-python-client/docs/dyn/drive_v3.files.html#list)  
