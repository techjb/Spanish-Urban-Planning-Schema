# Zaragoza — first real-world SUPS validation (draft)

Source: [Zaragoza PGOU consolidated urban regulations](https://www.zaragoza.es/contenidos/urbanismo/pgouz/TR2024/Normas_refundido_2025_con.pdf), articles **4.2.8–4.2.10**, PDF pp. 155–156. Municipal [planning portal](https://www.zaragoza.es/sede/portal/urbanismo/planeamiento/pgouz) labels TR2024 consolidated June 2026.

## Coverage

Two **A-3** regulation records (grades 1 and 2) normalize:
- `maxBuildabilityRatio`: 0.65 / 0.36.
- `maxOccupancyPct`: 35 / 20 percent.
- `minFrontSetbackM`: 3 / 5 m.
- `maxFloors`: conditional by building use in grade 1 (3 unifamiliar, 4 other); 3 in grade 2.
- `maxHeightM`: conditional by building use (grade 1: 10 / 13 m; grade 2: 10 / 10.5 m).
- `minPlotAreaM2`: typology-specific minimums (not a single unconditional parcel minimum).
- `minPlotFrontageM`: 15 m for ordinary subdivisions; exceptional 6 m under stated conditions.

## Findings / limitations

1. **Subdivision vs buildable parcel**: 1,000 m² / 15 m for general new subdivision is distinct from the buildable minimum by typology. The draft schema currently conflates these under `minPlotAreaM2` and `minPlotFrontageM`. Recommend adding `minSubdivisionPlotAreaM2` and `minSubdivisionFrontageM`.
2. **Per-dwelling area vs parcel area**: 500/250/200 m² **per dwelling** is not always a minimum whole-plot area. Prefer `minAreaPerDwellingM2` for these cases; current variants are an interim, lossy mapping.
3. **Shared overlay constraints**: article 4.2.9 also sets a 35% cap for the projected envelope of all floors including basements. This is not identical to `maxOccupancyPct` for grade 2; requires a distinct parameter or explicit calculation basis.
4. **Legal exceptions**: pre-existing registered plots, neighboring construction, detailed studies, and separation rules must be preserved as source-linked conditions; no automatic building entitlement is inferred.
5. **Applicability not yet established**: no cadastral plots or zoning polygons were matched. These records validate ordinance extraction only, **not** effective parcel parameters.
6. **Legal currency**: this is an extraction from a municipal consolidated PDF, not a certification of current legal applicability to a specific plot. Confirm amendments and other instruments before parcel calculations.

## Status

**PARTIAL — ordinance-level proof of concept.** No parcel-level resolution or full legal review completed. All conditional text is explanatory, not executable. See JSON samples for structured extracted values.


## Second pass — five samples (14 November 2026)

Additional **draft** samples:
- `ZARAGOZA-A1-G1.json` — A-1 grade 1, closed-block residential: plot subdivision, street-width-dependent height and floors; article 4.1.8.
- `ZARAGOZA-A6-G1.json` — A-6 grade 1, productive/industrial: subdivision minima depend on block type; setbacks, buildability and height depend on exceptions; article 4.2.20.
- `ZARAGOZA-A2-G4.json` — A-2 grade 4, tertiary and residential uses excluding dwellings: subdivision, occupation and buildability; article 4.2.5.

**Five ordinance/grade samples now recorded, not five independently certified complete regulations.** The new records use proposed catalogue extension keys `minSubdivisionPlotAreaM2`, `minSubdivisionFrontageM` and `maxGroundFloorOccupancyPct`, which are **not yet in the canonical vocabulary**. Some conditions are summarized and are **not executable**. This pass tests expressiveness; it does not establish that every legal exception has been extracted. No zoning polygons or actual parcels have been evaluated.

### Proposed catalogue changes

- `minSubdivisionPlotAreaM2` — minimum area for a new subdivision (distinct from buildability of an existing plot).
- `minSubdivisionFrontageM` — minimum street frontage for subdivision.
- `maxGroundFloorOccupancyPct` — ground-floor occupancy where the rules distinguish floors.
- Consider separate per-dwelling-area constraints and coverage across basement levels.

### Important schema limitation

The draft `regulation.schema.json` currently allows an arbitrary parameter key and permits null variant values. Passing JSON Schema validation therefore only confirms **structural validity**, not that the keys are registered in SUPS or that legal meaning and numeric values are correct. A strict vocabulary/type validator should be added before declaring SUPS 1.0 validated.
