# Barcelona — validación con cinco parcelas catastrales

El 14 de noviembre de 2026 se cruzaron en EPSG:25831 parcelas del [Catastro INSPIRE](https://www.catastro.hacienda.gob.es/webinspire/) con la [capa de calificaciones del AMB](https://geoportal.amb.cat/geoserveis/rest/services/qualificacio_refos/MapServer/0). De las 112 parcelas recuperadas se conservaron las cinco primeras referencias en orden alfanumérico con cobertura íntegra y exclusiva del polígono AMB `74768`.

| Referencia catastral | Superficie geométrica (m²) |
|---|---:|
| `0427610DF3802G` | 260,23 |
| `0427611DF3802G` | 125,14 |
| `0427612DF3802G` | 262,02 |
| `0526601DF3802F` | 221,26 |
| `0526602DF3802F` | 218,91 |

El polígono devuelve `CLAU_PD = 13E`, `CLAU_URB = 13a` y el expediente [`BE201A` (`2000/002253`)](https://ajuntament.barcelona.cat/informaciourbanistica/cerca/ca/fitxa/BE201A/--/--/ap/), relativo al conjunto del Eixample. Los cinco registros SUPS Plot 1.0 tienen estado `PARTIAL` y contienen `plotAreaM2`. La [capa de parámetros](https://geoportal.amb.cat/geoserveis/rest/services/qualificacio_refos/MapServer/1) devolvió cero entidades para el área consultada. La altura y edificabilidad por parcela quedan pendientes.

- [Registros SUPS Plot](sups-plots.json)
- [Evidencias y consultas reproducibles](evidencias.json)
- [Respuestas originales de Catastro y del AMB](respuestas-oficiales.zip)
