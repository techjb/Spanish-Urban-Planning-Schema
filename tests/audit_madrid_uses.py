"""Inventory all distinct Madrid urban planning use codes and suggest SUPS mappings.
Run: python tests/audit_madrid_uses.py
Produces validation/madrid/all-use-mappings.json. No geometry downloads.
"""
import json
import re
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
BASE="https://sigma.madrid.es/hosted/rest/services/DESARROLLO_URBANO_ACTUALIZADO/USOS_SUELO/MapServer/3"
OUTPUT=ROOT/"validation/madrid/all-use-mappings.json"
FIELDS="UGI_ID,USP_TX_DENOM"

def fetch(url, params):
    with urlopen(url+"?"+urlencode(params), timeout=60) as r:
        data=json.load(r)
    if "error" in data: raise RuntimeError(data["error"])
    return data

def normalize(value):
    s=unicodedata.normalize("NFKD",str(value or ""))
    return " ".join("".join(c for c in s if not unicodedata.combining(c)).upper().split())

def propose(label, code):
    t=normalize(label)
    rules=[
        ("ZONAS VERDES","GREEN_SPACE","OTHER"),
        ("ESPACIOS LIBRES","GREEN_SPACE","OTHER"),
        ("VIA PUBLICA","INFRASTRUCTURE","TRANSPORT"),
        ("VIARIO","INFRASTRUCTURE","TRANSPORT"),
        ("APARCAMIENTO","INFRASTRUCTURE","TRANSPORT"),
        ("GARAJE","INFRASTRUCTURE","TRANSPORT"),
        ("DEPORTIV","FACILITIES","SPORTS"),
        ("BIENESTAR SOCIAL","FACILITIES","SOCIAL"),
        ("EDUCATIV","FACILITIES","EDUCATION"),
        ("DOCENTE","FACILITIES","EDUCATION"),
        ("SANITARI","FACILITIES","HEALTH"),
        ("VIVIENDA COLECTIVA","RESIDENTIAL","MULTIFAMILY"),
        ("VIVIENDA UNIFAMILIAR","RESIDENTIAL","SINGLE_FAMILY"),
        ("RESIDENCIAL","RESIDENTIAL","OTHER"),
        ("COMERCIAL","COMMERCIAL","OTHER"),
        ("OFICINA","OFFICE","GENERAL"),
        ("HOTELER","HOTEL","HOTEL"),
        ("LOGISTIC","LOGISTICS","DISTRIBUTION"),
        ("INDUSTRIAL","INDUSTRIAL","OTHER"),
        ("TERCIARI","TERTIARY","OTHER"),
        ("EQUIPAMIENTO","FACILITIES","OTHER"),
        ("DOTACIONAL","FACILITIES","OTHER")]
    for term,use,subtype in rules:
        if term in t: return use,subtype
    if not t: return {"RE":("RESIDENTIAL","OTHER"),"IN":("INDUSTRIAL","OTHER"),"TE":("TERTIARY","OTHER")}.get(normalize(code),("UNKNOWN","UNKNOWN"))
    return "UNKNOWN","UNKNOWN"

def main():
    meta=fetch(BASE,{"f":"json"})
    available={f["name"] for f in meta["fields"]}
    assert set(FIELDS.split(",")).issubset(available), "Source fields changed"
    caps=meta.get("advancedQueryCapabilities",{})
    if not caps.get("supportsDistinct") or not caps.get("supportsPagination"):
        raise RuntimeError("Distinct/pagination not advertised; cannot guarantee complete results")
    size=min(int(meta.get("maxRecordCount",1000)),1000)
    assert size>0
    seen=set()
    offset=0
    while True:
        response=fetch(BASE+"/query",{"f":"json","where":"1=1","outFields":FIELDS,
            "returnDistinctValues":"true","returnGeometry":"false",
            "orderByFields":FIELDS,"resultOffset":offset,"resultRecordCount":size})
        batch=response.get("features",[])
        if not batch: break
        for f in batch:
            a=f["attributes"]
            seen.add((normalize(a.get("UGI_ID")),normalize(a.get("USP_TX_DENOM"))))
        offset+=len(batch)
        print("Distinct pairs fetched:",offset)
        if len(batch)<size and not response.get("exceededTransferLimit",False): break
        if offset>500000: raise RuntimeError("Unexpected number of distinct pairs")
    if not seen: raise RuntimeError("No records returned")
    catalogue=json.loads((ROOT/"vocabularies/land-uses.json").read_text(encoding="utf-8"))
    valid={u["id"]:{s["id"] for s in u["subtypes"]} for u in catalogue["uses"]}
    mappings=[]
    for code,label in sorted(seen):
        use,subtype=propose(label,code)
        assert use in valid and subtype in valid[use]
        mappings.append({"originalCode":code,"originalLabel":label,"normalizedUse":use,
            "normalizedSubtype":subtype,"status":"PROPOSED" if use!="UNKNOWN" else "REQUIRES_REVIEW"})
    summary=dict(Counter(m["status"] for m in mappings))
    result={"municipality":"Madrid","source":BASE,"domain":"CHARACTERISTIC_USE",
        "extractedAt":datetime.now(timezone.utc).isoformat(),
        "scope":"All distinct UGI_ID + USP_TX_DENOM pairs in layer 3",
        "distinctPairCount":len(mappings),"summary":summary,
        "warning":"Lexical proposals only; none legally verified. No land classification inferred.",
        "mappings":mappings}
    OUTPUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Saved",OUTPUT,"with",len(mappings),"pairs",summary)

if __name__=="__main__": main()
