[🇵🇱 Polski](README.md) | 🇬🇧 **English** | [🇸🇰 Slovenčina](README.sk.md)

# GPS Registry of Tatra Cave Entrances and Karst Features

[![Latest Release](https://img.shields.io/github/v/release/dlubom/gps-kataster-obiektow-tatr)](https://github.com/dlubom/gps-kataster-obiektow-tatr/releases/latest)

[Download the latest data](https://github.com/dlubom/gps-kataster-obiektow-tatr/releases/latest)

## Project overview

The GPS Registry of Tatra Cave Entrances and Karst Features is an open,
evolving dataset of locations important to speleology and karst research on
both the Polish and Slovak sides of the Tatra Mountains. It covers cave
entrances, adits, swallow holes, karst springs and related field features.

The project combines field GPS and GNSS measurements with catalogue and
institutional data. It preserves the source, accuracy, verification status and
history of every location. Each physical cave entrance is a separate object,
so caves with several entrances can be represented correctly.

Cavers can load the points into a GPS receiver or mobile app, while
cartographers and researchers can use them in GIS and assess how thoroughly a
location has been verified.

## Download the data

Download the latest data from
[GitHub Releases](https://github.com/dlubom/gps-kataster-obiektow-tatr/releases/latest).

Each release contains ready-to-use files for fieldwork and desktop analysis:

| Format | Best suited for |
|---|---|
| GPX | waypoints in a GPS receiver or field app |
| GeoJSON and Shapefile | mapping, analysis and combining layers in QGIS or another GIS |
| CSV | browsing, filtering and joining data in a table |
| SQLite | more detailed analysis of objects, caves, measurements and their history |

The package also includes `metadata.json` with the dataset version and basic
record counts for the release.

## Accuracy and verification

The points come from different years, devices and sources, so their accuracy
varies. A point marked as the “best available measurement” has not necessarily
been confirmed in the field. Before using a point, check its source,
verification status, stated accuracy and notes.

In early releases, the best available measurement for most objects may be
marked `verification_status: nieweryfikowany` (unverified). This means that the
point came from imported or transcribed source data and has not yet been
verified in the field or reviewed by a project maintainer. This does not by
itself mean that the point is wrong or lacks source information; until a better
measurement is available, it remains the best known location.

## Three connected projects

Three repositories describe the same area from different perspectives:

| Project | The question it answers | What it provides |
|---|---|---|
| **GPS Registry of Tatra Cave Entrances and Karst Features** (this project) | Where is a specific cave entrance or other field feature? | The best available coordinates together with their source, history and verification status. |
| [Tatra Cave Registry](https://github.com/dlubom/Jaskiniowy-Kataster-Tatr-Zachodnich) | What routes do the survey centrelines follow, and what is the geometry of the underground system? | Walls and Survex survey data, 2D visualisations and an [online 3D model](https://dlubom.github.io/Jaskiniowy-Kataster-Tatr-Zachodnich/) for caves with available surveys; ready-to-use files are in the [latest release](https://github.com/dlubom/Jaskiniowy-Kataster-Tatr-Zachodnich/releases/latest). |
| [Georeferencer](https://github.com/dlubom/Georeferencer) | How does a scanned cave plan align with a map? | Georeferenced cave-plan scans in GeoTIFF format, including caves without survey data in the Tatra Cave Registry; the package is available from the [latest release](https://github.com/dlubom/Georeferencer/releases/latest). |

This registry is the shared source of entrance coordinates: both the Tatra
Cave Registry and Georeferencer use the best measurements published here.

## How you can help

If you have a more accurate GPS/GNSS measurement, know of a missing entrance,
or find a point assigned to the wrong cave or entrance, open an
[issue](https://github.com/dlubom/gps-kataster-obiektow-tatr/issues) or prepare
a pull request. Include the cave name, identify the specific entrance, and
provide its coordinates, date, method or device, estimated accuracy and data
source. Distinguishing between separate entrances of the same cave is
particularly important.

## For developers and data maintainers

YAML files in `data/` are the source of truth. SQLite, GeoJSON, GPX, CSV and
Shapefile files are generated artifacts.

`Obiekt` represents a specific physical feature recorded as a point, while
`Jaskinia` is a catalogue record that groups one or more entrances. Every
object preserves its full measurement history and identifies the current best
measurement.

### Quick start

```bash
uv sync
uv run pytest
uv run python scripts/validate.py
uv run python scripts/build_release_artifacts.py
```

Local artifacts are written to `build/` and are not committed.

### Project documentation

- [Specification and domain model](specyfikacja_gps_kataster_obiektow_tatr_v_2.md)
- [Adding and verifying measurements](docs/operations.md)
- [Release file formats and fields](docs/release_artifacts.md)
- [CHANGELOG.md](CHANGELOG.md)

Public releases follow Semantic Versioning with `vX.Y.Z` tags and are
published manually. The repository, documentation and generated data exports
are licensed under Creative Commons Attribution 4.0 International, as stated
in [LICENSE](LICENSE).
