"""Audit classification and use codes in València's PGOU layer."""

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from audit_madrid_uses import fetch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "https://geoportal.valencia.es/server/rest/services/OPENDATA/UrbanismoEInfraestructuras/MapServer/231"
PLAN = "https://www.valencia.es/ayuntamiento/urbanismo2.nsf/0/293C3352E4C33D49C1257FD1002D5211/%24FILE/O.1-Calificacion%20del%20Suelo%20Serie%20B_firmado.pdf"
RULES = "https://www.valencia.es/documents/20142/629631/10.%2BNormas%2BUrban%EF%BF%BDsticas.%2B%28Transcripci%EF%BF%BDn%29.pdf/ba78c368-ab86-c719-b9c4-e504111b3863"
PUBLIC_SPACES = "https://www.valencia.es/ayuntamiento/urbanismo2.nsf/0/BC94A381E8155FB1C1258AD8002BD607/%24FILE/PUBLICACI%C3%93N%20ANUNCIO%20BOP.pdf?OpenElement=&lang=2"
PUBLIC_SERVICES = "https://www.valencia.es/cas/actualidad/-/content/ampliaci%C3%B3n-centre-cruz-roja"
ZONING_RULES = "https://www.valencia.es/documents/20142/4271204/_Normas%2BUrbanisticas%2BPGOU%2Bcon%2BINDICE.pdf/50679b78-5d70-1a19-c34b-6019b16ac71b?t=1663233568035"
COUNCIL_MINUTES = "https://www.valencia.es/documents/20142/264010/A_00001_20230427_0945_0_firmadoweb.pdf/b4bd161b-695b-2716-080c-652ab59a4fa0?t=1686818032040"
CIUTAT_VELLA_ROADS = "https://www.valencia.es/documents/20142/4271200/guillem_de_castro_101_firmada.pdf/8f9452a0-0b53-f902-24b6-e1f115cb45f7"
PRIMARY_ZONES = "https://www.valencia.es/ayuntamiento/urbanismo2.nsf/0/19127A86DB23CD45C1257DBD0043EAAB/%24FILE/P3%20ZONAS%20PRIMARIAS%20H1_firmado.pdf?OpenElement="
CIUTAT_VELLA_USES = "https://mhv.valencia.es/ayuntamiento/urbanismo2.nsf/0/FC6389A1526B56D6C1258B66002FEEF3/%24FILE/EF.N%203.%20PLANOS%20ORDENACION%20O-10..pdf?OpenElement="

SECONDARY_GARDENS = "https://www.valencia.es/ayuntamiento/urbanismo2.nsf/0/79E44B6EA572C8AFC1258B950029F996/%24FILE/36-2023%20Anuncio%20BOP%20Aprobaci%C3%B3n%20Definitiva.pdf?OpenElement=&lang=1"
FUENTE_SAN_LUIS = "https://mhv.valencia.es/ayuntamiento/urbanismo2.nsf/0/BD5C878410F910F4C1258CB600261B50/%24FILE/398-2024%20Anuncio%20BOP%20Aprobaci%C3%B3n%20Definitiva.pdf?OpenElement=&lang=2"
CIUTAT_VELLA_FACILITIES = "https://www.valencia.es/ayuntamiento/urbanismo2.nsf/0/C4B888C524B81ABBC1258B66002156CF/%24FILE/1.5.%20ESTUDI%20DE%20VIABILITAT%20ECON%C3%92MICA%20I%20MEM%C3%92RIA%20DE%20SOSTENIBILITAT%20ECON%C3%92MICA.%20Juny%2024.pdf?OpenElement="

CLASSES = {
    "SU": ("URBAN", "Suelo urbano"),
    "SUP": ("DEVELOPABLE", "Suelo urbanizable programado"),
    "SUNP": ("DEVELOPABLE", "Suelo urbanizable no programado"),
    "SNU": ("NON_DEVELOPABLE", "Suelo no urbanizable"),
}
USES = {
    "GTR": ("INFRASTRUCTURE", "TRANSPORT", ZONING_RULES),
    "DEL": ("GREEN_SPACE", "UNSPECIFIED", ZONING_RULES),
    "DED": ("FACILITIES", "EDUCATION", ZONING_RULES),
    "DRE": ("FACILITIES", "OTHER", ZONING_RULES),
    "SEL": ("GREEN_SPACE", "UNSPECIFIED", PUBLIC_SPACES),
    "PQL": ("GREEN_SPACE", "UNSPECIFIED", PRIMARY_ZONES),
    "PTR": ("INFRASTRUCTURE", "TRANSPORT", PRIMARY_ZONES),
    "GIS": ("INFRASTRUCTURE", "UTILITIES", ZONING_RULES),
    "SID": ("INFRASTRUCTURE", "UTILITIES", FUENTE_SAN_LUIS),
    "SED": ("FACILITIES", "EDUCATION", SECONDARY_GARDENS),
    "SRD": ("FACILITIES", "SPORTS", FUENTE_SAN_LUIS),
    "PRV": ("INFRASTRUCTURE", "TRANSPORT", SECONDARY_GARDENS),
    "SRV": ("INFRASTRUCTURE", "TRANSPORT", SECONDARY_GARDENS),
    "PJL": ("GREEN_SPACE", "OTHER", FUENTE_SAN_LUIS),
    "SAL": ("GREEN_SPACE", "OTHER", FUENTE_SAN_LUIS),
    "SJL": ("GREEN_SPACE", "OTHER", SECONDARY_GARDENS),
    "EC": ("FACILITIES", "UNSPECIFIED", COUNCIL_MINUTES),
    "ZV": ("GREEN_SPACE", "UNSPECIFIED", COUNCIL_MINUTES),
    "RV": ("INFRASTRUCTURE", "TRANSPORT", ZONING_RULES),
    "R": ("RESIDENTIAL", "UNSPECIFIED", RULES),
    "T": ("TERTIARY", "UNSPECIFIED", RULES),
    "EL": ("GREEN_SPACE", "UNSPECIFIED", PUBLIC_SPACES),
    "SP": ("FACILITIES", "UNSPECIFIED", PUBLIC_SERVICES),
    "UFA": ("RESIDENTIAL", "SINGLE_FAMILY", ZONING_RULES),
    "TER": ("TERTIARY", "UNSPECIFIED", ZONING_RULES),
    "IND": ("INDUSTRIAL", "UNSPECIFIED", ZONING_RULES),
}
ZONING_USES = {
    "GSR": ("FACILITIES", "OTHER", ZONING_RULES),
    "GFS": ("FACILITIES", "OTHER", ZONING_RULES),
    "GLT": ("OTHER", "OTHER", ZONING_RULES + "#search=Art%C3%ADculo%206.69"),
    "PQL": USES["PQL"],
    "PTR": USES["PTR"],
    "EL": USES["EL"],
    "SP": USES["SP"],
    "EC": USES["EC"],
    "ZV": USES["ZV"],
    "GIS": USES["GIS"],
    "SID": USES["SID"],
    "SED": USES["SED"],
    "SRD": USES["SRD"],
    "PRV": USES["PRV"],
    "SRV": USES["SRV"],
    "PJL": USES["PJL"],
    "SAL": USES["SAL"],
    "SJL": USES["SJL"],
    "RV": ("INFRASTRUCTURE", "TRANSPORT", ZONING_RULES),
    "UFA": USES["UFA"],
    "TER": USES["TER"],
    "IND": USES["IND"],
    "GRV": ("INFRASTRUCTURE", "TRANSPORT", ZONING_RULES),
    "GTR": ("INFRASTRUCTURE", "TRANSPORT", ZONING_RULES),
    "GEL": ("GREEN_SPACE", "UNSPECIFIED", ZONING_RULES),
    "GSP": ("FACILITIES", "UNSPECIFIED", ZONING_RULES),
    "GEC": ("FACILITIES", "UNSPECIFIED", ZONING_RULES),
    "PRR": ("RESIDENTIAL", "UNSPECIFIED", ZONING_RULES),
    "NPR": ("RESIDENTIAL", "UNSPECIFIED", ZONING_RULES),
    "PRT": USES["TER"],
    "NPT": USES["TER"],
    "PRI": USES["IND"],
    "NPI": USES["IND"],
}
GENERAL_PLAN_USES = {
    "CHP": ("RESIDENTIAL", "MULTIFAMILY", ZONING_RULES + "#search=Art%C3%ADculo%206.6"),
    "ENS": ("RESIDENTIAL", "MULTIFAMILY", ZONING_RULES),
    "EDA": ("RESIDENTIAL", "MULTIFAMILY", ZONING_RULES),
}
GENERAL_PLAN_RURAL_USES = {
    "PA": ("AGRICULTURAL", "FARMING", ZONING_RULES + "#search=Art%C3%ADculo%204.10"),
    "PM": ("OTHER", "OTHER", ZONING_RULES + "#search=Art%C3%ADculo%204.9"),
}
ORIGIN_ZONING_USES = {
    ("PE2020", "CV"): ("INFRASTRUCTURE", "TRANSPORT", CIUTAT_VELLA_ROADS),
}
ORIGIN_USES = {
    ("PE2020", "TE"): ("TERTIARY", "OTHER", CIUTAT_VELLA_USES),
    ("PE2020", "SQE"): ("FACILITIES", "UNSPECIFIED", CIUTAT_VELLA_FACILITIES),
    ("PE2020", "SQM"): ("FACILITIES", "OTHER", CIUTAT_VELLA_FACILITIES),
}
REGIONAL_DOTATIONS = "https://www.boe.es/buscar/doc.php?id=DOGV-r-2021-90283"
DOTATION_SUBTYPES = {
    "QA": "ADMINISTRATIVE",
    "QD": "SPORTS",
    "QE": "UNSPECIFIED",
    "QM": "OTHER",
    "QS": "UNSPECIFIED",
    "QR": "OTHER",
}
DOTATION_USES = {
    prefix + category: ("FACILITIES", subtype, REGIONAL_DOTATIONS)
    for prefix in ("P", "S")
    for category, subtype in DOTATION_SUBTYPES.items()
}
DOTATION_USES.update({
    prefix + category: ("GREEN_SPACE", subtype, REGIONAL_DOTATIONS)
    for prefix in ("P", "S")
    for category, subtype in (("VP", "PARK"), ("VJ", "OTHER"), ("VA", "OTHER"))
})
DOTATION_USES.update({
    prefix + category: ("INFRASTRUCTURE", "TRANSPORT", REGIONAL_DOTATIONS)
    for prefix in ("P", "S")
    for category in ("CV", "CVT", "CVP", "CF", "CA")
})


def code(value):
    return (value or "").strip()


def main():
    query = SOURCE + "/query"
    fields = ("clase", "uso", "tipouso", "califi", "origen")
    metadata = fetch(SOURCE, {"f": "json"})
    field_types = {field["name"]: field["type"] for field in metadata["fields"]}
    if not all(field in field_types for field in fields):
        raise RuntimeError("Required source fields are missing")
    oid = next(name for name, kind in field_types.items() if kind == "esriFieldTypeOID")
    params = {
        "f": "json", "returnGeometry": "false",
        "groupByFieldsForStatistics": ",".join(fields),
        "outStatistics": json.dumps([{"statisticType": "count", "onStatisticField": oid,
                                     "outStatisticFieldName": "record_count"}]),
    }
    total = fetch(query, {"f": "json", "where": "1=1", "returnCountOnly": "true"})["count"]
    ids = fetch(query, {"f": "json", "where": "1=1", "returnIdsOnly": "true"})["objectIds"]
    if len(set(ids)) != len(ids) or len(ids) != total:
        raise RuntimeError("Object IDs do not match the ArcGIS layer total")
    groups = Counter()
    size = min(500, metadata["maxRecordCount"])
    ids.sort()
    for start in range(0, len(ids), size):
        partition = ids[start:start + size]
        response = fetch(query, {**params, "where": f"{oid} BETWEEN {partition[0]} AND {partition[-1]}"})
        subtotal = 0
        for feature in response["features"]:
            attributes = feature["attributes"]
            key = tuple(attributes[field] for field in fields)
            count = attributes["record_count"]
            if not isinstance(count, int) or count <= 0:
                raise RuntimeError(f"Invalid grouped count for {key!r}")
            groups[key] += count
            subtotal += count
        if response.get("exceededTransferLimit") or subtotal != len(partition):
            raise RuntimeError("Grouped query did not cover the object ID partition")
    if not groups or sum(groups.values()) != total:
        raise RuntimeError("Grouped results do not cover the ArcGIS layer total")

    classes = json.loads((ROOT / "vocabularies/land-classifications.json").read_text(encoding="utf-8"))
    uses = json.loads((ROOT / "vocabularies/land-uses.json").read_text(encoding="utf-8"))
    valid_classes = {item["id"]: {category["id"] for category in item["categories"]}
                     for item in classes["classes"]}
    valid_uses = {item["id"]: {sub["id"] for sub in item["subtypes"]} for item in uses["uses"]}
    if not all("UNSPECIFIED" in valid_classes.get(value, ()) for value, _ in CLASSES.values()):
        raise RuntimeError("Class mapping lacks the UNSPECIFIED category in SUPS")
    if not all(subtype in valid_uses.get(use, ())
               for use, subtype, _ in (*USES.values(), *ZONING_USES.values(),
                                       *GENERAL_PLAN_USES.values(), *ORIGIN_ZONING_USES.values(),
                                       *ORIGIN_USES.values(), *GENERAL_PLAN_RURAL_USES.values(),
                                       *DOTATION_USES.values())):
        raise RuntimeError("Use mapping contains an unknown SUPS ID")

    class_counts, use_counts, evidence_counts = Counter(), Counter(), Counter()
    pending = Counter()
    rows = []
    for original, count in sorted(groups.items(), key=lambda item: (-item[1], repr(item[0]))):
        original_class, original_use, _, zoning, origin = original
        classification = CLASSES.get(code(original_class))
        use = ORIGIN_USES.get((code(origin), code(original_use))) or USES.get(code(original_use))
        if use is None:
            use = DOTATION_USES.get(code(original_use))
        use_field = "uso"
        if not code(original_use):
            use = ZONING_USES.get(code(zoning)) or DOTATION_USES.get(code(zoning))
            if use is None and code(origin) == "PGOU":
                use = GENERAL_PLAN_USES.get(code(zoning))
                if code(original_class) == "SNU":
                    use = use or GENERAL_PLAN_RURAL_USES.get(code(zoning))
            if use is None:
                use = ORIGIN_ZONING_USES.get((code(origin), code(zoning)))
            use_field = "califi"
        class_status = "DOCUMENTED" if classification else "REQUIRES_REVIEW" if code(original_class) else "MISSING"
        use_status = "DOCUMENTED" if use else "REQUIRES_REVIEW" if code(original_use) else "MISSING"
        class_counts[class_status] += count
        use_counts[use_status] += count
        class_result = {"status": class_status, "normalizedClass": classification[0] if classification else "UNKNOWN"}
        class_result["normalizedCategory"] = "UNSPECIFIED" if classification else "UNKNOWN"
        if classification:
            class_result.update(sourceLabel=classification[1], evidence=PLAN)
        use_result = {"status": use_status, "normalizedUse": "UNKNOWN", "normalizedSubtype": "UNKNOWN"}
        if use:
            evidence_counts[use_field] += count
            use_result.update(normalizedUse=use[0], normalizedSubtype=use[1], evidence=use[2],
                              sourceField=use_field)
            provenance = {
                "sourceField": use_field,
                "originalCode": original_use if use_field == "uso" else zoning,
                "basis": "PUBLISHED_USE" if use_field == "uso" else "ZONING_DESIGNATION",
            }
            if code(origin):
                provenance["planningInstrument"] = code(origin)
            use_result["provenance"] = provenance
            if use_field == "califi" and code(zoning) == "PM":
                use_result["sourceLabel"] = "Forestal y protección del medio natural"
        elif use_field == "califi" and code(zoning) == "PI" and code(origin) == "PGOU" and code(original_class) == "SNU":
            use_result.update(
                evidence=ZONING_RULES + "#search=Art%C3%ADculo%204.12",
                reviewReason="Infrastructure protection spans several subzones. The generic code does not establish a dominant use.",
            )
        elif use_field == "califi" and code(zoning) == "AR" and code(origin) == "PE1629":
            use_result["reviewReason"] = "Confirm the dominant use in the PE1629 rules before applying the general plan's rural settlement mapping."
        if not use:
            pending_code = code(original_use if use_field == "uso" else zoning)
            pending[use_field, pending_code, code(origin)] += count
        rows.append({"original": dict(zip(fields, original)), "recordCount": count,
                     "classification": class_result, "use": use_result})
    result = {
        "municipality": "València", "source": SOURCE,
        "extractedAt": datetime.now(timezone.utc).isoformat(),
        "scope": "PGOU layer features grouped by raw clase, uso, tipouso, califi and origen. Classification is mapped at class level. Use from califi represents the zoning designation when uso is blank. CHP, ENS and EDA rely on the general plan and require origen=PGOU.",
        "recordCount": total, "groupCount": len(rows), "classificationSummary": dict(class_counts),
        "useSummary": dict(use_counts), "documentedUseBySourceField": dict(evidence_counts),
        "pendingUseByCodeAndOrigin": [
            {"sourceField": field, "code": value, "origin": origin, "recordCount": count}
            for (field, value, origin), count in sorted(pending.items(), key=lambda item: (-item[1], item[0]))
        ],
        "groups": rows,
    }
    output = ROOT / "validation/valencia/planning-audit.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(total, len(rows), dict(class_counts), dict(use_counts))


if __name__ == "__main__":
    main()
