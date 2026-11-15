# València — validación con cinco parcelas catastrales

El 14 de noviembre de 2026 se cruzaron en EPSG:25830 las geometrías de las [parcelas urbanas con ficha](https://opendata.vlci.valencia.es/dataset/parcel-les-cadastrals-d-urbana-amb-fitxa-urbanistica) con las capas de [calificaciones](https://opendata.vlci.valencia.es/es/dataset/pgou-calificacions-pgou-calificaciones) y [alineaciones](https://opendata.vlci.valencia.es/es/dataset/pgou-alineacions-pgou-alineaciones). Se seleccionaron por identificador municipal las cinco primeras de siete candidatas contrastadas con calificación dominante `ENS`.

| Referencia catastral | Superficie geométrica (m²) | Solape con ENS |
|---|---:|---:|
| `6116402YJ2761E` | 202,09 | 99,9886 % |
| `6116406YJ2761E` | 189,94 | 100,0000 % |
| `6116213YJ2761E` | 89,24 | 99,9787 % |
| `6116204YJ2761E` | 179,46 | 99,9998 % |
| `6116212YJ2761E` | 93,64 | 99,9735 % |

Las cinco comparten `tipoca = 2` y `origen = MP2098A`. Las fichas municipales muestran el plano y tienen vacías las casillas de calificación, uso, plantas y edificabilidad. Varias parcelas cruzan polígonos con distintos valores de `altura`. Los cinco registros SUPS Cadastral Plot 1.0 tienen estado `PARTIAL` y contienen `plotAreaM2`. Quedan pendientes la verificación del uso por parcela, la interpretación de la altura y el cálculo de la edificabilidad.

- [Registros SUPS Plot](sups-cadastral-plots.json)
- [Evidencias, consultas y enlaces a las fichas](evidencias.json)
- [Fichas municipales originales](fichas-municipales.zip)

> Nota de migración: los registros se almacenan como parcelas catastrales con `measuredAreaM2` (superficie geométrica), no como parcelas urbanísticas ni derechos edificatorios efectivos. El estado `PARTIAL` del antiguo modelo mixto no se traslada a la entidad catastral.

## Auditoría de la capa municipal de calificaciones

La [auditoría](planning-audit.json) agrupa los valores originales de `clase`, `uso`, `tipouso` `califi` y `origen` en la [capa PGOU – Calificaciones](https://geoportal.valencia.es/server/rest/services/OPENDATA/UrbanismoEInfraestructuras/MapServer/231). Los 2.405 grupos suman 21.238 registros, cifra confirmada mediante una consulta de recuento independiente a ArcGIS. Los registros son entidades de la capa de planeamiento.

| Campo | Equivalencia documentada | Código sin revisar | Sin valor |
| --- | ---: | ---: | ---: |
| Clasificación (`clase`) | 21.198 | 27 | 13 |
| Uso (`uso` o calificación inequívoca) | 17.836 | 1.262 | 2.140 |

El [plano municipal de la serie B](https://www.valencia.es/ayuntamiento/urbanismo2.nsf/0/293C3352E4C33D49C1257FD1002D5211/%24FILE/O.1-Calificacion%20del%20Suelo%20Serie%20B_firmado.pdf) documenta `SU`, `SUP`, `SUNP` y `SNU`. La auditoría valida la clase SUPS y conserva la distinción histórica entre urbanizable programado y no programado en el código original. Para asignar categorías SUPS como sectorizado, consolidado o protegido se requiere evidencia adicional.

Se documentaron 5.629 registros desde el campo `uso` y 12.207 a partir de `califi` cuando `uso` estaba vacío. En este último caso se representa el destino urbanístico de la calificación según el artículo 6.3 de las Normas del PGOU. El JSON indica el campo que respalda cada equivalencia, conserva `tipouso` y usa `UNSPECIFIED` cuando el subtipo queda indeterminado.

La ampliación documenta 5.026 registros de red viaria (RV), 1.293 de Ensanche (ENS) y 1.074 de Edificación Abierta (EDA). Para ENS y EDA se exige origen PGOU y uso vacío, conforme a los artículos 6.17 y 6.23. ArcGIS se consulta por bloques de identificadores y se verifica cada subtotal antes de guardar el JSON.

La revisión posterior incorpora los códigos de uso EC (equipamiento educativo-cultural), ZV (zona verde) y RV (red viaria), además de la calificación CV de red viaria cuando el uso está vacío y el origen es PE2020 (PEP Ciutat Vella).

Se documentó también SJL (jardín de la red secundaria) y, para el origen PE2020, SQE (equipamiento educativo-cultural) y SQM (equipamiento dotacional múltiple).

La revisión de redes y espacios libres incorpora PRV y SRV como red viaria, y PJL, SAL y SJL como calificaciones de espacios libres. PJL y SAL se reconocen también en el campo de uso.

La revisión dotacional incorpora GIS y SID como infraestructuras y servicios, SED como equipamiento educativo y SRD como deportivo. PRV y SRV se reconocen también como códigos de uso.

El artículo 4.10 del PGOU establece el uso dominante agrícola para PA. La regla se aplica a las entidades con clase SNU, origen PGOU y campo de uso vacío. El artículo 4.9 identifica el uso forestal y de protección del medio natural de PM (54 registros), recogido como OTHER / OTHER ante la falta de una categoría específica. El código PI genérico (148 registros de origen PGOU en suelo no urbanizable) queda como UNKNOWN porque las subzonas tienen regímenes distintos según los artículos 4.6 y 4.12.

El artículo 6.6 del PGOU establece el uso dominante residencial plurifamiliar para CHP. La auditoría aplica la equivalencia a 52 registros con calificación CHP, origen PGOU y uso vacío. Los 34 registros AR de PE1629 requieren comprobar la ordenanza de ese instrumento.

La nomenclatura autonómica de equipamientos de red primaria y secundaria permite documentar 154 registros adicionales. La auditoría usa subtipos administrativo y deportivo cuando el código lo indica, y UNSPECIFIED en las familias educativo-cultural y sanitario-asistencial.

El anexo IV del texto refundido valenciano distingue parques (VP), jardines (VJ) y áreas de juego (VA). Con los prefijos de red primaria y secundaria, estos códigos documentan 63 registros adicionales como GREEN_SPACE. Los parques se asignan a PARK, y los jardines y áreas de juego a OTHER.

El anexo IV también identifica los códigos de comunicaciones. Con los prefijos de red primaria y secundaria, la auditoría incorpora 16 registros adicionales a INFRASTRUCTURE / TRANSPORT.

El JSON incluye un inventario de todos los usos pendientes en pendingUseByCodeAndOrigin, agrupado por campo, código e instrumento de origen y ordenado por número de registros. Los códigos sin evidencia suficiente se conservan para revisión.

Para actualizar la auditoría desde la raíz del repositorio, ejecutar `python tests/audit_valencia_planning.py`.

## Capa SUPS Zoning Area para Goolzoom Suelo

El generador captura la capa municipal completa [PGOU – Calificaciones, ArcGIS 231](https://geoportal.valencia.es/server/rest/services/OPENDATA/UrbanismoEInfraestructuras/MapServer/231). La geometría de calificación y la clasificación de cada polígono se publican juntas en esta capa. El filtro es `1=1` porque el conjunto del Ayuntamiento ya tiene ámbito municipal. El identificador SUPS `46250-pgou231-<objectid>` conserva el identificador de fila que publica el servicio. Si el proveedor renumera filas al republicar la capa, se necesita revisar las altas y bajas antes de atribuirlas a cambios del planeamiento. `linkid` se conserva como identificador auxiliar.

La fuente nativa está en ETRS89 / UTM 30N (EPSG:25830). Se solicita GeoJSON en EPSG:4326 y se guardan las coordenadas en orden longitud, latitud y con anillos orientados según GeoJSON. Se aceptan reparaciones GEOS poligonales, válidas y de superficie equivalente, con tolerancia relativa de `1e-8` medida en las coordenadas de salida. Las exclusiones incluyen el ID original y la causa. Para respuestas GeoJSON vacías se archiva también la consulta ArcGIS JSON nativa y se comprueba si hay anillos.

El [catálogo municipal](municipal-mappings.json) traslada las reglas y evidencias de la auditoría de València. `clase` determina la clase SUPS. Una `clase` reconocida recibe categoría `UNSPECIFIED` cuando la fuente no identifica una categoría homologable. El uso publicado en `uso` tiene prioridad. Con `uso` vacío se evalúa `califi` y se registra la procedencia como destino de calificación. Las condiciones de expediente se aplican a `origen`. Los códigos en blanco, nuevos, fuera de las condiciones de la regla o ambiguos quedan registrados en `pending`. La auditoría conserva los campos originales, entre ellos `tipoca`, `tipouso`, `idoperacion` y `fecha_valor`, junto con el identificador y la evidencia de cada equivalencia.

La [ficha oficial del catálogo](https://opendata.vlci.valencia.es/es/dataset/pgou-calificacions-pgou-calificaciones) indica licencia CC BY 4.0. La copia conserva los cuerpos de las respuestas, los metadatos de ArcGIS y CKAN, la URL completa, la hora UTC, el tamaño y la huella SHA-256 de cada solicitud. La ficha CKAN de esta extracción tenía fecha de modificación del 11 de noviembre de 2026. El servicio indicaba ArcGIS 10.81 y no declaraba una edición del planeamiento ni fecha de edición de la capa. Los 21.238 valores de `fecha_valor` estaban vacíos. La referencia temporal de la captura se identifica por su fecha UTC y la huella del ZIP. Se utiliza la geometría municipal original sin cruce cartográfico ni parcelario.

### Regeneración, comprobación y publicación

Desde la raíz del repositorio, con Python 3.12 y el esquema y vocabularios SUPS de este checkout. El manifiesto guarda sus huellas y las de los demás archivos de entrada.

```powershell
python -m pip install -r validation/valencia/requirements-zoning.txt
$work = "validation/valencia/zoning-work"
python -B validation/valencia/capture_zoning.py "$work/source-next.zip"
python -B validation/valencia/generate_zoning.py build "$work/source-next.zip" "$work/release-next"
python -B validation/valencia/check_zoning.py "$work/source-next.zip" "$work/release-next"
python -B validation/valencia/generate_zoning.py diff "$work/release/manifest.json" "$work/release-next/manifest.json"
python -B validation/valencia/generate_zoning.py publish "$work/source-next.zip" "$work/release-next"
```

Cada captura usa un ZIP nuevo. Los recuentos e inventarios inicial y final deben coincidir, y se exige que cada lote contenga exactamente los identificadores solicitados. `build` valida los registros del ZIP, también si procede de una publicación anterior, y crea la salida en un directorio nuevo tras comprobar que todos los registros son válidos. `check_zoning.py` compara byte a byte dos ejecuciones y prueba una clave inédita, una regla ambigua, un expediente fuera de condiciones y una captura truncada. `diff` enumera altas y bajas del inventario y de la capa exportada, cambios de geometría, clase, categoría, uso, subtipo y motivos pendientes o rechazos geométricos. El manifiesto conserva las huellas individuales de las geometrías.

El comando de publicación requiere AWS CLI y permisos S3 de escritura condicional y lectura en `eu-west-3`. Puede indicarse `--profile`. Cada fichero se sube con `If-None-Match: *` y se vuelve a leer para cotejar tamaño y SHA-256. El manifiesto se escribe al final. Los consumidores deben considerar completas las versiones con manifiesto. Se puede reintentar con los mismos archivos y se conservan las versiones anteriores.

### Publicación del 15 de noviembre de 2026

`s3://goolzoom-sups-data/46250 - València/20261115T143919Z-fd1517ea8d028625/`

| Indicador | Entidades |
| --- | ---: |
| Descargadas | 21.238 |
| Exportadas | 21.194 |
| Clasificación documentada en la capa exportada | 21.162 |
| Uso documentado en la capa exportada | 17.803 |
| Clasificación pendiente en la capa exportada | 32 |
| Uso pendiente en la capa exportada | 3.391 |
| Zonas exportadas con algún pendiente | 3.412 |
| Geometrías reparadas y exportadas | 38 |
| Geometrías excluidas | 44 |

Los 2.405 grupos de atributos y sus recuentos coinciden con la auditoría previa. En origen hay 21.198 clasificaciones y 17.836 usos documentados, de los cuales 5.629 proceden de `uso` y 12.207 de `califi`. Las diferencias tras exportar corresponden a 44 exclusiones geométricas. La consulta nativa confirmó 36 geometrías con lista de anillos vacía y ocho geometrías ausentes. Entre las exclusiones había 36 clasificaciones y 33 usos con equivalencia documentada.

Se verificaron por lectura, tamaño y SHA-256 los cuatro objetos publicados, `sups-zoning-areas.json`, `zoning-audit.json`, `valencia-source.zip` y `manifest.json`. La publicación de esta edición utilizó URLs prefirmadas del conector AWS con escritura condicional y checksum SHA-256. El conjunto, la auditoría y el manifiesto fueron idénticos byte por byte en la regeneración desde el ZIP publicado.
