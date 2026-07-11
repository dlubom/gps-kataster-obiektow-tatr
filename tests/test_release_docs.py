from pathlib import Path


def test_readme_links_latest_release_and_changelog() -> None:
    text = Path("README.md").read_text(encoding="utf-8")

    assert "https://github.com/dlubom/gps-kataster-obiektow-tatr/releases/latest" in text
    assert "[CHANGELOG.md](CHANGELOG.md)" in text
    assert "Tu możesz pobrać najnowszą wersję danych" in text
    assert "vX.Y.Z" in text
    assert "Creative Commons Attribution 4.0" in text
    assert "SOURCE_LICENSE_CONFIRMED" not in text


def test_readmes_are_trilingual_and_link_the_project_ecosystem() -> None:
    polish = Path("README.md").read_text(encoding="utf-8")
    english = Path("README.en.md").read_text(encoding="utf-8")
    slovak = Path("README.sk.md").read_text(encoding="utf-8")

    assert "🇵🇱 **Polski**" in polish
    assert "[🇬🇧 English](README.en.md)" in polish
    assert "[🇸🇰 Slovenčina](README.sk.md)" in polish
    assert "🇸🇰 **Slovenčina**" in slovak
    assert "[🇵🇱 Polski](README.md)" in slovak
    assert "[🇬🇧 English](README.en.md)" in slovak
    assert "🇬🇧 **English**" in english
    assert "[🇵🇱 Polski](README.md)" in english
    assert "[🇸🇰 Slovenčina](README.sk.md)" in english

    required_links = [
        "https://github.com/dlubom/gps-kataster-obiektow-tatr/releases/latest",
        "https://github.com/dlubom/Jaskiniowy-Kataster-Tatr-Zachodnich",
        "https://github.com/dlubom/Jaskiniowy-Kataster-Tatr-Zachodnich/releases/latest",
        "https://github.com/dlubom/Georeferencer",
        "https://github.com/dlubom/Georeferencer/releases/latest",
    ]

    for text in (polish, english, slovak):
        for link in required_links:
            assert link in text
        assert "[CHANGELOG.md](CHANGELOG.md)" in text
        assert "Creative Commons Attribution 4.0" in text
        assert "vX.Y.Z" in text


def test_changelog_has_semver_release_entry() -> None:
    text = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert "Semantic Versioning" in text
    assert "## [v1.0.2] - 2026-05-21" in text
    assert "## [v1.0.1] - 2026-05-17" in text
    assert "## [v1.0.0] - 2026-05-17" in text
    assert "GitHub Release" in text
