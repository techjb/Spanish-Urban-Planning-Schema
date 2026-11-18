# Relaciones entre instrumentos en SUPS 1.1

El [esquema de documento](../schemas/v1/planning-document.schema.json) acepta registros `1.0` y `1.1`. Los registros existentes pueden seguir validándose sin migración. Usa `1.1` en los documentos que incorporen estas extensiones. Los campos nuevos se interpretan y validan solo en documentos `1.1`.

Cada entrada de `instrumentRelations` va del documento que la contiene al `targetDocumentId`. El tipo puede ser `MODIFIES` (modifica), `REPLACES` (sustituye), `DEVELOPS` (desarrolla) o `SUSPENDS` (suspende). Usa un `relationId` estable y único dentro del documento y referencia la evidencia en `sourceIds` mediante registros de Regulation Source.

## Alcance normativo

`normativeScope` indica qué parte del instrumento de destino resulta afectada. Es independiente del alcance geográfico.

| Tipo | Significado |
|---|---|
| `ENTIRE_TARGET` | Afecta a todo el contenido normativo del instrumento de destino en el ámbito geográfico indicado. |
| `SPECIFIC_DETERMINATIONS` | Afecta a las determinaciones listadas en `determinations`. |
| `UNKNOWN` | Queda pendiente identificar el contenido normativo afectado. |

Cada determinación se localiza dentro del documento de destino mediante `regulationId`, `article` o ambos. `section` precisa el apartado dentro de un artículo y `parameterId` identifica, cuando procede, el parámetro del catálogo SUPS.

`publicationDate` indica la publicación del instrumento. `effectiveFrom` incluye el primer día de vigencia y `effectiveTo` es el primer día en que deja de estar vigente. La relación tiene sus propias fechas de efecto y sigue la misma convención. Cuando se conocen ambos extremos, el inicio debe preceder al fin. `effectiveEndStatus` distingue `DATED` (fecha de fin conocida, requiere `effectiveTo`), `NO_END_DATE` (la fuente no fija fecha de fin) y `UNKNOWN` (fin pendiente de determinar). Es obligatorio en cada relación y opcional en el documento. La ausencia del estado en el documento equivale a un fin sin documentar. Las fechas de extracción y edición cartográfica se gestionan aparte.

| Tipo de ámbito | Significado |
|---|---|
| `ENTIRE_TARGET` | Todo el ámbito geográfico del instrumento afectado. |
| `ZONING_AREAS` | Unión de las zonas identificadas en `areaIds`. |
| `GEOMETRY` | Polígono o multipolígono GeoJSON propio de la relación. |
| `UNKNOWN` | Alcance geográfico pendiente de determinar. |

Una lista ausente o vacía indica que el documento carece de relaciones registradas. La cobertura documental puede estar incompleta. JSON Schema valida la estructura. El [validador de referencia](../tests/validate_instrument_relations.py) comprueba además el orden de las fechas, los identificadores de relación duplicados y las autorreferencias. La integridad entre registros, la validez espacial y la resolución de conflictos requieren comprobaciones adicionales.

El [ejemplo ficticio](../examples/planning-document-amendment.json) muestra una modificación de altura máxima en dos manzanas con una fecha de efecto propia.
