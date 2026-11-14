"""Offline regression tests for Madrid municipality-wide normalization rules."""
import importlib.util
from pathlib import Path

path=Path(__file__).with_name("audit_madrid_uses.py")
spec=importlib.util.spec_from_file_location("audit_madrid_uses",path)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

cases={
    "RESIDENCIAL VIVIENDA COLECTIVA":("RESIDENTIAL","MULTIFAMILY"),
    "RESIDENCIAL VIVIENDA UNIFAMILIAR":("RESIDENTIAL","SINGLE_FAMILY"),
    "DOTACIONAL ZONAS VERDES BÁSICO":("GREEN_SPACE","OTHER"),
    "DOTACIONAL VÍA PÚBLICA SECUNDARIA LOCAL":("INFRASTRUCTURE","TRANSPORT"),
    "DOTACIONAL DEPORTIVO PÚBLICO BÁSICO":("FACILITIES","SPORTS"),
    "DOTACIONAL EQUIPAMIENTO PÚBLICO BIENESTAR SOCIAL BÁSICO":("FACILITIES","SOCIAL"),
    "SERVICIOS TERCIARIOS":("TERTIARY","OTHER"),
    "USO INDETERMINADO":("UNKNOWN","UNKNOWN"),
}
for label,expected in cases.items():
    actual=module.propose(label,None)
    assert actual==expected,(label,actual,expected)
print("PASS: Madrid use classification regression tests")
