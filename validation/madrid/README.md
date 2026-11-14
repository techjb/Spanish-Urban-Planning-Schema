# Madrid — vector parcel urban planning validation (discovery)

Date: 2026-11-14. **Status: source verified; no individual parcel records downloaded or calculated.**

## Official service

- Dataset: https://datos.madrid.es/dataset/300744-0-usos-suelo-urbanismo
- Layer metadata: https://sigma.madrid.es/hosted/rest/services/DESARROLLO_URBANO_ACTUALIZADO/USOS_SUELO/MapServer/3?f=pjson
- Service: https://sigma.madrid.es/hosted/rest/services/DESARROLLO_URBANO_ACTUALIZADO/USOS_SUELO/MapServer?f=pjson
- Official planning regulations: https://wpgeoportal.madrid.es/normativa-urbanistica/
- GML-PU format and XSD: https://wpgeoportal.madrid.es/formato-gml-pu-de-parcela-urbanistica/

Layer 3, **Parcelas Urbanísticas**, is polygon geometry, spatial reference **EPSG:25830**, and supports **Query** with JSON, GeoJSON, PBF responses. The service's maximum per request is 2,000 records; use paging or spatial partitions for bulk ingestion.

## Confirmed attributes

| Source field | Meaning | SUPS target |
| --- | --- | --- |
| `UBOV_ID` | Urbanistic plot ID | plot identifier (verify schema property) |
| `ZURV_TX_NOMBRE` | Urban planning zone name | zoning area reference / code after normalization |
| `USP_TX_DENOM` | Primary use | primaryUse (normalize) |
| `AMB_TX_ETIQ` | Planning scope | planning area code |
| `AMB_TX_DENOM` | Scope name | planning area label |
| `UBOV_TX_ETIQ` | Plot label | source plot label |
| `SHAPE.STArea()` | Polygon area in square metres | geometric area; not necessarily legal net plot area |
| `SHAPE` | Polygon | plot geometry |

Do **not** assume GML-PU fields `NORMA` or `EDIFI` are fields in this ArcGIS layer: they do not appear in its published field list.

## Next validation procedure

1. Query a small set of actual layer-3 features; persist immutable source response and request URL.
2. Normalize into SUPS Plot, retaining raw codes and geometries.
3. Cross-check cadastral plots: urbanistic and cadastral parcels may not coincide 1:1. Record overlay/intersection area and mismatch.
4. Map each planning zone to the applicable consolidated ordinance, amendments, and specific planning instruments.
5. Compute only legally supported parameters; mark all others UNKNOWN or CONDITIONAL.
6. Compare 10–20 plots with official viewer and record discrepancies.

## Example ArcGIS REST query

```
GET https://sigma.madrid.es/hosted/rest/services/DESARROLLO_URBANO_ACTUALIZADO/USOS_SUELO/MapServer/3/query
    ?where=1%3D1
    &outFields=UBOV_ID,ZURV_TX_NOMBRE,USP_TX_DENOM,AMB_TX_ETIQ,AMB_TX_DENOM,UBOV_TX_ETIQ
    &returnGeometry=true
    &outSR=4326
    &resultRecordCount=20
    &f=geojson
```

The endpoint and fields are verified from official metadata, but **the query itself has not returned feature records in this environment**. No parcel-level calculation is claimed.

## Legal caveat

The municipal dataset explicitly says its interpretation of the planning designation has **no legal force**. Source ordinance and officially approved changes remain necessary for legal conclusions.
