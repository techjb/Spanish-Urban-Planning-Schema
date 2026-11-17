# SUPS — Spanish Urban Planning Schema

**SUPS 1.0 (draft)** is an open, technology-independent data model for Spanish municipal planning regulations and resolved parcel-level development parameters.

> Community proposal, **not** an official government standard. All examples are fictitious. Planning determinations require verification against legally applicable documents.

## Model

- **Regulation**: normalized municipal ordinance parameters, including fixed values and non-executable natural-language conditions.
- **Cadastral Plot**: cadastral reference, source, urban/rustic/mixed cadastral nature, official built area, and explicitly distinguished measured versus official land area.
- **Urban Planning Plot**: planning-source plot and effective or unresolved urbanistic parameters, including per-parameter evidence, allowed/conditional/prohibited uses, and normalized land classification. These entities are not necessarily equivalent.
- **Planning Document**: source planning instrument.
- **Zoning Area**: geographic applicability, including zoning and land-classification polygons (GeoJSON-like geometry).
- **Regulation Source**: article/page provenance.

The [parameter catalogue](vocabularies/parameters.json) defines **178 identifiers** across 15 groups. This is a draft vocabulary: definitions, legal equivalences and units must be refined against real municipal plans before stable release.

## Structure

- [schemas/v1](schemas/v1): six JSON Schema Draft 2020-12 schemas
- [vocabularies](vocabularies): parameter identifiers, normalized [land classifications](vocabularies/land-classifications.json), hierarchical [land uses](vocabularies/land-uses.json), and status vocabulary
- [examples](examples): fixed and conditional ordinances and an illustrative urban-planning plot
- [docs/model.md](docs/model.md): model overview
- [tests/validate.py](tests/validate.py): example validation
- [.github/workflows/validate.yml](.github/workflows/validate.yml): CI

## Validation

```bash
pip install -r requirements-dev.txt
python tests/validate.py
python tests/validate_filters.py
python tests/validate_vocabularies.py
```

## Principles

1. Preserve original ordinance terminology and source references.
2. Do not treat missing data as unrestricted development rights.
3. Do not interpret conditional natural-language rules as executable logic.
4. Keep legal effective dates separate from extraction and calculation dates.
5. Track all applicable regulation versions per urban-planning plot.
6. Distinguish cadastral parcels, urban-planning parcels and zoning areas; never infer one-to-one correspondence.

## Status

This repository contains an **initial draft**, not a legally validated or feature-complete standard. Contributions and test cases from municipalities are welcome.

## License

MIT. See [LICENSE](LICENSE).

## Goolzoom Suelo search attributes

Search-ready attributes include `parameters.effectiveBuildabilityRatio`, `parameters.effectiveBuildableAreaM2`, `parameterEvidence`, `allowedUses`, and `landClassification`. Only resolved/verified values should be presented as confirmed; estimated or unknown values must remain distinguishable. Use a materialized indexed search table for high-volume filtering. A planning parcel is not necessarily a cadastral parcel, and multiple classifications can overlap an analysis unit. See [search model](docs/search-filters.md).

## Municipal normalization

Normalize distinct source codes per municipality, layer and version before assigning map colors. Keep original codes, legal terminology, provenance and review status. See [municipal normalization](docs/municipal-normalization.md) and the [fictional mapping example](examples/municipal-mappings.json). Zone characteristic use is distinct from legally permitted plot uses.
