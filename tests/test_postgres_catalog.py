"""Real PostgreSQL acceptance tests; KATASTER_DATABASE_URL selects the test server."""

from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from spatial_test_support import spatial_reference

from gps_kataster_obiektow_tatr.catalog_records import record_rows
from gps_kataster_obiektow_tatr.postgres import CatalogLoadError, open_catalog

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def records():
    obj = yaml.safe_load((ROOT / "tests/fixtures/canonical-object.yml").read_text())
    cave = yaml.safe_load((ROOT / "tests/fixtures/canonical-cave.yml").read_text())
    for record in (obj, cave):
        record["bibliography_status"] = "unknown"
    return obj, cave


def snapshot(tmp_path, records):
    from export_test_support import initialize_source

    initialize_source(tmp_path)
    for kind, record in zip(("objects", "caves"), records, strict=True):
        root = tmp_path / kind
        root.mkdir(parents=True, exist_ok=True)
        (root / f"{record['id']}.yml").write_text(yaml.safe_dump(record))
    (tmp_path / "relations").mkdir(exist_ok=True)
    (tmp_path / "publications").mkdir(exist_ok=True)
    return tmp_path


def test_native_catalog_round_trip(tmp_path, records):
    with open_catalog(snapshot(tmp_path / "first", records)) as catalog:
        dataset = catalog.dataset()
        assert dataset.objects[0].data["best_measurement"] == {
            **records[0]["best_measurement"],
            "measurement_id": "m-001",
        }
        assert dataset.objects[0].data["measurements"][0]["lat"] == 49.2423
        assert (
            catalog.connection.execute("SELECT count(*) n FROM catalog.v_best").fetchone()["n"] == 1
        )
    with open_catalog(tmp_path / "first") as catalog:
        assert catalog.dataset().objects[0].data == dataset.objects[0].data


@pytest.mark.parametrize(
    "change", ["fk", "id", "nan", "epsg", "manual", "known", "system-fk", "system-self"]
)
def test_native_constraints_reject_invalid_catalog(tmp_path, records, change):
    obj, cave = records
    if change == "fk":
        obj["cave_id"] = "C-9999"
    if change == "id":
        obj["id"] = "bad"
    if change == "nan":
        obj["measurements"][0]["elevation_m"] = float("nan")
    if change == "epsg":
        obj["measurements"][0].update(input_srid=3857, input_x=1, input_y=2)
    if change == "manual":
        obj["best_measurement"].update(mode="manual", reason=" ")
    if change == "known":
        cave["bibliography_status"] = "known"
    if change == "system-fk":
        cave["system_cave_id"] = "C-9999"
    if change == "system-self":
        cave["system_cave_id"] = cave["id"]
    with pytest.raises((CatalogLoadError, ValueError)), open_catalog(snapshot(tmp_path, records)):
        pass


def test_cave_system_must_not_be_a_member_of_another_system(tmp_path, records):
    _, cave = records
    cave["system_cave_id"] = "C-0002"
    root = snapshot(tmp_path, records)
    for cave_id, system_id in (("C-0002", "C-0003"), ("C-0003", None)):
        path = root / "caves" / f"{cave_id}.yml"
        path.write_text(yaml.safe_dump({**cave, "id": cave_id, "system_cave_id": system_id}))
    with pytest.raises(CatalogLoadError, match="NESTED_CAVE_SYSTEM"), open_catalog(root):
        pass


def test_native_geometry_and_citations_survive_projection(tmp_path, records):
    obj, cave = records
    obj["measurements"][0].pop("lat")
    obj["measurements"][0].pop("lon")
    obj["measurements"][0].update(input_srid=2180, input_x=562729.5, input_y=152838.5)
    obj["bibliography_status"] = "known"
    obj["citations"] = [{"publication_id": "example", "locator": "s. 3", "purpose": "identity"}]
    root = snapshot(tmp_path / "first", records)
    (root / "publications/example.yml").write_text(
        yaml.safe_dump(
            {"id": "example", "citation": "Autor, Tytuł, 2026.", "url": "https://example.com"}
        )
    )
    with open_catalog(root) as catalog:
        m = catalog.dataset().objects[0].data["measurements"][0]
        assert (m["input_srid"], m["input_x"], m["input_y"]) == (2180, 562729.5, 152838.5)
        assert catalog.dataset().objects[0].data["citations"] == obj["citations"]
        assert len(catalog.dataset().publications) == 1


@pytest.mark.parametrize(
    "sql",
    [
        r"\! touch /tmp/unsafe",
        "DROP TABLE catalog.objects;",
        "INSERT INTO catalog.publications (id,citation) VALUES ('x', pg_read_file('/etc/passwd'));",
        "SET session_replication_role=replica;",
        "BEGIN; COMMIT;",
        "INSERT INTO catalog.publications (id,citation) VALUES ('x','ok'); SELECT 1;",
    ],
)
def test_data_sql_cannot_execute_commands(tmp_path, records, sql):
    root = snapshot(tmp_path, records)
    (root / "publications/evil.sql").write_text(sql)
    with pytest.raises(CatalogLoadError), open_catalog(root):
        pass


def test_auto_best_utc_accuracy_and_text_id(tmp_path, records):
    obj, _ = records
    first = obj["measurements"][0]
    first.update(observed_at="2026-05-15T10:00:00+02:00", horizontal_accuracy_m=None)
    second = deepcopy(first)
    second.update(id="m-002", observed_at="2026-05-15T08:00:00Z", horizontal_accuracy_m=3)
    third = deepcopy(second)
    third["id"] = "m-010"
    obj["measurements"].extend([third, second])
    with open_catalog(snapshot(tmp_path, records)) as catalog:
        assert catalog.dataset().objects[0].data["best_measurement"]["measurement_id"] == "m-002"


@pytest.mark.parametrize("first", range(6))
def test_sql_best_priority_precedes_recency_and_retains_rejected_fallback(tmp_path, records, first):
    obj, _ = records
    priorities = [
        ("wlasne", "zweryfikowany"),
        ("TPN", "nieweryfikowany"),
        ("wlasne", "nieweryfikowany"),
        ("PIG", "nieweryfikowany"),
        ("geoportal", "nieweryfikowany"),
        ("TPN", "odrzucony"),
    ]
    obj["measurements"] = [
        obj["measurements"][0]
        | {
            "id": f"m-{i + 1:03}",
            "source": source,
            "verification_status": status,
            "observed_date": f"2026-05-{i + 1:02}",
        }
        for i, (source, status) in enumerate(priorities)
        if i >= first
    ]
    obj["id_assignment"]["assigned_from_measurement_id"] = f"m-{first + 1:03}"
    with open_catalog(snapshot(tmp_path, records)) as catalog:
        selected = catalog.connection.execute(
            "SELECT id,rejected_fallback FROM catalog.v_best"
        ).fetchone()
    assert selected == {"id": f"m-{first + 1:03}", "rejected_fallback": first == 5}


@pytest.mark.parametrize(
    "column,expression",
    [
        ("input_geom", "ST_SetSRID(ST_MakePoint(%s,49),4326)"),
        ("input_geom", "ST_SetSRID(ST_MakePoint(20,%s),4326)"),
        ("elevation_m", "%s"),
        ("horizontal_accuracy_m", "%s"),
        ("vertical_accuracy_m", "%s"),
    ],
)
def test_database_rejects_non_finite_values_without_python_preflight(
    tmp_path, records, column, expression
):
    import psycopg
    from psycopg import sql

    with (
        open_catalog(snapshot(tmp_path, records)) as catalog,
        psycopg.connect(catalog._dsn, autocommit=True) as connection,
    ):
        for value in (float("nan"), float("inf"), float("-inf")):
            with pytest.raises(psycopg.errors.CheckViolation):
                connection.execute(
                    sql.SQL("UPDATE catalog.measurements SET {}={}").format(
                        sql.Identifier(column), sql.SQL(expression)
                    ),
                    (value,),
                )


def test_yaml_filename_cannot_own_another_entity(tmp_path, records):
    root = snapshot(tmp_path, records)
    (root / "objects/KSW-0001.yml").rename(root / "objects/KSW-0002.yml")
    with pytest.raises(CatalogLoadError, match="filename"), open_catalog(root):
        pass


@pytest.mark.parametrize(
    "srid,x,y", [(3857, 1, 2), (4326, float("nan"), 49), (4326, 20, float("inf")), (4326, 200, 49)]
)
def test_catalogue_rejects_invalid_geometry_in_hand_edited_yaml(tmp_path, records, srid, x, y):
    records[0]["measurements"][0].update(input_srid=srid, input_x=x, input_y=y)
    with pytest.raises(CatalogLoadError), open_catalog(snapshot(tmp_path, records)):
        pass


def test_storage_marker_cannot_fall_back_to_yaml(tmp_path):
    from gps_kataster_obiektow_tatr.postgres import read_catalog_projection

    for directory in ("objects", "caves", "relations"):
        (tmp_path / directory).mkdir()
    (tmp_path / "catalog.json").write_text('{"format":"postgresql-inserts","schema_version":2}')
    (tmp_path / "objects/legacy.yml").write_text("id: KSW-0001\n")
    with pytest.raises(CatalogLoadError, match="Unsupported catalogue storage format"):
        read_catalog_projection(tmp_path)


def test_native_resource_cleanup_and_loader_privileges(tmp_path, records, monkeypatch):
    import os

    import psycopg

    dsn = os.environ.get("KATASTER_DATABASE_URL")
    if not dsn:
        pytest.skip("Shared-server resource observation requires KATASTER_DATABASE_URL")

    import uuid
    from types import SimpleNamespace

    from gps_kataster_obiektow_tatr import postgres

    owned_id = uuid.uuid4().hex
    monkeypatch.setattr(postgres.uuid, "uuid4", lambda: SimpleNamespace(hex=owned_id))
    database = "kataster_" + owned_id
    role = database + "_loader"

    def resources(connection):
        return (
            connection.execute(
                "SELECT datname FROM pg_database WHERE datname=%s", (database,)
            ).fetchall(),
            connection.execute("SELECT rolname FROM pg_roles WHERE rolname=%s", (role,)).fetchall(),
        )

    with psycopg.connect(dsn, autocommit=True) as observer:
        before = resources(observer)
        assert before == ([], [])
        with open_catalog(snapshot(tmp_path, records)) as catalog:
            assert resources(observer) == ([(database,)], [(role,)])
            name = catalog.connection.info.dbname + "_loader"
            row = catalog.connection.execute(
                "SELECT rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls "
                "FROM pg_roles WHERE rolname=%s",
                (name,),
            ).fetchone()
            assert not any(row.values())
            assert not catalog.connection.execute(
                "SELECT has_table_privilege(%s, 'catalog.boundaries', 'INSERT') allowed", (role,)
            ).fetchone()["allowed"]
            assert not catalog.connection.execute(
                "SELECT has_schema_privilege(%s, 'catalog', 'CREATE') allowed", (name,)
            ).fetchone()["allowed"]
        assert resources(observer) == before
        records[0]["cave_id"] = "C-9999"
        with pytest.raises(CatalogLoadError), open_catalog(snapshot(tmp_path, records)):
            pass
        assert resources(observer) == before


def test_native_dump_restores_without_transient_roles(tmp_path, records):
    import os
    import subprocess
    import uuid

    import psycopg
    from psycopg import sql
    from psycopg.conninfo import make_conninfo

    dsn = os.environ.get("KATASTER_DATABASE_URL")
    binary = os.environ.get("KATASTER_PG_BIN")
    if not dsn or not binary:
        pytest.skip("Native dump restore proof requires KATASTER_DATABASE_URL and KATASTER_PG_BIN")
    target = "kataster_restore_" + uuid.uuid4().hex
    dump = tmp_path / "catalog.dump"
    with open_catalog(snapshot(tmp_path / "data", records)) as catalog:
        expected = catalog.connection.execute(
            "SELECT object_id,id,lat,lon FROM catalog.v_best"
        ).fetchall()
        catalog.dump(dump)
    with psycopg.connect(dsn, autocommit=True) as admin:
        admin.execute(
            sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(target))
        )
        try:
            restore_dsn = make_conninfo(dsn, dbname=target)
            subprocess.run(
                [
                    str(Path(binary) / "pg_restore"),
                    "--no-owner",
                    "--no-acl",
                    "--exit-on-error",
                    "--dbname",
                    restore_dsn,
                    str(dump),
                ],
                check=True,
                capture_output=True,
                timeout=60,
            )
            with psycopg.connect(restore_dsn, row_factory=psycopg.rows.dict_row) as restored:
                assert (
                    restored.execute("SELECT object_id,id,lat,lon FROM catalog.v_best").fetchall()
                    == expected
                )
        finally:
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(target)))


@pytest.mark.parametrize("field", ["notes", "prefix_override_reason"])
def test_yaml_presence_distinguishes_null_from_absence(tmp_path, records, field):
    obj, _ = records
    target = obj["id_assignment"] if field == "prefix_override_reason" else obj
    target[field] = None
    root = snapshot(tmp_path, records)
    with open_catalog(root) as catalog:
        restored = catalog.dataset().objects[0].data
    assert (restored["id_assignment"] if field == "prefix_override_reason" else restored)[
        field
    ] is None
    del target[field]
    snapshot(root, records)
    with open_catalog(root) as catalog:
        restored = catalog.dataset().objects[0].data
    assert field not in (
        restored["id_assignment"] if field == "prefix_override_reason" else restored
    )


def test_canonical_input_retains_native_coordinates(tmp_path, records):
    measurement = records[0]["measurements"][0]
    measurement.pop("lat")
    measurement.pop("lon")
    measurement.update(input_srid=2180, input_x=562729.5, input_y=152838.5)
    with open_catalog(snapshot(tmp_path, records)) as catalog:
        m = catalog.dataset().objects[0].data["measurements"][0]
        assert (m["input_srid"], m["input_x"], m["input_y"]) == (2180, 562729.5, 152838.5)


def test_computed_best_is_auto_even_when_manual_selects_another_measurement(tmp_path, records):
    obj, _ = records
    newer = deepcopy(obj["measurements"][0])
    newer.update(id="m-002", observed_date="2026-05-16")
    obj["measurements"].append(newer)
    obj["best_measurement"].update(mode="manual", measurement_id="m-001", reason="Retain baseline")
    with open_catalog(snapshot(tmp_path, records)) as catalog:
        data = catalog.dataset().objects[0].data
        assert data["best_measurement"]["measurement_id"] == "m-001"
        assert data["computed_best_measurement_id"] == "m-002"


def test_measurement_citation_attachment_relation_and_literal_notes_roundtrip(tmp_path, records):
    obj, cave = records
    obj["measurements"][0]["citations"] = [
        {"publication_id": "pub", "locator": "fig. 2", "notes": "Measured point, not cave history"}
    ]
    attachment = tmp_path / "report.txt"
    attachment.write_text("Source report")
    obj["attachments"] = [
        {
            "id": "a-001",
            "kind": "raport_gnss",
            "measurement_id": "m-001",
            "path": str(attachment),
            "caption": None,
            "date": "2026-05-15",
            "created_at": "2026-05-15T10:00:00+02:00",
            "created_by": "dl",
        }
    ]
    obj["notes"] = "Quotes ' ; -- comment-like \\ text\nSecond line."
    second = deepcopy(obj)
    second["id"] = "KSW-0002"
    second["membership_ordinal"] = 2
    root = snapshot(tmp_path / "first", records)
    (root / "objects/KSW-0002.yml").write_text(yaml.safe_dump(second))
    publication = {
        "id": "pub",
        "citation": "Author, Title, 2026",
        "authors": "Author",
        "title": "Title",
        "publication_year": 2026,
        "container_title": "Journal",
        "issue": "1",
        "url": None,
        "doi": "10.000/test",
        "isbn": None,
    }
    (root / "publications/pub.yml").write_text(yaml.safe_dump(publication))
    relation = {
        "schema_version": 1,
        "id": "R-0001",
        "from_object_id": obj["id"],
        "to_object_id": second["id"],
        "relation_type": "sasiad",
        "notes": None,
    }
    (root / "relations/R-0001.yml").write_text(yaml.safe_dump(relation))
    with open_catalog(root) as catalog:
        readback = catalog.dataset()
        assert readback.objects[0].data["notes"] == obj["notes"]
        assert readback.objects[0].data["attachments"] == obj["attachments"]
        assert (
            readback.objects[0].data["measurements"][0]["citations"]
            == obj["measurements"][0]["citations"]
        )
        assert readback.publications[0].data == publication
        assert readback.relations[0].data == relation


def test_default_catalog_missing_marker_cannot_be_downgraded_to_legacy(tmp_path, monkeypatch):
    from gps_kataster_obiektow_tatr import postgres

    monkeypatch.setattr(postgres, "DEFAULT_DATA_DIR", tmp_path)
    for directory in ("objects", "caves", "relations"):
        (tmp_path / directory).mkdir()
    with pytest.raises(CatalogLoadError, match="marker is missing"):
        postgres.read_catalog_projection(tmp_path)


def test_membership_is_derived_from_object_fk(tmp_path, records):
    with open_catalog(snapshot(tmp_path, records)) as catalog:
        assert catalog.dataset().caves[0].data["object_ids"] == ["KSW-0001"]
        assert (
            catalog.connection.execute(
                "SELECT relkind FROM pg_class WHERE oid='catalog.cave_members'::regclass"
            ).fetchone()["relkind"]
            == "v"
        )


def test_attachment_owner_ordinal_is_unique(tmp_path, records):
    import psycopg

    obj, _ = records
    attachment = {
        "id": "a-001",
        "kind": "inne",
        "path": "https://example.com",
        "created_at": obj["created_at"],
        "created_by": "test",
    }
    obj["attachments"] = [attachment, {**attachment, "id": "a-002"}]
    with (
        open_catalog(snapshot(tmp_path, records)) as catalog,
        psycopg.connect(catalog._dsn, autocommit=True) as connection,
        pytest.raises(psycopg.errors.UniqueViolation, match="ordinal"),
    ):
        connection.execute("UPDATE catalog.attachments SET ordinal = 1 WHERE id = 'a-002'")


def test_multiline_yaml_notes_remain_literal_in_database(tmp_path, records):
    obj, _ = records
    obj["notes"] = "Line one ' quoted\n-- not a comment\nDROP TABLE catalog.objects;"
    with open_catalog(snapshot(tmp_path, records)) as catalog:
        assert catalog.dataset().objects[0].data["notes"] == obj["notes"]


def test_catalog_binds_explicit_reference_root_and_attachment_paths(tmp_path, records):
    import yaml

    root = tmp_path / "reference"
    (root / "config").mkdir(parents=True)
    (root / "data").mkdir()
    config = yaml.safe_load((ROOT / "config/prefixes.yml").read_text())
    config["valley_prefixes"] = {name: "ZZZ" for name in config["valley_prefixes"]}
    (root / "config/prefixes.yml").write_text(yaml.safe_dump(config))
    (root / "data/shapes").symlink_to(ROOT / "data/shapes", target_is_directory=True)
    obj, _ = records
    obj["attachments"] = [
        {
            "id": "a-001",
            "kind": "inne",
            "path": "local.txt",
            "created_at": obj["created_at"],
            "created_by": "test",
        }
    ]
    (root / "local.txt").write_text("attachment")
    with open_catalog(
        snapshot(tmp_path / "catalog", records), reference_root=root, validate=False
    ) as catalog:
        issues = catalog.issues()
        assert any(i.code == "OBJECT_PREFIX_MISMATCH" and "ZZZ" in i.description for i in issues)
        assert not any(i.code == "ATTACHMENT_PATH_MISSING" for i in issues)


def test_catalog_reports_incomplete_best_and_attachments_in_postgis(tmp_path, records):
    from gps_kataster_obiektow_tatr.validator import validate_catalog

    obj, _ = records
    measurement = obj["measurements"][0]
    measurement.pop("lat")
    measurement.pop("lon")
    measurement.update(input_srid=2180, input_x=560004, input_y=150004)  # valley hole
    reference = spatial_reference(tmp_path / "reference")
    obj["attachments"] = [
        {
            "id": f"a-{i:03}",
            "kind": "inne",
            "path": path,
            "created_at": obj["created_at"],
            "created_by": "test",
        }
        for i, path in enumerate(
            ("https://example.com/image.jpg", "ftp://example.com/image.jpg", "missing.txt"), 1
        )
    ]
    root = snapshot(tmp_path / "catalog", records)
    path = root / "objects/KSW-0001.yml"
    from gps_kataster_obiektow_tatr.postgres import _open_rows, _read_snapshots

    rows, paths = _read_snapshots(root)
    rows = [entry for entry in rows if entry[1] != "best_policy"]
    with _open_rows(rows, paths, root, False, reference) as catalog:
        issues = validate_catalog(catalog, repo_root=tmp_path)
    errors = {issue.code: issue for issue in issues if issue.severity == "error"}
    assert set(errors) == {
        "FILE_ID_MISMATCH",
        "OBJECT_WITHOUT_BEST_POLICY",
        "ATTACHMENT_URL_INVALID",
        "ATTACHMENT_PATH_MISSING",
    }
    assert all(issue.path == path for issue in errors.values())
    assert "a-002" in errors["ATTACHMENT_URL_INVALID"].description
    assert "a-003" in errors["ATTACHMENT_PATH_MISSING"].description
    assert [i.code for i in issues if i.code.startswith("MEASUREMENT_OUTSIDE")] == [
        "MEASUREMENT_OUTSIDE_VALLEYS"
    ]
    assert not any(i.code == "OBJECT_PREFIX_MISMATCH" for i in issues)


@pytest.mark.parametrize("target", ["object_citations", "cave_citations", "measurement_citations"])
def test_citation_owner_ordinal_must_be_unique(tmp_path, records, target):

    obj, cave = records
    citations = [{"publication_id": "pub", "locator": f"p. {i}"} for i in (1, 2)]
    if target == "measurement_citations":
        obj["measurements"][0]["citations"] = citations
    else:
        for citation in citations:
            citation["purpose"] = "identity"
        (obj if target == "object_citations" else cave)["citations"] = citations
    root = snapshot(tmp_path, records)
    (root / "publications/pub.yml").write_text(
        yaml.safe_dump({"id": "pub", "citation": "A complete citation"})
    )
    import psycopg
    from psycopg import sql

    with (
        open_catalog(root) as catalog,
        psycopg.connect(catalog._dsn, autocommit=True) as connection,
        pytest.raises(psycopg.errors.UniqueViolation, match="ordinal"),
    ):
        connection.execute(
            sql.SQL("UPDATE catalog.{} SET ordinal = 1 WHERE ordinal = 2").format(
                sql.Identifier(target)
            )
        )


@pytest.mark.parametrize(
    "partial", [{"input_x": 562000.0}, {"input_y": 152000.0}, {"input_srid": 2180}]
)
def test_serializer_rejects_partial_native_geometry_instead_of_discarding_it(records, partial):
    records[0]["measurements"][0].update(partial)
    with pytest.raises(ValueError, match="together"):
        record_rows("object", records[0])


def test_untransformable_native_geometry_returns_controlled_catalog_error(tmp_path, records):
    records[0]["measurements"][0].pop("lat")
    records[0]["measurements"][0].pop("lon")
    records[0]["measurements"][0].update(input_srid=2180, input_x=1e308, input_y=1e308)
    with pytest.raises(CatalogLoadError), open_catalog(snapshot(tmp_path, records)):
        pass


@pytest.mark.parametrize("owner", ["object", "cave"])
def test_native_catalog_preserves_external_reference_uniqueness(tmp_path, records, owner):
    record = records[0 if owner == "object" else 1]
    ref = {
        "system": "inne",
        "ref_type": "url",
        "external_id": "source",
        "url": "https://example.com",
    }
    record["external_refs"] = [ref, dict(ref)]
    with pytest.raises(CatalogLoadError), open_catalog(snapshot(tmp_path, records)):
        pass


def test_canonical_sql_rejects_empty_verifier(tmp_path, records):
    records[0]["measurements"][0]["verified_by"] = ""
    with pytest.raises(CatalogLoadError), open_catalog(snapshot(tmp_path, records)):
        pass


@pytest.mark.parametrize("verifier", [None, "reviewer:example"])
def test_canonical_sql_allows_nullable_or_named_verifier(tmp_path, records, verifier):
    records[0]["measurements"][0]["verified_by"] = verifier
    with open_catalog(snapshot(tmp_path, records)) as catalog:
        assert catalog.dataset().objects[0].data["measurements"][0]["verified_by"] == verifier


@pytest.mark.parametrize("reverse", [False, True], ids=["first-ordinal", "reversed-ordinal"])
def test_catalog_geography_uses_polygon_coverage_and_priority(
    tmp_path, records, make_canonical_data_dir, reverse
):
    from gps_kataster_obiektow_tatr.validator import validate_catalog

    reference = spatial_reference(tmp_path / "reference", reverse=reverse)
    root = make_canonical_data_dir(tmp_path / "catalog")
    # Literal expectations: covers includes exterior and hole boundaries;
    # valley order wins overlaps, then PL precedes SK, then no match is an error.
    cases = (
        (560001, 150001, "MTW", None),  # valley interior
        (560000, 150005, "MTW", None),  # outer edge
        (560000, 150000, "MTW", None),  # outer vertex
        (560004, 150004, "PL", "MEASUREMENT_OUTSIDE_VALLEYS"),  # hole interior
        (560002, 150005, "MTW", None),  # hole edge
        (560002, 150002, "MTW", None),  # hole vertex
        (560009, 150009, "KSW" if reverse else "MTW", None),  # overlapping valleys
        (560015, 150015, "KSW", None),  # second valley only
        (560025, 150025, "PL", "MEASUREMENT_OUTSIDE_VALLEYS"),  # both countries
        (560030, 150025, "PL", "MEASUREMENT_OUTSIDE_VALLEYS"),  # PL boundary
        (560050, 150005, "SK", "MEASUREMENT_OUTSIDE_VALLEYS"),  # SK only
        (560060, 150005, "SK", "MEASUREMENT_OUTSIDE_VALLEYS"),  # SK boundary
        (560100, 150005, None, "MEASUREMENT_OUTSIDE_PL_SK"),  # outside all polygons
    )
    template, cave = records
    (root / "caves/C-0001.yml").write_text(yaml.safe_dump(cave))
    paths, expected_regions, expected_issues = {}, [], []
    for index, (x, y, prefix, code) in enumerate(cases, 1):
        obj = deepcopy(template)
        obj["id"] = f"KSW-{index:04d}"
        obj["membership_ordinal"] = index
        measurement = obj["measurements"][0]
        measurement.pop("lat")
        measurement.pop("lon")
        measurement.update(input_srid=2180, input_x=x, input_y=y)
        path = root / "objects/KSW" / f"{obj['id']}.yml"
        path.parent.mkdir(exist_ok=True)
        path.write_text(yaml.safe_dump(obj))
        paths[obj["id"]] = path
        expected_regions.append((obj["id"], "m-001", prefix))
        if code:
            severity = "error" if code == "MEASUREMENT_OUTSIDE_PL_SK" else "warning"
            expected_issues.append((code, severity, path))
        if prefix not in (None, "KSW"):
            expected_issues.append(("OBJECT_PREFIX_MISMATCH", "warning", path))

    with open_catalog(root, validate=False, reference_root=reference) as catalog:
        assert catalog.dataset().measurement_regions == tuple(expected_regions)
        issues = validate_catalog(catalog)
    geography = [i for i in issues if i.code.startswith(("MEASUREMENT_OUTSIDE", "OBJECT_PREFIX"))]
    assert sorted((i.code, i.severity, i.path) for i in geography) == sorted(expected_issues)
    for issue in geography:
        assert f"{issue.path.stem}/m-001:" in issue.description
        if issue.code == "OBJECT_PREFIX_MISMATCH":
            prefix = next(p for oid, _, p in expected_regions if paths[oid] == issue.path)
            assert issue.description.endswith(f"OBJECT_PREFIX_MISMATCH {prefix}")


@pytest.mark.parametrize("mode", ["manual", "auto"])
def test_catalog_prefix_mismatch_follows_selected_best_not_assignment_or_auto(
    tmp_path, records, mode
):
    from gps_kataster_obiektow_tatr.validator import validate_catalog

    obj, _ = records
    first = obj["measurements"][0]
    first.pop("lat")
    first.pop("lon")
    first.update(input_srid=2180, input_x=560001, input_y=150001)
    obj["measurements"].append(
        {
            **first,
            "id": "m-002",
            "input_x": 560015,
            "input_y": 150015,
            "observed_date": "2026-06-01",
        }
    )
    if mode == "manual":
        obj["best_measurement"].update(
            mode="manual", measurement_id="m-001", reason="Keep the older point"
        )
    root = snapshot(tmp_path / "catalog", records)
    with open_catalog(
        root, validate=False, reference_root=spatial_reference(tmp_path / "reference")
    ) as catalog:
        assert catalog.dataset().objects[0].data["best_measurement"]["measurement_id"] == (
            "m-001" if mode == "manual" else "m-002"
        )
        issues = validate_catalog(catalog)
    mismatch = [i for i in issues if i.code == "OBJECT_PREFIX_MISMATCH"]
    assert [(i.severity, i.path, i.description) for i in mismatch] == (
        [("warning", root / "objects/KSW-0001.yml", "KSW-0001/m-001: OBJECT_PREFIX_MISMATCH MTW")]
        if mode == "manual"
        else []
    )


@pytest.mark.parametrize("distance", [99, 100, 100.1])
def test_catalog_distance_outlier_threshold_and_non_best_outside_countries(
    tmp_path, records, distance
):
    from gps_kataster_obiektow_tatr.validator import validate_catalog

    obj, _ = records
    first = obj["measurements"][0]
    first.pop("lat")
    first.pop("lon")
    first.update(input_srid=2180, input_x=560015, input_y=150015)
    obj["measurements"].append(
        {**first, "id": "m-002", "input_x": 560015 + distance, "observed_date": "2026-06-01"}
    )
    obj["best_measurement"].update(
        mode="manual", measurement_id="m-001", reason="Keep the in-valley point"
    )
    root = snapshot(tmp_path / "catalog", records)
    with open_catalog(
        root, validate=False, reference_root=spatial_reference(tmp_path / "reference")
    ) as catalog:
        issues = validate_catalog(catalog)
    path = root / "objects/KSW-0001.yml"
    outside = [i for i in issues if i.code.startswith("MEASUREMENT_OUTSIDE")]
    assert [(i.code, i.severity, i.path) for i in outside] == [
        ("MEASUREMENT_OUTSIDE_PL_SK", "error", path)
    ]
    assert "KSW-0001/m-002:" in outside[0].description
    assert not any(i.code == "OBJECT_PREFIX_MISMATCH" for i in issues)
    outliers = [i for i in issues if i.code == "MEASUREMENT_DISTANCE_OUTLIER"]
    assert [(i.severity, i.path, i.description) for i in outliers] == (
        [("warning", path, "KSW-0001/m-001: MEASUREMENT_DISTANCE_OUTLIER m-002: 100.1 m")]
        if distance > 100
        else []
    )
