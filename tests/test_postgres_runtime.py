"""Managed Docker lifecycle, check runner propagation and real CI smoke."""

import os
import subprocess
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest
from sql_test_support import module

from gps_kataster_obiektow_tatr import postgres

ROOT = Path(__file__).resolve().parents[1]


def managed(monkeypatch):
    monkeypatch.delenv("KATASTER_DATABASE_URL", raising=False)
    monkeypatch.delenv("KATASTER_POSTGRES_CONTAINER", raising=False)
    monkeypatch.setattr(postgres.shutil, "which", lambda name: "/bin/docker")


def fake_docker(monkeypatch, failure=None):
    managed(monkeypatch)
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        if command[1] == failure:
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])
        return SimpleNamespace(stdout="127.0.0.1:45678\n", stderr="", returncode=0)

    monkeypatch.setattr(postgres.subprocess, "run", run)
    return calls


def test_external_server_is_never_removed(monkeypatch):
    monkeypatch.setenv("KATASTER_DATABASE_URL", "postgresql://external")
    monkeypatch.setenv("KATASTER_POSTGRES_CONTAINER", "external-container")
    monkeypatch.setattr(postgres.subprocess, "run", lambda *a, **k: pytest.fail("Docker called"))
    with postgres._server() as value:
        assert value == ("postgresql://external", "external-container")


@pytest.mark.parametrize("failure", ["run", "port"])
def test_startup_failure_removes_only_owned_container(monkeypatch, failure):
    calls = fake_docker(monkeypatch, failure)
    with pytest.raises(subprocess.TimeoutExpired), postgres._server():
        pytest.fail("Startup unexpectedly succeeded")
    assert calls[-1][:3] == ["docker", "rm", "--force"]
    owned = calls[0][calls[0].index("--name") + 1]
    assert calls[-1][-1] == owned
    assert owned.startswith("kataster-")


def test_missing_docker_fails_without_starting_anything(monkeypatch):
    managed(monkeypatch)
    monkeypatch.setattr(postgres.shutil, "which", lambda name: None)
    with (
        pytest.raises(postgres.CatalogLoadError, match="Docker is unavailable"),
        postgres._server(),
    ):
        pass


@pytest.mark.parametrize("unready", [True, False])
def test_server_readiness_timeout_and_consumer_error_cleanup(monkeypatch, unready):
    calls = fake_docker(monkeypatch)

    @contextmanager
    def connect(dsn):
        assert "port=45678" in dsn
        if unready:
            raise postgres.psycopg.OperationalError("not ready")
        yield

    monkeypatch.setattr(postgres.psycopg, "connect", connect)
    clock = iter([0, 61])
    monkeypatch.setattr(postgres.time, "monotonic", lambda: next(clock))
    error = postgres.CatalogLoadError if unready else RuntimeError
    with pytest.raises(error, match="ready" if unready else "consumer"), postgres._server():
        raise RuntimeError("consumer")
    assert calls[-1][:3] == ["docker", "rm", "--force"]
    assert "127.0.0.1::5432" in calls[0]
    assert postgres.DOCKER_IMAGE in calls[0]


def test_cleanup_failure_is_reported(monkeypatch):
    fake_docker(monkeypatch, "run")
    original = postgres.subprocess.run

    def run(command, **kwargs):
        if command[1] == "rm":
            return SimpleNamespace(returncode=1, stderr="daemon refused cleanup")
        return original(command, **kwargs)

    monkeypatch.setattr(postgres.subprocess, "run", run)
    with (
        pytest.raises(postgres.CatalogLoadError, match="Could not remove owned"),
        postgres._server(),
    ):
        pass


@pytest.mark.parametrize("failure", [False, True])
def test_check_runner_shares_one_server_and_propagates_failure(monkeypatch, failure, tmp_path):
    runner = module("check_project")
    lifecycle = []
    calls = []

    @contextmanager
    def server():
        lifecycle.append("start")
        try:
            yield "postgresql://shared", "owned-test"
        finally:
            lifecycle.append("stop")

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(stdout="1" * 40, returncode=7 if failure else 0)

    monkeypatch.setattr(runner, "_server", server)
    monkeypatch.setattr(runner.subprocess, "run", run)
    assert runner.main(["--base-ref", "accepted", "--output-dir", str(tmp_path)]) == (
        7 if failure else 0
    )
    assert lifecycle == ["start", "stop"]
    assert len(calls) == (2 if failure else 7)
    for _, kwargs in calls[1:]:
        assert kwargs["env"]["KATASTER_DATABASE_URL"] == "postgresql://shared"
        assert kwargs["env"]["KATASTER_POSTGRES_CONTAINER"] == "owned-test"
    if not failure:
        assert calls[-3][0][-1] == "1" * 40
        assert "--base-ref" in calls[-2][0]


@pytest.mark.skipif(
    os.environ.get("KATASTER_DOCKER_SMOKE") != "1",
    reason="Actual Docker smoke enabled explicitly in CI",
)
def test_real_managed_docker_startup_dump_restore_and_cleanup(monkeypatch, tmp_path):
    # This must fail rather than skip when enabled and Docker is unavailable.
    monkeypatch.delenv("KATASTER_DATABASE_URL", raising=False)
    monkeypatch.delenv("KATASTER_POSTGRES_CONTAINER", raising=False)
    monkeypatch.delenv("KATASTER_PG_BIN", raising=False)
    owned = None
    try:
        with (
            pytest.raises(RuntimeError, match="^exercise failure cleanup$"),
            postgres._server() as (dsn, owned),
        ):
            assert owned is not None
            storage = subprocess.check_output(
                ["docker", "exec", owned, "stat", "-f", "-c", "%T", "/var/lib/postgresql"],
                text=True,
                timeout=15,
            )
            assert storage.strip() == "tmpfs"
            monkeypatch.setenv("KATASTER_DATABASE_URL", dsn)
            monkeypatch.setenv("KATASTER_POSTGRES_CONTAINER", owned)
            path = tmp_path / "catalog.dump"
            with postgres.open_catalog(ROOT / "data") as catalog:
                fingerprints = catalog.fingerprints()
                assert (
                    catalog.connection.execute("SELECT version()")
                    .fetchone()["version"]
                    .startswith("PostgreSQL 18.")
                )
                catalog.dump(path)
            with postgres.restore_dump(path) as restored:
                assert restored.fingerprints() == fingerprints
            raise RuntimeError("exercise failure cleanup")
    finally:
        if owned is not None:
            result = subprocess.run(
                ["docker", "inspect", owned], capture_output=True, text=True, timeout=15
            )
            assert result.returncode != 0 and "no such" in result.stderr.lower()
