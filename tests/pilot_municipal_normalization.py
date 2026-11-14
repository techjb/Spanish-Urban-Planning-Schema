"""Pilot: fetch Madrid original planning labels and suggest SUPS use mappings.

Run with network access: python tests/pilot_municipal_normalization.py
Does not overwrite original municipal validation samples.
"""
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
BASE="https://sigma.madrid.es/hosted/rest/services/DESARROLLO_URBANO_ACTUALIZADO/USOS_SUELO/MapServer/3/query"
OUTPUT=ROOT/"validation/madrid/normalization-pilot.json"

def normalize_text(s):
    s=unicodedata.normalize("NFKD",s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()

def propose_use(label):
    text=normalize_text(label)
    # Only unambiguous lexical suggestions, never VERIFIED without source review.
    patterns=[(r"\bresidencial\b", "RESIDENTIAL"),(r"\bcomercial\b", "COMMERCIAL"),
              (r"\boficinas?\b", "OFFICE"),(r"\bhotelero\b", "HOTEL"),
              (r"\bindustrial\b", "INDUSTRIAL"),(r"\blogistic", "LOGISTICS"),
              (r"\bdotacional\b|\bequipamiento\b", "FACILITIES")]
    matches={use for pat,use in patterns if re.search(pat,text)}
    return next(iter(matches)) if len(matches)==1 else "UNKNOWN"

def main():
    records=json.loads((ROOT/"validation/madrid/sups-urban-planning-plots.json").read_text())
    ids=sorted({int(r["source"]["featureId"]) for r in records})
    params={"where":"UBOV_ID IN ("+",".join(map(str,ids))+")","outFields":"UBOV_ID,USP_TX_DENOM,ZURV_TX_NOMBRE,UBOV_TX_ETIQ","returnGeometry":"false","f":"json"}
    with urlopen(BASE+"?"+urlencode(params),timeout=40) as response:
        payload=json.load(response)
    if "error" in payload: raise RuntimeError(payload["error"])
    by_id={str(f["attributes"]["UBOV_ID"]):f["attributes"] for f in payload.get("features",[]) if f["attributes"].get("UBOV_ID") is not None}
    output=[]
    for rec in records:
        fid=rec["source"]["featureId"]
        a=by_id.get(fid)
        label=a.get("USP_TX_DENOM") if a else None
        proposed=propose_use(label)
        output.append({"plotId":rec["plotId"],"sourceFeatureId":fid,"originalUse":label,"originalZone":a.get("ZURV_TX_NOMBRE") if a else None,"proposedUse":proposed,"mappingStatus":"PROPOSED" if proposed!="UNKNOWN" else "REQUIRES_REVIEW","classification":"UNKNOWN","notes":"La capa de usos no demuestra clasificación del suelo; propuesta léxica pendiente de revisión."})
    OUTPUT.write_text(json.dumps({"source":BASE,"recordCount":len(records),"retrievedCount":len(by_id),"results":output},ensure_ascii=False,indent=2)+"\n")
    print("Madrid: retrieved",len(by_id),"of",len(records),"mapped",sum(x["proposedUse"]!="UNKNOWN" for x in output))
    print("Saved",OUTPUT)

if __name__=="__main__": main()
