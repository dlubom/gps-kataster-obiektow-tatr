"""Read-only PBI-054 review: schema-valid public-path reproductions in temp dirs."""

from __future__ import annotations

# ruff: noqa: E402
import json
import sys
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
from test_staging_review import _cave_data, _object_data, _write_yaml
from test_tpn_staging import _tpn_row, _write_tpn_csv

from gps_kataster_obiektow_tatr.data_loader import load_dataset
from gps_kataster_obiektow_tatr.staging_review import (
    StagingReports,
    apply_review_decisions,
    load_staging_reports,
)
from gps_kataster_obiektow_tatr.tpn_staging import build_tpn_staging, write_staging_files
from gps_kataster_obiektow_tatr.validator import (
    has_errors,
    validate_data_dir,
    validate_record_schemas,
)

STAMP = "2026-10-14T10:00:00Z"


def ref(value: str) -> dict:
    return {"system": "NR_INWENT", "ref_type": "inventory_number", "external_id": value}


def snapshot(root: Path) -> dict:
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def stage(root: Path, data: Path, *, globalid: str) -> object:
    source = root / "tpn.csv"
    _write_tpn_csv(
        source,
        [
            _tpn_row(
                nr_inwent="T.CURRENT-2",
                name="Updated source name",
                globalid=globalid,
                x_1992="152267,23",
                y_1992="563744,25",
            )
        ],
    )
    return build_tpn_staging(source, generated_at=STAMP, data_dir=data, pig_staging_path=None)


def review(root: Path, data: Path, report: object, decisions: list) -> object:
    path, _ = write_staging_files(report, output_dir=root / "staging")
    reports = load_staging_reports(pig_staging_path=None, tpn_staging_path=path)
    return apply_review_decisions(
        {"reviewed_at": STAMP, "reviewed_by": "independent-review", "decisions": decisions},
        staging_reports=reports,
        data_dir=data,
    )


def inventory_probe(root: Path) -> dict:
    data = root / "data"
    obj = _object_data(cave_id="C-0001")
    obj.update(
        name_local="Original name",
        external_refs=[
            {"system": "TPN", "ref_type": "source_globalid", "external_id": "{EXISTING}"}
        ],
    )
    cave = _cave_data(object_ids=["KSW-0001"], external_refs=[ref("T.OLD-1")])
    _write_yaml(data / "objects/KSW/KSW-0001.yml", obj)
    cave_path = data / "caves/C-0001.yml"
    _write_yaml(cave_path, cave)
    assert not has_errors(validate_data_dir(data))
    first = stage(root, data, globalid="{EXISTING}")
    assert first.rows[0].status == "matched" and first.rows[0].match_strategy == "globalid"
    accepted = review(
        root, data, first, [{"action": "add_measurement", "source": "TPN", "record_number": 1}]
    )
    assert not accepted.has_errors
    current_cave = load_dataset(data).caves[0].raw_data
    assert [r["external_id"] for r in current_cave["external_refs"]] == ["T.OLD-1", "T.CURRENT-2"]
    assert not has_errors(validate_data_dir(data))
    before = snapshot(data)
    original = stage(root, data, globalid="{MULTI-NR}")
    assert snapshot(data) == before
    changed = deepcopy(current_cave)
    changed["external_refs"].reverse()
    _write_yaml(cave_path, changed)
    assert not has_errors(validate_data_dir(data))
    reordered = stage(root, data, globalid="{MULTI-NR}")
    _write_yaml(cave_path, current_cave)
    result = review(
        root,
        data,
        original,
        [
            {"action": "create_cave", "source": "TPN", "record_number": 1},
            {"action": "create_object", "source": "TPN", "record_number": 1},
        ],
    )
    final = load_dataset(data)
    return {
        "case": "inventory_refs_order",
        "supported_add_measurement_created_refs": [
            r["external_id"] for r in current_cave["external_refs"]
        ],
        "original_order": [
            original.rows[0].status,
            original.rows[0].object_id,
            original.rows[0].cave_id,
            original.rows[0].match_strategy,
        ],
        "reversed_refs": [
            reordered.rows[0].status,
            reordered.rows[0].object_id,
            reordered.rows[0].cave_id,
            reordered.rows[0].match_strategy,
        ],
        "create_accepted_has_errors": result.has_errors,
        "final_yaml_written": len(result.written_paths),
        "final_counts": {"objects": len(final.objects), "caves": len(final.caves)},
        "final_validation_codes": [i.code for i in validate_data_dir(data)],
        "final_has_validation_errors": has_errors(validate_data_dir(data)),
    }


def url_probe(root: Path) -> list:
    data = root / "data"
    obj = _object_data(cave_id="C-0001")
    cave = _cave_data(object_ids=["KSW-0001"])
    _write_yaml(data / "caves/C-0001.yml", cave)
    path = data / "objects/KSW/KSW-0001.yml"
    output = []
    for url in ["https://[", "http://[abc]", "http://exa／mple.test/"]:
        obj["attachments"] = [
            {
                "id": "a-001",
                "kind": "inne",
                "path": url,
                "created_at": STAMP,
                "created_by": "independent-review",
            }
        ]
        _write_yaml(path, obj)
        before = snapshot(data)
        record = {
            "case": "malformed_attachment_url",
            "url": url,
            "schema_error_count": len(validate_record_schemas(load_dataset(data).records())),
        }
        for action, call in [
            ("validate_data_dir", lambda: validate_data_dir(data)),
            (
                "apply_review_decisions",
                lambda: apply_review_decisions(
                    {"reviewed_at": STAMP, "decisions": []},
                    staging_reports=StagingReports(),
                    data_dir=data,
                ),
            ),
        ]:
            try:
                call()
                record[action] = "returned result"
            except Exception as exc:
                record[action] = {"exception": type(exc).__name__, "message": str(exc)}
        record["final_bytes_unchanged"] = snapshot(data) == before
        output.append(record)
    return output


if __name__ == "__main__":
    with TemporaryDirectory(prefix="PBI-054-independent-review-", dir="/tmp") as tmp:
        root = Path(tmp)
        inventory = inventory_probe(root / "inventory")
        urls = url_probe(root / "urls")
        assert inventory["original_order"] == ["new", "KSW-0002", "C-0002", None]
        assert inventory["reversed_refs"] == ["matched", "KSW-0001", "C-0001", "nr_inwent"]
        assert inventory["create_accepted_has_errors"] is False
        assert inventory["final_counts"] == {"objects": 2, "caves": 2}
        assert inventory["final_yaml_written"] == 2
        assert inventory["final_has_validation_errors"] is False
        for result in urls:
            assert result["schema_error_count"] == 0
            assert result["final_bytes_unchanged"]
            for action in ("validate_data_dir", "apply_review_decisions"):
                assert result[action]["exception"] == "ValueError"
        print(json.dumps({"inventory": inventory, "urls": urls}, ensure_ascii=False, indent=2))
