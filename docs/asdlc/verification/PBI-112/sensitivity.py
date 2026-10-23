"""Negative controls for the one-off published-export audit."""

import csv
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
AUDIT = Path(__file__).resolve().parent / "audit.py"
ENGINE = ROOT / "vendor/geographiclib-build/tools/TransverseMercatorProj"


def run_case(name, mutation, expected, update_hash=True, fake_engine=False):
    with tempfile.TemporaryDirectory() as temp:
        folder = Path(temp)
        shutil.copytree(ROOT / "assets", folder / "assets")
        for filename in ("release.json", "release-tag.json"):
            shutil.copyfile(ROOT / filename, folder / filename)
        csv_path = folder / "assets/best-measurements.csv"
        with csv_path.open(newline="") as file:
            reader = csv.DictReader(file)
            fields, rows = reader.fieldnames, list(reader)
        mutation(rows)
        with csv_path.open("w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        if update_hash:
            release = json.loads((folder / "release.json").read_text())
            for asset in release["assets"]:
                if asset["name"] == csv_path.name:
                    asset["size"] = csv_path.stat().st_size
                    asset["digest"] = "sha256:" + hashlib.sha256(csv_path.read_bytes()).hexdigest()
            (folder / "release.json").write_text(json.dumps(release))
        engine = ENGINE
        if fake_engine:
            engine = folder / "injected-engine"
            engine.write_text(
                "#!" + sys.executable + "\nimport sys,subprocess\n"
                "data=sys.stdin.read()\n"
                "r=subprocess.run([" + repr(str(ENGINE)) + ",*sys.argv[1:]],input=data,"
                "text=True,capture_output=True,check=True)\n"
                "if '--version' in sys.argv:\n print(r.stdout,end='')\n"
                "else:\n"
                " for inp,line in zip(data.splitlines(),r.stdout.splitlines(),strict=True):\n"
                "  fields=line.split(); lat,lon=map(float,inp.split())\n"
                "  if (lat,lon) not in {(0,19),(49,19),(49,18),(49,20)}:\n"
                "   fields[1]=str(float(fields[1])+.03)\n"
                "  print(' '.join(fields))\n"
            )
            engine.chmod(0o755)
        result = subprocess.run(
            [
                sys.executable,
                str(AUDIT),
                str(folder / "assets"),
                str(engine),
                str(folder / "output"),
            ],
            text=True,
            capture_output=True,
        )
        assert result.returncode != 0, name + " unexpectedly accepted"
        assert expected in result.stdout + result.stderr, (name, result.stderr)
        if fake_engine:
            summary = json.loads((folder / "output/summary.json").read_text())
            assert summary["unexplained_differences"] == 11872
            assert summary["all_representations"]["max_distance_m"] > 0.02
        print(name + ": PASS (rejected)")


run_case("asset bytes without matching GitHub digest", lambda rows: rows.pop(), "Size:", False)
run_case("missing CSV point", lambda rows: rows.pop(), "Missing/extra keys: CSV")
run_case("duplicate CSV point", lambda rows: rows.append(dict(rows[0])), "Empty/duplicate key:")


def swap(rows):
    rows[0]["x_1992"], rows[0]["y_1992"] = rows[0]["y_1992"], rows[0]["x_1992"]


run_case("swapped PL-1992 axes", swap, "XY differs: CSV")
run_case("nonfinite latitude", lambda rows: rows[0].update(lat="nan"), "Nonfinite WGS84: CSV")
run_case(
    "injected 3 cm projection error",
    lambda rows: None,
    '"unexplained_differences": 11872',
    fake_engine=True,
)
