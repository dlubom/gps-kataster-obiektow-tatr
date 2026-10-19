"""Versioned precision of derived TPN values, never raw source coordinates.

PROJ/geodesic implementations can differ below a nanometre across platforms.
Persist derived projections and displayed distances at a declared precision;
all radius/tolerance decisions still use the unrounded geodesic result.
"""

POLICY = {
    "version": "tpn-derived-numerics-v1",
    "csv_projected_degrees": 9,
    "reported_distance_metres": 3,
    "new_measurement_projected_metres": 3,
    "rounding": "half_even",
    "raw_api_geometry": "exact_unchanged",
    "distance_predicates": "unrounded",
    "existing_catalog_measurements": "unchanged",
}


def csv_degrees(value):
    return round(value, POLICY["csv_projected_degrees"])


def reported_distance(value):
    return round(value, POLICY["reported_distance_metres"])


def projected_metres(value):
    return round(value, POLICY["new_measurement_projected_metres"])
