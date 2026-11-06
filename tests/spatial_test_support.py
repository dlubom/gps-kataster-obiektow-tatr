"""Small EPSG:2180 reference polygons shared by catalogue and GPX tests."""

import shapefile
import yaml


def spatial_reference(root, *, reverse=False):
    (root / "config").mkdir(parents=True)
    (root / "config/prefixes.yml").write_text(
        yaml.safe_dump(
            {
                "valley_prefixes": {"first": "MTW", "second": "KSW"},
                "fallback_prefixes": {"polska": "PL", "slowacja": "SK"},
            }
        )
    )
    shapes = root / "data/shapes"
    shapes.mkdir(parents=True)
    outer = [
        (560000, 150000),
        (560000, 150010),
        (560010, 150010),
        (560010, 150000),
        (560000, 150000),
    ]
    hole = [
        (560002, 150002),
        (560008, 150002),
        (560008, 150008),
        (560002, 150008),
        (560002, 150002),
    ]
    overlap = [
        (560006, 150006),
        (560006, 150020),
        (560020, 150020),
        (560020, 150006),
        (560006, 150006),
    ]
    valleys = [("first", [outer, hole]), ("second", [overlap])]
    if reverse:
        valleys.reverse()
    with shapefile.Writer(str(shapes / "doliny"), shapeType=shapefile.POLYGON) as w:
        w.field("NAME", "C")
        for name, rings in valleys:
            w.poly(rings)
            w.record(name)
    for name, x0, x1 in (("granica_polski", 559990, 560030), ("granica_slowacji", 559990, 560060)):
        with shapefile.Writer(str(shapes / name), shapeType=shapefile.POLYGON) as w:
            w.field("NAME", "C")
            w.poly([[(x0, 149990), (x0, 150030), (x1, 150030), (x1, 149990), (x0, 149990)]])
            w.record(name)
    return root
