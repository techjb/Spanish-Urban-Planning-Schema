import json
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
for name, example in [('regulation','simple-regulation'),('regulation','conditional-regulation'),('plot','resolved-plot')]:
    schema = json.loads((ROOT / 'schemas' / 'v1' / f'{name}.schema.json').read_text())
    data = json.loads((ROOT / 'examples' / f'{example}.json').read_text())
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(data)
    print(f'PASS: {example}')
