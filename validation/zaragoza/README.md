# Zaragoza — first real-world SUPS validation (draft)

## Versión con fuentes principales municipales

`20261115T154949Z-366d1a0454a5cff2` usa las capas del Ayuntamiento de
Zaragoza para la clasificación y la calificación. Los tres archivos
de áreas conservan las respectivas geometrías de origen en GeoJSON
longitud/latitud. El SIUa se utiliza en la auditoría de contraste.
La versión se publicó en
`s3://goolzoom-sups-data/50297 - Zaragoza/20261115T154949Z-366d1a0454a5cff2/`.
Los seis objetos se recuperaron de S3 y coincidieron byte a byte con
la versión validada.

| Archivo | Capa IDEZar | Filas WFS | Áreas exportadas | Equivalencias verificadas |
|---|---|---:|---:|---:|
| `sups-zoning-areas.json` | `Clasificaciones` | 684 | 682 | 663 de clasificación |
| `sups-municipal-zoning-areas.json` | `Calificaciones_Urbanas` | 7.963 | 7.963 | 5.049 de uso |
| `sups-municipal-non-urban-zoning-areas.json` | `Calificaciones_No_Urbanas` | 995 | 994 | 0 de uso |

La clasificación aplica la leyenda del PGOUZ, hoja 067, a las claves
de `clasificacion` con `tipo=CLAS` y `clase=P`. Los sistemas generales
`SGU`, `SGUZ` y `SGNU` fijan la clase y dejan la categoría sin
especificar. Quedan 18 cauces `RIO` y una geometría con claves
contradictorias `SU` y `SNU-E`. Esta última reúne tres filas y conserva
los tres identificadores y atributos originales. La capa no urbana
fusiona un duplicado geométrico con los mismos atributos y mantiene los
usos pendientes, ya que sus claves expresan categorías o protecciones.
El identificador SUPS municipal se deriva de la capa y de la huella de
la geometría. Los cambios de geometría aparecen como baja y alta.

Las uniones de polígonos municipales y regionales coinciden en el
99,45 % de la huella SIUa y en el 99,48 % de la municipal. Las
intersecciones por clase se calculan sobre las geometrías en CRS84 y
se agrupan mediante unión antes de medir el área. Hay 274 polígonos
municipales cuya clase regional conocida difiere en más del 1 % del
polígono. El 54,41 % de la huella municipal tiene clasificación
verificada y el 45,59 % queda pendiente. El SIUa identifica como no
urbanizable el 97,91 % de la geometría municipal con claves
contradictorias. El contraste mantiene visibles ambas fuentes y la
geometría queda pendiente en la capa municipal.

El catálogo municipal de clasificación indica el 24 de febrero de
2024 para la ficha de datos asociada al WMS. El portal del PGOUZ
documenta la consolidación de junio de 2026. Las tres capturas WFS son
del 15 de noviembre de 2026. Los atributos WFS carecen de fecha de
edición, por lo que no se ha confirmado su correspondencia con la
consolidación documental. El manifiesto conserva las marcas de tiempo
de las respuestas, los recuentos y los SHA-256 de las fuentes.

Para capturar, regenerar, comprobar y publicar desde la raíz del repositorio:

```text
python validation/zaragoza/municipal_qualification.py work/classification --layer Clasificaciones
python validation/zaragoza/municipal_qualification.py work/urban --layer Calificaciones_Urbanas
python validation/zaragoza/municipal_qualification.py work/non-urban --layer Calificaciones_No_Urbanas
python validation/zaragoza/generate_municipal_zoning.py work/classification work/urban work/non-urban work/regional-contrast.json work/releases
python validation/zaragoza/check_municipal_zoning.py work/releases/<version>
python validation/zaragoza/publish_zoning.py work/releases/<version>
```

Para reproducir sin red, extrae `municipal-sources.zip` en `work`.
El ZIP contiene las tres capturas, los catálogos y el conjunto histórico
del SIUa en `regional-contrast.json`. El comparador de manifiestos
registra el cambio de geometrías e identificadores al sustituir el
SIUa y permite comparar las tres capas municipales entre versiones.

## Capa SUPS de calificación urbana municipal

Publicación verificada en
`s3://goolzoom-sups-data/50297 - Zaragoza/20261115T151818Z-337470aefbffd036/`.
Los cinco objetos se descargaron de S3 y coincidieron byte a byte con
la versión local validada.

`sups-municipal-zoning-areas.json` contiene las 7.963 geometrías de
`Calificaciones_Urbanas` del Ayuntamiento en registros SUPS `ZONING`.
Hay 5.049 usos verificados (63,41 % de la capa municipal) y 2.914
pendientes. Se exportaron 1.714 zonas residenciales, 1.666 zonas verdes,
1.613 equipamientos, 46 industriales y 10 terciarias con uso verificado.
La capa publicada por el SIUa y sus indicadores conservan su propia
granularidad. La capa municipal no lleva clasificación heredada y el
63,41 % se refiere a entidades de calificación urbana municipal.

Los FID municipales solo identifican entidades en su respuesta WFS.
El identificador SUPS usa una huella SHA-256 de la geometría canónica,
conserva el FID original como evidencia y se mantiene si cambia la
clave de uso con la misma geometría. Un cambio geométrico se observa
como baja y alta en el manifiesto municipal. Las coincidencias de
huella detienen la generación hasta revisar la identidad. El
comparador informa de la capa municipal en `municipalZoningAreas`.

Los comandos con `--municipal` que figuran abajo generan, validan y
archivan ambos conjuntos. Para consultar uso a la escala de
calificación debe leerse `sups-municipal-zoning-areas.json`.
El manifiesto y la auditoría registran los recuentos y los motivos
pendientes. Entre ellos destacan 901 ámbitos de planeamiento recogido
(`PR`) y 556 sectores con plan parcial aprobado (`SUZ-PD`), cuya
calificación pormenorizada depende del instrumento de desarrollo.

## Actualización con calificación municipal

Publicada y verificada en
`s3://goolzoom-sups-data/50297 - Zaragoza/20261115T151818Z-dc7d19230b6f9808/`.
Los cuatro objetos coinciden byte a byte con la versión validada y el
prefijo anterior sigue disponible.

La versión `20261115T151818Z-dc7d19230b6f9808` incorpora la capa
`urbanismo:Calificaciones_Urbanas` del Ayuntamiento al conjunto SIUa.
De las 268 zonas urbanas consolidadas con clasificación verificada y sin
código regional de uso, 32 obtuvieron uso característico municipal
verificado, 231 quedaron por debajo del requisito de cobertura y 5
presentaron calificaciones competidoras o sin equivalencia por encima
de la tolerancia. Los 32 usos son 23 equipamientos, 4 zonas verdes,
3 residenciales y 2 industriales. El resultado pasa de 76 a 108 usos
verificados (4,05 % de 2.665 zonas). La comparación registra 32 cambios
de uso y de pendiente, con cero altas, bajas, cambios de clasificación
o cambios de geometría.

Se aplican claves exactas de `municipal-use-mappings.json` y los artículos
del PGOU que figuran en él. Las claves con sufijos, las vinculadas a
planeamiento de desarrollo y las que no cuentan con una regla aplicable
se mantienen sin inferir. La regla exige que la unión de las
intersecciones con la misma familia de uso cubra al menos el 95 % del
polígono SIUa y que el área de la unión de calificaciones distintas o
sin equivalencia no supere el 1 %. Ambos umbrales son criterios del
importador. El informe conserva las claves, atributos, identificadores
de la respuesta y fracciones de solape de cada cruce evaluado. El uso
verificado significa que se ha comprobado la equivalencia cartográfica,
con alcance en el polígono SUPS. La capa urbana devuelve una fecha de
respuesta WFS del 15 de noviembre de 2026 y se desconoce su edición
normativa exacta. La vista municipal no urbana se empleó en la auditoría
exploratoria que figura más abajo.

Para regenerar con calificación municipal, después de capturar el SIUa:

```text
python validation/zaragoza/municipal_qualification.py work/zaragoza-municipal
python validation/zaragoza/generate_zoning.py generate work/zaragoza-capture work/releases --municipal work/zaragoza-municipal
python validation/zaragoza/check_zoning.py work/zaragoza-capture work/releases/<version> --municipal work/zaragoza-municipal
```

Para reproducir esta versión sin red, usa la raíz de `siua-source.zip`
extraído como captura SIUa y su subcarpeta `municipal` como valor de
`--municipal`. Conserva las dos respuestas WFS municipales, sus URLs,
fechas de respuesta, recuentos, huellas y catálogo aplicado.
Origen de la calificación: Ayuntamiento de Zaragoza, IDEZar.
[Condiciones de reutilización](https://www.zaragoza.es/sede/portal/aviso-legal).

## Capa municipal Zoning Area — INE 50297

Publicación verificada el 15 de noviembre de 2026 en
`s3://goolzoom-sups-data/50297 - Zaragoza/20261115T150650Z-990c73d041d6e616/`.
Los cuatro objetos se descargaron de S3 y coincidieron byte a byte con la
versión local. El conjunto está en `sups-zoning-areas.json`, la auditoría
en `zoning-audit.json`, las fuentes en `siua-source.zip` y el inventario de
publicación en `manifest.json`.

La [captura WFS del SIUa](https://idearagon.aragon.es/SIUa/servicios-web) del 15 de
noviembre de 2026 usa `SIUa:clasificacion_idearagon` y `SIUa:usoglobal`, con
`cod_ine=50297`. El [catálogo de clasificación municipal](https://www.zaragoza.es/web/espacio-de-datos/servicio/catalogo/3040)
describe `Plano_Clasificacion` como WMS y fecha su conjunto el 24 de febrero de 2024.
El WFS municipal consultado publica hojas y ámbitos de desarrollo, pero no las
capas vectoriales homólogas de clasificación y calificación general. El
[portal del PGOUZ](https://www.zaragoza.es/sede/portal/urbanismo/planeamiento/pgouz)
identifica su edición documental como TR2024 consolidado en junio de 2026.
El [visor del SIUa](https://idearagon.aragon.es/SIUa/visor) declara noviembre de
2025 como actualización general de sus capas. En ambas vistas capturadas,
`date_acu` e `inicio` son 18 de enero de 2025 y `fin` está vacío en todas las
filas, con `n_expedien=CPU-50/2024/123`, `cod_plan=TRPGOU`,
`bd_origina=MunZarPlan` y `control=2025`. La consolidación municipal de
junio de 2026 queda como referencia documental independiente. Su incorporación
a la edición vectorial requiere confirmación.

El catálogo de equivalencias aplica la [NOTEPA](https://www.boa.aragon.es/cgi-bin/EBOA/BRSCGI?CMD=VEROBJ&MLKOB=964971862323)
y la [leyenda de clasificación del PGOUZ](https://www.zaragoza.es/contenidos/urbanismo/pgouz/TR2024/tomo_10_estructura_clasificacion_tr_2024.pdf)
a las combinaciones compatibles de `clase`, `clase_s` y `notepa`.
`uso_glob` representa uso global publicado, con las condiciones de `dot_sg`
del catálogo cuando procede. Cada regla exige el instrumento, expediente
y origen registrados. Las etiquetas de protección y los usos no publicados
quedan pendientes. `regulationIds` se mantiene vacío porque los cinco
ejemplos de ordenanzas de esta carpeta carecen de un vínculo poligonal acreditado.

El WFS devuelve 2.665 filas por vista. Se comprobaron 11 páginas por vista,
los recuentos WFS antes y después y un inventario independiente de claves.
Las 2.665 parejas coincidieron en la geometría GeoJSON original y en todos
los atributos. La unión exige igualdad exacta de `objectid`, `shape_area` y
`shape_le_1` e igualdad de las geometrías. La auditoría registra el método y
los recuentos. Se exporta un área `MIXED` por pareja. Las vistas divergentes
detienen la generación para revisar la asociación.

Los identificadores SUPS se basan en `objectid`. Para 5064 (tres filas) y
82916 (dos filas), se añade un sufijo derivado de su clave compuesta, porque
el identificador WFS `fid-…` es temporal. Si el área o perímetro de uno de
esos cinco polígonos cambia, la comparación puede reflejar una baja y un alta.
Las nuevas colisiones de `objectid` detienen la publicación hasta revisarlas.
Las geometrías se solicitan en CRS84 (longitud, latitud) y se comprueban con
Shapely. Se repararon dos autointersecciones mediante `make_valid` y se
exportaron las 2.665 zonas. La auditoría conserva los identificadores y las
causas de reparaciones o rechazos y el ZIP conserva los datos originales.

La clasificación se verificó en 2.661 zonas (99,85 %) y el uso en 76
(2,85 %). Quedaron 4 clasificaciones contradictorias y 2.589 usos pendientes.
En uso, 2.494 carecían de valor y 95 traían `CA` (44), `EN` (31),
`GENERICO` (17) o `EC` (3). Hay 2.591 zonas con al menos una dimensión
pendiente. La auditoría previa cubría cinco muestras de ordenanzas y carecía
de recuentos geográficos comparables.

Fuente de los datos Gobierno de Aragón, IGEAR, Sistema de Información
Urbanística de Aragón (SIUa). [Condiciones generales CC BY 4.0](https://icearagon.aragon.es/portal/en/politica-privacidad.jsp).

### Regeneración, comparación y publicación

Desde la raíz del repositorio, con Python 3.12 y curl disponibles:

```text
python -m pip install -r validation/zaragoza/requirements-zoning.txt
python validation/zaragoza/capture_zoning.py work/zaragoza-capture
python validation/zaragoza/generate_zoning.py generate work/zaragoza-capture work/releases
python validation/zaragoza/check_zoning.py work/zaragoza-capture work/releases/<version>
python validation/zaragoza/generate_zoning.py compare work/releases/<anterior>/manifest.json work/releases/<version>/manifest.json
python validation/zaragoza/publish_zoning.py work/releases/<version>
```

Usa una ruta nueva para cada captura y generación. Para reproducir sin red,
extrae `siua-source.zip` y usa ese directorio como captura. Cada respuesta
conserva su URL, tamaño y SHA-256. El manifiesto compara altas, bajas,
geometría normalizada, clasificación, uso y motivos pendientes. El comprobador
reproduce la versión byte a byte, introduce una clave de uso desconocida,
comprueba el cambio de cobertura y confirma que una página incompleta
impide generar una versión.

El publicador admite `--profile` y requiere una AWS CLI con
`s3api put-object --if-none-match`. Crea objetos en un prefijo por versión,
verifica el contenido descargado y escribe el manifiesto al final. Los procesos
que consuman el conjunto deben tratar el manifiesto como señal de publicación
completa y comprobar las huellas de sus objetos. Una versión incompleta
puede reintentarse con los mismos archivos. Los objetos existentes se
verifican antes de continuar y las versiones anteriores permanecen disponibles.

### Contraste con la calificación municipal — 15 de noviembre de 2026

El [visor de Urbanismo](https://idezar-sig.zaragoza.es/servicios/visorUrbanismo/)
usa dos capas de calificación que responden en el servicio general OWS.
Cada descarga completa coincide con `resultType=hits`, `numberMatched`,
`numberReturned` y el número de identificadores WFS distintos observados.
Los FID suministrados son temporales. Los atributos incluyen
`calificacion`, `descripcion`, `tipo` y `clase`. La edición de estas
capas no se ha fechado a partir de sus atributos.

| Vista | Filas | SHA-256 de la respuesta |
|---|---:|---|
| [Calificaciones_Urbanas](https://idezar-sig.zaragoza.es/servicios/geoserver/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=urbanismo:Calificaciones_Urbanas&srsName=CRS:84&outputFormat=application%2Fjson) | 7.963 | `c89609e552338b39498b5754cd5f5c3fa8165505bc85b856f554cfa11be62c44` |
| [Calificaciones_No_Urbanas](https://idezar-sig.zaragoza.es/servicios/geoserver/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=urbanismo:Calificaciones_No_Urbanas&srsName=CRS:84&outputFormat=application%2Fjson) | 995 | `84a8c5eca6955f02e55c639ebd25f6d2d43d34230d3f69d4ad5563938e85e333` |

`audit_municipal_qualification.py` recibe el conjunto SUPS y las dos
respuestas GeoJSON. Para cada una de las 2.589 zonas con uso pendiente,
intersecta los polígonos municipales con clave y mide la fracción de
superficie de la unión de las intersecciones en CRS84. El resultado mide
solape geométrico por capa. La asignación de uso requeriría revisar las
claves, el instrumento aplicable y la coexistencia de calificaciones.

| Vista | Solape con superficie positiva | Solape ≥ 50 % | Solape ≥ 95 % |
|---|---:|---:|---:|
| Urbana | 724 | 482 | 150 |
| No urbana | 2.152 | 1.910 | 1.846 |

Las capas pueden solaparse entre sí, de modo que las filas del cuadro
no son aditivas. Las claves urbanas observadas incluyen `A1/1`, `A6/1`,
`EQ` y `ZV`. En suelo no urbano predominan las claves de protección y
las categorías del suelo. La prueba se realizó con posterioridad a la
publicación SIUa y sus resultados se conservan como auditoría.

## Auditoría de ordenanzas

Source: [Zaragoza PGOU consolidated urban regulations](https://www.zaragoza.es/contenidos/urbanismo/pgouz/TR2024/Normas_refundido_2025_con.pdf), articles **4.2.8–4.2.10**, PDF pp. 155–156. Municipal [planning portal](https://www.zaragoza.es/sede/portal/urbanismo/planeamiento/pgouz) labels TR2024 consolidated June 2026.

## Coverage

Two **A-3** regulation records (grades 1 and 2) normalize:
- `maxBuildabilityRatio`: 0.65 / 0.36.
- `maxOccupancyPct`: 35 / 20 percent.
- `minFrontSetbackM`: 3 / 5 m.
- `maxFloors`: conditional by building use in grade 1 (3 unifamiliar, 4 other); 3 in grade 2.
- `maxHeightM`: conditional by building use (grade 1: 10 / 13 m; grade 2: 10 / 10.5 m).
- `minPlotAreaM2`: typology-specific minimums (not a single unconditional parcel minimum).
- `minPlotFrontageM`: 15 m for ordinary subdivisions; exceptional 6 m under stated conditions.

## Findings / limitations

1. **Subdivision vs buildable parcel**: 1,000 m² / 15 m for general new subdivision is distinct from the buildable minimum by typology. The draft schema currently conflates these under `minPlotAreaM2` and `minPlotFrontageM`. Recommend adding `minSubdivisionPlotAreaM2` and `minSubdivisionFrontageM`.
2. **Per-dwelling area vs parcel area**: 500/250/200 m² **per dwelling** is not always a minimum whole-plot area. Prefer `minAreaPerDwellingM2` for these cases; current variants are an interim, lossy mapping.
3. **Shared overlay constraints**: article 4.2.9 also sets a 35% cap for the projected envelope of all floors including basements. This is not identical to `maxOccupancyPct` for grade 2; requires a distinct parameter or explicit calculation basis.
4. **Legal exceptions**: pre-existing registered plots, neighboring construction, detailed studies, and separation rules must be preserved as source-linked conditions; no automatic building entitlement is inferred.
5. **Applicability not yet established**: no cadastral plots or zoning polygons were matched. These records validate ordinance extraction only, **not** effective parcel parameters.
6. **Legal currency**: this is an extraction from a municipal consolidated PDF, not a certification of current legal applicability to a specific plot. Confirm amendments and other instruments before parcel calculations.

## Status

**PARTIAL — ordinance-level proof of concept.** No parcel-level resolution or full legal review completed. All conditional text is explanatory, not executable. See JSON samples for structured extracted values.


## Second pass — five samples (14 November 2026)

Additional **draft** samples:
- `ZARAGOZA-A1-G1.json` — A-1 grade 1, closed-block residential: plot subdivision, street-width-dependent height and floors; article 4.1.8.
- `ZARAGOZA-A6-G1.json` — A-6 grade 1, productive/industrial: subdivision minima depend on block type; setbacks, buildability and height depend on exceptions; article 4.2.20.
- `ZARAGOZA-A2-G4.json` — A-2 grade 4, tertiary and residential uses excluding dwellings: subdivision, occupation and buildability; article 4.2.5.

**Five ordinance/grade samples now recorded, not five independently certified complete regulations.** The new records use proposed catalogue extension keys `minSubdivisionPlotAreaM2`, `minSubdivisionFrontageM` and `maxGroundFloorOccupancyPct`, which are **not yet in the canonical vocabulary**. Some conditions are summarized and are **not executable**. This pass tests expressiveness; it does not establish that every legal exception has been extracted. No zoning polygons or actual parcels have been evaluated.

### Proposed catalogue changes

- `minSubdivisionPlotAreaM2` — minimum area for a new subdivision (distinct from buildability of an existing plot).
- `minSubdivisionFrontageM` — minimum street frontage for subdivision.
- `maxGroundFloorOccupancyPct` — ground-floor occupancy where the rules distinguish floors.
- Consider separate per-dwelling-area constraints and coverage across basement levels.

### Important schema limitation

The draft `regulation.schema.json` currently allows an arbitrary parameter key and permits null variant values. Passing JSON Schema validation therefore only confirms **structural validity**, not that the keys are registered in SUPS or that legal meaning and numeric values are correct. A strict vocabulary/type validator should be added before declaring SUPS 1.0 validated.
