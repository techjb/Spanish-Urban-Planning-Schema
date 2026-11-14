# Normalización municipal de clasificación y usos

Normalizar **valores distintos por capa y versión**, no cada polígono. Un código municipal solo puede recibir una equivalencia validada en el contexto de su municipio, instrumento, capa y versión. Las correspondencias siguientes son ficticias y **no deben aplicarse a datos reales**.

## Contrato de correspondencias

Cada entrada incluye `municipalityCode` (INE), `sourceDataset`, `sourceLayer`, `sourceVersion`, `domain` (LAND_CLASSIFICATION o CHARACTERISTIC_USE), `originalCode`, `originalLabel`, `normalizedClass` + `normalizedCategory` o `normalizedUse` + `normalizedSubtype`, `status` (VERIFIED, PROPOSED, REQUIRES_REVIEW), `reviewedBy` y `sourceDocumentId` cuando estén disponibles.

El uso característico de una zona no implica que todos sus usos sean permitidos. Los usos permitidos y compatibles se resuelven por normativa y se guardan en `Urban Planning Plot.allowedUses`.

## Flujo recomendado

1. Importar la capa municipal, conservar el original y extraer pares distintos código/denominación.
2. Resolver primero por diccionario versionado y revisado; sugerir equivalencias nuevas mediante reglas o IA.
3. Enviar a revisión los códigos ambiguos o sin respaldo legal. No marcar `VERIFIED` por coincidencia textual.
4. Aplicar el diccionario a todos los polígonos de esa capa y versión.
5. Guardar `originalCode`, `originalUse` / `originalClass`, `mappingId`, `mappingStatus` y fuentes.
6. Publicar filtros solo con valores verificados por defecto; ofrecer una opción explícita para propuestas/no verificados.
7. Invalidar y recalcular asignaciones si cambia el instrumento, la capa o el diccionario.

La clasificación urbanística no es la naturaleza catastral. Los valores `OTHER` y `UNKNOWN` deben permanecer visibles como ausencia de equivalencia fiable, no como permisos de construcción.
