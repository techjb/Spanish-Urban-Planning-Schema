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
