# SUPS — Spanish Urban Planning Schema

**SUPS 1.0 (draft)** is an open, technology-independent data model for Spanish municipal planning regulations and resolved parcel-level development parameters.

> Community proposal, **not** an official government standard. All examples are fictitious. Planning determinations require verification against legally applicable documents.

## Model

- **Regulation**: normalized municipal ordinance parameters, including fixed values and non-executable natural-language conditions.
- **Plot**: effective parcel-level parameters calculated upstream.
- **Planning Document**: source planning instrument.
- **Zoning Area**: geographic applicability (GeoJSON-like geometry).
- **Regulation Source**: article/page provenance.

The [parameter catalogue](vocabularies/parameters.json) defines **175 initial identifiers** across 15 groups. This is a draft vocabulary: definitions, legal equivalences and units must be refined against real municipal plans before stable release.

## Structure

- [schemas/v1](schemas/v1): five JSON Schema Draft 2020-12 schemas
- [vocabularies](vocabularies): parameter identifiers and status vocabulary
- [examples](examples): fixed and conditional ordinances and resolved plots
- [docs/model.md](docs/model.md): model overview
- [tests/validate.py](tests/validate.py): example validation
- [.github/workflows/validate.yml](.github/workflows/validate.yml): CI

## Validation

```bash
pip install -r requirements-dev.txt
python tests/validate.py
```

## Principles

1. Preserve original ordinance terminology and source references.
2. Do not treat missing data as unrestricted development rights.
3. Do not interpret conditional natural-language rules as executable logic.
4. Keep legal effective dates separate from extraction and calculation dates.
5. Track all applicable regulation versions per plot.
6. Distinguish zoning-level values from parcel-level resolved results.

## Status

This repository contains an **initial draft**, not a legally validated or feature-complete standard. Contributions and test cases from municipalities are welcome.

## License

MIT. See [LICENSE](LICENSE).
