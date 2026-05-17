from pathlib import Path


def test_operational_documentation_covers_pbi_021_scope() -> None:
    text = Path("docs/operations.md").read_text(encoding="utf-8")

    required_phrases = [
        "## Dodanie recznego pomiaru",
        "## Walidacja",
        "## Tagowany release danych",
        "## Statusy weryfikacji pomiarow",
        "CHANGELOG.md",
        "annotated tag",
        "duzy udzial statusu",
        "najlepsza dostepna lokalizacja",
        "zweryfikowany",
        "odrzucony",
        "uv run python scripts/validate.py --data-dir",
        "uv run python scripts/build_release_artifacts.py",
        "best-measurements.geojson",
    ]

    for phrase in required_phrases:
        assert phrase in text


def test_operational_documentation_keeps_build_outputs_out_of_git() -> None:
    text = Path("docs/operations.md").read_text(encoding="utf-8")

    assert "Nie dodawaj `build/`" in text
