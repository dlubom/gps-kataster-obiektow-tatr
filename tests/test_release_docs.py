from pathlib import Path


def test_readme_links_latest_release_and_changelog() -> None:
    text = Path("README.md").read_text(encoding="utf-8")

    assert "https://github.com/dlubom/gps-kataster-obiektow-tatr/releases/latest" in text
    assert "[CHANGELOG.md](CHANGELOG.md)" in text
    assert "Tu możesz pobrać najnowszą wersję danych" in text
    assert "vX.Y.Z" in text
    assert "Creative Commons Attribution 4.0" in text
    assert "SOURCE_LICENSE_CONFIRMED" not in text


def test_changelog_has_semver_release_entry() -> None:
    text = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert "Semantic Versioning" in text
    assert "## [v1.0.1] - 2026-05-17" in text
    assert "## [v1.0.0] - 2026-05-17" in text
    assert "GitHub Release" in text
