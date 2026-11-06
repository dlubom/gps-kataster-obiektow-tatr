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

## Odbiór

Punkt odniesienia kodu: `069599649831f8861cc4cffd47dc88cc085a6a10`;
zaakceptowana historia: `ad5fa191a36d5a5f45f0b2de523bd39125827573`
(`origin/main`). Usunięto trzy CLI importu/decyzji, trzy moduły staging,
profiler z czytnikiem, jednorazową naprawę TPN i ich martwe helpery/testy.
`utc_timestamp`, API TPN/NMT, przydział ID, writer i adapter historii pozostają.
Ochrona wyjść nadal jest testowana; test odtworzenia członkostwa przygotowuje
kanoniczny YAML bez pośrednictwa usuniętego review.

Przed zmianą i po niej zweryfikowano wszystkie 2084 pliki `data/` według
[manifestu SHA-256](../../../verification/PBI-119-U12-data.sha256)
(hash manifestu `493d0f18713a30e8520d3e32c9b729b93296f64b4b83be9e1a201f33125e0d54`).
`data/`, `config/` i `schema/` bez różnic względem bazy zadania.
Karta wymienia edycję `data/sources/README.md`, lecz kontrakt serii wymaga
bajtowej niezmienności całego `data/`. Pierwszeństwo ma ten niezmiennik:
README nie zmieniono; aktualny sposób pracy opisuje `docs/operations.md`.
W README pozostaje historyczna instrukcja dopisania `Jaskinia.object_ids`;
kanoniczna edycja używa `cave_id` i `membership_ordinal`.

Przy `--generated-at 2026-11-06T00:00:00Z`, identycznym `source-commit`
i baseline, build przed/po dał **13 artefaktów**, 1029 obiektów, 1019 jaskiń,
1946 pomiarów i 4185 ostrzeżeń. CSV, GeoJSON, GPX, JSON i Markdown identyczne
bajtowo; XLSX porównano dla wszystkich komórek, formatów i tabel. GeoPackage:
`integrity_check`, `foreign_key_check` oraz wszystkie tabele, wartości,
geometrie i CRS zgodne; pominięto jedynie `gpkg_contents.last_change` oraz
`gpkg_metadata_reference.timestamp`. Shapefile: wszystkie składowe zgodne
po normalizacji daty nagłówka DBF i metadanych ZIP. Dumpy odtworzono natywnie;
wszystkie tabele, dziewięć widoków, kolumny, typy, wartości domyślne,
nullability i constraints zgodne. Metadane kontenerów dump/XLSX pominięto.
Osobne czytniki odczytały CSV, GeoJSON, GPX, Shapefile i oba arkusze XLSX.

Przed zmianą testy karty: **318 PASS**; po zmianie z testem konfiguracji
mutation: **223 PASS**, a 17 zachowanych testów deklaracji legacy: **17 PASS**.
Niezależny review wskazał te testy oraz nieaktualny opis review; oba naprawiono.
Produkcyjny Python `src/` i `scripts/`: **+1/−4506**,
netto **−4505** linii fizycznych, także przy `--ignore-space-change`;
SQL i schematy bez zmian. Testy (w tym 69 przeniesionych linii): **+88/−4620**, netto **−4532**.
Nie uruchamiano pełnej kampanii mutation; wcześniejsze ograniczenie U11
pozostaje udokumentowane. Pełna lokalna bramka `check_project.py --base-ref origin/main`: **1036 PASS /
1 SKIP**, 490,63 s; Ruff, walidacja, historia, build, restore dumpa, odczyt
GeoPackage i `git diff --check` zakończyły się powodzeniem. Skip to osobny
managed Docker smoke, wymagany w CI. Zdalny wynik jest podawany w opisie PR.
