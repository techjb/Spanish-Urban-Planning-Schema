# SUPS 1.0 — Cross-municipality validation audit

Date: 2026-11-14. Source: committed `validation/*` fixtures and their evidence files.

| Municipality | SUPS Plot records | Status | Verified from committed documentation |
| --- | ---: | --- | --- |
| Madrid | 20 | UNKNOWN | 20 municipal urbanistic plot geometries; zoning-name field empty; no legal parameters resolved |
| València | 5 | PARTIAL | Cadastral area and dominant ENS overlay; some plots cross different height polygons |
| Barcelona | 5 | PARTIAL | Cadastral area and AMB zoning 13a / 13E; height and buildability unresolved |
| Bilbao | 5 | PARTIAL | Cadastral area and near-complete overlap with subareas; total floor area verified at **subarea**, not parcel, level |
| Zaragoza | 0 plot records | Ordinance samples | Five regulation/grade samples; not parcel-level evidence |

**35 parcel fixtures across four municipalities, none with fully resolved effective parcel buildability.**

## Conclusions

1. **Structural portability:** SUPS Plot can represent unresolved and partially resolved plots from four municipalities without requiring a new core object shape.
2. **Legal-semantic portability not yet proven:** field-level correctness, conditional rules and amendments still need manual review.
3. **Scope must be explicit:** a subarea's `TechoEdificableTotalSR` cannot be assigned to each intersecting cadastral parcel. Recommend adding a separate planning-unit/aggregate-rights entity or scoped regulation parameter, rather than treating the total as a parcel entitlement.
4. **Urbanistic vs cadastral parcel:** the two geometries and identifiers may differ; retain provenance and overlap metrics.
5. **Spatial conflict:** València height polygons may disagree across one plot; a single unqualified height is unsafe.
6. **Provenance:** a geometrically measured area does not necessarily equal the legally relevant net plot area.

## Reproducible fixture check

```bash
pip install -r requirements-dev.txt
python tests/validate_municipalities.py
```

This validates schema conformance, counts, uniqueness and conservative status/value invariants. It **does not** independently re-query source services, verify all urban planning rules, or calculate legally effective buildability. CI execution remains to be verified.
