# Parcel search filters (SUPS draft 1.0)

SUPS stores facts and calculated results; it does not itself implement SQL indexes or certify legal buildability.

## Buildability

- `parameters.effectiveBuildabilityRatio`: resolved effective buildability coefficient, m²t/m²s.
- `parameters.effectiveBuildableAreaM2`: resolved total computable buildable floor area (m²t).
- `parameters.remainingBuildableAreaM2`: remaining entitlement, if independently calculated.
- `parameterEvidence.<parameter>`: individual `status`, `method`, source regulation/area IDs and `basisAreaM2` where applicable.

A global `calculationStatus` of `PARTIAL` does not invalidate an individually resolved parameter; conversely, do not treat an unproven parameter as verified.

## Uses

`allowedUses[]` contains normalized `use`, `status` (ALLOWED, CONDITIONAL, PROHIBITED, UNKNOWN), `role` (PRIMARY, COMPATIBLE, ALTERNATIVE, COMPLEMENTARY, UNKNOWN), original municipality label, optional use-specific ceiling, conditions and evidence. A maximum by use is not additive to another use's ceiling unless a rule explicitly permits it. The catalogue's `primaryUse`, `permittedUses`, etc. continue to describe **regulation** source values.

## Classification

`landClassification` has normalized `class` (URBAN, DEVELOPABLE, NON_DEVELOPABLE, OTHER, UNKNOWN), `category`, original terminology, jurisdiction, verification, source references and optional `planningStatus`. `planningStatus` is separately determined; URBAN + CONSOLIDATED alone is not a building permit. The categories vary by autonomous community and must not be forced into an inaccurate national equivalent. Use OTHER and retain original terms when necessary.

`landClassificationOverlays[]` records partial spatial overlaps. A single classification field must not silently imply homogeneous coverage of an entire parcel.

`Zoning Area.areaType` can be ZONING, LAND_CLASSIFICATION or MIXED. A classification area is not necessarily an ordinance zone or an urban-planning parcel.

## Analysis unit and operational search

`analysisUnit` identifies whether the calculated result refers to a municipal urban-planning plot or a cadastral plot used as an analysis unit. If using a cadastral unit without an officially identified urban-planning plot, its urban-planning status and parcel equivalence must not be asserted.

For Goolzoom Suelo, denormalize validated numeric results and use/classification associations into indexed SQL Server tables. Filter by (a) minimum effective buildability ratio, (b) minimum effective buildable area, (c) permitted/conditional use and primary/compatible role, (d) classification/category and (e) evidence status. Treat unknown results separately rather than treating them as zero or as unconstrained.

All values in `examples/resolved-plot.json` are fictional and only demonstrate schema structure.
