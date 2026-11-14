# SUPS — Spanish Urban Planning Schema

**SUPS 1.0 (draft)** is an open, technology-independent data model for Spanish municipal planning regulations and resolved parcel-level development parameters.

> Community proposal, **not** an official government standard. All examples are fictitious. Planning determinations require verification against legally applicable documents.

## Model

- **Regulation**: normalized municipal ordinance parameters, including fixed values and non-executable natural-language conditions.
- **Cadastral Plot**: cadastral reference, source, cadastral attributes and explicitly distinguished measured versus official area.\n- **Urban Planning Plot**: planning-source plot and effective or unresolved urbanistic parameters. These entities are not necessarily equivalent.
- **Planning Document**: source planning instrument.
- **Zoning Area**: geographic applicability (GeoJSON-like geometry).
- **Regulation Source**: article/page provenance.

The [parameter catalogue](vocabularies/parameters.json) defines **178 identifiers** across 15 groups. This is a draft vocabulary: definitions, legal equivalences and units must be refined against real municipal plans before stable release.

## Structure

- [schemas/v1](schemas/v1): six JSON Schema Draft 2020-12 schemas
- [vocabularies](vocabularies): parameter identifiers and status vocabulary
- [examples](examples): fixed and conditional ordinances and an illustrative urban-planning plot
- [docs/model.md](docs/model.md): model overview
- [tests/validate.py](tests/validate.py): example validation
- [.github/workflows/validate.yml](.github/workflows/validate.yml): CI

## Validation

```bash
pip install -r requirements-dev.txt
python tests/validate.py\npython tests/validate_municipalities.py
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
