"""Madrid SUPS use normalization. Offline: --from-file; online: default."""
import argparse
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
BASE="https://sigma.madrid.es/hosted/rest/services/DESARROLLO_URBANO_ACTUALIZADO/USOS_SUELO/MapServer/3/query"
OUTPUT=ROOT/"validation/madrid/normalization-pilot.json"
MAPPINGS=ROOT/"validation/madrid/use-mappings.json"

def normalize_text(value):
    value=unicodedata.normalize("NFKD", value or "")
    return " ".join("".join(c for c in value if not unicodedata.combining(c)).upper().split())

def propose_use(label):
    t=normalize_text(label)
    # Specific categories before the general DOTACIONAL prefix.
    rules=[
        (r"\bZONAS? VERDES?\b", "GREEN_SPACE", "OTHER"),
        (r"\bVIA PUBLICA\b", "INFRASTRUCTURE", "TRANSPORT"),
        (r"\bDEPORTIV", "FACILITIES", "SPORTS"),
        (r"\bBIENESTAR SOCIAL\b", "FACILITIES", "SOCIAL"),
        (r"\bVIVIENDA COLECTIVA\b", "RESIDENTIAL", "MULTIFAMILY"),
        (r"\bVIVIENDA UNIFAMILIAR\b", "RESIDENTIAL", "SINGLE_FAMILY"),
        (r"\bRESIDENCIAL\b", "RESIDENTIAL", "OTHER"),
        (r"\bSERVICIOS TERCIARIOS\b", "TERTIARY", "OTHER"),
        (r"\bCOMERCIAL\b", "COMMERCIAL", "OTHER"),
        (r"\bOFICINAS?\b", "OFFICE", "GENERAL"),
        (r"\bHOTELER", "HOTEL", "HOTEL"),
        (r"\bINDUSTRIAL\b", "INDUSTRIAL", "OTHER"),
        (r"\bLOGISTIC", "LOGISTICS", "DISTRIBUTION"),
        (r"\bEQUIPAMIENTO\b|\bDOTACIONAL\b", "FACILITIES", "OTHER")
    ]
    for pattern, use, subtype in rules:
        if re.search(pattern, t):
            return use, subtype
    return "UNKNOWN", "UNKNOWN"

def generate(records, source, retrieved_count):
    catalogue=json.loads((ROOT/"vocabularies/land-uses.json").read_text(encoding="utf-8"))
    valid={u["id"]:{s["id"] for s in u["subtypes"]} for u in catalogue["uses"]}
    mappings={}
    results=[]
    for rec in records:
        label=rec.get("originalUse")
        key=normalize_text(label)
        if key not in mappings:
            use,subtype=propose_use(label)
            assert use in valid and subtype in valid[use]
            mappings[key]={"mappingId":"MADRID-USE-"+str(len(mappings)+1).zfill(3),
                           "originalLabel":key,"normalizedUse":use,"normalizedSubtype":subtype,
                           "status":"PROPOSED" if use!="UNKNOWN" else "REQUIRES_REVIEW"}
        m=mappings[key]
        results.append({**rec,"proposedUse":m["normalizedUse"],"proposedSubtype":m["normalizedSubtype"],
                        "mappingId":m["mappingId"],"mappingStatus":m["status"],
                        "classification":"UNKNOWN",
                        "notes":"Propuesta por etiqueta; pendiente de revisión normativa. No acredita clasificación del suelo."})
    mapping_output={"municipality":"Madrid","source":source,"domain":"CHARACTERISTIC_USE",
                    "mappings":list(mappings.values())}
    output={"source":source,"recordCount":len(records),"retrievedCount":retrieved_count,"results":results}
    return output,mapping_output

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--from-file",action="store_true",help="Reprocesa el JSON descargado sin red")
    args=parser.parse_args()
    if args.from_file:
        old=json.loads(OUTPUT.read_text(encoding="utf-8-sig"))
        records=old["results"]
        source=old["source"]
        retrieved=old["retrievedCount"]
    else:
        original=json.loads((ROOT/"validation/madrid/sups-urban-planning-plots.json").read_text(encoding="utf-8"))
        ids=sorted({int(x["source"]["featureId"]) for x in original})
        params={"where":"UBOV_ID IN ("+",".join(map(str,ids))+")",
                "outFields":"UBOV_ID,USP_TX_DENOM,ZURV_TX_NOMBRE,UBOV_TX_ETIQ",
                "returnGeometry":"false","f":"json"}
        with urlopen(BASE+"?"+urlencode(params),timeout=40) as response:
            payload=json.load(response)
        if "error" in payload: raise RuntimeError(payload["error"])
        by_id={str(f["attributes"]["UBOV_ID"]):f["attributes"] for f in payload.get("features",[])
               if f["attributes"].get("UBOV_ID") is not None}
        records=[]
        for x in original:
            fid=x["source"]["featureId"]
            a=by_id.get(fid) or {}
            records.append({"plotId":x["plotId"],"sourceFeatureId":fid,
                            "originalUse":a.get("USP_TX_DENOM"),
                            "originalZone":a.get("ZURV_TX_NOMBRE")})
        source=BASE
        retrieved=len(by_id)
    result,mapping=generate(records,source,retrieved)
    OUTPUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    MAPPINGS.write_text(json.dumps(mapping,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Madrid: {retrieved}/{len(records)} recovered; {sum(x['proposedUse']!='UNKNOWN' for x in result['results'])} use proposals; {len(mapping['mappings'])} unique labels")
    print("Saved:",OUTPUT,MAPPINGS)

if __name__=="__main__":
    main()
