# Relaciones entre instrumentos en SUPS 1.1

El [esquema de documento](../schemas/v1/planning-document.schema.json) acepta registros `1.0` y `1.1`. Los registros existentes pueden seguir validándose sin migración. Usa `1.1` en los documentos que incorporen estas extensiones.

Cada entrada de `instrumentRelations` va del documento que la contiene al `targetDocumentId`. El tipo puede ser `MODIFIES` (modifica), `REPLACES` (sustituye), `DEVELOPS` (desarrolla) o `SUSPENDS` (suspende). Usa un `relationId` estable y único dentro del documento y referencia la evidencia en `sourceIds` mediante registros de Regulation Source.

`affectedRegulationIds` identifica las ordenanzas afectadas y `affectedProvisions` permite indicar artículos, apartados o determinaciones del instrumento afectado. Si faltan ambos campos, el detalle de las disposiciones afectadas queda sin especificar.

`publicationDate` indica la publicación del instrumento. `effectiveFrom` incluye el primer día de vigencia y `effectiveTo` es el primer día en que deja de estar vigente. La relación tiene sus propias fechas de efecto y sigue la misma convención. Cuando se conocen ambos extremos, el inicio debe preceder al fin. Las fechas ausentes quedan sin documentar. Las fechas de extracción y edición cartográfica se gestionan aparte.

| Tipo de ámbito | Significado |
|---|---|
| `ENTIRE_TARGET` | Todo el ámbito geográfico del instrumento afectado. |
| `ZONING_AREAS` | Unión de las zonas identificadas en `areaIds`. |
| `GEOMETRY` | Polígono o multipolígono GeoJSON propio de la relación. |
| `UNKNOWN` | Alcance geográfico pendiente de determinar. |

Una lista ausente o vacía indica que el documento carece de relaciones registradas. La cobertura documental puede estar incompleta. JSON Schema valida la estructura. El orden de las fechas, la integridad de referencias, la validez espacial y la resolución de conflictos requieren comprobaciones adicionales.

El [ejemplo ficticio](../examples/planning-document-amendment.json) muestra una modificación de altura máxima en dos manzanas con una fecha de efecto propia.
