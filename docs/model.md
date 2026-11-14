# SUPS 1.0 data model

SUPS distinguishes **Cadastral Plot** (cadastre-derived parcel and measured or official attributes) from **Urban Planning Plot** (planning-source plot and its resolved or unresolved urbanistic parameters). They are not necessarily spatially identical; one-to-many and many-to-many relationships are possible. Do not invent cadastral references or equivalences.

- `schemas/v1/cadastral-plot.schema.json`: cadastral reference, provenance, official area (only if reported), GIS-measured area (if calculated), cadastral use and optional geometry.
- `schemas/v1/urban-planning-plot.schema.json`: municipal planning plot ID, planning source, applicable regulation references, parameter values and calculation status.
- `schemas/v1/zoning-area.schema.json`: zone geometry, **not** necessarily an urban planning parcel.
- Regulation, Planning Document and Regulation Source retain their existing meanings.

The `plotId` is an urban-planning-source identifier, not a cadastral reference. Links between entities must be evidenced; polygon overlap alone is not legal equivalence. Subarea-wide buildability is not automatically a parcel entitlement. A geometrically measured area is not automatically the legally relevant plot area.

Fixtures: Madrid has 20 urban-planning plots with unknown parameters; València, Barcelona and Bilbao have five cadastral parcels each with GIS-measured areas. These are source-data/structural validations, **not** certified effective building rights.

Conditions in natural language are not executable; absence of a parameter never means unrestricted permission. SUPS is a community draft, not an official standard.

## Search results

Urban Planning Plot now supports `analysisUnit`, `parameterEvidence`, `allowedUses`, `landClassification` and `landClassificationOverlays`. Zoning Area supports `areaType` and classification metadata. These optional extensions describe results for querying, not legal authorization. See [search filters](search-filters.md).
