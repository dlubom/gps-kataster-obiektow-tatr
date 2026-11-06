# U12 — wycofaj zakończone importy i naprawy

Czytaj [indeks](README.md), [spec](spec.md) i [odbiór](../development.md).
Zależności: brak. Dostarcz tylko tę kartę.

## Pliki i interfejs

Usuń `scripts/importers/{import_pig,import_tpn,apply_review}.py`, moduły
`src/gps_kataster_obiektow_tatr/{pig_staging,tpn_staging,staging_review}.py`,
`source_profile.py`, `source_table.py`, `scripts/profile_sources.py` oraz
`scripts/maintenance/restore_tpn_notes.py` i `tpn_notes.py`.
Odbiorców w testach, docs i pyproject znajdź przed usunięciem.

Wejście: aktualny katalog i archiwalne źródła. Wynik: pozostające publiczne
CLI walidacji, przydziału ID, API TPN/NMT i eksportu zachowują kontrakty.
`write_dataset`, adapter legacy i schematy historii pozostają do U15.

## Kroki i kryteria

- [ ] Utrwal manifest SHA-256 wszystkich `data/sources/`, `data/shapes/`
  i katalogu przed zmianą oraz referencyjny build. Sprawdź domknięcie importów.
- [ ] Usuń wskazany podsystem. Usuń dedykowane testy `test_pig_staging.py`,
  `test_tpn_staging.py`, `test_staging_review.py`, `test_review_declarations.py`,
  `test_source_profile.py`, `test_source_table.py`, `test_restore_tpn_notes.py`.
  Zachowaj przypadki w testach mieszanych, które chronią nadal żywe zachowanie.
- [ ] Usuń nieużywane helpery parsowania/raportowania dopiero po sprawdzeniu
  wszystkich odbiorców. `utc_timestamp` pozostaje używany przez buildery.
  `test_review_output_safety.py` chroni eksporty i pozostaje.
- [ ] Usuń scope mutation dotyczący nieistniejących importerów. Zaktualizuj
  §7–8, §16 i §20 specyfikacji oraz operations/source README: materiały
  źródłowe służą ręcznej ocenie, a przyszłe pomiary są edytowane w YAML/PR.
  Zachowaj dowody danych i historie dawnych napraw, usuń nieaktualne komendy.
- [ ] Uruchom `uv run --frozen pytest -q tests/test_source_helpers.py tests/test_validation_phases.py tests/test_build_db.py tests/test_review_output_safety.py tests/test_tpn_download.py tests/test_tpn_simple.py tests/test_tpn_elevation.py`;
  plik helperów można usunąć tylko jeśli nie ma już żywego zachowania.
- [ ] Pełna bramka, zgodność manifestów źródeł, pełny odczyt eksportów przed/po
  oraz bilans kodu. Cel: usunięcie całych nieużywanych ścieżek; bez nowego
  uniwersalnego importera, przenoszenia kodu do archiwum runtime lub utraty testów ochrony danych.
- [ ] Commit `refactor: retire one-time source imports (PBI-119 U12)`, push,
  terminalne CI i odbiór według indeksu. Zakończ po U12.
