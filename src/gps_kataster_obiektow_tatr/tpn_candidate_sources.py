"""Historical PIG names as candidate signals, never opening identity."""

import csv
import io
import re
from pathlib import Path

from .tpn_api import require
from .tpn_normalization import digest
from .tpn_snapshot import sha256

PIG_CSV = Path("data/sources/pig/pig_otwory_jaskin_.xlsx.-.Export.csv")


def pig_sides(root: Path) -> tuple[list[dict], dict]:
    path = root / PIG_CSV
    if not path.is_file():
        return [], {
            "complete": False,
            "reason": "missing historical PIG name source",
            "path": str(PIG_CSV),
        }
    require(path.resolve() == path, "PIG name source symlink")
    raw = path.read_bytes()
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
    require(
        reader.fieldnames is not None
        and len(reader.fieldnames) == len(set(reader.fieldnames))
        and {"ID", "Nazwa", "Inne nazwy", "Nr inw."} <= set(reader.fieldnames),
        "PIG name source schema mismatch",
    )
    result = []
    for i, row in enumerate(reader, 1):
        require(
            None not in row and all(value is not None for value in row.values()),
            "PIG name source non-rectangular",
        )
        names = [{"field": f"PIG.{k}", "value": row[k]} for k in ("Nazwa", "Inne nazwy") if row[k]]
        # Keep the full field as evidence; each comma/semicolon alias is also
        # a conservative signal. No numeric/opening suffix is removed.
        aliases = re.split(r"[,;]", row["Inne nazwy"])
        if len(aliases) > 1:
            names.extend(
                {
                    "field": "PIG.Inne nazwy.alias",
                    "value": alias.strip(),
                    "raw_field": row["Inne nazwy"],
                }
                for alias in aliases
                if alias.strip()
            )
        result.append(
            {
                "key": f"pig:{i}:{row['ID']}",
                "target": {"pig_catalog_id": row["ID"], "source_row": i},
                "names": names,
                "inventories": [{"field": "PIG.Nr inw.", "value": row["Nr inw."]}]
                if row["Nr inw."]
                else [],
                "systems": [],
                "positions": [],
                "revision_hash": digest(row),
                "preimage": {},
            }
        )
    return result, {"complete": True, "path": str(PIG_CSV), "raw_sha256": sha256(raw)}
