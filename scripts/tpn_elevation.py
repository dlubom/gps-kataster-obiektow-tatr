#!/usr/bin/env python3
"""Read the ground elevation of one WGS84 point from the public TPN NMT."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gps_kataster_obiektow_tatr.tpn_elevation import (  # noqa: E402
    ElevationError,
    fetch_elevation,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lat", required=True, type=float, help="WGS84 latitude, decimal degrees")
    parser.add_argument("--lon", required=True, type=float, help="WGS84 longitude, decimal degrees")
    parser.add_argument("--json", action="store_true", help="Print JSON with the raw API value")
    parser.add_argument(
        "--timeout", type=float, default=20.0, help="Timeout per HTTP request, seconds"
    )
    args = parser.parse_args(argv)
    try:
        result = fetch_elevation(args.lat, args.lon, timeout=args.timeout)
    except ElevationError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2))
    else:
        source = result["source"]
        print(
            f"Wysokość gruntu NMT: {result['elevation_m']:.2f} "
            f"{source['elevation_reference_label']} (według legendy TPN)"
        )
        print(f"WGS84: lat={args.lat}, lon={args.lon}")
        print(f"TPN: {source['model']}; siatka {source['grid_resolution_m']} m")
        print("Dokładny układ wysokości: unknown; dokładność pionowa: unknown")
        print(f"Data pozyskania danych: {source['data_date']} (według dokumentacji TPN)")
        print("Najnowszość: unconfirmed; interpolacja: unknown")
        print(f"Pobrano: {result['retrieved_at']}")
        print(f"Źródło: {source['identify_url']}")
        print(f"Legenda odniesienia wysokości: {source['legend_url']}")
        print("Liczba cyfr i siatka rastra nie określają dokładności wysokości.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
