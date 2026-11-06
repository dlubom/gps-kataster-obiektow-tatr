"""Generate reader-facing statistics from the artifacts of one release build."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable, Sequence
from html import escape
from pathlib import Path
from typing import Any

from gps_kataster_obiektow_tatr.export_data import ExportData

LABELS = {
    "title": ("Statystyki wydania (PL)", "Release statistics (EN)", "Štatistiky vydania (SK)"),
    "local": ("Podgląd lokalny", "Local preview", "Lokálny náhľad"),
    "version": ("Wydanie", "Release", "Vydanie"),
    "generated": ("Wygenerowano", "Generated", "Vygenerované"),
    "metric": ("Co liczymy", "What is counted", "Čo počítame"),
    "count": ("Liczba", "Count", "Počet"),
    "objects": (
        "Obiekty / punkty do pobrania",
        "Objects / downloadable points",
        "Objekty / body na stiahnutie",
    ),
    "caves": (
        "Jaskinie / pozycje katalogowe",
        "Caves / catalog entries",
        "Jaskyne / katalógové záznamy",
    ),
    "measurements": (
        "Wszystkie zachowane pomiary",
        "All preserved measurements",
        "Všetky zachované merania",
    ),
    "category": ("Rodzaj obiektu", "Object type", "Druh objektu"),
    "jaskinia_otwor": ("Otwory jaskiń", "Cave entrances", "Jaskynné vchody"),
    "sztolnia": ("Sztolnie", "Adits", "Štôlne"),
    "ponor": ("Ponory", "Sink points", "Ponory"),
    "wywierzysko": ("Wywierzyska", "Karst springs", "Vyvieračky"),
    "inne": ("Inne", "Other", "Iné"),
    "source": ("Źródło", "Source", "Zdroj"),
    "wlasne": ("Opracowania własne", "Project work", "Vlastné spracovanie"),
    "publikacja": ("Publikacje", "Publications", "Publikácie"),
    "position_method": (
        "Sposób wyznaczenia pozycji",
        "Position determination method",
        "Spôsob určenia polohy",
    ),
    "gps_receiver": ("Odbiornik GPS", "GPS receiver", "Prijímač GPS"),
    "gnss": (
        "GNSS (rodzaj nieudokumentowany)",
        "GNSS (type undocumented)",
        "GNSS (druh nezdokumentovaný)",
    ),
    "smartfon": ("Smartfon", "Smartphone", "Smartfón"),
    "mapa_topo": ("Mapa topograficzna", "Topographic map", "Topografická mapa"),
    "source_record": (
        "Zapis źródłowy — metoda pierwotna nieznana",
        "Source record — original method unknown",
        "Zdrojový záznam — pôvodná metóda neznáma",
    ),
    "siec_pomiarowa": ("Sieć pomiarowa", "Survey network", "Meračská sieť"),
    "ustalenie": ("Inne ustalenie", "Other determination", "Iné určenie"),
    "lidar_gnss": (
        "LiDAR dowiązany GNSS",
        "GNSS-anchored LiDAR",
        "LiDAR naviazaný na GNSS",
    ),
    "survey_anchor": (
        "Punkt dowiązania — pierwotna metoda nieznana",
        "Survey anchor — original method unknown",
        "Bod pripojenia — pôvodná metóda neznáma",
    ),
    "selected": ("Punkty do pobrania", "Downloadable points", "Body na stiahnutie"),
    "history": ("Cała historia pomiarów", "Full measurement history", "Celá história meraní"),
    "status": ("Weryfikacja pomiaru", "Measurement verification", "Overenie merania"),
    "nieweryfikowany": ("Nieweryfikowane", "Unverified", "Neoverené"),
    "zweryfikowany": ("Zweryfikowane", "Verified", "Overené"),
    "odrzucony": ("Odrzucone", "Rejected", "Zamietnuté"),
    "accuracy": (
        "Dokładność pozioma punktów do pobrania",
        "Horizontal accuracy of downloadable points",
        "Vodorovná presnosť bodov na stiahnutie",
    ),
    "known": ("Podana w źródle", "Declared in the source", "Uvedená v zdroji"),
    "unknown": ("Nie podano — nieznana", "Not provided — unknown", "Neuvedená — neznáma"),
    "note": (
        "Jeden punkt odpowiada jednemu obiektowi, np. otworowi; "
        "jedna jaskinia może mieć kilka otworów. Historia zawiera także starsze "
        "i odrzucone pomiary. Weryfikacja oznacza ocenę w projekcie, "
        "nie zawsze sprawdzenie w terenie. Brak dokładności nie oznacza zera metrów błędu. "
        "Źródło pomiaru nie jest oceną jego jakości. "
        "Sposób wyznaczenia pozycji wynika z zapisanej metody i udokumentowanych tagów. "
        "GNSS nie oznacza automatycznie pomiaru geodezyjnego; "
        "dowiązanie LiDAR lub sieci do GNSS nie jest bezpośrednim pomiarem GNSS otworu. "
        "Zestawienie nie określa kompletności rozpoznania Tatr.",
        "One point represents one object, such as an entrance; a cave may have several entrances. "
        "History includes older and rejected measurements. "
        "Verification means a project assessment, "
        "not necessarily a field check. Missing accuracy does not mean zero error. "
        "A measurement source is not a quality rating. "
        "Position determination follows the recorded method and documented tags. "
        "GNSS does not automatically mean a geodetic survey; "
        "a GNSS-anchored LiDAR or network position is not a direct GNSS entrance measurement. "
        "These figures do not measure completeness across the Tatras.",
        "Jeden bod predstavuje jeden objekt, napríklad vchod; jaskyňa môže mať viac vchodov. "
        "História zahŕňa aj staršie a zamietnuté merania. Overenie znamená posúdenie v projekte, "
        "nie vždy kontrolu v teréne. Chýbajúca presnosť neznamená nulovú chybu. "
        "Zdroj merania nie je hodnotením kvality. "
        "Spôsob určenia polohy vychádza zo zaznamenanej metódy a doložených značiek. "
        "GNSS automaticky neznamená geodetické meranie; poloha z LiDAR alebo siete "
        "naviazanej na GNSS nie je priamym meraním vchodu pomocou GNSS. "
        "Prehľad nevyjadruje úplnosť preskúmania Tatier.",
    ),
}


def write_release_statistics(
    export_data: ExportData,
    *,
    output_dir: Path,
    release_version: str | None,
    source_commit: str | None,
) -> tuple[Path, Path]:
    """Count the exported selections and packaged history without choosing points again."""

    history = export_data.history
    selected = export_data.selected
    selected_methods = (_position_method(row["method"], row["tags"]) for row in selected)

    known_accuracy = sum(row["horizontal_accuracy_m"] is not None for row in selected)
    statistics = {
        "statistics_schema_version": 1,
        "release": {"version": release_version, "source_commit": source_commit},
        "generated_at": export_data.generated_at,
        "counts": {
            "objects": len(selected),
            "caves": export_data.cave_count,
            "measurements": len(history),
        },
        "selected_points": {
            "by_category": _count(row["category"] for row in selected),
            "by_source": _count(row["source"] for row in selected),
            "by_position_method": _count(selected_methods),
            "by_verification_status": _count(row["verification_status"] for row in selected),
            "horizontal_accuracy": {
                "known": known_accuracy,
                "unknown": len(selected) - known_accuracy,
            },
        },
        "measurement_history": {
            "by_source": _count(row["source"] for row in history),
            "by_position_method": _count(
                _position_method(row["method"], row["tags"]) for row in history
            ),
            "by_verification_status": _count(row["verification_status"] for row in history),
        },
    }
    json_path = output_dir / "statistics.json"
    markdown_path = output_dir / "statistics.md"
    json_path.write_text(
        json.dumps(statistics, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(_render_markdown(statistics), encoding="utf-8")
    return json_path, markdown_path


def _count(values: Iterable[str]) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def _position_method(method: str, tags: Sequence[str]) -> str:
    if method == "ustalenie" and "lidar" in tags and "gnss_anchor" in tags:
        return "lidar_gnss"
    if method == "source_record" and "survey_anchor" in tags:
        return "survey_anchor"
    return method


def _render_markdown(statistics: dict[str, Any]) -> str:
    sections = []
    selected = statistics["selected_points"]
    history = statistics["measurement_history"]
    for language in range(3):

        def label(key: str, index: int = language) -> str:
            return LABELS.get(key, (key, key, key))[index]

        release = statistics["release"]
        version = escape(release["version"] or label("local"))
        commit = escape(release["source_commit"] or "—")
        lines = [
            f"<details>\n<summary>{label('title')}</summary>\n",
            f"{label('version')}: **{version}** · commit: <code>{commit}</code>  ",
            f"{label('generated')}: {escape(statistics['generated_at'])}\n",
            label("note") + "\n",
            _table(
                [label("metric"), label("count")],
                [
                    [label(key), statistics["counts"][key]]
                    for key in ("objects", "caves", "measurements")
                ],
            ),
            _table(
                [label("category"), label("selected")],
                [
                    [label(key), selected["by_category"].get(key, 0)]
                    for key in ("jaskinia_otwor", "sztolnia", "ponor", "wywierzysko", "inne")
                ],
            ),
        ]
        for field, title, keys in (
            ("by_source", "source", ("TPN", "PIG", "wlasne", "geoportal", "publikacja", "inne")),
            (
                "by_position_method",
                "position_method",
                (
                    "gps_receiver",
                    "gnss",
                    "lidar_gnss",
                    "siec_pomiarowa",
                    "survey_anchor",
                    "smartfon",
                    "mapa_topo",
                    "source_record",
                    "ustalenie",
                    "inne",
                ),
            ),
            ("by_verification_status", "status", ("zweryfikowany", "nieweryfikowany", "odrzucony")),
        ):
            lines.append(
                _table(
                    [label(title), label("selected"), label("history")],
                    [
                        [label(key), selected[field].get(key, 0), history[field].get(key, 0)]
                        for key in keys
                    ],
                )
            )
        lines.append(
            _table(
                [label("accuracy"), label("count")],
                [
                    [label(key), selected["horizontal_accuracy"][key]]
                    for key in ("known", "unknown")
                ],
            )
        )
        lines.append("</details>\n")
        sections.append("\n".join(lines))
    return "\n".join(sections)


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    return (
        "\n".join(
            "| " + " | ".join(str(cell) for cell in row) + " |"
            for row in (headers, ["---"] * len(headers), *rows)
        )
        + "\n"
    )
