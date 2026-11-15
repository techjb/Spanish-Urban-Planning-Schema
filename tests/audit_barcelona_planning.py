"""Inventory Barcelona's AMB zoning and MUC municipal classification."""
import json
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from audit_madrid_uses import fetch

ROOT = Path(__file__).resolve().parents[1]
AMB = "https://geoportal.amb.cat/geoserveis/rest/services/qualificacio_refos/MapServer/0"
LEGEND = AMB.rsplit("/", 1)[0] + "/legend"
MUC = "https://analisi.transparenciacatalunya.cat/resource/epsm-zskb.json"
MUC_SPEC = "https://territori.gencat.cat/web/.content/home/06_territori_i_urbanisme/07_observatori_territori/mapa_urbanistic_de_catalunya/estandard/documents/et_mucs.pdf"
REGIME_GLOSSARY = "https://territori.gencat.cat/ca/06_territori_i_urbanisme/planejament_urbanistic/planejament_general/abreviacions_i_acronims/"
DENSITY_RULES = "https://bcnroc.ajuntament.barcelona.cat/jspui/bitstream/11703/112776/1/DOGC_pla_metropolita_12_des.pdf"
EIXAMPLE_RULES = "https://contractaciopublica.cat/portal-api/descarrega-document/300959670/276D8CE7DAECF912F3C19514BC027DB0"
AMB_CRITERIA = "https://geoportalplanejament.amb.cat/Informacio/Contingut/Contingut/Contingut_ca.html"
EQUIPMENT_22 = "https://bcnroc.ajuntament.barcelona.cat/jspui/bitstream/11703/134237/4/GM_Conveni-AjuntamentGeneralitatINCAS%C3%92L-HabitatgesProtecci%C3%B3OficialLloguerAssequible-Annex2_2024.pdf"
PUBLIC_HOUSING = "https://bcnroc.ajuntament.barcelona.cat/jspui/bitstream/11703/89281/1/19178.pdf"
HERITAGE_EQUIPMENT = "https://bcnroc.ajuntament.barcelona.cat/jspui/bitstream/11703/86881/1/3201.pdf"
PUBLIC_GREEN = "https://ajuntament.barcelona.cat/instituturbanisme/sites/default/files/2024-05/campanya_terrasses_compressed.pdf"
MARINA_HOUSING = "https://ajuntament.barcelona.cat/instituturbanisme/sites/default/files/2024-05/03_Marina_Zona_Franca_Sector_14.pdf"
HOUSING_22 = "https://bcnroc.ajuntament.barcelona.cat/jspui/bitstream/11703/135968/1/GM_instruccio-22-arroba-annex_2024.pdf"
CIUTAT_VELLA_HOUSING = "https://ajuntament.barcelona.cat/fomentdeciutat/data/12069-ccaa2010.pdf"
PRIM_HOUSING = "https://www.gencat.cat/territori/urbanisme/ctu_inf/SUB_inf_20220225.pdf"
SOCIAL_HOUSING = "https://bcnroc.ajuntament.barcelona.cat/jspui/bitstream/11703/85328/4/gm2014_09_20_num_25.pdf"
INE = "08019"
CLASSES = {
    "SUC": ("URBAN", "CONSOLIDATED"),
    "SNC": ("URBAN", "UNCONSOLIDATED"),
    "SUD": ("DEVELOPABLE", "SECTORIZED"),
    "SND": ("DEVELOPABLE", "NON_SECTORIZED"),
    "SNU": ("NON_DEVELOPABLE", "UNSPECIFIED"),
}
# AMB SU identifies the class only. Preserve the more specific MUC categories separately.
AMB_CLASSES = {"SU": ("URBAN", "UNSPECIFIED"), "SNU": CLASSES["SNU"],
               "SUD": CLASSES["SUD"], "SUNC": CLASSES["SNC"]}
USES = {
    "12": ("RESIDENTIAL", "UNSPECIFIED"),
    "12b": ("RESIDENTIAL", "UNSPECIFIED"),
    "7hd": ("FACILITIES", "OTHER"),
    "F": ("RESIDENTIAL", "SINGLE_FAMILY"),
    "T": ("TERTIARY", "UNSPECIFIED"),
    **dict.fromkeys(("27", "28", "29"), ("OTHER", "OTHER")),
    **dict.fromkeys(("1a", "2", "3", "5"), ("INFRASTRUCTURE", "TRANSPORT")),
    "4": ("INFRASTRUCTURE", "UTILITIES"),
    "25": ("FACILITIES", "OTHER"),
    "5b": ("INFRASTRUCTURE", "TRANSPORT"),
    "13a": ("RESIDENTIAL", "MULTIFAMILY"),
    "13b": ("RESIDENTIAL", "MULTIFAMILY"),
    **dict.fromkeys(("6a", "6b", "6c"), ("GREEN_SPACE", "PARK")),
    **dict.fromkeys(("7a", "7b", "7c"), ("FACILITIES", "UNSPECIFIED")),
    **dict.fromkeys(("22a", "22b"), ("INDUSTRIAL", "UNSPECIFIED")),
    **dict.fromkeys(("20a/5", "20a/6", "20a/7", "20a/8", "20a/9", "20a/9b"),
                    ("RESIDENTIAL", "MULTIFAMILY")),
    **dict.fromkeys(("20a/9u", "20a/10", "20a/11", "20a/12"),
                    ("RESIDENTIAL", "SINGLE_FAMILY")),
    "24": ("AGRICULTURAL", "FARMING"),
    "EL": ("GREEN_SPACE", "UNSPECIFIED"),
    "ZL": ("LOGISTICS", "DISTRIBUTION"),
}
DERIVED_USES = {
    ("13a", "13E", "2000/002253"): ("RESIDENTIAL", "MULTIFAMILY", EIXAMPLE_RULES),
    **{(base, key, "2007/029524"): ("RESIDENTIAL", "UNSPECIFIED", CIUTAT_VELLA_HOUSING)
       for base, key in (("12", "12c-hs"), ("12", "12d-hs"), ("12b", "12b-hs"))},
    ("18", "18hp", "2019/069475"): ("RESIDENTIAL", "UNSPECIFIED", PRIM_HOUSING),
}
DERIVED_FAMILIES = {
    **{("18", key): ("RESIDENTIAL", "UNSPECIFIED", SOCIAL_HOUSING)
       for key in ("18hs", "18HS")},
    **{("18", key): ("RESIDENTIAL", "UNSPECIFIED", EQUIPMENT_22)
       for key in ("18hp", "18HP", "22@HS")},
    **{("13a", key): ("RESIDENTIAL", "UNSPECIFIED", HOUSING_22)
       for key in ("13@", "13@C")},
    ("15", "15@h(p)"): ("RESIDENTIAL", "UNSPECIFIED", EQUIPMENT_22),
    ("12", "F"): ("RESIDENTIAL", "SINGLE_FAMILY", AMB_CRITERIA),
    ("7hd", "7AD"): ("FACILITIES", "OTHER", EQUIPMENT_22),
    ("7a-7hd", "(7@/7AD)"): ("FACILITIES", "UNSPECIFIED", EQUIPMENT_22),
    **{(base, "22@T"): ("TERTIARY", "UNSPECIFIED", EQUIPMENT_22)
       for base in ("22@", "18")},
    **{("22@", key): ("TERTIARY", "UNSPECIFIED", EQUIPMENT_22)
       for key in ("22@T-hpl", "(22@T)")},
    **{("18", key): ("RESIDENTIAL", "UNSPECIFIED", EQUIPMENT_22)
       for key in ("18@hp", "18@hp/hpl", "(18@hp/hpl)", "18@h/hp/hpl")},
    ("15", "15@h"): ("RESIDENTIAL", "UNSPECIFIED", HOUSING_22),
    ("6a", "VP"): ("GREEN_SPACE", "UNSPECIFIED", PUBLIC_GREEN),
    **{(base, "6"): ("GREEN_SPACE", "PARK", LEGEND) for base in ("6a", "6b", "6c")},
    **{(base, "7"): ("FACILITIES", "UNSPECIFIED", LEGEND) for base in ("7a", "7b", "7c")},
    **{(base, "7(p)"): ("FACILITIES", "UNSPECIFIED", HERITAGE_EQUIPMENT)
       for base in ("7a", "7b", "7c")},
    **{(base, "HD/7"): ("FACILITIES", "OTHER", MARINA_HOUSING) for base in ("7hd", "7a")},
    ("7a", "7@"): ("FACILITIES", "UNSPECIFIED", EQUIPMENT_22),
    ("7a", "7@(p)"): ("FACILITIES", "UNSPECIFIED", EQUIPMENT_22),
    **{("7hd", key): ("FACILITIES", "OTHER", PUBLIC_HOUSING)
       for key in ("HD/7-j", "HD/7-g")},
}


def main():
    fields = ("REGIM", "CLAU_URB", "CLAU_PD", "EXP_PD", "PLAN", "DESCRIP", "US_SECT")
    where = f"CODI_INE = '{INE}'"
    query = AMB + "/query"
    total = fetch(query, {"f": "json", "where": where, "returnCountOnly": "true"})["count"]
    ids = sorted(fetch(query, {"f": "json", "where": where, "returnIdsOnly": "true"})["objectIds"])
    if not ids or len(ids) != len(set(ids)) or len(ids) != total:
        raise RuntimeError("AMB identifiers do not match the municipal count")
    counts = Counter()
    for start in range(0, len(ids), 200):
        batch = ids[start:start + 200]
        response = fetch(query, {"f": "json", "where": where, "objectIds": ",".join(map(str, batch)),
                                 "outFields": ",".join(("OBJECTID", "CODI_INE", *fields)),
                                 "returnGeometry": "false"})
        rows = [feature["attributes"] for feature in response["features"]]
        if (response.get("exceededTransferLimit") or sorted(row["OBJECTID"] for row in rows) != batch
                or any(row["CODI_INE"] != INE for row in rows)):
            raise RuntimeError("Incomplete or out-of-scope AMB response")
        counts.update(tuple(row[field] for field in fields) for row in rows)

    muc = fetch(MUC, {"codi_ine_5_txt": INE, "$order": "any DESC", "$limit": 1})[0]
    if muc["codi_ine_5_txt"] != INE:
        raise RuntimeError("Incorrect MUC municipality")
    areas = []
    for code, (land_class, category) in CLASSES.items():
        source_field = "_05_" + code.lower()
        value = Decimal(muc[source_field])
        if not value.is_finite() or value < 0:
            raise RuntimeError(f"Invalid MUC area for {code}")
        areas.append({"originalCode": code, "sourceField": source_field, "areaHa": float(value),
                      "normalizedClass": land_class, "normalizedCategory": category,
                      "status": "DOCUMENTED", "evidence": MUC_SPEC})

    for file, key, item_key in (
        ("land-classifications.json", "classes", "categories"),
        ("land-uses.json", "uses", "subtypes"),
    ):
        catalog = json.loads((ROOT / "vocabularies" / file).read_text(encoding="utf-8"))
        valid = {(item["id"], sub["id"]) for item in catalog[key] for sub in item[item_key]}
        pairs = (set(USES.values()) | {value[:2] for value in DERIVED_USES.values()}
                 | {value[:2] for value in DERIVED_FAMILIES.values()}
                 if key == "uses" else set(CLASSES.values()) | set(AMB_CLASSES.values()))
        if not pairs <= valid:
            raise RuntimeError(f"Invalid mappings for {file}")

    groups, pending = [], Counter()
    class_summary, use_summary = Counter(), Counter()
    for values, count in sorted(counts.items(), key=lambda entry: (-entry[1], repr(entry[0]))):
        original = dict(zip(fields, values))
        regime, zoning = original["REGIM"], original["CLAU_URB"]
        land_class, category = AMB_CLASSES.get(regime, ("UNKNOWN", "UNKNOWN"))
        use, subtype = USES.get(zoning, ("UNKNOWN", "UNKNOWN"))
        source_field = "CLAU_URB"
        evidence = DENSITY_RULES if zoning in ("12", "12b", "13a", "13b") else LEGEND
        if zoning in ("7hd", "F", "T"):
            evidence = AMB_CRITERIA
        class_status = "DOCUMENTED" if regime in AMB_CLASSES else "REQUIRES_REVIEW"
        # The legend describes base zoning. Derived keys may change the dominant use.
        if original["CLAU_PD"] and original["CLAU_PD"] != zoning:
            key = (zoning, original["CLAU_PD"], original["EXP_PD"])
            use, subtype = "UNKNOWN", "UNKNOWN"
            source_field = "CLAU_PD"
            mapping = DERIVED_USES.get(key) or DERIVED_FAMILIES.get(key[:2])
            if mapping:
                use, subtype, evidence = mapping
            elif zoning in ("6a", "6b", "6c", "7a", "7b", "7c") and key[1] in (
                zoning + "(p)", zoning + "*", "(" + zoning + ")",
            ):
                use, subtype = USES[zoning]
                evidence = AMB_CRITERIA
        use_status = "DOCUMENTED" if use != "UNKNOWN" else "REQUIRES_REVIEW"
        class_summary[class_status] += count
        use_summary[use_status] += count
        use_result = {"status": use_status, "normalizedUse": use, "normalizedSubtype": subtype}
        if use_status == "DOCUMENTED":
            provenance = {"sourceField": source_field, "originalCode": original[source_field],
                          "basis": "ZONING_DESIGNATION"}
            if original["EXP_PD"]:
                provenance["planningInstrument"] = original["EXP_PD"]
            use_result.update(provenance=provenance, evidence=evidence)
        else:
            pending[zoning, original["CLAU_PD"]] += count
        classification = {"normalizedClass": land_class, "normalizedCategory": category,
                          "status": class_status}
        if regime == "SUNC":
            classification["evidence"] = REGIME_GLOSSARY
        groups.append({"original": original, "recordCount": count,
                       "classification": classification,
                       "use": use_result})
    result = {
        "municipality": "Barcelona", "municipalityCode": INE,
        "extractedAt": datetime.now(timezone.utc).isoformat(),
        "muc": {"source": MUC, "year": muc["any"], "municipalAreaHa": float(muc["superficie_ha"]),
                "classification": areas},
        "amb": {"source": AMB, "where": where, "recordCount": total, "groupCount": len(groups),
                "classificationSummary": dict(class_summary), "useSummary": dict(use_summary),
                "pendingUseByZoning": [{"CLAU_URB": key[0], "CLAU_PD": key[1], "recordCount": count}
                                      for key, count in sorted(pending.items(), key=lambda row: (-row[1], repr(row[0])))],
                "groups": groups},
    }
    output = ROOT / "validation/barcelona/planning-audit.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(muc["any"], total, len(groups), dict(class_summary), dict(use_summary))


if __name__ == "__main__":
    main()
