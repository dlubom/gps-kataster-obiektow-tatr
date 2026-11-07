"""Read-only export rows prepared from one validated PostgreSQL read model."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, fields
from types import MappingProxyType

from gps_kataster_obiektow_tatr.catalog_records import CAVE_MORPHOMETRY, FIELDS
from gps_kataster_obiektow_tatr.data_loader import LoadedDataset
from gps_kataster_obiektow_tatr.report_formatting import utc_timestamp


@dataclass(frozen=True, slots=True)
class BestMeasurementExportRow:
    """One selected measurement; field order is the public CSV order."""

    object_id: str
    category: str
    name_local: str | None
    cave_id: str | None
    measurement_id: str
    best_mode: str
    computed_best_measurement_id: str | None
    best_reason: str | None
    lat: float
    lon: float
    x_1992: float
    y_1992: float
    elevation_m: float | None
    source: str
    source_ref: str | None
    nr_inwent: str | None
    pig_id: str | None
    pig_url: str | None
    tpn_globalid: str | None
    observed_at: str | None
    observed_date: str
    method: str
    verification_status: str
    horizontal_accuracy_m: float | None
    vertical_accuracy_m: float | None
    object_notes: str | None
    cave_notes: str | None
    measurement_notes: str | None
    cave_length_m: float | None
    cave_depth_m: float | None
    cave_denivelation_m: float | None
    cave_denivelation_qualifier: str | None
    cave_morphometry_source_ref: str | None
    system_cave_id: str | None
    cave_system_name: str | None
    system_length_m: float | None
    system_depth_m: float | None
    system_denivelation_m: float | None
    system_denivelation_qualifier: str | None
    system_morphometry_source_ref: str | None


BEST_FIELDS = tuple(field.name for field in fields(BestMeasurementExportRow))

# Ordered shared Full attributes. Presentation (headers, widths, formats) belongs to Excel.
# Keep existing REAL declarations also for schema_version and input_srid.
FULL_FIELDS = MappingProxyType(
    {
        "object_id": str,
        "name_local": str,
        "selected": str,
        "category": str,
        "lat": float,
        "lon": float,
        "elevation_m": float,
        "source": str,
        "verification_status": str,
        "horizontal_accuracy_m": float,
        "observed_date": str,
        "nr_inwent": str,
        "measurement_id": str,
        "source_ref": str,
        "cave_id": str,
        "cave_name": str,
        "cave_system_name": str,
        "x_1992": float,
        "y_1992": float,
        "vertical_accuracy_m": float,
        "elevation_datum": str,
        "elevation_source": str,
        "source_date": str,
        "observed_at": str,
        "method": str,
        "device": str,
        "tags_json": str,
        "verified_by": str,
        "verified_at": str,
        "measurement_notes": str,
        "object_notes": str,
        "cave_notes": str,
        "pig_id": str,
        "pig_url": str,
        "tpn_globalid": str,
        "object_external_refs": str,
        "cave_external_refs": str,
        "attachments": str,
        "relations": str,
        "schema_version": float,
        "id_assignment_method": str,
        "assigned_from_measurement_id": str,
        "assigned_prefix": str,
        "prefix_override_reason": str,
        "best_mode": str,
        "best_measurement_id": str,
        "computed_best_measurement_id": str,
        "best_reason": str,
        "best_updated_at": str,
        "best_updated_by": str,
        "object_created_at": str,
        "object_created_by": str,
        "object_updated_at": str,
        "object_updated_by": str,
        "measurement_created_at": str,
        "measurement_created_by": str,
        "input_srid": float,
        "input_x": float,
        "input_y": float,
        "cave_length_m": float,
        "cave_depth_m": float,
        "cave_denivelation_m": float,
        "cave_denivelation_qualifier": str,
        "cave_morphometry_source_ref": str,
        "system_cave_id": str,
        "system_length_m": float,
        "system_depth_m": float,
        "system_denivelation_m": float,
        "system_denivelation_qualifier": str,
        "system_morphometry_source_ref": str,
    }
)
NUMERIC_FIELDS = frozenset(key for key, kind in FULL_FIELDS.items() if kind is float)
ExportRecord = Mapping[str, str | float | int | tuple[str, ...] | None]


@dataclass(frozen=True, slots=True)
class ExportData:
    best: tuple[BestMeasurementExportRow, ...]
    history: tuple[ExportRecord, ...]
    selected: tuple[ExportRecord, ...]
    caves: tuple[ExportRecord, ...]
    relation_count: int
    generated_at: str
    gpx_regions: Mapping[str, str | None]

    @property
    def cave_count(self) -> int:
        return len(self.caves)


def prepare_export_data(dataset: LoadedDataset, *, generated_at: str | None = None) -> ExportData:
    """Assemble once, retaining SQL's selected and computed Best and historical nulls."""
    caves = {r.data["id"]: r.data for r in dataset.caves}
    cave_rows = {}
    for cave_id, cave in sorted(caves.items()):
        system_id = cave.get("system_cave_id")
        system = caves[system_id] if system_id is not None else {}
        cave_rows[cave_id] = MappingProxyType(
            {
                "cave_id": cave_id,
                "cave_name": cave["name"],
                "cave_system_name": system.get("name", cave.get("system_name")),
                "nr_inwent": _joined_values(_external_ids(cave, "NR_INWENT")),
                **{f"cave_{key}": cave.get(key) for key in CAVE_MORPHOMETRY},
                "system_cave_id": system_id,
                **{f"system_{key}": system.get(key) for key in CAVE_MORPHOMETRY},
            }
        )
    empty_cave = dict.fromkeys(
        (
            "cave_name",
            "cave_system_name",
            "nr_inwent",
            *(f"cave_{key}" for key in CAVE_MORPHOMETRY),
            "system_cave_id",
            *(f"system_{key}" for key in CAVE_MORPHOMETRY),
        )
    )
    regions = {(oid, mid): prefix for oid, mid, prefix in dataset.measurement_regions}
    relations = {}
    for relation in dataset.relations:
        for oid in {relation.data["from_object_id"], relation.data["to_object_id"]}:
            relations.setdefault(oid, []).append(relation.data)
    best, history, selected = [], [], []
    for obj_record in sorted(dataset.objects, key=lambda r: r.data["id"]):
        obj = obj_record.data
        oid = obj["id"]
        cave = caves.get(obj.get("cave_id"), {})
        choice = obj["best_measurement"]
        metadata = {
            "object_id": oid,
            "name_local": obj.get("name_local"),
            "category": obj["category"],
            "schema_version": obj["schema_version"],
            "cave_id": obj.get("cave_id"),
            **cave_rows.get(obj.get("cave_id"), empty_cave),
            "object_notes": obj.get("notes"),
            "cave_notes": cave.get("notes"),
            "pig_id": _joined_values(_external_ids(cave, "PIG", "catalog_id")),
            "pig_url": _joined_values(
                ref.get("url") or (ref["external_id"] if ref["ref_type"] == "url" else "")
                for ref in cave.get("external_refs", [])
                if ref["system"] == "PIG"
            ),
            "tpn_globalid": _joined_values(
                [*_external_ids(obj, "TPN", "source_globalid"), *_tpn_measurement_refs(obj)]
            ),
            "object_external_refs": _json(_flat_refs(obj.get("external_refs", []))),
            "cave_external_refs": _json(_flat_refs(cave.get("external_refs", []))),
            "attachments": _json(
                [{**dict.fromkeys(FIELDS["attachments"]), **a} for a in obj.get("attachments", [])]
            ),
            "relations": _json([{"notes": None, **r} for r in relations.get(oid, [])]),
            "id_assignment_method": obj["id_assignment"]["method"],
            **{k: v for k, v in obj["id_assignment"].items() if k != "method"},
            "best_mode": choice["mode"],
            "best_measurement_id": choice["measurement_id"],
            "computed_best_measurement_id": obj["computed_best_measurement_id"],
            "best_reason": choice.get("reason"),
            "best_updated_at": choice["updated_at"],
            "best_updated_by": choice["updated_by"],
            **{
                f"object_{k}": obj[k]
                for k in ("created_at", "created_by", "updated_at", "updated_by")
            },
        }
        for measurement in sorted(obj["measurements"], key=lambda m: m["id"]):
            # No Best measurement values enter a history row, including omitted/null fields.
            row = MappingProxyType(
                {
                    **metadata,
                    **{
                        k: measurement.get(k)
                        for k in (
                            *FIELDS["measurements"],
                            "lat",
                            "lon",
                            "x_1992",
                            "y_1992",
                            "input_srid",
                            "input_x",
                            "input_y",
                        )
                        if k not in ("id", "notes", "created_at", "created_by")
                    },
                    "measurement_id": measurement["id"],
                    "selected": "Tak" if measurement["id"] == choice["measurement_id"] else "Nie",
                    "measurement_notes": measurement.get("notes"),
                    "measurement_created_at": measurement["created_at"],
                    "measurement_created_by": measurement["created_by"],
                    "tags": tuple(measurement.get("tags", [])),
                    "tags_json": _json(measurement.get("tags", [])),
                }
            )
            history.append(row)
            if row["selected"] == "Tak":
                selected.append(row)
                best.append(BestMeasurementExportRow(**{key: row.get(key) for key in BEST_FIELDS}))
        if not best or best[-1].object_id != oid:
            raise ValueError(
                f"Selected measurement {oid}/{choice['measurement_id']} "
                "is missing from packaged history"
            )
    return ExportData(
        tuple(best),
        tuple(history),
        tuple(selected),
        tuple(cave_rows.values()),
        len(dataset.relations),
        generated_at or utc_timestamp(),
        MappingProxyType(
            {row.object_id: regions.get((row.object_id, row.measurement_id)) for row in best}
        ),
    )


def _flat_refs(refs):
    return [{**dict.fromkeys(FIELDS["external_refs"]), **ref} for ref in refs]


def _external_ids(data, system, ref_type=None):
    return [
        ref["external_id"]
        for ref in data.get("external_refs", [])
        if ref["system"] == system and (ref_type is None or ref["ref_type"] == ref_type)
    ]


def _tpn_measurement_refs(obj):
    for measurement in obj["measurements"]:
        value = measurement.get("source_ref") or ""
        if value.startswith("TPN:{") and value.endswith("}"):
            yield value.removeprefix("TPN:")


def _joined_values(values):
    return ";".join(dict.fromkeys(value.strip() for value in values if value.strip())) or None


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)
