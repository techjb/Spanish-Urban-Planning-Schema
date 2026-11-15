# Bilbao — validación de parcelas y edificabilidad por subámbito

Validación del 14 de noviembre de 2026 sobre el PGOU de Bilbao de 2022. Se cruzaron en EPSG:25830 las geometrías del [parcelario catastral foral](https://datos.gob.es/es/catalogo/l02000048-parcelario-catastral-bilbao) con las capas de [planeamiento de la Diputación Foral de Bizkaia](https://www.opendatabizkaia.eus/es/catalogo/planeamiento-urbanistico). De las 36 parcelas recuperadas, se conservaron las cinco con al menos un 99,98 % de solape con alguno de los cuatro subámbitos seleccionados de Amezola-Irala.

| Referencia catastral | Superficie geométrica (m²) | Subámbito | Solape |
|---|---:|---|---:|
| `48.020.1716.04003` | 1.651,62 | RE.02.9 · Isasi Andrés 15 | 99,99986 % |
| `48.020.1716.04004` | 868,89 | RE.02.8 · Isasi Andrés 13 | 99,98745 % |
| `48.020.1716.04005` | 1.176,96 | RE.02.7 · Isasi Andrés 11 | 99,99989 % |
| `48.020.1727.03003` | 493,98 | RE.02.6 · Moncada 11 y otros | 99,99998 % |
| `48.020.1727.03004` | 598,45 | RE.02.6 · Moncada 11 y otros | 99,99995 % |

El campo foral `TechoEdificableTotalSR` coincide con el total sobre rasante publicado en los apartados IV.1.6 a IV.1.9 de las [Normas Urbanísticas Particulares de Rekalde](https://www.bilbao.eus/pgou2022/1_NORMAS_URBANISTICAS_GENERALES_Y_DISTRITOS/NORMAS_URBANISTICAS_PARTICULARES_DISTRITOS_Y_SNU/7_REKALDE/07_Doc_2_2_NN_PP_REKALDE.pdf).

| Subámbito | Techo total sobre rasante (m²t) |
|---|---:|
| RE.02.6 | 8.556 |
| RE.02.7 | 5.520 |
| RE.02.8 | 4.285 |
| RE.02.9 | 7.508 |

## Correspondencia con SUPS Plot

Los cinco registros cumplen SUPS Cadastral Plot 1.0 y tienen estado `PARTIAL`. El parámetro `plotAreaM2` recoge la superficie geométrica catastral. El techo contrastado corresponde a cada subámbito completo. En RE.02.6, dos referencias de la muestra comparten el mismo total de 8.556 m²t. Para asignar `maxBuildableAreaM2` hace falta identificar las parcelas urbanísticas y verificar el reparto del techo. El uso residencial se conserva como uso global de la capa foral.

## Archivos

- [Registros SUPS Plot](sups-cadastral-plots.json).
- [Evidencias, solapes y consultas reproducibles](evidencias.json).
- [Respuestas originales de los servicios forales](respuestas-oficiales.zip), archivadas sin alterar los datos devueltos. Fuente: Bizkaiko Foru Aldundia – Diputación Foral de Bizkaia. [Condiciones de reutilización](https://www.bizkaia.eus/es/inspirebizkaia).

> Nota de migración: los registros se almacenan como parcelas catastrales con `measuredAreaM2` (superficie geométrica), no como parcelas urbanísticas ni derechos edificatorios efectivos. El estado `PARTIAL` del antiguo modelo mixto no se traslada a la entidad catastral.

## Capa SUPS Zoning Area · 48020

Publicación `20261115T170148Z-6dfe27b2096b111b` en
`s3://goolzoom-sups-data/48020 - Bilbao/20261115T170148Z-6dfe27b2096b111b/`.
Incluye `sups-zoning-areas.json`, `zoning-audit.json`, `source.zip` y `manifest.json`.

### Fuentes y vigencia

| Prioridad | Fuente | Decisión |
|---|---|---|
| Municipal | [PGOU de Bilbao](https://www.bilbao.eus/cs/ContentServer?c=Page&cid=1279216046646&language=es&pagename=Bilbaonet%2FPage%2FBIO_Listado), expediente 2018-064662, aprobado el 31/03/2022 y publicado en el portal con actualización a febrero de 2023 | Referencia para el significado de las clases y usos y para identificar el instrumento aplicable. Se revisaron los planos y el catálogo de [GeoBilbao](https://www.bilbao.eus/opendata/es/aplicaciones/app-geobilbao), cuya ficha devolvió HTTP 403 durante la comprobación. Quedó sin localizar una descarga vectorial municipal verificable que cubriera el término completo. |
| Provincial | [Servicio foral de planeamiento](https://www.opendatabizkaia.eus/es/catalogo/planeamiento-urbanistico), captura del 15/11/2026 | Geometrías y atributos de clasificación, usos globales, calificación y ámbitos de desarrollo. Se conserva una copia de las respuestas con atribución a Bizkaiko Foru Aldundia – Diputación Foral de Bizkaia. La fecha de corte de la cartografía y el expediente por entidad carecen de campo publicado. [Condiciones de reutilización](https://www.bizkaia.eus/es/inspirebizkaia). |
| Autonómica | [UDALPLAN](https://www.geo.euskadi.eus/udalplan-cartografia-del-planeamiento-municipal-en-el-pais-vasco/webgeo00-dataset/es/), ficha de 03/06/2024, actualización anual del inventario | Referencia para evaluar una alternativa de clasificación y calificación global. La cartografía foral ofrece el detalle vectorial empleado en esta publicación. |
| Estatal | [SIU 2025](https://publicaciones.transportes.gob.es/sistema-de-informacion-urbana-siu-2025), [catálogo de servicios IDEE](https://idee.es/ca/web/idee/monitorizacion-de-servicios) | Referencia estatal para clasificación y ámbitos de desarrollo. No aporta la calificación municipal que se necesita para cerrar las discrepancias identificadas. |

La [Sentencia 283/2024](https://www.bilbao.eus/asesoriajuridica/resolucionesjudiciales/2024/240610%20SENTENCIA%20N%20283%20-%2024.pdf), publicada el 28/10/2024, anuló las determinaciones de 2022 para `RE.02.22` y `RE.02.23`. El [Ayuntamiento indica que rige el PGOU de 1995](https://www.bilbao.eus/cs/ContentServer?c=BIO_Generico_FA&cid=1279215608265&d=&language=es&pageid=1279216046646&pagename=Bilbaonet%2FBIO_Generico_FA%2FBIO_Generico). Las seis entidades forales con esas claves conservan su geometría y etiqueta original, con uso pendiente hasta contrastar la ordenanza previa. Las capas de suspensión contienen 15 geometrías repetidas en las tres familias de capas para Artxanda y el ámbito Bilbao–Barakaldo. Se conservan con revisión pendiente del instrumento aplicable.

### Extracción, equivalencias y comprobaciones

- La consulta exacta `Municipio = 'BILBAO'` se ejecuta en las 41 capas poligonales del servicio. Se comprueba el recuento y el conjunto de identificadores antes y después de descargar por lotes, se verifica el conjunto de IDs de cada lote y se conserva cada respuesta original. La copia cubre el inventario foral etiquetado como Bilbao.
- Cada registro usa `ES-48020-DFB-<capa>-<OBJECTID>`. Se mantiene mientras la Diputación conserve el identificador en la capa. Si el proveedor reasigna IDs, la comparación los mostrará como altas y bajas. Las coordenadas se exportan como longitud, latitud en WGS 84. Se conservan por separado las entidades de clasificación, calificación y desarrollo incluso si sus geometrías coinciden. Los atributos originales y las consultas están en `source.zip` y su inventario en el manifiesto.
- El [catálogo municipal](municipal-mappings.json) exige coincidencia exacta de capa y clave. Para los usos globales genéricos de actividades económicas, categorías rurales y sistemas generales se buscaron 1.140 contrapartes pormenorizadas. Todas coincidieron por `OBJECTID` y geometría topológicamente igual. Se trasladaron 682 equivalencias de uso verificadas. La auditoría conserva las relaciones y la decisión por registro.
- El cruce de clasificación usa intersecciones poligonales del GeoJSON de origen. Para cada zona calcula la fracción de su superficie cubierta por la unión de las piezas de cada clase y categoría, en el plano de coordenadas WGS 84. Se asigna una clase cuando una única combinación conocida cubre al menos el 99,9 % y ninguna otra, incluida la suspensión, supera el 0,1 %. La auditoría conserva los IDs fuente y las fracciones. Los casos de solape o suspensión quedan pendientes.
- La auditoría anterior se limitó a cinco parcelas de Rekalde. En la nueva copia se encontraron los 14 IDs forales distintos de sus consultas de uso global (5), calificación (5) y ámbitos de desarrollo (4), con los mismos valores para todos los campos archivados. Esta comparación se hizo por identificador y atributos; el alcance actual es el inventario municipal de zonas.
- Se descargaron y exportaron **4.707** registros. Se rechazaron **0** geometrías. Hay **4.662/4.707** clasificaciones normalizadas y **2.210/3.202** usos normalizados. Las 1.505 entidades de las capas de clasificación carecen de campo de uso aplicable. Quedaron **1.007** registros con alguna revisión pendiente, con 45 incidencias de clasificación y 992 de uso. Las 30 entidades de uso vinculadas a zonas suspendidas cuentan en ambos grupos. Los mayores grupos de uso pendiente son las categorías rurales genéricas, las designaciones de protección y los polígonos sin clave publicada.

### Regenerar, comparar y publicar

Desde la raíz del repositorio, con Python 3.12 y un directorio de trabajo nuevo para cada captura:

```powershell
python -m pip install -r validation/bilbao/requirements-zoning.txt
New-Item -ItemType Directory -Force validation/bilbao/local
python validation/bilbao/capture_zoning.py validation/bilbao/local/source.zip
python validation/bilbao/generate_zoning.py generate validation/bilbao/local/source.zip validation/bilbao/local/releases
python validation/bilbao/check_zoning.py validation/bilbao/local/source.zip
python validation/bilbao/generate_zoning.py compare anterior/manifest.json nueva/manifest.json
python validation/bilbao/publish_zoning.py nueva --verify-only
python validation/bilbao/publish_zoning.py nueva
```

`nueva` es el directorio de versión mostrado por el generador. Se puede reconstruir con el `source.zip` de una publicación. El manifiesto conserva fecha, URL, filtro y SHA-256 de cada respuesta, además de las huellas por archivo y por registro para comparar altas, bajas, geometría, clasificación, uso y pendientes.

El publicador usa AWS CLI en `eu-west-3` (admite `--profile`) o pares de URL prefirmadas por entrada estándar (`--presigned-stdin`). Escribe claves de versión con `If-None-Match: *`, comprueba cada objeto descargándolo y coloca el manifiesto al final. Si falla la descarga de origen, la comprobación o la transferencia, la versión anterior sigue disponible. Una transferencia parcial se puede reintentar con la misma carpeta local.
