# Prueba de normalización — municipios de validación

Fecha: 2026-11-14. **Estado: auditoría de datos completada; normalización real pendiente de recuperar atributos de planeamiento.** No se han inventado valores.

| Municipio | Registros existentes | Tipo de muestra | Clasificación y uso originales presentes | Normalizados verificados |
|---|---:|---|---|---:|
| Madrid | 20 | Parcelas urbanísticas | No: solo UBOV_ID, sin etiqueta de uso | 0 |
| Valencia | 5 | Parcelas catastrales | No | 0 |
| Barcelona | 5 | Parcelas catastrales | No | 0 |
| Bilbao | 5 | Parcelas catastrales | No | 0 |

## Fuentes urbanísticas identificadas

- **Madrid:** servicio municipal ArcGIS `USOS_SUELO/MapServer/3`, campos `UBOV_ID`, `USP_TX_DENOM`, `ZURV_TX_NOMBRE`. Tabla relacionada de uso cualificado principal `/4`. Fuente: https://sigma.madrid.es/hosted/rest/services/DESARROLLO_URBANO_ACTUALIZADO/USOS_SUELO/MapServer
- **Valencia:** datos abiertos PGOU - Calificaciones, campos `clase`, `califi`, `tipoca`, `uso`, `tipouso`, `categoria`. Fuente: https://opendata.vlci.valencia.es/es/dataset/pgou-calificacions-pgou-calificaciones
- **Barcelona:** Mapa urbanístic de Catalunya (MUC). Es necesario obtener la capa geográfica correspondiente y cruzarla espacialmente con las muestras catastrales. Fuente: https://analisi.transparenciacatalunya.cat/Urbanisme-infraestructures/Dades-del-mapa-urban-stic-de-Catalunya/epsm-zskb
- **Bilbao:** falta seleccionar y obtener una capa oficial de clasificación/calificación con geometría y códigos para realizar la intersección.

## Qué se ha probado

1. Se han inspeccionado los 35 registros originales y se ha comprobado que ninguno incluye el código/denominación urbanística a normalizar.
2. Se ha identificado la fuente y los campos necesarios para Madrid y Valencia.
3. Se ha preparado `tests/pilot_municipal_normalization.py` para descargar los valores originales de los 20 elementos de Madrid y generar propuestas no verificadas.
4. No se ha podido ejecutar una consulta en vivo al servicio municipal desde el entorno de trabajo; por ello no se publican supuestos porcentajes de acierto ni etiquetas inventadas.

## Próximo paso verificable

Ejecutar `python tests/pilot_municipal_normalization.py` con acceso a Internet; revisar las etiquetas propuestas y marcar `VERIFIED` únicamente tras contrastar las fuentes. Para Valencia, Barcelona y Bilbao obtener primero polígonos urbanísticos y cruzarlos con las parcelas catastrales; los registros actuales carecen de geometría almacenada, por lo que será necesario recuperar también las geometrías de parcela.
