"""Disposable PostgreSQL catalogue with a separate, least-privilege data loader."""

from __future__ import annotations

import json
import os
import secrets
import shutil
import subprocess
import tempfile
import time
import uuid
from collections import defaultdict
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from psycopg.rows import dict_row

from gps_kataster_obiektow_tatr.catalog_records import (
    ENTITY_TABLES,
    FIELDS,
    SourceDataset,
    check_source_fields,
    dataset_records,
    record_rows,
)
from gps_kataster_obiektow_tatr.data_loader import (
    CATALOG_FORMAT,
    DEFAULT_DATA_DIR,
    FORMAT_MARKER,
    DataDirectoryError,
    DataKind,
    LoadedDataset,
    LoadedYamlRecord,
    iter_yaml_paths,
    load_yaml_dataset,
    require_dataset_layout,
)

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schema/catalog.sql"
DOCKER_IMAGE = (
    "postgis/postgis:18-3.6@sha256:4a43e3c3e5d55b9208240fc71db543b79c638766280c625a425bd0a2390989c4"
)
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_CATALOG_BYTES = 256 * 1024 * 1024


class CatalogLoadError(ValueError):
    """Malformed snapshot, database constraint violation or failed validation."""

    def __init__(self, message: str, *, path: Path | None = None):
        self.path = path
        super().__init__(f"{path}: {message}" if path else message)


@contextmanager
def _server():
    dsn = os.environ.get("KATASTER_DATABASE_URL")
    if dsn:
        yield dsn, os.environ.get("KATASTER_POSTGRES_CONTAINER")
        return
    container = "kataster-" + uuid.uuid4().hex
    password = secrets.token_urlsafe(32)
    if shutil.which("docker") is None:
        raise CatalogLoadError("Docker is unavailable; configure KATASTER_DATABASE_URL")
    try:
        subprocess.run(
            [
                "docker",
                "run",
                "--detach",
                "--platform",
                "linux/amd64",
                "--rm",
                "--name",
                container,
                "-e",
                f"POSTGRES_PASSWORD={password}",
                "-p",
                "127.0.0.1::5432",
                DOCKER_IMAGE,
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=180,
        )
        published = subprocess.run(
            ["docker", "port", container, "5432/tcp"],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        ).stdout.strip()
        port = published.rsplit(":", 1)[1]
        dsn = make_conninfo(
            host="127.0.0.1",
            port=port,
            dbname="postgres",
            user="postgres",
            password=password,
            connect_timeout=3,
        )
        deadline = time.monotonic() + 60
        while True:
            try:
                with psycopg.connect(dsn):
                    break
            except psycopg.OperationalError:
                if time.monotonic() >= deadline:
                    raise CatalogLoadError(
                        "Local PostgreSQL container did not become ready"
                    ) from None
                time.sleep(0.2)
        yield dsn, container
    finally:
        # Even a timed-out `docker run` may already have created this unique container.
        cleanup = subprocess.run(
            ["docker", "rm", "--force", container],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if cleanup.returncode and "No such container" not in cleanup.stderr:
            raise CatalogLoadError(
                f"Could not remove owned container {container}: {cleanup.stderr}"
            )


def check_snapshot_files(data_dir: Path, *, canonical: bool) -> None:
    """Preserve filesystem guards before parsing either canonical or legacy build inputs."""
    require_dataset_layout(data_dir, canonical=canonical)
    size = 0
    for table in ENTITY_TABLES.values():
        root = data_dir / table
        for path in iter_yaml_paths(root):
            if path.is_symlink():
                raise CatalogLoadError("YAML snapshots must not be symlinks", path=path)
            file_size = path.stat().st_size
            size += file_size
            if file_size > MAX_FILE_BYTES or size > MAX_CATALOG_BYTES:
                raise CatalogLoadError("YAML snapshot size limit exceeded", path=path)


def _read_snapshots(data_dir: Path):
    marker = data_dir / FORMAT_MARKER
    if data_dir.resolve() == DEFAULT_DATA_DIR.resolve() and not marker.is_file():
        raise CatalogLoadError("Canonical YAML catalogue format marker is missing", path=marker)
    if marker.exists():
        try:
            metadata = json.loads(marker.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise CatalogLoadError("Invalid catalogue format marker", path=marker) from exc
        if metadata != CATALOG_FORMAT:
            raise CatalogLoadError("Unsupported catalogue storage format", path=marker)
    check_snapshot_files(data_dir, canonical=marker.exists())
    try:
        dataset = load_yaml_dataset(data_dir)
        from gps_kataster_obiektow_tatr.validator import _validate_proposal_membership

        if not marker.exists() and (issues := _validate_proposal_membership(dataset)):
            issue = issues[0]
            raise CatalogLoadError(f"{issue.code}: {issue.description}", path=issue.path)
        if marker.exists():
            for record in dataset.records():
                try:
                    check_source_fields(str(record.kind), record.raw_data)
                except (KeyError, TypeError, ValueError) as exc:
                    raise CatalogLoadError(str(exc), path=record.path) from exc
        return _catalog_rows(dataset, raw=True, legacy_membership=not marker.exists())
    except (CatalogLoadError, DataDirectoryError):
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise CatalogLoadError(str(exc), path=getattr(exc, "path", data_dir)) from exc


def _catalog_rows(dataset: LoadedDataset, *, raw: bool = False, legacy_membership: bool = True):
    rows, paths = [], {}
    for record, data in dataset_records(dataset, raw=raw, legacy_membership=legacy_membership):
        kind, record_id = str(record.kind), data["id"]
        if raw and record.path.stem != record_id:
            raise CatalogLoadError(
                "YAML entity ID does not match snapshot filename", path=record.path
            )
        try:
            entries = record_rows(kind, data)
        except (KeyError, TypeError, ValueError) as exc:
            raise CatalogLoadError(str(exc), path=record.path) from exc
        paths[kind, record_id] = record.path
        rows.extend((record.path, table, values) for table, values in entries)
    return rows, paths


@dataclass
class Catalog:
    """One loaded SQL state; validation is explicit and uses this connection."""

    connection: psycopg.Connection
    data_dir: Path
    paths: dict
    _dsn: str
    _container: str | None = None
    reference_root: Path = SCHEMA_PATH.parents[1]

    def _fetchall(self, query):
        try:
            return self.connection.execute(query).fetchall()
        except psycopg.Error as exc:
            raise CatalogLoadError(str(exc)) from exc

    def issues(self, *, repo_root=None, prefix_resolver=None):
        """Core relational findings; domain/geography validation builds on these."""
        from gps_kataster_obiektow_tatr.validator import ValidationIssue, ValidationSeverity

        findings = []
        for view, severity in [
            ("v_integrity_issues", ValidationSeverity.ERROR),
            ("v_warnings", ValidationSeverity.WARNING),
            ("v_domain_warnings", ValidationSeverity.WARNING),
        ]:
            rows = self._fetchall(
                sql.SQL("SELECT * FROM catalog.{} ORDER BY code, entity_id").format(
                    sql.Identifier(view)
                )
            )
            for row in rows:
                entity_id = row["entity_id"]
                kind = "cave" if entity_id.startswith("C-") else "object"
                findings.append(
                    ValidationIssue(
                        code=row["code"],
                        severity=severity,
                        path=self.paths.get((kind, entity_id)),
                        description=f"{entity_id}: {row['code']}"
                        + (f" ({row['measurement_id']})" if row.get("measurement_id") else ""),
                    )
                )
        from gps_kataster_obiektow_tatr.prefix_resolver import PrefixResolutionStatus
        from gps_kataster_obiektow_tatr.validator import (
            _validate_attachments,
        )

        findings.extend(
            _validate_attachments(
                self._fetchall(
                    "SELECT object_id,id,path FROM catalog.attachments ORDER BY object_id,ordinal"
                ),
                paths=self.paths,
                repo_root=repo_root or self.reference_root,
            )
        )
        for row in self._fetchall(
            "SELECT * FROM catalog.v_geography_issues ORDER BY code,entity_id,measurement_id"
        ):
            if prefix_resolver is not None and row["code"] != "MEASUREMENT_DISTANCE_OUTLIER":
                continue
            findings.append(
                ValidationIssue(
                    row["code"],
                    ValidationSeverity(row["severity"]),
                    self.paths.get(("object", row["entity_id"])),
                    f"{row['entity_id']}/{row['measurement_id']}: "
                    f"{row['code']} {row['detail'] or ''}",
                )
            )
        if prefix_resolver is not None:
            for row in self._fetchall(
                "SELECT m.object_id,m.id,m.lat,m.lon,b.id IS NOT NULL AS is_best "
                "FROM catalog.v_measurements m LEFT JOIN catalog.v_best b "
                "ON (m.object_id,m.id)=(b.object_id,b.id) ORDER BY m.object_id,m.history_order"
            ):
                path = self.paths.get(("object", row["object_id"]))
                resolution = prefix_resolver.resolve(lat=row["lat"], lon=row["lon"])
                code = {
                    PrefixResolutionStatus.ERROR: "MEASUREMENT_OUTSIDE_PL_SK",
                    PrefixResolutionStatus.WARNING: "MEASUREMENT_OUTSIDE_VALLEYS",
                }.get(resolution.status)
                if code:
                    findings.append(
                        ValidationIssue(
                            code,
                            ValidationSeverity.ERROR
                            if resolution.status == PrefixResolutionStatus.ERROR
                            else ValidationSeverity.WARNING,
                            path,
                            f"{row['object_id']}/{row['id']}: {code}",
                        )
                    )
                if (
                    row["is_best"]
                    and resolution.prefix is not None
                    and resolution.prefix != row["object_id"].split("-")[0]
                ):
                    findings.append(
                        ValidationIssue(
                            "OBJECT_PREFIX_MISMATCH",
                            ValidationSeverity.WARNING,
                            path,
                            f"Resolved prefix {resolution.prefix}",
                        )
                    )
        return tuple(findings)

    def dataset(self) -> LoadedDataset:
        """Reconstruct the legacy read model from normalized rows, never an audit payload."""
        tables = {}
        for table in (
            "objects",
            "caves",
            "relations",
            "publications",
            "object_external_refs",
            "cave_external_refs",
            "object_citations",
            "cave_citations",
            "measurement_citations",
            "cave_members",
            "measurement_tags",
            "best_policy",
            "attachments",
            "v_best",
            "v_auto_best",
        ):
            tables[table] = self._fetchall(
                sql.SQL("SELECT * FROM catalog.{}").format(sql.Identifier(table))
            )

        tables["v_measurements"] = self._fetchall(
            "SELECT m.*, r.prefix AS region_prefix FROM catalog.v_measurements m "
            "JOIN catalog.v_measurement_regions r USING (object_id,id) ORDER BY m.object_id,m.id"
        )

        def fields(row, field_set):
            return {key: row[key] for key in FIELDS[field_set] if key in row["fields_present"]}

        def group(table, key, order="ordinal"):
            grouped = defaultdict(list)
            for row in sorted(tables[table], key=lambda row: row.get(order, 0)):
                grouped[row[key]].append(row)
            return grouped

        refs = {kind: group(f"{kind}_external_refs", f"{kind}_id") for kind in ("object", "cave")}
        cites = {kind: group(f"{kind}_citations", f"{kind}_id") for kind in ("object", "cave")}
        members = group("cave_members", "cave_id")
        measures = group("v_measurements", "object_id", "history_order")
        attachments = group("attachments", "object_id")
        best = {row["object_id"]: row for row in tables["v_best"]}
        auto = {row["object_id"]: row["measurement_id"] for row in tables["v_auto_best"]}
        policies = {row["object_id"]: row for row in tables["best_policy"]}
        tags = defaultdict(list)
        for row in sorted(tables["measurement_tags"], key=lambda row: row["ordinal"]):
            tags[row["object_id"], row["measurement_id"]].append(row["tag"])
        measurement_cites = defaultdict(list)
        for row in sorted(tables["measurement_citations"], key=lambda row: row["ordinal"]):
            measurement_cites[row["object_id"], row["measurement_id"]].append(
                fields(row, "measurement_citations")
            )
        result = {}
        for kind, table in ENTITY_TABLES.items():
            records = []
            for row in sorted(tables[table], key=lambda row: row["id"]):
                data = fields(row, table)
                entity_id = row["id"]
                if kind in ("object", "cave"):
                    data["bibliography_status"] = row["bibliography_status"]
                    data["external_refs"] = [
                        fields(ref, "external_refs") for ref in refs[kind][entity_id]
                    ]
                    if cites[kind][entity_id] or "citations" in row["fields_present"]:
                        data["citations"] = [fields(c, "citations") for c in cites[kind][entity_id]]
                if kind == "cave":
                    data["object_ids"] = [m["object_id"] for m in members[entity_id]]
                if kind == "object":
                    assignment = {
                        "method": row["assignment_mode"],
                        **{
                            key: row[key]
                            for key in (
                                "assigned_from_measurement_id",
                                "assigned_prefix",
                                "prefix_override_reason",
                            )
                        },
                    }
                    data["id_assignment"] = {
                        key: value
                        for key, value in assignment.items()
                        if key in row["assignment_fields_present"]
                    }
                    data["measurements"] = []
                    for m in measures[entity_id]:
                        measurement = fields(m, "measurements")
                        measurement.update(
                            {
                                key: m[key]
                                for key in (
                                    "lat",
                                    "lon",
                                    "x_1992",
                                    "y_1992",
                                    "input_srid",
                                    "input_x",
                                    "input_y",
                                )
                            }
                        )
                        measurement["tags"] = tags[entity_id, m["id"]]
                        if (
                            measurement_cites[entity_id, m["id"]]
                            or "citations" in m["fields_present"]
                        ):
                            measurement["citations"] = measurement_cites[entity_id, m["id"]]
                        data["measurements"].append(measurement)
                    if entity_id in policies:
                        data["best_measurement"] = fields(policies[entity_id], "best_policy")
                        data["best_measurement"]["measurement_id"] = (
                            best[entity_id]["id"] if entity_id in best else None
                        )
                    data["computed_best_measurement_id"] = auto.get(entity_id)
                    data["attachments"] = [fields(a, "attachments") for a in attachments[entity_id]]
                path = self.paths.get((kind, entity_id), self.data_dir / table / f"{entity_id}.yml")
                records.append(LoadedYamlRecord(DataKind(kind), path, data, deepcopy(data)))
            result[table] = tuple(records)
        return LoadedDataset(
            **result,
            measurement_regions=tuple(
                (m["object_id"], m["id"], m["region_prefix"]) for m in tables["v_measurements"]
            ),
        )

    def dump(self, path: Path) -> None:
        """Write a portable custom-format dump without transient role ownership/ACLs."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
        try:
            command, env = self._client_command("pg_dump")
            with os.fdopen(descriptor, "wb") as output:
                descriptor = -1
                subprocess.run(
                    [*command, "--format=custom", "--no-owner", "--no-acl"],
                    stdout=output,
                    stderr=subprocess.PIPE,
                    check=True,
                    timeout=180,
                    env=env,
                )
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, path)
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            Path(temporary).unlink(missing_ok=True)

    def _client_command(self, tool: str, *, dsn: str | None = None):
        """Matching native/container PostgreSQL clients, credentials outside argv."""
        options = conninfo_to_dict(dsn or self._dsn)
        if self._container:
            return (
                [
                    "docker",
                    "exec",
                    "-i",
                    self._container,
                    tool,
                    "-U",
                    options.get("user", "postgres"),
                    "-d",
                    options["dbname"],
                ],
                None,
            )
        configured = os.environ.get("KATASTER_PG_BIN")
        binary = str(Path(configured) / tool) if configured else shutil.which(tool)
        if not binary or not Path(binary).is_file():
            raise CatalogLoadError(
                f"{tool} unavailable; set KATASTER_PG_BIN or KATASTER_POSTGRES_CONTAINER"
            )
        env = dict(os.environ)
        if "password" in options:
            env["PGPASSWORD"] = options["password"]
        return (
            [
                binary,
                "--dbname",
                make_conninfo(**{k: v for k, v in options.items() if k != "password"}),
            ],
            env,
        )

    @contextmanager
    def restored(self, path: Path):
        """Restore into a separate owned database; remove it on every exit path."""
        name = "kataster_restore_" + uuid.uuid4().hex
        admin_dsn = make_conninfo(self._dsn, dbname="postgres")
        with psycopg.connect(admin_dsn, autocommit=True) as admin:
            created = False
            try:
                admin.execute(
                    sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(name))
                )
                created = True
                dsn = make_conninfo(self._dsn, dbname=name)
                command, env = self._client_command("pg_restore", dsn=dsn)
                with Path(path).open("rb") as stream:
                    subprocess.run(
                        [*command, "--no-owner", "--no-acl", "--exit-on-error"],
                        stdin=stream,
                        capture_output=True,
                        check=True,
                        timeout=180,
                        env=env,
                    )
                with psycopg.connect(dsn, autocommit=True, row_factory=dict_row) as connection:
                    connection.execute("SET default_transaction_read_only = on")
                    yield Catalog(
                        connection,
                        self.data_dir,
                        self.paths,
                        dsn,
                        self._container,
                        self.reference_root,
                    )
            finally:
                if created:
                    admin.execute(
                        sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name))
                    )

    def fingerprints(self) -> dict[str, str]:
        """Every normalized table and both Best views, including all attributes."""
        import hashlib

        tables = [
            row["tablename"]
            for row in self._fetchall(
                "SELECT tablename FROM pg_tables WHERE schemaname='catalog' ORDER BY tablename"
            )
        ]
        result = {}
        for name in [*tables, "v_best", "v_auto_best"]:
            rows = self._fetchall(
                sql.SQL("SELECT row_to_json(t)::text AS row FROM catalog.{} t").format(
                    sql.Identifier(name)
                )
            )
            canonical = "\n".join(sorted(row["row"] for row in rows))
            result[name] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return result


def verify_dump(catalog: Catalog, path: Path) -> None:
    """Mandatory independent restore/readback; metadata is never a substitute."""
    expected = catalog.fingerprints()
    with catalog.restored(path) as restored:
        if restored.fingerprints() != expected:
            raise CatalogLoadError("Restored dump differs from validated catalogue tables/Best")


def _load_boundaries(connection, root: Path):
    """Load only repository-controlled geometry; PostGIS performs all spatial checks."""
    import shapefile
    import yaml

    config = yaml.safe_load((root / "config/prefixes.yml").read_text())
    ordinal = 0
    for filename, area, fallback in [
        ("doliny.shp", "valley", None),
        ("granica_polski.shp", "poland", "polska"),
        ("granica_slowacji.shp", "slovakia", "slowacja"),
    ]:
        with shapefile.Reader(str(root / "data/shapes" / filename), encoding="utf-8") as reader:
            for feature in reader.iterShapeRecords():
                ordinal += 1
                name = str(feature.record["NAME"]) if area == "valley" else None
                prefix = (
                    config["valley_prefixes"][name]
                    if name
                    else config["fallback_prefixes"][fallback]
                )
                connection.execute(
                    "INSERT INTO catalog.boundaries VALUES (%s,%s,%s,%s,"
                    "ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(%s),2180)))",
                    (ordinal, area, prefix, name, json.dumps(feature.shape.__geo_interface__)),
                )


@contextmanager
def open_catalog(
    data_dir: Path, *, validate: bool = True, reference_root: Path = SCHEMA_PATH.parents[1]
):
    """Load YAML sources in a private database."""
    data_dir = Path(data_dir)
    rows, paths = _read_snapshots(data_dir)
    with _open_rows(rows, paths, data_dir, validate, reference_root) as catalog:
        yield catalog


@contextmanager
def _open_rows(rows, paths, data_dir, validate, reference_root):
    identifier = "kataster_" + uuid.uuid4().hex
    role = identifier + "_loader"
    password = secrets.token_urlsafe(32)
    with (
        _server() as (admin_dsn, container),
        psycopg.connect(
            admin_dsn, autocommit=True, row_factory=dict_row, connect_timeout=10
        ) as admin,
    ):
        database_created = role_created = False
        reader = None
        try:
            admin.execute(
                sql.SQL(
                    "CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB "
                    "NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 1"
                ).format(sql.Identifier(role), sql.Literal(password))
            )
            role_created = True
            admin.execute(
                sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(identifier))
            )
            database_created = True
            db_dsn = make_conninfo(admin_dsn, dbname=identifier)
            with psycopg.connect(db_dsn, autocommit=True) as owner:
                owner.execute(SCHEMA_PATH.read_text(encoding="utf-8"))
                _load_boundaries(owner, reference_root)
                owner.execute(
                    sql.SQL("REVOKE ALL ON DATABASE {} FROM PUBLIC").format(
                        sql.Identifier(identifier)
                    )
                )
                owner.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
                owner.execute(
                    sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                        sql.Identifier(identifier), sql.Identifier(role)
                    )
                )
                owner.execute(
                    sql.SQL("GRANT USAGE ON SCHEMA catalog, public TO {}").format(
                        sql.Identifier(role)
                    )
                )
                owner.execute(
                    sql.SQL("GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA catalog TO {}").format(
                        sql.Identifier(role)
                    )
                )
                owner.execute(
                    sql.SQL("REVOKE INSERT ON catalog.boundaries FROM {}").format(
                        sql.Identifier(role)
                    )
                )
            loader_dsn = make_conninfo(db_dsn, user=role, password=password)
            with psycopg.connect(loader_dsn) as loader:
                loader.execute("SET LOCAL search_path = catalog, public")
                loader.execute("SET LOCAL TIME ZONE 'UTC'")
                loader.execute("SET LOCAL statement_timeout = '15s'")
                loader.execute("SET LOCAL lock_timeout = '5s'")
                loader.execute("SET LOCAL idle_in_transaction_session_timeout = '30s'")
                loader.execute("SET LOCAL transaction_timeout = '120s'")
                for path, table, values in rows:
                    try:
                        loader.execute(
                            sql.SQL("INSERT INTO catalog.{} ({}) VALUES ({})").format(
                                sql.Identifier(table),
                                sql.SQL(",").join(map(sql.Identifier, values)),
                                sql.SQL(",").join(sql.Placeholder() for _ in values),
                            ),
                            tuple(values.values()),
                        )
                    except psycopg.Error as exc:
                        raise CatalogLoadError(str(exc), path=path) from exc
                try:
                    loader.execute("SET CONSTRAINTS ALL IMMEDIATE")
                except psycopg.Error as exc:
                    raise CatalogLoadError(str(exc)) from exc
            # Callers receive read-only transactions. Loading uses a different login.
            reader = psycopg.connect(db_dsn, autocommit=True, row_factory=dict_row)
            reader.execute("SET search_path = catalog, public")
            reader.execute("SET TIME ZONE 'UTC'")
            reader.execute("SET default_transaction_read_only = on")
            reader.execute("SET statement_timeout = '30s'")
            catalog = Catalog(reader, data_dir, paths, db_dsn, container, reference_root)
            if validate:
                errors = [issue for issue in catalog.issues() if issue.severity == "error"]
                if errors:
                    raise CatalogLoadError("; ".join(issue.description for issue in errors))
            yield catalog
        finally:
            if reader is not None:
                reader.close()
            if database_created:
                admin.execute(
                    sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(identifier))
                )
            if role_created:
                admin.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(role)))


@contextmanager
def open_proposal(
    dataset: LoadedDataset, *, validate: bool = True, reference_root: Path = SCHEMA_PATH.parents[1]
):
    """Load an in-memory proposal; import assertions belong to validator.py."""
    rows, paths = _catalog_rows(dataset)
    with _open_rows(rows, paths, DEFAULT_DATA_DIR, validate, reference_root) as catalog:
        yield catalog


@contextmanager
def open_source_proposal(
    source: SourceDataset, *, validate: bool = True, reference_root: Path = SCHEMA_PATH.parents[1]
):
    """Load canonical edits without legacy membership or derived-field normalization."""
    if not isinstance(source, SourceDataset):
        raise TypeError("Canonical proposals require SourceDataset, not a read projection")
    for record in source.records():
        try:
            check_source_fields(str(record.kind), record.raw_data)
        except (KeyError, TypeError, ValueError) as exc:
            raise CatalogLoadError(str(exc), path=record.path) from exc
    rows, paths = _catalog_rows(source, raw=True, legacy_membership=False)
    with _open_rows(rows, paths, DEFAULT_DATA_DIR, validate, reference_root) as catalog:
        yield catalog


def read_catalog_projection(data_dir: Path = DEFAULT_DATA_DIR) -> LoadedDataset:
    """Read SQL-derived fields after source/adapter checks, without domain or Git validation."""
    with open_catalog(data_dir, validate=False) as catalog:
        return catalog.dataset()


@contextmanager
def restore_dump(path: Path):
    """Independently open a portable dump, owning only its temporary database."""
    with _server() as (dsn, container):
        shell = Catalog(None, Path("."), {}, dsn, container)
        with shell.restored(path) as restored:
            restored.connection.execute("SET search_path = catalog, public")
            yield restored
