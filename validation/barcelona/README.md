# Barcelona — validación con cinco parcelas catastrales

El 14 de noviembre de 2026 se cruzaron en EPSG:25831 parcelas del [Catastro INSPIRE](https://www.catastro.hacienda.gob.es/webinspire/) con la [capa de calificaciones del AMB](https://geoportal.amb.cat/geoserveis/rest/services/qualificacio_refos/MapServer/0). De las 112 parcelas recuperadas se conservaron las cinco primeras referencias en orden alfanumérico con cobertura íntegra y exclusiva del polígono AMB `74768`.

| Referencia catastral | Superficie geométrica (m²) |
|---|---:|
| `0427610DF3802G` | 260,23 |
| `0427611DF3802G` | 125,14 |
| `0427612DF3802G` | 262,02 |
| `0526601DF3802F` | 221,26 |
| `0526602DF3802F` | 218,91 |

El polígono devuelve `CLAU_PD = 13E`, `CLAU_URB = 13a` y el expediente [`BE201A` (`2000/002253`)](https://ajuntament.barcelona.cat/informaciourbanistica/cerca/ca/fitxa/BE201A/--/--/ap/), relativo al conjunto del Eixample. Los cinco registros SUPS Cadastral Plot 1.0 tienen estado `PARTIAL` y contienen `plotAreaM2`. La [capa de parámetros](https://geoportal.amb.cat/geoserveis/rest/services/qualificacio_refos/MapServer/1) devolvió cero entidades para el área consultada. La altura y edificabilidad por parcela quedan pendientes.

- [Registros SUPS Plot](sups-cadastral-plots.json)
- [Evidencias y consultas reproducibles](evidencias.json)
- [Respuestas originales de Catastro y del AMB](respuestas-oficiales.zip)

> Nota de migración: los registros se almacenan como parcelas catastrales con `measuredAreaM2` (superficie geométrica), no como parcelas urbanísticas ni derechos edificatorios efectivos. El estado `PARTIAL` del antiguo modelo mixto no se traslada a la entidad catastral.

## Auditoría municipal de clasificación y calificaciones

El [catálogo de equivalencias de Barcelona](municipal-mappings.json) recoge 463 reglas verificadas para la clasificación y el uso, con la fuente y las condiciones de cada regla. Las claves del AMB conservan el contexto de su expediente cuando se usa una clave derivada. Las equivalencias de uso del MUC corresponden a su código sintético.

El [JSON de auditoría](planning-audit.json) reúne dos fuentes filtradas por el código INE `08019`. El AMB aporta 4.607 polígonos, comprobados mediante recuento directo y recuperación de cada identificador, agrupados en 3.774 combinaciones de régimen, claves, expediente y otros atributos. El MUC aporta superficies municipales de 2025 en hectáreas.

| Código MUC | Clase y categoría SUPS | Superficie (ha) |
|---|---|---:|
| SUC | URBAN / CONSOLIDATED | 8.360,40 |
| SNC | URBAN / UNCONSOLIDATED | 112,02 |
| SUD | DEVELOPABLE / SECTORIZED | 29,40 |
| SND | DEVELOPABLE / NON_SECTORIZED | 0,00 |
| SNU | NON_DEVELOPABLE / UNSPECIFIED | 1.676,35 |

En el AMB se documentaron los 4.607 polígonos a partir de `REGIM`. Los 191 con `SUNC` se asignan a `URBAN / UNCONSOLIDATED` según el glosario de la Generalitat. La equiparación de categorías del MUC se refiere a sus superficies agregadas.

El uso SUPS se documentó para 2.688 polígonos (58,3 %). Quedan 1.919 en revisión. La auditoría conserva `CLAU_URB`, `CLAU_PD` y el expediente. Las claves derivadas se asignan cuando hay una regla documentada para la combinación o el expediente correspondiente.

La ampliación de 267 polígonos cubre claves residenciales, terciarias, de equipamientos, de espacios libres y de protección natural. Las variantes de equipamiento y espacios libres se incorporan cuando se puede conservar el uso general. Las fuentes de cada asignación constan en el JSON. [Leyenda del AMB](https://geoportal.amb.cat/geoserveis/rest/services/qualificacio_refos/MapServer/legend) · [Criterios del geoportal del AMB](https://geoportalplanejament.amb.cat/Informacio/Contingut/Contingut/Contingut_ca.html)

La siguiente tanda incorpora 265 polígonos de actividad terciaria y vivienda del 22@, verde público, parques y jardines, equipamientos y alojamiento dotacional. Las reglas se limitan a combinaciones concretas de claves. Las variantes numeradas de `22@T` y las combinaciones con otros usos siguen pendientes de contraste con sus expedientes. La clave genérica `18` identifica la ordenación volumétrica y exige consultar el instrumento para resolver el uso. [Normas urbanísticas del 22@](https://bcnroc.ajuntament.barcelona.cat/jspui/bitstream/11703/134237/4/GM_Conveni-AjuntamentGeneralitatINCAS%C3%92L-HabitatgesProtecci%C3%B3OficialLloguerAssequible-Annex2_2024.pdf)

Las claves de sistemas de transporte, servicios técnicos y cementerios se contrastaron con la leyenda. Para 13E, la equivalencia residencial plurifamiliar se limita al expediente 2000/002253 (BE201A). El JSON indica si se usó la clave de base o la clave derivada.

La última revisión incorpora 138 polígonos. Incluye vivienda social o protegida en Ciutat Vella, el sector Prim y el 22@, otras claves residenciales y equipamientos de alojamiento dotacional. Las reglas por expediente tienen prioridad sobre las reglas por combinación de claves, de modo que el JSON conserva la evidencia específica cuando está disponible. [Sector Prim](https://www.gencat.cat/territori/urbanisme/ctu_inf/SUB_inf_20220225.pdf) · [Vivienda social en Ciutat Vella](https://ajuntament.barcelona.cat/fomentdeciutat/data/12069-ccaa2010.pdf)

Para reproducir la auditoría, ejecutar `python tests/audit_barcelona_planning.py` desde la raíz del repositorio.

## Cruce cartográfico de los 1.919 usos pendientes

El [resultado por polígono](muc-pending-comparison.json) registra el identificador AMB, el código sintético del MUC y la fracción de superficie cubierta por cada código. Se exige que un único código cubra al menos el 99 % de la superficie del polígono y que ningún otro supere el 1 %. Las equivalencias a SUPS se aplican a los códigos con un uso identificable según el glosario. El MUC usado para el cruce corresponde a la edición metropolitana de enero de 2025. [Descarga oficial y fecha de referencia](https://territori.gencat.cat/ca/06_territori_i_urbanisme/observatori_territori/mapa_urbanistic_de_catalunya/serveis-web-dades-obertes/descarrega-dades/format-shapefile-shp/)

El cruce aporta 1.477 asignaciones adicionales. Sumadas a las 2.688 de la auditoría AMB, se obtiene cobertura cartográfica de uso SUPS para 4.165 de 4.607 polígonos (90,4 %). Quedan 442 pendientes. En particular, 369 de los 395 polígonos con claves AMB `18` y `18` tienen correspondencia espacial con `R4`, residencial en ordenación abierta plurifamiliar.

Para reproducir el cruce, descargar el ZIP oficial del Barcelonès, instalar `pyshp` y `shapely>=2` y ejecutar `python tests/compare_barcelona_muc.py <zip> validation/barcelona/muc-pending-comparison.json`.

## Generación del conjunto municipal de zonas SUPS

El [generador](generate_zoning.py) utiliza AMB `pcd` (capa 0 del servicio de calificación)
como unidad de salida, filtrada por `CODI_INE = '08019'`. Identifica las zonas como
`ES-08019-AMB-PCD-{OBJECTID}`. La estabilidad depende de que el AMB preserve esos
identificadores al republicar la capa. El servicio declara 1 de julio de 2023 en
su campo Subject. El generador registra ese texto tal como se recibe en cada extracción.

La [capa AMB de clasificación prga](https://geoportal.amb.cat/geoserveisapp/rest/services/Planejament/Classificacio/MapServer/0)
declara 1 de enero de 2024. Contiene `OBJECTID`, `CODI_INE`, `REGIM` y `DESC_CS`.
Para conservar una sola geometría AMB por zona, se aplica el `REGIM` de `pcd`,
según el catálogo auditado para esa capa. Las superficies agregadas del MUC
sirven de referencia municipal. Las fechas declaradas de las capas describen
sus respectivas ediciones y no se usan como fechas de vigencia de cada polígono.

Desde la raíz del repositorio, con Python 3.10 o posterior:

```sh
python -m pip install -r requirements-dev.txt "shapely>=2.1,<3" pyshp
python validation/barcelona/generate_zoning.py update --muc-zip <ZIP-MUC> --muc-edition 2025-01-01 --muc-downloaded-at <ISO-8601>
```

La fecha de edición se obtiene del [calendario oficial del MUC](https://territori.gencat.cat/ca/06_territori_i_urbanisme/observatori_territori/mapa_urbanistic_de_catalunya/actualitzacions/)
para el ámbito metropolitano. El comando recalcula el cruce en EPSG:25831 con
el ZIP oficial del Barcelonès enlazado arriba, aplica únicamente reglas verificadas
con la misma edición y guarda las fracciones de intersección por código. Puede
ejecutarse sin el ZIP MUC si solo se desea medir la cobertura del AMB.
La primera edición documentada del MUC tiene el SHA-256 que figura en
`muc-pending-comparison.json`. Una descarga posterior puede contener otra entrega.

El ZIP generado contiene `sups-zoning-areas.json` (array de registros con geometría
GeoJSON longitud/latitud), `zoning-audit.json` (atributos originales, evidencia,
motivos pendientes y geometrías rechazadas), `manifest.json` y las copias de
las fuentes. El manifiesto recoge recuentos, diferencias respecto a las auditorías
y huellas SHA-256. El generador compara el recuento y los identificadores antes y
después de descargar y valida el contenido de cada lote. Publica el ZIP mediante un
reemplazo atómico después de validar la extracción, el esquema y los vocabularios.

La auditoría identifica las geometrías nulas devueltas por el AMB. Para
geometrías poligonales inválidas se admite la reparación topológica de GEOS
solo si el resultado es poligonal y válido, y la diferencia relativa de área
es como máximo `1e-8`. Se registra el motivo, el método y la variación de área
por identificador. Los registros que siguen sin geometría publicable figuran
en la auditoría junto con sus atributos originales.

Extrae `amb-source.zip` y `muc-source.zip` de la versión que quieras reproducir.
Usa `--amb-source` para trabajar sin conexión. Pasa la misma edición y fecha de
descarga del MUC para reproducir también el manifiesto. Usa otro archivo de salida
para conservar una versión anterior que quieras comparar.

```sh
python validation/barcelona/generate_zoning.py update --amb-source amb-source.zip --muc-zip muc-source.zip --muc-edition 2025-01-01 --muc-downloaded-at <ISO-8601> --output reproducido.zip
python validation/barcelona/generate_zoning.py compare anterior.zip reproducido.zip
```

La [comprobación sin conexión](check_zoning.py) usa pyshp, pyproj y Shapely para
reproyectar una geometría AMB archivada. Compara dos normalizaciones del mismo
polígono, prueba una clave nueva y rechaza un inventario y una página incompletos.
También reproduce los recuentos de clasificación y uso a partir de la auditoría y
comprueba las 1.477 equivalencias del cruce histórico con el catálogo. Instala
`pyproj` además de las dependencias del generador y ejecuta
`python validation/barcelona/check_zoning.py`.

### Publicación en S3

El [publicador](publish_zoning.py) prepara los objetos de la versión a partir
del ZIP validado. Comprueba las huellas de los JSON y de las copias de las fuentes.
Con AWS CLI v2 y credenciales con acceso de escritura y lectura al destino:

```sh
python validation/barcelona/publish_zoning.py validation/barcelona/barcelona-zoning.zip release-barcelona --publish
```

Sin `--publish` solo prepara los archivos y muestra la ruta. Se admite
`--profile` para elegir un perfil de AWS CLI. La ruta es
`s3://goolzoom-sups-data/08019 - Barcelona/<versión>/` en `eu-west-3`.
La versión combina la hora UTC de la captura AMB y los primeros 16 caracteres
del SHA-256 del ZIP. Se publica cada objeto con escritura condicional, sin ACL,
y se descarga para verificar su SHA-256. El manifiesto se escribe al final y
contiene la ruta y las huellas de los otros objetos. Una repetición acepta objetos
ya existentes si tienen exactamente el contenido de la publicación. Si falla
una subida, la carpeta local preparada permite reintentar la misma versión.

### Captura del 15 de noviembre de 2026

Se descargaron 4.607 entidades `pcd`; el recuento y los identificadores
coincidieron al inicio y al final, y cada uno de los 47 lotes se verificó en
las dos proyecciones. El AMB devolvió 187 geometrías nulas en ambas proyecciones
y también en la consulta adicional con formato Esri JSON. La zona `58540`
se exportó tras reparar una autointersección de anillo, con una variación
relativa del área de `8.35e-16`.

Se validaron 4.420 zonas SUPS. Las 4.420 tienen clasificación y 4.070 tienen
uso (92,1 %), con 2.593 asignaciones directas AMB y 1.477 del cruce MUC.
De las 350 zonas exportadas con uso pendiente, 343 tienen un código MUC sin
equivalencia aplicable y siete no cumplen el criterio de solape.
Entre las 187 entidades con geometría nula había 95 con uso documentado
en el AMB y 92 con uso pendiente en la auditoría previa. Las 1.477
asignaciones del MUC reproducen las de la auditoría histórica.

Dos generaciones con las mismas fuentes produjeron el mismo ZIP, con
SHA-256 `f2990fa12148ada1c65ed545a6a792ca90d256fd29981ef81610be74a2442060`.
La prueba con una clave nueva quedó en revisión. Eliminar el último lote
de la captura provocó un fallo y dejó intacto el ZIP local anterior.

Versión publicada en
`s3://goolzoom-sups-data/08019 - Barcelona/20261115T085756-f2990fa12148ada1/`.
Se descargaron de S3 los cuatro objetos de esta versión y sus SHA-256
coincidieron con los calculados antes de la subida.

La verificación posterior descargó los cuatro objetos y regeneró dos veces el
conjunto con las copias AMB y MUC incluidas en el ZIP. Los JSON de zonas y
auditoría coincidieron byte por byte con S3. El comparador devolvió cero altas,
bajas y cambios. Para repetir esta comprobación se puede usar la fecha
`muc.downloadedAt` del manifiesto como argumento `--muc-downloaded-at`.
