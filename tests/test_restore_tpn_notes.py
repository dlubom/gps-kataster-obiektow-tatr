import csv
import json
import subprocess
import sys
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/maintenance/restore_tpn_notes.py"
GID = "{000EF2B6-F573-434D-B6DD-D3F0D6F9F568}"


def _source(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["GLOBALID", "NAZWA", "WER_LOK", "UWAGI"])
        writer.writeheader()
        writer.writerows(rows)


def _seed(tmp_path, make_data_dir):
    data = make_data_dir(tmp_path / "data")
    path = data / "objects/MTW/MTW-0047.yml"
    path.parent.mkdir(parents=True)
    original = yaml.safe_load((ROOT / "data/objects/MTW/MTW-0047.yml").read_text())
    original["measurements"][1]["notes"] = "Ręczna uwaga bez utraty.  "
    path.write_text(yaml.safe_dump(original, allow_unicode=True, sort_keys=False))
    source = tmp_path / "source.csv"
    _source(
        source,
        [
            {
                "GLOBALID": GID,
                "NAZWA": "inna nazwa",
                "WER_LOK": "niepewna",
                "UWAGI": "przybliżona lokalizacja",
            }
        ],
    )
    return data, path, source, original


def _run(source, data, report, apply=False):
    assert SCRIPT.is_file(), "Missing dry-run restoration tool"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--source",
            str(source),
            "--data-dir",
            str(data),
            "--report",
            str(report),
            "--generated-at",
            "2026-10-15T00:00:00Z",
            *(["--apply"] if apply else []),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(report.read_text())


def test_restore_manifest_manual_notes_allowed_fields_and_idempotence(tmp_path, make_data_dir):
    data, path, source, original = _seed(tmp_path, make_data_dir)
    before = path.read_bytes()
    source_before = source.read_bytes()
    report = tmp_path / "manifest.json"
    dry = _run(source, data, report)
    assert path.read_bytes() == before
    assert dry["mode"] == "dry-run"
    assert dry["source_sha256"] == sha256(source_before).hexdigest()
    change = dry["changes"][0]
    assert change["globalid"] == GID
    assert change["object_id"] == "MTW-0047" and change["measurement_id"] == "m-002"
    assert change["path"] == "objects/MTW/MTW-0047.yml"
    assert change["before"]["notes"] == "Ręczna uwaga bez utraty.  "
    expected = (
        "Ręczna uwaga bez utraty.  \nTPN WER_LOK: niepewna\nTPN UWAGI: przybliżona lokalizacja"
    )
    assert change["after"]["notes"] == expected
    assert change["reason"]
    applied = _run(source, data, report, True)
    assert applied["changes"] == dry["changes"]
    obj = yaml.safe_load(path.read_text())
    assert obj["measurements"][1]["notes"] == expected
    assert obj["updated_by"] == "maintenance:PBI-082"
    assert obj["updated_at"] != original["updated_at"]
    allowed = deepcopy(original)
    allowed["measurements"][1]["notes"] = expected
    allowed["updated_by"] = obj["updated_by"]
    allowed["updated_at"] = obj["updated_at"]
    assert obj == allowed
    after = path.read_bytes()
    again = _run(source, data, report, True)
    assert again["changes"] == []
    assert path.read_bytes() == after and source.read_bytes() == source_before


@pytest.mark.parametrize(
    "damage",
    [
        "source-duplicate",
        "object-duplicate",
        "measurement-duplicate",
        "missing-object",
        "missing-measurement",
        "wrong-ref-type",
        "wrong-system",
        "wrong-source",
        "other-owner",
        "cross-owned",
        "duplicate-object-id",
        "duplicate-local-id",
        "blank-globalid",
    ],
)
def test_uncertain_identity_never_writes_by_name_or_row(tmp_path, make_data_dir, damage):
    data, path, source, obj = _seed(tmp_path, make_data_dir)
    if damage == "source-duplicate":
        row = {"GLOBALID": GID, "NAZWA": "Studnia na Szlaku", "WER_LOK": "niepewna"}
        _source(source, [row, row])
    elif damage == "blank-globalid":
        _source(source, [{"GLOBALID": "", "NAZWA": "Studnia na Szlaku", "UWAGI": "uwaga"}])
    elif damage in {"object-duplicate", "other-owner", "cross-owned", "duplicate-object-id"}:
        other = deepcopy(obj)
        other["id"] = "MTW-9999"
        if damage in {"other-owner", "cross-owned", "duplicate-object-id"}:
            other["external_refs"] = []
        if damage in {"object-duplicate", "duplicate-object-id"}:
            other["measurements"] = other["measurements"][:1]
        if damage == "duplicate-object-id":
            other["id"] = obj["id"]
        if damage == "cross-owned":
            obj["measurements"][1]["source_ref"] = "TPN:{other}"
        (path.parent / "MTW-9999.yml").write_text(yaml.safe_dump(other))
    elif damage == "measurement-duplicate":
        other = deepcopy(obj["measurements"][1])
        other["id"] = "m-003"
        obj["measurements"].append(other)
    elif damage == "duplicate-local-id":
        obj["measurements"][0]["id"] = "m-002"
    elif damage == "missing-object":
        obj["external_refs"] = []
    elif damage == "missing-measurement":
        obj["measurements"][1]["source_ref"] = "TPN:{other}"
    elif damage == "wrong-ref-type":
        obj["external_refs"][0]["ref_type"] = "other"
    elif damage == "wrong-system":
        obj["external_refs"][0]["system"] = "PIG"
    elif damage == "wrong-source":
        obj["measurements"][1]["source"] = "PIG"
    path.write_text(yaml.safe_dump(obj, sort_keys=False))
    before = {p: p.read_bytes() for p in data.rglob("*.yml")}
    report = _run(source, data, tmp_path / "report.json", True)
    assert report["changes"] == []
    assert report["issues"] and all(i["reason"] for i in report["issues"])
    assert {p: p.read_bytes() for p in data.rglob("*.yml")} == before


def test_no_context_has_no_changes_or_audit_updates(tmp_path, make_data_dir):
    data, path, source, _ = _seed(tmp_path, make_data_dir)
    _source(source, [{"GLOBALID": GID}])
    before = path.read_bytes()
    assert _run(source, data, tmp_path / "report.json", True)["changes"] == []
    assert path.read_bytes() == before


@pytest.mark.parametrize("level", ["object", "measurement"])
@pytest.mark.parametrize("invalid", [None, "", "  ", [], {}, 123, "missing"])
def test_invalid_local_id_skips_only_uncertain_record(tmp_path, make_data_dir, level, invalid):
    data, path, source, obj = _seed(tmp_path, make_data_dir)
    valid = deepcopy(obj)
    valid["id"] = "MTW-9999"
    valid["external_refs"][0]["external_id"] = "{valid}"
    valid["measurements"][1]["source_ref"] = "TPN:{valid}"
    valid_path = path.parent / "MTW-9999.yml"
    valid_path.write_text(yaml.safe_dump(valid, allow_unicode=True, sort_keys=False))
    target = obj if level == "object" else obj["measurements"][1]
    if invalid == "missing":
        del target["id"]
    else:
        target["id"] = invalid
    path.write_text(yaml.safe_dump(obj, allow_unicode=True, sort_keys=False))
    before = path.read_bytes()
    _source(
        source,
        [
            {"GLOBALID": GID, "UWAGI": "pomijana"},
            {"GLOBALID": "{valid}", "UWAGI": "poprawny kontekst"},
        ],
    )
    report = _run(source, data, tmp_path / "report.json", True)
    assert path.read_bytes() == before
    assert len(report["changes"]) == 1
    assert report["changes"][0]["object_id"] == "MTW-9999"
    assert report["issues"] and report["issues"][0]["globalid"] == GID
    assert (
        "TPN UWAGI: poprawny kontekst"
        in yaml.safe_load(valid_path.read_text())["measurements"][1]["notes"]
    )


@pytest.mark.parametrize(
    "initial", [None, "", "TPN UWAGI: przybliżona lokalizacja rozszerzona", "TPN WER_LOK: niepewna"]
)
def test_restore_retains_partial_and_longer_manual_context(tmp_path, make_data_dir, initial):
    data, path, source, obj = _seed(tmp_path, make_data_dir)
    obj["measurements"][1]["notes"] = initial
    path.write_text(yaml.safe_dump(obj, allow_unicode=True, sort_keys=False))
    _run(source, data, tmp_path / "report.json", True)
    note = yaml.safe_load(path.read_text())["measurements"][1]["notes"]
    assert note.count("TPN WER_LOK: niepewna") == 1
    assert "\nTPN UWAGI: przybliżona lokalizacja\n" in f"\n{note}\n"
    if initial:
        assert note.startswith(initial)


@pytest.mark.parametrize("report_target", ["source", "object", "inside-data"])
def test_report_cannot_overwrite_source_or_dataset(tmp_path, make_data_dir, report_target):
    data, path, source, _ = _seed(tmp_path, make_data_dir)
    report = {"source": source, "object": path, "inside-data": data / "report.json"}[report_target]
    before = {p: p.read_bytes() for p in (path, source)}
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--source",
            str(source),
            "--data-dir",
            str(data),
            "--report",
            str(report),
            "--apply",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1 and "Report must be outside" in result.stderr
    assert {p: p.read_bytes() for p in before} == before
    assert not (data / "report.json").exists()


@pytest.mark.parametrize(
    "csv_text",
    ["NAZWA\nTest\n", "GLOBALID,WER_LOK,UWAGI,UWAGI\nx,y,z,z\n", "GLOBALID,WER_LOK,UWAGI\nx,y\n"],
)
def test_malformed_source_blocks_all_writes(tmp_path, make_data_dir, csv_text):
    data, path, source, _ = _seed(tmp_path, make_data_dir)
    source.write_text(csv_text)
    before = path.read_bytes()
    report = tmp_path / "report.json"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--source",
            str(source),
            "--data-dir",
            str(data),
            "--report",
            str(report),
            "--apply",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1 and "CSV" in result.stderr
    assert path.read_bytes() == before and not report.exists()


@pytest.mark.parametrize(
    ("object_id", "text"),
    [
        ("MTW-0047", "przybliżona lokalizacja"),
        ("CHZ-0021", "Wg opisu z inwentarza. Trzeba uściślić położenie"),
        ("BYW-0015", "Opis dojścia w inwentarzu jest błędny"),
        ("BYW-0031", "Opis dojścia w inwentarzu jest błędny"),
    ],
)
def test_real_source_context_at_correct_measurement(tmp_path, make_data_dir, object_id, text):
    data = make_data_dir(tmp_path / "data")
    path = data / f"objects/{object_id.split('-')[0]}/{object_id}.yml"
    path.parent.mkdir(parents=True)
    obj = yaml.safe_load((ROOT / "data" / path.relative_to(data)).read_text())
    for measurement in obj["measurements"]:
        if measurement["source"] == "TPN":
            measurement["notes"] = "Ręczna uwaga zachowana przy odtworzeniu."
    path.write_text(yaml.safe_dump(obj, allow_unicode=True, sort_keys=False))
    source = ROOT / "data/sources/tpn/tpn_otwory_jaskin.xlsx.-.Export.csv"
    result = _run(source, data, tmp_path / "report.json", True)
    obj = yaml.safe_load(path.read_text())
    measurement = next(m for m in obj["measurements"] if m["source"] == "TPN")
    assert f"TPN UWAGI: {text}" in measurement["notes"]
    assert all(c["object_id"] == object_id for c in result["changes"])
