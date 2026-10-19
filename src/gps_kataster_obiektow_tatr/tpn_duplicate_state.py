"""Read-only remembered duplicate evidence, accepted only through main."""

from pathlib import Path

from .tpn_api import require
from .tpn_normalization import digest, exact_json
from .tpn_snapshot import validate_time
from .tpn_source_state import git, hash_value

DUPLICATES_PATH = "data/source_state/tpn/duplicates.json"
OUTCOMES = {"same_opening", "different_openings_same_cave", "different_objects", "unresolved"}


def validate_resolutions(resolutions: list[dict]) -> None:
    require(isinstance(resolutions, list), "duplicate resolutions must be a list")
    seen = set()
    for r in resolutions:
        require(
            isinstance(r, dict)
            and set(r)
            == {"pair", "outcome", "basis", "basis_hash", "evidence", "reviewed_by", "reviewed_at"},
            "invalid duplicate resolution fields",
        )
        pair = r["pair"]
        require(
            isinstance(pair, list)
            and len(pair) == 2
            and all(isinstance(k, str) and k for k in pair)
            and pair == sorted(set(pair)),
            "invalid duplicate pair",
        )
        require(tuple(pair) not in seen, "duplicate pair resolution")
        seen.add(tuple(pair))
        require(
            isinstance(r["outcome"], str) and r["outcome"] in OUTCOMES, "invalid duplicate outcome"
        )
        hash_value(r["basis_hash"])
        require(
            isinstance(r["basis"], dict)
            and set(r["basis"]) == {"sides", "policy", "catalog_hash", "source_set_hash"},
            "invalid duplicate basis",
        )
        require(
            isinstance(r["basis"]["sides"], list)
            and len(r["basis"]["sides"]) == 2
            and all(
                isinstance(s, dict) and isinstance(s.get("key"), str) for s in r["basis"]["sides"]
            )
            and [s["key"] for s in r["basis"]["sides"]] == pair,
            "duplicate basis pair mismatch",
        )
        hash_value(r["basis"]["source_set_hash"])
        require(digest(r["basis"]) == r["basis_hash"], "duplicate basis hash mismatch")
        for key in ("evidence", "reviewed_by"):
            require(
                isinstance(r[key], str) and bool(r[key].strip()),
                "missing duplicate review evidence/author",
            )
        validate_time(r["reviewed_at"])


def read_accepted_duplicates(repo: Path, commit: str) -> list[dict]:
    paths = git(repo, "ls-tree", "--name-only", commit, "--", DUPLICATES_PATH).decode().splitlines()
    if not paths:
        return []
    require(paths == [DUPLICATES_PATH], "invalid duplicate state path")
    state = exact_json(git(repo, "show", f"{commit}:{DUPLICATES_PATH}"))
    require(
        isinstance(state, dict)
        and set(state) == {"format", "format_version", "resolutions"}
        and state["format"] == "tpn-duplicate-state"
        and type(state["format_version"]) is int
        and state["format_version"] == 1,
        "unsupported duplicate state",
    )
    validate_resolutions(state["resolutions"])
    return state["resolutions"]
