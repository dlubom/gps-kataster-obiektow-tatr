"""Generate reader-facing statistics from the artifacts of one release build."""

from __future__ import annotations

import csv
import json
import sqlite3
from collections import Counter
from collections.abc import Iterable
from contextlib import closing
from html import escape
from pathlib import Path
from typing import Any

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
    "wlasne": ("Własne pomiary", "Project measurements", "Vlastné merania"),
    "publikacja": ("Publikacje", "Publications", "Publikácie"),
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
        "Zestawienie nie określa kompletności rozpoznania Tatr.",
        "One point represents one object, such as an entrance; a cave may have several entrances. "
        "History includes older and rejected measurements. "
        "Verification means a project assessment, "
        "not necessarily a field check. Missing accuracy does not mean zero error. "
        "A measurement source is not a quality rating. "
        "These figures do not measure completeness across the Tatras.",
        "Jeden bod predstavuje jeden objekt, napríklad vchod; jaskyňa môže mať viac vchodov. "
        "História zahŕňa aj staršie a zamietnuté merania. Overenie znamená posúdenie v projekte, "
        "nie vždy kontrolu v teréne. Chýbajúca presnosť neznamená nulovú chybu. "
        "Zdroj merania nie je hodnotením kvality. Prehľad nevyjadruje úplnosť preskúmania Tatier.",
    ),
}


def write_release_statistics(
    *,
    csv_path: Path,
    sqlite_path: Path,
    output_dir: Path,
    generated_at: str,
    release_version: str | None,
    source_commit: str | None,
) -> tuple[Path, Path]:
    """Count the exported selections and packaged history without choosing points again."""

    with csv_path.open(encoding="utf-8", newline="") as stream:
        selected = list(csv.DictReader(stream))
    with closing(sqlite3.connect(f"{sqlite_path.resolve().as_uri()}?mode=ro", uri=True)) as db:
        history = db.execute("SELECT source, verification_status FROM measurements").fetchall()
        caves = db.execute("SELECT COUNT(*) FROM caves").fetchone()[0]

    known_accuracy = sum(row["horizontal_accuracy_m"] != "" for row in selected)
    statistics = {
        "statistics_schema_version": 1,
        "release": {"version": release_version, "source_commit": source_commit},
        "generated_at": generated_at,
        "counts": {"objects": len(selected), "caves": caves, "measurements": len(history)},
        "selected_points": {
            "by_category": _count(row["category"] for row in selected),
            "by_source": _count(row["source"] for row in selected),
            "by_verification_status": _count(row["verification_status"] for row in selected),
            "horizontal_accuracy": {
                "known": known_accuracy,
                "unknown": len(selected) - known_accuracy,
            },
        },
        "measurement_history": {
            "by_source": _count(row[0] for row in history),
            "by_verification_status": _count(row[1] for row in history),
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
