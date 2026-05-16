"""Build a SQLite snapshot from source-of-truth YAML records."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from gps_kataster_obiektow_tatr.best_measurement import select_default_best_measurement_id
from gps_kataster_obiektow_tatr.data_loader import (
    DEFAULT_DATA_DIR,
    LoadedDataset,
    LoadedYamlRecord,
    load_dataset,
)
from gps_kataster_obiektow_tatr.validator import (
    ValidationIssue,
    format_issue,
    has_errors,
    validate_dataset,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SQLITE_PATH = REPO_ROOT / "build" / "katalog.sqlite"
SQLITE_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class BuildDatabaseResult:
    """Summary of a completed SQLite build."""

    sqlite_path: Path
    metadata: dict[str, str]
    validation_issues: tuple[ValidationIssue, ...]


class BuildDatabaseValidationError(ValueError):
    """Raised when source YAML has validation errors that block SQLite build."""

    def __init__(self, issues: tuple[ValidationIssue, ...]) -> None:
        self.issues = issues
        details = "\n".join(format_issue(issue) for issue in issues if issue.severity == "error")
        super().__init__(f"Cannot build SQLite from invalid YAML:\n{details}")


def build_sqlite_database(
    *,
    data_dir: Path = DEFAULT_DATA_DIR,
    output_path: Path = DEFAULT_SQLITE_PATH,
    generated_at: str | None = None,
) -> BuildDatabaseResult:
    """Validate YAML and build ``output_path`` as a SQLite snapshot."""

    dataset = load_dataset(data_dir)
    validation_issues = validate_dataset(dataset, data_dir=data_dir, repo_root=REPO_ROOT)
    if has_errors(validation_issues):
        raise BuildDatabaseValidationError(validation_issues)

    metadata = _build_metadata(
        dataset,
        generated_at=generated_at or _utc_timestamp(),
        validation_issues=validation_issues,
    )
    _write_sqlite_snapshot(
        dataset, output_path=output_path, metadata=metadata, issues=validation_issues
    )
    return BuildDatabaseResult(
        sqlite_path=output_path,
        metadata=metadata,
        validation_issues=validation_issues,
    )


def _write_sqlite_snapshot(
    dataset: LoadedDataset,
    *,
    output_path: Path,
    metadata: dict[str, str],
    issues: tuple[ValidationIssue, ...],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_name(f"{output_path.name}.tmp")
    if tmp_path.exists():
        tmp_path.unlink()

    connection = sqlite3.connect(tmp_path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        _create_schema(connection)
        _insert_metadata(connection, metadata)
        _insert_caves(connection, dataset.caves)
        _insert_objects(connection, dataset.objects)
        _insert_measurements(connection, dataset.objects)
        _insert_external_refs(connection, dataset.objects, dataset.caves)
        _insert_attachments(connection, dataset.objects)
        _insert_relations(connection, dataset.relations)
        _insert_best_measurements(connection, dataset.objects)
        _insert_validation_flags(connection, issues)
        connection.commit()
    except Exception:
        connection.close()
        tmp_path.unlink(missing_ok=True)
        raise
    else:
        connection.close()
        tmp_path.replace(output_path)


def _create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE caves (
            id TEXT PRIMARY KEY,
            schema_version INTEGER NOT NULL,
            name TEXT NOT NULL,
            system_name TEXT,
            object_ids_json TEXT NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            updated_by TEXT NOT NULL
        );

        CREATE TABLE objects (
            id TEXT PRIMARY KEY,
            schema_version INTEGER NOT NULL,
            category TEXT NOT NULL,
            name_local TEXT,
            cave_id TEXT REFERENCES caves(id),
            id_assignment_method TEXT NOT NULL,
            assigned_from_measurement_id TEXT NOT NULL,
            assigned_prefix TEXT NOT NULL,
            prefix_override_reason TEXT,
            best_measurement_id TEXT NOT NULL,
            computed_best_measurement_id TEXT,
            best_lat REAL,
            best_lon REAL,
            best_x_1992 REAL,
            best_y_1992 REAL,
            best_geom_wgs84 TEXT,
            best_geom_1992 TEXT,
            notes TEXT,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            updated_by TEXT NOT NULL
        );

        CREATE TABLE measurements (
            object_id TEXT NOT NULL REFERENCES objects(id) ON DELETE CASCADE,
            id TEXT NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            x_1992 REAL NOT NULL,
            y_1992 REAL NOT NULL,
            geom_wgs84 TEXT NOT NULL,
            geom_1992 TEXT NOT NULL,
            elevation_m REAL,
            elevation_datum TEXT,
            elevation_source TEXT,
            horizontal_accuracy_m REAL,
            vertical_accuracy_m REAL,
            source TEXT NOT NULL,
            source_ref TEXT,
            observed_at TEXT,
            observed_date TEXT NOT NULL,
            source_date TEXT,
            method TEXT NOT NULL,
            device TEXT,
            tags_json TEXT NOT NULL,
            verification_status TEXT NOT NULL,
            verified_by TEXT,
            verified_at TEXT,
            notes TEXT,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            PRIMARY KEY (object_id, id)
        );

        CREATE TABLE object_external_refs (
            rowid INTEGER PRIMARY KEY,
            object_id TEXT NOT NULL REFERENCES objects(id) ON DELETE CASCADE,
            system TEXT NOT NULL,
            ref_type TEXT NOT NULL,
            external_id TEXT NOT NULL,
            url TEXT,
            scope TEXT,
            notes TEXT
        );

        CREATE TABLE cave_external_refs (
            rowid INTEGER PRIMARY KEY,
            cave_id TEXT NOT NULL REFERENCES caves(id) ON DELETE CASCADE,
            system TEXT NOT NULL,
            ref_type TEXT NOT NULL,
            external_id TEXT NOT NULL,
            url TEXT,
            scope TEXT,
            notes TEXT
        );

        CREATE TABLE attachments (
            object_id TEXT NOT NULL REFERENCES objects(id) ON DELETE CASCADE,
            id TEXT NOT NULL,
            kind TEXT NOT NULL,
            measurement_id TEXT,
            path TEXT NOT NULL,
            caption TEXT,
            date TEXT,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            PRIMARY KEY (object_id, id)
        );

        CREATE TABLE relations (
            id TEXT PRIMARY KEY,
            schema_version INTEGER NOT NULL,
            from_object_id TEXT NOT NULL REFERENCES objects(id),
            to_object_id TEXT NOT NULL REFERENCES objects(id),
            relation_type TEXT NOT NULL,
            notes TEXT
        );

        CREATE TABLE best_measurements (
            object_id TEXT PRIMARY KEY REFERENCES objects(id) ON DELETE CASCADE,
            mode TEXT NOT NULL,
            measurement_id TEXT NOT NULL,
            computed_best_measurement_id TEXT,
            reason TEXT,
            updated_at TEXT NOT NULL,
            updated_by TEXT NOT NULL
        );

        CREATE TABLE validation_flags (
            rowid INTEGER PRIMARY KEY,
            code TEXT NOT NULL,
            severity TEXT NOT NULL,
            path TEXT,
            description TEXT NOT NULL
        );

        CREATE INDEX idx_measurements_object_id ON measurements(object_id);
        CREATE INDEX idx_measurements_source ON measurements(source);
        CREATE INDEX idx_object_external_refs_lookup
            ON object_external_refs(system, ref_type, external_id);
        CREATE INDEX idx_cave_external_refs_lookup
            ON cave_external_refs(system, ref_type, external_id);
        CREATE INDEX idx_relations_from_object ON relations(from_object_id);
        CREATE INDEX idx_relations_to_object ON relations(to_object_id);
        """
    )


def _insert_metadata(connection: sqlite3.Connection, metadata: dict[str, str]) -> None:
    connection.executemany(
        "INSERT INTO metadata(key, value) VALUES (?, ?)",
        sorted(metadata.items()),
    )


def _insert_caves(
    connection: sqlite3.Connection, cave_records: tuple[LoadedYamlRecord, ...]
) -> None:
    connection.executemany(
        """
        INSERT INTO caves(
            id, schema_version, name, system_name, object_ids_json, notes,
            created_at, created_by, updated_at, updated_by
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            (
                cave.data["id"],
                cave.data["schema_version"],
                cave.data["name"],
                cave.data.get("system_name"),
                _json(cave.data.get("object_ids", [])),
                cave.data.get("notes"),
                cave.data["created_at"],
                cave.data["created_by"],
                cave.data["updated_at"],
                cave.data["updated_by"],
            )
            for cave in cave_records
        ),
    )


def _insert_objects(
    connection: sqlite3.Connection,
    object_records: tuple[LoadedYamlRecord, ...],
) -> None:
    rows = []
    for object_record in object_records:
        data = object_record.data
        best_measurement = _best_measurement_data(data)
        best_measurement_id = best_measurement.get("measurement_id")
        computed_best_measurement_id = select_default_best_measurement_id(
            _measurement_dicts(data.get("measurements"))
        )
        best = _measurement_by_id(data, str(best_measurement_id))
        id_assignment = data["id_assignment"]
        rows.append(
            (
                data["id"],
                data["schema_version"],
                data["category"],
                data.get("name_local"),
                data.get("cave_id"),
                id_assignment["method"],
                id_assignment["assigned_from_measurement_id"],
                id_assignment["assigned_prefix"],
                id_assignment.get("prefix_override_reason"),
                best_measurement_id,
                computed_best_measurement_id,
                _number_or_none(best, "lat"),
                _number_or_none(best, "lon"),
                _number_or_none(best, "x_1992"),
                _number_or_none(best, "y_1992"),
                _geom_wgs84(best),
                _geom_1992(best),
                data.get("notes"),
                data["created_at"],
                data["created_by"],
                data["updated_at"],
                data["updated_by"],
            )
        )

    connection.executemany(
        """
        INSERT INTO objects(
            id, schema_version, category, name_local, cave_id,
            id_assignment_method, assigned_from_measurement_id, assigned_prefix,
            prefix_override_reason, best_measurement_id, computed_best_measurement_id,
            best_lat, best_lon, best_x_1992, best_y_1992, best_geom_wgs84, best_geom_1992,
            notes, created_at, created_by, updated_at, updated_by
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def _insert_measurements(
    connection: sqlite3.Connection,
    object_records: tuple[LoadedYamlRecord, ...],
) -> None:
    rows = []
    for object_record in object_records:
        object_id = object_record.data["id"]
        for measurement in _measurement_dicts(object_record.data.get("measurements")):
            rows.append(
                (
                    object_id,
                    measurement["id"],
                    measurement["lat"],
                    measurement["lon"],
                    measurement["x_1992"],
                    measurement["y_1992"],
                    _geom_wgs84(measurement),
                    _geom_1992(measurement),
                    measurement.get("elevation_m"),
                    measurement.get("elevation_datum"),
                    measurement.get("elevation_source"),
                    measurement.get("horizontal_accuracy_m"),
                    measurement.get("vertical_accuracy_m"),
                    measurement["source"],
                    measurement.get("source_ref"),
                    measurement.get("observed_at"),
                    measurement["observed_date"],
                    measurement.get("source_date"),
                    measurement["method"],
                    measurement.get("device"),
                    _json(measurement.get("tags", [])),
                    measurement["verification_status"],
                    measurement.get("verified_by"),
                    measurement.get("verified_at"),
                    measurement.get("notes"),
                    measurement["created_at"],
                    measurement["created_by"],
                )
            )

    connection.executemany(
        """
        INSERT INTO measurements(
            object_id, id, lat, lon, x_1992, y_1992, geom_wgs84, geom_1992,
            elevation_m, elevation_datum, elevation_source, horizontal_accuracy_m,
            vertical_accuracy_m, source, source_ref, observed_at, observed_date,
            source_date, method, device, tags_json, verification_status, verified_by,
            verified_at, notes, created_at, created_by
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        """,
        rows,
    )


def _insert_external_refs(
    connection: sqlite3.Connection,
    object_records: tuple[LoadedYamlRecord, ...],
    cave_records: tuple[LoadedYamlRecord, ...],
) -> None:
    connection.executemany(
        """
        INSERT INTO object_external_refs(
            object_id, system, ref_type, external_id, url, scope, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            (
                object_record.data["id"],
                ref["system"],
                ref["ref_type"],
                ref["external_id"],
                ref.get("url"),
                ref.get("scope"),
                ref.get("notes"),
            )
            for object_record in object_records
            for ref in _dicts(object_record.data.get("external_refs"))
        ),
    )
    connection.executemany(
        """
        INSERT INTO cave_external_refs(cave_id, system, ref_type, external_id, url, scope, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            (
                cave_record.data["id"],
                ref["system"],
                ref["ref_type"],
                ref["external_id"],
                ref.get("url"),
                ref.get("scope"),
                ref.get("notes"),
            )
            for cave_record in cave_records
            for ref in _dicts(cave_record.data.get("external_refs"))
        ),
    )


def _insert_attachments(
    connection: sqlite3.Connection,
    object_records: tuple[LoadedYamlRecord, ...],
) -> None:
    connection.executemany(
        """
        INSERT INTO attachments(
            object_id, id, kind, measurement_id, path, caption, date, created_at, created_by
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            (
                object_record.data["id"],
                attachment["id"],
                attachment["kind"],
                attachment.get("measurement_id"),
                attachment["path"],
                attachment.get("caption"),
                attachment.get("date"),
                attachment["created_at"],
                attachment["created_by"],
            )
            for object_record in object_records
            for attachment in _dicts(object_record.data.get("attachments"))
        ),
    )


def _insert_relations(
    connection: sqlite3.Connection,
    relation_records: tuple[LoadedYamlRecord, ...],
) -> None:
    connection.executemany(
        """
        INSERT INTO relations(
            id, schema_version, from_object_id, to_object_id, relation_type, notes
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            (
                relation.data["id"],
                relation.data["schema_version"],
                relation.data["from_object_id"],
                relation.data["to_object_id"],
                relation.data["relation_type"],
                relation.data.get("notes"),
            )
            for relation in relation_records
        ),
    )


def _insert_best_measurements(
    connection: sqlite3.Connection,
    object_records: tuple[LoadedYamlRecord, ...],
) -> None:
    connection.executemany(
        """
        INSERT INTO best_measurements(
            object_id, mode, measurement_id, computed_best_measurement_id,
            reason, updated_at, updated_by
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            (
                object_record.data["id"],
                best["mode"],
                best["measurement_id"],
                select_default_best_measurement_id(
                    _measurement_dicts(object_record.data.get("measurements"))
                ),
                best.get("reason"),
                best["updated_at"],
                best["updated_by"],
            )
            for object_record in object_records
            for best in (_best_measurement_data(object_record.data),)
        ),
    )


def _insert_validation_flags(
    connection: sqlite3.Connection,
    issues: tuple[ValidationIssue, ...],
) -> None:
    connection.executemany(
        """
        INSERT INTO validation_flags(code, severity, path, description)
        VALUES (?, ?, ?, ?)
        """,
        (
            (
                issue.code,
                issue.severity.value,
                str(issue.path) if issue.path is not None else None,
                issue.description,
            )
            for issue in issues
        ),
    )


def _build_metadata(
    dataset: LoadedDataset,
    *,
    generated_at: str,
    validation_issues: tuple[ValidationIssue, ...],
) -> dict[str, str]:
    warning_count = sum(1 for issue in validation_issues if issue.severity == "warning")
    error_count = sum(1 for issue in validation_issues if issue.severity == "error")
    measurement_count = sum(
        len(_measurement_dicts(record.data.get("measurements"))) for record in dataset.objects
    )
    return {
        "generated_at": generated_at,
        "schema_version": str(SQLITE_SCHEMA_VERSION),
        "object_count": str(len(dataset.objects)),
        "cave_count": str(len(dataset.caves)),
        "relation_count": str(len(dataset.relations)),
        "measurement_count": str(measurement_count),
        "validation_warning_count": str(warning_count),
        "validation_error_count": str(error_count),
    }


def _best_measurement_data(object_data: dict[str, Any]) -> dict[str, Any]:
    best_measurement = object_data.get("best_measurement")
    return best_measurement if isinstance(best_measurement, dict) else {}


def _measurement_by_id(
    object_data: dict[str, Any],
    measurement_id: str,
) -> dict[str, Any] | None:
    for measurement in _measurement_dicts(object_data.get("measurements")):
        if measurement.get("id") == measurement_id:
            return measurement
    return None


def _measurement_dicts(value: object) -> tuple[dict[str, Any], ...]:
    return _dicts(value)


def _dicts(value: object) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, dict))


def _number_or_none(data: dict[str, Any] | None, key: str) -> float | None:
    if data is None:
        return None
    value = data.get(key)
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(value)
    return None


def _geom_wgs84(measurement: dict[str, Any] | None) -> str | None:
    if measurement is None:
        return None
    lon = _number_or_none(measurement, "lon")
    lat = _number_or_none(measurement, "lat")
    if lon is None or lat is None:
        return None
    return f"POINT({lon} {lat})"


def _geom_1992(measurement: dict[str, Any] | None) -> str | None:
    if measurement is None:
        return None
    y_1992 = _number_or_none(measurement, "y_1992")
    x_1992 = _number_or_none(measurement, "x_1992")
    if y_1992 is None or x_1992 is None:
        return None
    return f"POINT({y_1992} {x_1992})"


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _utc_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
