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
