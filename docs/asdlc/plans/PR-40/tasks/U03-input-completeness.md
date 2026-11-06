# U03 — kompletny katalog wejściowy

Przed wykonaniem przeczytaj [indeks](../README.md), [spec](../spec.md),
[design](../design.md) i [development](../development.md).
Zależność: U02. To zalecane pierwsze zadanie. Realizuje S01; chroni S02/S04/S06.

## Spec

Przed U03 `load_yaml_dataset` wymagał `objects`, `caves`, `relations`, ale nie
`publications`. `_read_snapshots` tylko iterował czwarty katalog. Brak lub
plik `publications` przyjmowano jako zero publikacji, sprzecznie z §10.1
specyfikacji i `docs/operations.md`. Poniższy odbiór zamyka tę lukę.

Kanoniczny katalog wymaga wszystkich czterech katalogów. Pusty istniejący
katalog pozostaje poprawny. Odczyt nie może automatycznie odtwarzać braków.
Jawnie zachowaj kompatybilność starego YAML bez bibliografii: w formacie
legacy brak `publications` oznacza brak publikacji; jeśli ścieżka istnieje
jako plik, zgłoś błąd katalogu. Nie zmieniaj reguł markerów ani symlinków.

## Design

- Dodaj jeden opis/guard wymaganego układu z jawnym rozróżnieniem
  kanonicznego źródła i legacy. Wykorzystaj `DataDirectoryError` i istniejące
  mapowanie błędów; nie dokładaj sprawdzeń w każdym eksporcie.
- Zachowaj kolejność diagnostyki z U02: uszkodzony/brakujący marker domyślnego
  źródła nie może zostać zastąpiony innym błędem tylko przez przesunięcie guarda.
- Guard działa przed `_open_rows`/uruchomieniem bazy i przygotowaniem wyjścia.
  Nie zmieniaj tolerancji ogólnego `iter_yaml_paths` dla opcjonalnych źródeł.
- Osobno sprawdź `_git_baseline` w `history.py`: stare zaakceptowane rewizje
  bez bibliografii muszą pozostać odczytywalne; niepełny format kanoniczny
  nie może zostać po cichu zdegradowany do legacy.

## Development

1. Dodaj regresję publicznego API oraz CLI dla kanonicznego wejścia z markerem:
   brak/plik zamiast każdej z czterech ścieżek, poprawny pusty komplet,
   istniejące publikacje. Przypadki `publications` muszą odtworzyć lukę przed poprawką.
2. Wprowadź wspólną kontrolę w
   `src/gps_kataster_obiektow_tatr/data_loader.py` i podłącz odpowiednie wejście
   `postgres.py::_read_snapshots`; użyj obecnego wyboru formatu, nie zgaduj
   go na podstawie liczby rekordów. Prześledź `validator.py`, build i review.
3. Uzupełnij kanoniczne fixtures o jawne `publications/` i znacznik.
   `tests/conftest.py::make_data_dir`, `tests/sql_test_support.py` oraz
   `tests/test_postgres_exports.py::source` tworzą także legacy: rozdziel
   intencję zamiast dodawać marker do wszystkich starych fixtures.
4. Sprawdź prawdziwy zaakceptowany Git baseline obu formatów, w tym pusty,
   niedostępny i niepełny. Nie naprawiaj baseline w trakcie jego odczytu.
5. Uaktualnij opis wymaganych katalogów w specyfikacji i operacjach, jeśli
   potrzebne jest doprecyzowanie legacy. Zakończ według wspólnej procedury.

```bash
uv run --frozen pytest -q tests/test_data_loader.py tests/test_catalog_yaml.py tests/test_catalog_input_contract.py tests/test_validation_phases.py tests/test_history.py tests/test_postgres_exports.py
```

## Odbiór

- [x] Brak/plik katalogu kanonicznego daje kontrolowany błąd z właściwą ścieżką,
  zanim baza zostanie otwarta; kod CLI jest niezerowy.
- [x] Pusty komplet działa; legacy bez bibliografii działa; plik zamiast
  opcjonalnego katalogu legacy jest jawnie odrzucony.
- [x] Błędne wejście pozostawia bajtowo istniejące YAML i artefakty, także
  przy dry-run i zwykłym wywołaniu build/review.
- [x] Diagnostyka pozostałych przypadków U02 jest niezmieniona; dotychczasowe
  testy nie zniknęły z powodu uszczelnienia fixtures.
- [x] Pełna bramka i porównanie eksportów z bazy zadania przechodzą;
  zapisano bilans kodu, commit, terminalne CI oraz wynik w karcie/indeksie.

Po odbiorze zakończ. Następna karta: [U04](U04-canonical-proposals.md).
Nie implementuj w U03 konwersji staging ani nowych modeli całego katalogu.


## Wynik

- Podstawa porównania: `5fd411bc75ae710df7224f00dbf58876af26c6b9`, aktualny
  head otwartego draft PR #40 przy rozpoczęciu. Zaakceptowana baza historii:
  `ad5fa191a36d5a5f45f0b2de523bd39125827573` (ówczesne base PR / `origin/main`).
- Jeden opis układu i guard w `data_loader` obsługuje źródło i wejście
  PostgreSQL. Kontrola znacznika w `_read_snapshots` poprzedza guard.
  `iter_yaml_paths`, reguły markerów i symlinków pozostają bez zmian.
- Ekstrakcja historii zachowuje katalogi dowiedzione ścieżkami zaakceptowanego
  drzewa Git, również z samym plikiem pomocniczym. Plik w miejscu katalogu
  nie znika podczas filtrowania blobów. Braków nie odtwarza.
- Fixtures jawnie rozdzielają legacy i kanoniczny pusty komplet. Istniejących
  testów U02 nie usunięto. Przed poprawką: **29 FAIL / 50 PASS** w 79 nowych
  przypadkach; po poprawce: **258 PASS** we wszystkich sześciu plikach z karty
  (179 dotychczasowych i 79 nowych). Dla `publications` odtworzono brak/plik
  przez bezpośrednie API, CLI, build i review; kontrola blokuje przed `_open_rows`.
  Zapis i dry-run zachowują bajty wejścia i istniejących artefaktów.
- Pełna diagnostyka katalogu porównana z kodem podstawy: **4185/4185 wpisów
  identycznych**, w tym kody, severity, ścieżki, opisy i kolejność; 0 błędów.
- Python produkcyjny (`src/` + `scripts/`): **+25 / −17, netto +8 linii**,
  również po pominięciu zmian białych znaków. SQL i schematy: 0/0.
  To uszczelnienie kompletności, bez redukcji rozmiaru. Guard jest współdzielony
  przez granice odczytu; `open_catalog` sprawdza układ przed skanem rozmiarów
  oraz ponownie w publicznym loaderze YAML. Nie deklarujemy redukcji IO/baz.
  `data/`, `config/` i `schema/` są identyczne z podstawą zadania.
- Pełne buildy podstawy i U03 na niezmienionych danych, stałym
  `generated_at=2026-11-05T16:00:00Z`, `release_version=U03-comparison` i tym
  samym `source_commit`: **13/13 artefaktów zgodnych**. Dziewięć formatów
  tekstowych jest identycznych bajtowo. XLSX: wszystkie komórki, typy,
  style i części XML; Shapefile: wszystkie składowe, pola, rekordy, geometrie
  i CRS; GeoPackage: `integrity_check`, wszystkie tabele, geometrie, null,
  deklaracje i CRS. Oba dumpy odtworzono natywnie: 15 tabel, oba widoki Best
  i cały schemat są zgodne. Zachowano 1029 obiektów, 1019 jaskiń, 1946 pomiarów
  oraz 27 ręcznych Best. Pominięto wyłącznie techniczne nagłówki ZIP/dump,
  datę nagłówka DBF, `gpkg_contents.last_change`,
  `gpkg_metadata_reference.timestamp` i losowy token `restrict` klienta PG.
- Pełna lokalna bramka `uv sync --frozen`, następnie
  `uv run --frozen python scripts/check_project.py --base-ref
  ad5fa191a36d5a5f45f0b2de523bd39125827573`: **1267 PASS / 1 SKIP**,
  Ruff, historia, pełny build z restore/odczytem i `git diff --check` PASS.
  Użyto własnego natywnego PostgreSQL 18.6/PostGIS 3.6.4. Lokalny skip to
  zarządzany smoke Dockera, obowiązkowy w CI. Niezależny review: brak
  Critical/Important; potwierdzono także brak przygotowania wyjścia po błędzie.
- Kod dostarczono fast-forward jako
  [`80123268e7a08dca5ff170fae47f3b3023d672be`](https://github.com/dlubom/gps-kataster-obiektow-tatr/commit/80123268e7a08dca5ff170fae47f3b3023d672be),
  z potwierdzonym zdalnym SHA. **SUCCESS dla tego SHA**:
  [Validate code and data](https://github.com/dlubom/gps-kataster-obiektow-tatr/actions/runs/42066657715)
  i [PR export preview](https://github.com/dlubom/gps-kataster-obiektow-tatr/actions/runs/42066657661).
  CI: **1266 PASS / 2 SKIP**, osobny wymagany smoke Dockera: **1 PASS**
  (start, dump, restore, cleanup). Drugi skip to test natywnych klientów,
  sprawdzony lokalnie; CI używa klientów z kontenera.
- [Odebrana paczka CI](https://github.com/dlubom/gps-kataster-obiektow-tatr/actions/runs/42066657661/artifacts/13434162523):
  SHA-256 archiwum `f49a6500c5a5245c8ef07cfce7b7c2eff1e7ce9f3d6e45f3d323c51a2309ce2e`
  zgodny z GitHub, **14/14 sum**, 15 właściwych plików. Head/base/run/attempt
  są zgodne; merge `fbe3487913b78b0ac501694919c29b8fa44b289f` ma zweryfikowanych
  obu rodziców. Niezależny odbiór **13/13 formatów** z tej paczki potwierdził
  wszystkie pola, kolejność, null i źródłowe EPSG. Odtworzony dump ma wszystkie
  15 tabel identyczne z lokalnym buildem o tych samych metadanych, łącznie
  z geometrią źródłową, historią, cytowaniami i ręcznym Best. Odczytano oba
  arkusze XLSX, rekordy/geometrie Shapefile, obie warstwy i deklaracje GPKG,
  wszystkie CSV/GeoJSON/GPX/grupy i statystyki. Między natywnym runtime i CI
  obliczone PL-1992 różnią się najwyżej o `1.93e-9 m`; przy odbiorze przyjęto
  jawne `1e-8 m` wyłącznie dla tych pochodnych współrzędnych/geometrii.
  Źródła, wysokości i dokładności porównano dokładnie. Porównanie przed/po U03
  w tym samym runtime nie wymagało tej tolerancji.
- Końcowy SHA dostarczenia dokumentacji i CI bieżącego head wskazuje
  [opis PR #40](https://github.com/dlubom/gps-kataster-obiektow-tatr/pull/40).
  U04 nie rozpoczęto; bez merge, taga i wydania.
- Ograniczenie odłożone po niezależnym review (Minor, obecne już w podstawie):
  Git blob `data` zamiast drzewa katalogu daje nieobsłużony `IndexError`,
  choć blokuje wyjście. Zapisano do [U07](U07-production-path-tests.md#development)
  jako przypadek kontrolowanej diagnostyki historii; bez rozszerzenia U03.
