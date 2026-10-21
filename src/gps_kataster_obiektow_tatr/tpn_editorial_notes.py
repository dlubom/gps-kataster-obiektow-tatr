"""Fixed, source-preserving reader-note rules approved for PR #12.

Raw source wording and superseded descriptions remain in immutable Git inputs.
This module changes presentation only; no coordinates, identities or best choices.
"""

from __future__ import annotations

import re

IMPORT_NOTES = (
    "Imported from PIG source record after operator review.",
    "Imported from TPN source record after operator review.",
)
LOCATION_CONTEXT = {
    "lok. orientacyjnie na podstawie opisu",
    "lokalizacja orientacyjna",
    "Wg opisu z inwentarza. Trzeba uściślić położenie",
    "Opis dojścia w inwentarzu jest błędny",
    "lokalizacja wg opisu z inwentarza",
    "błędna lokalizacja otworu, zweryfikowano dane w terenie i poprawiono umiejscowienie punktu",
    "Na podstawie opisu z inwentarza",
    "Lokalizacja przybliżona. Na podstawie opisu z inwentarza.",
    "poożenie wg opisu dojścia z inwentarza",
    "wg opisu z inwentarza",
    "przybliżona lokalizacja",
}
OPENING_CONTEXT = {"zasypana, ale widoczne belkowanie stropu"}
CAVE_CONTEXT = {
    "Dane morfometr. orientacyjnie",
    "dane morfometryczne do poprawy",
    "Dane morfometryczne orientacyjne",
    "dane morf orient",
    "do zinwentaryzowania",
    "dane morfometryczne do ustalenia",
    "do pomierzenia",
    "długość do zweryfikowania",
    "min 5 m głeboka",
    "Dane morfometr. orentacyjne",
    "Dane morf. orient.",
    "dane mofr do wpisania",
    "dane morf do wpisania",
    "niezmierzona",
    "dane mofrometryczne na oko",
    "dane morf. orientacyjne, do dokumentacji",
    "wg sprawozdania M. Wierzbowski",
    "Dane mofometr. orientaccyjne",
    "dane morfometryczne na oko",
    "Dane morfometryczne orientacyjnie",
    "długość do uściślenia",
    "dane morf do wprowadzenia",
    "Dane morfometr. orientacyjne",
    "dane morfometryczne do uzupełnienia",
    "dł za Nowakiem",
    "dł wg sprawozdania ST za 2020, 2022",
    "Jaskinie 100",
    "u Nowaka dł 917",
    "dł za Nowakiem (Jaskinie nr 3 2022 r. - domierzono 81 m)",
    "dane morf. wg listy J.Nowaka",
    "dł. jako suma 5 jaskin składowych wg PIG",
    *{f"Sztolnia nr {n} wg Jach Jaskinie nr 3 (28) 2002" for n in range(1, 9)},
}

OBJECT_NOTES = {
    "CHZ-0011": (
        "Wylot sztolni nr 7 prowadzącej do naturalnej jaskini Wojtkowa Szpara. "
        "Według PIG:1042 i Jach (2002) wejścia do naturalnej próżni znajdują "
        "się 6–8 m wewnątrz sztolni. Kategoria sztolnia dotyczy wylotu na "
        "powierzchni; TPN podaje genezę jaskinia/sztolnia."
    ),
    "KSW-0081": (
        "Wyjście z trasy turystycznej Jaskini Mroźnej; punkt PIG i "
        "odpowiadający mu wpis TPN przypisano do tego otworu. Wejście na "
        "trasę: KSW-0256."
    ),
    "KSW-0090": "Dolny otwór Jaskini Zimnej. Górny otwór, Jaskinia Biała: KSW-0257.",
    "KSW-0189": "Otwór Jaskini Wysokiej oznaczony w przekazanych danych jako Wysoka7Progow.",
    "KSW-0201": "Główny otwór Jaskini Czarnej. Otwór III: KSW-0240.",
    "KSW-0240": (
        "Otwór III Jaskini Czarnej; według PIG ku NNE, 1404 m n.p.m. Oznaczenie otworu w TPN: N."
    ),
    "KSW-0256": (
        "Wejście na trasę turystyczną Jaskini Mroźnej; według PIG otwór 2, ku NE, 1100 m n.p.m."
    ),
    "KSW-0257": (
        "Górny otwór Jaskini Zimnej, Jaskinia Biała; według PIG otwór 2, ku "
        "SW, 1260 m n.p.m. Dolny otwór: KSW-0090."
    ),
    "KSZ-0064": "Główny, południowy otwór Jaskini Mylnej. Otwór północny: KSZ-0113.",
    "KSZ-0112": "Dolny otwór Jaskini Bańdzioch Kominiarski. Górny otwór: LEJ-0002.",
    "KSZ-0113": "Północny otwór Jaskini Mylnej; według PIG otwór 3, ku NE, 1084 m n.p.m.",
    "LEJ-0002": (
        "Górny otwór Jaskini Bańdzioch Kominiarski; według PIG otwór 2, ku N, "
        "1682 m n.p.m. Dolny otwór: KSZ-0112."
    ),
    "MLW-0044": "Otwór N według TPN; położony na północ od MLW-0050.",
    "MLW-0050": "Otwór S według TPN; położony na południe od MLW-0044.",
    "MLZ-0072": "Północno-zachodni otwór Jaskini nad Korytem. Otwór wschodni: MLZ-0108.",
    "MLZ-0087": (
        "Dwa wpisy TPN rozpoznano jako ten sam otwór; zachowano oba pomiary i referencje źródłowe."
    ),
    "MLZ-0089": (
        "Dwa wpisy TPN rozpoznano jako ten sam otwór; zachowano oba pomiary i referencje źródłowe."
    ),
    "MLZ-0108": (
        "Wschodni otwór Jaskini nad Korytem; według PIG otwór 2, ku E, 1618,7 "
        "m n.p.m.; oznaczenie TPN: SE."
    ),
    "SK-0001": None,
    "SK-0002": None,
    "STR-0024": (
        "Nazwa robocza BEZ_NAZWY_001: źródłowy rekord TPN nie podaje nazwy ani "
        "numeru inwentarzowego. Według TPN sztolnia; zasypana, ale widoczne "
        "belkowanie stropu."
    ),
}

CAVE_EXTRA = {
    "C-0078": None,
    "C-0267": None,
    "C-0297": None,
    "C-0573": None,
    "C-0665": None,
    "C-0699": None,
    "C-0713": None,
    "C-0903": None,
    "C-0403": "Według PIG należy do systemu Jaskinie Pawlikowskiego.",
    "C-0759": "Według PIG należy do systemu Jaskinie Pawlikowskiego.",
}
MEASUREMENT_NOTES = {
    (
        "KSW-0189",
        "m-003",
    ): (
        "Punkt przekazany jako „unknown GNSS” dla Wysoka7Progow; pochodzenie i "
        "metoda pomiaru niepotwierdzone."
    ),
    (
        "KSW-0257",
        "m-002",
    ): (
        "Punkt przekazany jako „unknown GNSS” dla Jaskini Białej; pochodzenie "
        "i metoda pomiaru niepotwierdzone."
    ),
    (
        "KSZ-0047",
        "m-003",
    ): (
        "Punkt przekazany jako „unknown GNSS” z oznaczeniem "
        "Pawlikowskiego:Raptawicka; pochodzenie i metoda pomiaru "
        "niepotwierdzone."
    ),
    (
        "KSZ-0064",
        "m-003",
    ): (
        "Punkt przekazany jako „unknown GNSS” z oznaczeniem "
        "Pawlikowskiego:Mylna; pochodzenie i metoda pomiaru niepotwierdzone."
    ),
    (
        "KSZ-0090",
        "m-003",
    ): (
        "Punkt przekazany jako „unknown GNSS” z oznaczeniem "
        "Pawlikowskiego:Oblazkowa; pochodzenie i metoda pomiaru "
        "niepotwierdzone."
    ),
    (
        "KSZ-0112",
        "m-001",
    ): (
        "Punkt przekazany jako „unknown GNSS” dla Bandzioch Kominiarski Dolny; "
        "pochodzenie i metoda pomiaru niepotwierdzone."
    ),
    (
        "LEJ-0002",
        "m-003",
    ): (
        "Punkt przekazany jako „unknown GNSS” dla Bandzioch Kominiarski Gorny; "
        "pochodzenie i metoda pomiaru niepotwierdzone. Wysokość 1675.02 m "
        "przekazano z punktem BandziochKom:136."
    ),
    (
        "SK-0001",
        "m-001",
    ): "Współrzędne WGS84 E19.91418777 N49.22918839 i wysokość 2016 m przekazane przez maintenera.",
    (
        "SK-0002",
        "m-001",
    ): (
        "Współrzędne źródłowe E19:55:47.53 N49:13:35.8 przeliczono na WGS84: "
        "lon=19.92986944, lat=49.22661111."
    ),
}


def context_kind(value):
    if value in LOCATION_CONTEXT:
        return "measurement"
    if value in OPENING_CONTEXT:
        return "object"
    if value in CAVE_CONTEXT:
        return "cave"
    return "unknown"


def measurement_notes(notes):
    lines = []
    for line in (notes or "").splitlines():
        if line.startswith(
            ("TPN source-record measurement imported", "PIG source-record measurement imported")
        ):
            continue
        if re.fullmatch(r"TPN revision: [0-9a-f]{64}", line) or line.startswith(
            "TPN LAST_EDITED_DATE:"
        ):
            continue
        if line.startswith("TPN UWAGI:") and context_kind(
            line.removeprefix("TPN UWAGI:").strip()
        ) in {"cave", "object"}:
            continue
        if line.strip() and line not in lines:
            lines.append(line)
    return "\n".join(lines) or None


def clean_object(obj):
    notes = obj.get("notes") or ""
    for prefix in IMPORT_NOTES:
        if notes.startswith(prefix):
            notes = notes[len(prefix) :].strip()
    obj["notes"] = OBJECT_NOTES.get(obj["id"], notes or None)
    moved = []
    for m in obj["measurements"]:
        for line in (m.get("notes") or "").splitlines():
            if line.startswith("TPN UWAGI:"):
                value = line.removeprefix("TPN UWAGI:").strip()
                if context_kind(value) == "object" and value not in (obj["notes"] or ""):
                    moved.append("Stan otworu według TPN: " + value + ".")
        m["notes"] = MEASUREMENT_NOTES.get((obj["id"], m["id"]), measurement_notes(m.get("notes")))
        if m["source"] == "TPN" and "tpn" not in m.get("tags", []):
            m["tags"] = [*m.get("tags", []), "tpn"]
    if moved:
        obj["notes"] = "\n".join(dict.fromkeys([*([obj["notes"]] if obj["notes"] else []), *moved]))
    return obj


def cave_source_context(value):
    lower = value.lower()
    if ("morf" in lower or "mofr" in lower or "mofom" in lower) and "wg " not in lower:
        if "orient" in lower or "orent" in lower or "na oko" in lower:
            result = "Dane morfometryczne orientacyjne"
            if "do dokumentacji" in lower:
                result += "; wymagają dokumentacji"
        elif "do poprawy" in lower:
            result = "Dane morfometryczne wymagają poprawy"
        elif "do ustalenia" in lower:
            result = "Dane morfometryczne do ustalenia"
        else:
            result = "Dane morfometryczne wymagają uzupełnienia"
        return "Uwagi TPN: " + result + "."
    return "Uwagi TPN: " + value.rstrip(".") + "."


def clean_cave(cave, objects):
    lines, metrics = [], []
    for line in (cave.get("notes") or "").splitlines():
        line = line.replace("ChochoĹ‚owska", "Chochołowska")
        if line.startswith(("Multi-opening review", "Maintainer review")):
            replacement = CAVE_EXTRA[cave["id"]]
            if replacement:
                lines.append(replacement)
        elif line.startswith("PIG aliases:"):
            lines.append(line.replace("PIG aliases:", "Inne nazwy według PIG:", 1))
        elif line.startswith("PIG sector:"):
            lines.append(line.replace("PIG sector:", "Sektor według PIG:", 1))
        elif line.startswith("PIG morphometry:"):
            value = line.removeprefix("PIG morphometry:").strip()
            for old, new in [
                ("length_m=", "długość "),
                ("depth_m=", "głębokość "),
                ("denivelation_m=", "deniwelacja "),
            ]:
                value = value.replace(old, new)
            year = re.search(r"PIG source state year: (\d{4})", cave["notes"])
            state = "; stan źródła " + year[1] if year else ""
            lines.append("PIG" + state + ": " + " m; ".join(value.split(", ")) + " m.")
        elif line.startswith("PIG source state year:"):
            if "PIG morphometry:" not in cave["notes"]:
                lines.append(line.replace("PIG source state year:", "PIG; stan źródła:", 1))
            continue
        elif line.startswith("TPN verification/location note:"):
            continue
        elif line.startswith("TPN notes:"):
            value = line.removeprefix("TPN notes:").strip()
            if context_kind(value) not in {"measurement", "object"}:
                lines.append(cave_source_context(value))
        elif line.startswith(("TPN length:", "TPN depth:", "TPN denivelation:")):
            label, value = line.split(":", 1)
            label = {
                "TPN length": "długość",
                "TPN depth": "głębokość",
                "TPN denivelation": "deniwelacja",
            }[label]
            metrics.append(label + " " + value.strip() + " m")
        elif line == "Historyczny import TPN:":
            continue
        elif line.startswith(("Nowa pozycja według TPN.", "Pozycja według TPN.")):
            lines.append("W przeglądzie źródeł 2026-10-20 nie odnaleziono odrębnej dokumentacji.")
        elif line.startswith("Dawne C-0888"):
            lines.append(
                "Drugi historyczny wpis TPN (dawne C-0888): długość 10 m; głębokość 2 "
                "m; deniwelacja 1 m."
            )
            lines.append("Literatura: F.F., Jaskinie 118–119/2025, s. 37–38; plan jednego otworu.")
        elif line.startswith("Dawne C-0998"):
            lines.append(
                "Drugi historyczny wpis TPN (dawne C-0998): długość 27 m; głębokość 0 "
                "m; deniwelacja 0 m."
            )
            lines.append("Literatura: F.F., Jaskinie 116–117/2024, s. 49–50; plan jednego otworu.")
        elif line.startswith("Slovak cave added"):
            lines.append(
                "Współrzędne przekazane przez maintenera 2026-05-16. "
                + (
                    "Źródło przyjęte do repozytorium na licencji CC BY 4.0."
                    if cave["id"] == "C-1003"
                    else "Źródło: Oblastna skupina SSS Ruzomberok."
                )
            )
        elif line.startswith("Metryka źródła TPN:"):
            dates = {
                m.get("source_date")
                for o in objects
                if o.get("cave_id") == cave["id"]
                for m in o["measurements"]
                if "TPN revision:" in (m.get("notes") or "")
            }
            date = next(iter(dates)) if len(dates) == 1 else None
            lines.append(
                line.replace(
                    "Metryka źródła TPN:",
                    "TPN" + (f"; stan rekordu {date}" if date else "") + ":",
                    1,
                )
            )
        else:
            lines.append(line)
    if metrics:
        lines.insert(0, "TPN; historyczny import: " + "; ".join(metrics) + ".")
    for obj in objects:
        if obj.get("cave_id") != cave["id"]:
            continue
        for measurement in obj["measurements"]:
            for line in (measurement.get("notes") or "").splitlines():
                if line.startswith("TPN UWAGI:"):
                    value = line.removeprefix("TPN UWAGI:").strip()
                    if context_kind(value) == "cave":
                        lines.append(cave_source_context(value))
    cave["notes"] = "\n".join(dict.fromkeys(line for line in lines if line)) or None
    return cave
