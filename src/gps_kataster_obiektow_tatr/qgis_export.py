"""Create a portable, versioned QGIS comparison package without a QGIS runtime."""

from __future__ import annotations

import hashlib
import html
import json
import math
import sqlite3
import zipfile
from contextlib import closing
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from gps_kataster_obiektow_tatr.jktz_snapshot import load_jktz_snapshot
from gps_kataster_obiektow_tatr.qgis_project import BASEMAPS, project_xml

QGIS_ZIP_FILENAME = "katalog-qgis.zip"
POINT_ROLES = (
    ("best", "★ Best — wybrane pozycje"),
    ("other", "○ Pozostałe pomiary"),
    ("rejected", "× Pomiary odrzucone"),
    ("differences", "Linie do Best — różnice XY [m]"),
    ("full", "Full — wszystkie pomiary (tabela)"),
)
REGIONS = (
    ("Chochołowska i Lejowa", {"CHZ", "CHW", "LEJ"}),
    ("Kościeliska", {"KSZ", "KSW"}),
    ("Miętusia", {"MTZ", "MTW"}),
    ("Mała Łąka", {"MLZ", "MLW"}),
    ("Doliny reglowe i Bystrej", {"STN", "BRA", "STR", "DZI", "BIA", "BYZ", "BYW"}),
    ("Olczyska i Sucha Woda", {"OLC", "SUW"}),
)


def write_qgis_export(
    *,
    sqlite_path: Path,
    best_geojson_path: Path,
    jktz_source_dir: Path,
    output_path: Path,
    generated_at: str,
    release_version: str | None,
    source_commit: str | None,
) -> Path:
    """Atomically write the complete package from explicit, already-local inputs."""
    snapshot = load_jktz_snapshot(jktz_source_dir)
    collections = _point_collections(sqlite_path, best_geojson_path)
    members = {}
    layers = []
    for role, name in POINT_ROLES:
        path = f"points/{role}.geojson"
        members[path] = _json({"type": "FeatureCollection", "features": collections[role]})
        layers.append(
            {
                "id": f"gps_{role}_layer",
                "role": role,
                "name": name,
                "path": path,
                "count": len(collections[role]),
                "crs": "EPSG:4326",
            }
        )
    for model in snapshot.models:
        for suffix in ("shp", "shx", "dbf", "prj", "cpg"):
            original = f"exports/caves/{model.prefix}.{suffix}"
            if original in snapshot.members:
                members[f"jktz/{model.prefix}.{suffix}"] = snapshot.members[original]
        layers.append(
            {
                "id": "jktz_" + uuid5(NAMESPACE_URL, model.prefix).hex,
                "role": "jktz",
                "model": model.prefix,
                "name": model.prefix,
                "path": f"jktz/{model.prefix}.shp",
                "count": model.feature_count,
                "crs": "EPSG:32634",
            }
        )
    for name in ("LICENCE", "INFO.txt", "README.md", "LISTA_JASKIN.md"):
        if name in snapshot.members:
            members[f"jktz/{name}"] = snapshot.members[name]
    best = collections["best"]
    extent = _bounds(best)
    bookmarks = [("Cały zbiór Best", extent)]
    for name, prefixes in REGIONS:
        selected = [f for f in best if f["properties"]["object_id"].split("-")[0] in prefixes]
        if selected:
            bookmarks.append((name, _bounds(selected)))
    members["kataster.qgs"] = project_xml(
        layers=layers,
        extent=extent,
        bookmarks=bookmarks,
        version=release_version,
        jktz_version=snapshot.metadata["version"],
    )
    members["README.txt"] = _readme(release_version, source_commit, snapshot.metadata).encode(
        "utf-8"
    )
    manifest = {
        "schema_version": 1,
        "generated_at": generated_at,
        "project": "kataster.qgs",
        "project_crs": "EPSG:2180",
        "gps": {
            "version": release_version,
            "source_commit": source_commit,
            "sqlite_sha256": _sha(sqlite_path.read_bytes()),
            "best_geojson_sha256": _sha(best_geojson_path.read_bytes()),
            "license": "CC-BY-4.0",
        },
        "jktz": snapshot.metadata,
        "layers": layers,
        "basemaps": BASEMAPS,
        "counts": {
            **{role: len(collections[role]) for role, _ in POINT_ROLES},
            "jktz_models": len(snapshot.models),
            "jktz_legs": sum(m.feature_count for m in snapshot.models),
        },
        "sha256": {name: _sha(content) for name, content in sorted(members.items())},
    }
    members["manifest.json"] = _json(manifest)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(output_path.name + ".tmp")
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, content in sorted(members.items()):
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                info.create_system = 3
                archive.writestr(info, content)
        temporary.replace(output_path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return output_path


def _point_collections(sqlite_path: Path, best_geojson_path: Path) -> dict[str, list]:
    exported = json.loads(best_geojson_path.read_text(encoding="utf-8"))["features"]
    selected = {f["properties"]["object_id"]: f for f in exported}
    if len(selected) != len(exported):
        raise ValueError("Duplicate objects in the selected Best export")
    with closing(sqlite3.connect(f"{sqlite_path.resolve().as_uri()}?mode=ro", uri=True)) as db:
        db.row_factory = sqlite3.Row
        object_ids = {row[0] for row in db.execute("SELECT id FROM objects")}
        rows = [
            dict(row)
            for row in db.execute("""
            SELECT m.*, o.name_local, o.category, o.cave_id, o.notes AS object_notes,
                   c.name AS cave_name, c.notes AS cave_notes,
                   b.measurement_id AS best_measurement_id, b.mode AS best_mode,
                   b.reason AS best_reason
            FROM measurements m JOIN objects o ON o.id=m.object_id
            JOIN best_measurements b ON b.object_id=o.id
            LEFT JOIN caves c ON c.id=o.cave_id
            ORDER BY m.object_id, m.id
        """)
        ]
    chosen = {row["object_id"]: row for row in rows if row["id"] == row["best_measurement_id"]}
    if set(chosen) != object_ids or set(selected) != object_ids:
        raise ValueError("Best selection does not cover the same SQLite objects")
    for oid, row in chosen.items():
        feature = selected[oid]
        if feature["properties"]["measurement_id"] != row["id"] or feature["geometry"][
            "coordinates"
        ] != [row["lon"], row["lat"]]:
            raise ValueError(f"Selected Best export differs from SQLite: {oid}/{row['id']}")
    collections = {role: [] for role, _ in POINT_ROLES}
    for row in rows:
        if not all(
            isinstance(row[key], (int, float)) and math.isfinite(row[key])
            for key in ("lat", "lon", "x_1992", "y_1992")
        ):
            raise ValueError(f"Invalid point coordinates: {row['object_id']}/{row['id']}")
        target = chosen[row["object_id"]]
        is_best = row["id"] == target["id"]
        distance = math.hypot(row["x_1992"] - target["x_1992"], row["y_1992"] - target["y_1992"])
        display_name = (
            row["name_local"]
            if row["name_local"] and row["name_local"].strip()
            else row["object_id"]
        )
        properties = {
            **selected[row["object_id"]]["properties"],
            **row,
            "measurement_id": row["id"],
            "is_best": int(is_best),
            "display_name": display_name,
            "display_name_html": html.escape(display_name),
            "source_html": html.escape(row["source"]),
            "measurement_notes": row["notes"],
            "measurement_notes_html": html.escape(row["notes"] or ""),
            "distance_to_best_m": distance,
        }
        feature = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [row["lon"], row["lat"]]},
            "properties": properties,
        }
        collections["full"].append(feature)
        role = (
            "best"
            if is_best
            else "rejected"
            if row["verification_status"] == "odrzucony"
            else "other"
        )
        collections[role].append(feature)
        if not is_best and distance > 0:
            collections["differences"].append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[row["lon"], row["lat"]], [target["lon"], target["lat"]]],
                    },
                    "properties": {
                        "object_id": row["object_id"],
                        "measurement_id": row["id"],
                        "best_measurement_id": target["id"],
                        "source": row["source"],
                        "distance_m": distance,
                    },
                }
            )
    return collections


def _bounds(features: list) -> tuple[float, float, float, float]:
    if not features:
        return 550000.0, 143000.0, 580000.0, 166000.0
    east = [f["properties"]["y_1992"] for f in features]
    north = [f["properties"]["x_1992"] for f in features]
    padding = max(max(east) - min(east), max(north) - min(north), 250) * 0.06
    return min(east) - padding, min(north) - padding, max(east) + padding, max(north) + padding


def _sha(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _json(value) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")


def _readme(version: str | None, commit: str | None, jktz: dict) -> str:
    return f"""GPS KATASTER OBIEKTÓW TATR — PROJEKT QGIS 2D

Rozpakuj cały ZIP i otwórz kataster.qgs w QGIS 3.44 LTR lub 4.0.1.
Zachowaj pliki warstw obok projektu; ścieżki są względne.

GPS: {version or "podgląd lokalny"}; commit: {commit or "niepodany"}.
JKTZ: {jktz["version"]}; {jktz["release_url"]}
JKTZ archive SHA-256: {jktz["sha256"]}
Pełne pochodzenie, liczniki i sumy plików: manifest.json.

PUNKTY I OBSŁUGA
★ Best: wybrany pomiar każdego obiektu, domyślnie włączony.
○ Pozostałe: pomiary historyczne i alternatywne, domyślnie wyłączone.
× Odrzucone: odrzucone pomiary poza Best, domyślnie wyłączone.
Linie do Best: rozbieżność XY w metrach, domyślnie wyłączone.
Full: wszystkie pomiary, także odrzucone; otwórz tabelę atrybutów tej warstwy.
Pomiary o identycznej pozycji nakładają się na mapie, lecz pozostają w tabeli.
Wybierz warstwę i narzędzie Identify Features (i), następnie kliknij punkt.
Możesz włączyć Show Map Tips. Nazwy punktów pojawiają się przy powiększeniu.
Show Spatial Bookmarks udostępnia zakładki regionalne według grup ID.

JKTZ
W grupie JKTZ można osobno włączać modele jaskiń/systemów.
Nazwy odpowiadają prefixom opublikowanych eksportów. Nie są powiązaniem
z GPS object_id. Linie to ciągi pomiarowe w rzucie na mapę, nie obrysy ścian.
Oryginalne XYZ i EPSG:32634 są zachowane; QGIS wykonuje reprojekcję widoku.
Punkty GPS i JKTZ są niezależnymi migawkami. Nie przesunięto ciągów do Best.

PODKŁADY ONLINE
TPN RGB 2020 jest wybrany domyślnie; alternatywy: RGB 2018, NMT, NMPT.
Przy skali 1:25000 i większym oddaleniu TPN jest ukryte, aby ograniczyć
pobieranie kafelków; widoczne jest OSM. Po przybliżeniu pojawia się wybrany TPN.
Wybierz jeden podkład TPN. Poza pokryciem źródła widoczne pozostaje OSM.
NMT/NMPT to obrazy modeli, nie rastry numerycznych wysokości. Rok nalotu,
datum pionowe i dokładność tych dwóch warstw nie zostały potwierdzone.
Podkłady wymagają internetu; wszystkie punkty i ciągi są lokalne.
TPN / ObliView / MGGP Aero: https://tpn.obliview.com/
Parametry podkładów: https://tpn.obliview.com/Data/conf.json
© OpenStreetMap contributors: https://www.openstreetmap.org/copyright
Dostępność i aktualność podkładów zależą od ich operatorów.

INTERPRETACJA I ATRYBUCJA
Best oznacza wybór katalogu, nie gwarancję dokładności lub weryfikacji terenowej.
Brak dokładności oznacza dokładność nieznaną. Różnica względem Best nie jest
oszacowaniem błędu, odległością ścian jaskiń ani odległością pod ziemią.
Zachowano źródłowe daty, statusy, wysokości i datum; data źródła nie musi
oznaczać pomiaru terenowego. Wysokość gruntu nie musi być wysokością otworu.
GPS: CC BY 4.0, https://github.com/dlubom/gps-kataster-obiektow-tatr
JKTZ: CC BY-SA 4.0; oryginalne LICENCE, INFO.txt i README.md są w jktz/.
Przy dalszym udostępnianiu zachowaj oddzielne informacje o obu źródłach.
"""
