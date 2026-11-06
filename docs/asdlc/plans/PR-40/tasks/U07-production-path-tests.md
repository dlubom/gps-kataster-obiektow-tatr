# U07 — testy właściwej ścieżki produkcyjnej

Przeczytaj [indeks](../README.md), [spec](../spec.md), [design](../design.md)
i [development](../development.md). Zależności: U03/U04/U06. Realizuje S06.

## Spec

`tests/export_test_support.py::fixture_sql` waliduje legacy, zapisuje
kanoniczny snapshot i dopiero potem wywołuje produkcyjny build/eksport.
Część błędów może zatem pochodzić z wrappera, a nie badanego API.
Zwykły test eksportu ma podać prawidłowy format wejścia bez dodatkowej
walidacji/naprawy. Test błędu ma dotrzeć bezpośrednio do publicznego API/CLI.

Zachowaj osobne testy legacy/importu i realnej migracji. Redukcja kodu
testowego nie może oznaczać usunięcia scenariuszy, niezależnych oczekiwań
formatu ani ochrony historii.

## Design

- Wspólne fabryki tworzą jawny kanoniczny YAML: cztery katalogi, marker,
  źródłowe pola, manual/auto Best, opcjonalne publikacje i cytowania.
- Baseline to osobny prawdziwy repozytorium/commit zaakceptowanego fixture,
  tworzony przed mutacją. Helper nie ładuje SQL ani nie wywołuje walidatora
  zamiast testowanego wejścia.
- Zachowaj proste legacy fixtures do testowania adaptera/historii; nazwij
  ich cel. Wzorce wartości eksportu nie mogą powstawać przez `ExportData`
  lub ten sam serializer, którego poprawność sprawdzają.
- Przenieś współdzielone konstrukcje z importów `test_*.py` do istniejących
  modułów wsparcia lub `conftest.py`, grupując je według celu.

## Development

1. Zinwentaryzuj użycia `export_test_support`, `sql_test_support`,
   `_write_sample_data` i importy między modułami testów. Przypisz testy
   do: canonical API/CLI, adapter legacy, historia, niezależny odbiorca.
2. Dodaj kanoniczne fabryki i przełącz zwykłe testy w
   `test_best_measurements_export.py`, `test_release_artifacts.py`,
   `test_postgres_exports.py`, `test_export_data.py` i `test_pr_preview.py`.
   Nie wykonuj masowej zamiany legacy bez sprawdzenia intencji scenariusza.
3. Zastąp wrappery bezpośrednimi importami produkcyjnymi; usuń ich
   `validate_proposal`/`write_dataset` i sztucznie rzucane wyjątki z tej ścieżki.
4. Sprawdź błędny YAML, brak katalogu, zły manual Best, niezgodne deklaracje,
   utratę pomiaru, niedostępny baseline i błąd późnego eksportera przez
   rzeczywiste wejście. Nie przenoś tych przypadków wyłącznie do unit testów.
   Uwzględnij drobną lukę diagnostyki potwierdzoną przy odbiorze U03:
   zaakceptowany Git blob `data` (mode `100644`) zamiast drzewa katalogu
   wywołuje obecnie `IndexError` w `_git_baseline`, zamiast kontrolowanego
   `HISTORY_BASELINE_UNAVAILABLE`. Błąd istniał przed U03 i blokuje wyjście;
   nie stanowi obejścia historii ani utraty danych. U03 go nie zmienia.
5. Uruchom cały zestaw, porównaj listę zachowanych scenariuszy i usuń martwe
   wyjątki/aliasy tylko jeśli nie mają odbiorców produkcyjnych ani publicznych.

```bash
uv run --frozen pytest -q tests/test_best_measurements_export.py tests/test_release_artifacts.py tests/test_postgres_exports.py tests/test_export_data.py tests/test_pr_preview.py tests/test_history.py tests/test_validation_phases.py
```

## Odbiór

- [x] Zwykłe testy nie wykonują walidacji ani migracji przed badanym API.
- [x] Błędy zachowują kod/ścieżkę przez publiczne wejście; udowodniono,
  że usunięcie odpowiedniej bramki produkcyjnej powoduje porażkę regresji.
- [x] Osobne testy adaptera i rzeczywistego baseline legacy nadal przechodzą.
- [x] Odczyty XLSX/GPKG/Shapefile/dump pozostają niezależne od serializera;
  każdy dawny scenariusz ma odpowiednik, nawet jeśli liczba testów się zmieni.
- [x] Bilans testów/helperów jest podany oddzielnie od kodu produkcji;
  pełna bramka, porównanie eksportów i CI spełniają procedurę.

Zakończ po U07. Następna karta: [U08](U08-shared-helpers.md).


### Wdrożenie i dowody odbioru

Baza refaktoru: `1cebb54617140c35d959b37cf658dc3906693ae8` (zdalny head
otwartego draft PR #40). Osobna zaakceptowana baza historii z aktualnego PR:
`ad5fa191a36d5a5f45f0b2de523bd39125827573`. Zakres kończy się na U07.

| Cel | Dawna ścieżka / zachowane scenariusze | Ścieżka U07 |
|---|---|---|
| Canonical API/CLI | `fixture_sql` i wrappery w Best, release, build DB, non-finite, missing-inputs i preview | Literalne fabryki źródła; bezpośredni import badanego API; jawny osobny commit Git |
| Odczyty i przygotowanie | `source` z modułu testowego, `consumer_state`, trzy kopie sample data | Wsparcie fixtures w `export_test_support`; jawny `read_catalog_projection` tylko przy testowaniu konsumenta projekcji |
| Legacy/import | Walidacja redundantnych współrzędnych i symetrii członkostwa | Zachowane testy walidatora/staging oraz osobne cztery negatywne przypadki migracji i rzeczywista konwersja z baseline legacy |
| Historia | Fabryka importowana z `test_history`, wrapper budujący baseline podczas wywołania | Nazwana fabryka legacy w `sql_test_support`; zwykłe testy akceptują poprawne źródło przed mutacją |
| Niezależny odbiorca | openpyxl, pyshp, SQLite/GDAL, natywne odtworzenie dumpa | Te same narzędzia i literalne oczekiwania; wspólny odczyt arkuszy poza `test_*.py` |

Usunięto `fixture_sql`, trzy wrappery build/eksport oraz `consumer_state`
i wszystkie importy między modułami `test_*.py`, a także martwy
`canonical_records` (brak odbiorców). Helpery nie rzucają wyjątków
w imieniu API ani nie uruchamiają `validate_proposal`/`write_dataset`.
`accept_source` kopiuje bajty do osobnego repozytorium; utrwala wyłącznie
katalogi faktycznie obecne w fixture, bez naprawy braków kandydata.
Nie zapisuje `.gitkeep` przez dowiązanie assetu do zewnętrznego pustego
katalogu; rozszerzony test odtworzył ten efekt uboczny, a następnie przeszedł
po wykluczeniu symlinków podczas utrwalania pustych katalogów kopii Git.

Macierz `test_production_entrypoints.py` przechodzi przez trzy API i cztery
CLI: kolizja YAML, brak `publications`, zły manual Best, pola pochodnych
współrzędnych i członkostwa, utrata pomiaru oraz niedostępny baseline.
Testy późnego błędu dump/GPKG/Excel i standalone nadal badają rzeczywiste
wejścia i zachowanie poprzednich wyjść. Manual Best i cytowania trzech
zakresów są też odczytywane niezależnie z natywnie odtworzonego dumpa.

Dla sześciu przypadków pominięto po jednej rzeczywistej bramce w osobnym
procesie: unikalność YAML, komplet katalogów, kontrola źródłowych pól
współrzędnych/członkostwa oraz historia utraty pomiaru/niedostępnej rewizji.
Każda regresja publicznego API zakończyła się `DID NOT RAISE`: **6/6 mutantów
wykrytych**. Eksperyment zmieniał tylko funkcje w pamięci, bez edycji źródeł.
Regresja Git blob `data` (potwierdzony mode `100644`) najpierw odtworzyła
`IndexError` przez produkcyjny build. Dwuliniowa kontrola typu drzewa daje
`HISTORY_BASELINE_UNAVAILABLE`; API i CLI zachowują wcześniejszy dump.

Lista z `pytest --collect-only`: **1322/1322 dawnych scenariuszy zachowane**:
1316 ma te same ID, a sześć przypadków NaN/±Inf dla `x_1992`/`y_1992` ma
jawny odpowiednik w macierzy legacy. Kanoniczna macierz sprawdza źródłowe
`input_x`/`input_y` EPSG:2180, token błędu i konkretne pole. Łącznie
**1440 scenariuszy, netto +118**. Na tej samej próbce pełnego builda liczba ładowań
katalogu przez `_open_rows` spada z **2 do 1**: znika walidacja wrappera.
Setup źródła nie otwiera bazy. Natywny restore pozostaje wymagany i nie jest
liczony jako ładowanie katalogu. Kontroluje to także
`test_single_catalogue_supplies_every_writer`.

Przy stałym `generated_at=2026-11-06T08:00:00Z`, wersji `u07-comparison`
i identycznym `source_commit` pełny odczyt **13/13 formatów jest zgodny**.
Dziewięć formatów tekstowych jest zgodnych bajtowo. XLSX porównano przez
wszystkie komórki, typy, formaty i części XML; Shapefile przez składowe,
rekordy, geometrię i CRS; GeoPackage przez wszystkie tabele, deklaracje,
geometrie, typy/null, `integrity_check` i FK. Oba dumpy odtworzono natywnie:
zgodne wszystkie tabele, oba widoki Best i schemat. Normalizowano wyłącznie
czas nagłówka ZIP/DBF, techniczny czas utworzenia GeoPackage i metadane
kontenera dumpa/losowy token `restrict`. Nie normalizowano danych źródłowych.
Liczniki: 1029 obiektów, 1019 jaskiń, 1946 pomiarów, 27 manual Best.

Bilans względem bazy: Python produkcyjny **+2/−0, netto +2** (również bez
białych znaków); SQL i schematy 0. Testy/helpery **+911/−773, netto +138**
(bez białych znaków +908/−770). Usunięte duplikaty równoważy dodane pokrycie
bezpośrednich wejść; nie jest to redukcja liczby linii całego zadania.
Dokumentacja: **+162/−12**.
Brak zmian `data/`, `config/`, `schema/` i workflow.

Zachowano rzeczywistą diagnostykę produkcji, różną od dawnych wyjątków
wrappera: kanoniczne błędy YAML mają `SQL_CATALOG_INVALID`, a odroczony FK
manual Best wskazuje `<dataset>` i ID obiektu/pomiaru, bez ścieżki pliku.
To istniejące ograniczenie; U07 nie zmienia polityki diagnostyki.

Niezależne review wskazało osłabienie sześciu przypadków NaN/±Inf przez
zakaz pól pochodnych. Wzmocnione oczekiwania najpierw dały **6 FAIL / 15 PASS**;
poprawka rozdziela deklaracje legacy od legalnej geometrii źródłowej 2180.
Po poprawce cały `test_non_finite_values.py`: **58 PASS**. Przypadki nie mogą
przejść wyłącznie dzięki odrzuceniu pola pochodnego. Pozostałych ustaleń
Critical/Important nie było; nie zlecano ponownego review.

Zestaw karty i osobnych regresji API/CLI/migracji: **244 PASS**. Pełne
**4185/4185 diagnostyk katalogu są identyczne** przed/po, także kody, severity,
ścieżki, kolejność i opis. Przebieg bramki sprzed poprawki review przerwano
(405 PASS do przerwania); nie jest dowodem końcowego sukcesu.

Pełna lokalna bramka: **1439 PASS / 1 SKIP**, Ruff, historia, build 13 formatów,
natywny restore dumpa, odczyt GeoPackage i `git diff --check` — PASS. Lokalny
skip dotyczy smoke zarządzanego Dockera; wymaga osobnego sukcesu w CI.
Dodatkowa regresja ochrony dowiązania assetu w baseline: **1 PASS**.

Kod U07: `caf559480881b002495d42cc39607d4d07151434` (zdalny SHA potwierdzony).
[Preview](https://github.com/dlubom/gps-kataster-obiektow-tatr/actions/runs/42173508341)
ma terminalne **SUCCESS**, próba 1.
[Paczka 13482415749](https://github.com/dlubom/gps-kataster-obiektow-tatr/actions/runs/42173508341/artifacts/13482415749):
SHA-256 `f7064f785dc5e8ff7586b31cc194a40bcff0de7fb19f44fd52cc571455d3a461`
zgodny z GitHub, **14/14 sum**, 15 plików i head/base/merge/run/próba zgodne.
Rodzice merge `4849ccff1af5c4076cafccf843c47b10387ecb09` potwierdzeni w Git.
Pełny odczyt **13/13 formatów** odebrany. Wszystkie źródłowe wartości zgodne
ściśle; 21982 pochodne wartości EPSG:2180 porównane z tolerancją `1e-8 m`,
maksymalna różnica `1.9208528101444244e-9 m`. Oprócz technicznych metadanych
wymienionych wyżej porównanie środowisk normalizuje komentarze wersji klienta
PG18 oraz wariant zapisu/triggerów i fizycznych stron RTree GDAL. Każdy indeks
sprawdzono przez niezależne odtworzenie z geometrii, `rtreecheck` i operacje
geometry/fid/null/delete/insert na kopiach w pamięci; nie pominięto danych
logicznych ani deklaracji pól, geometrii i CRS.

Wymagane [Validate code and data](https://github.com/dlubom/gps-kataster-obiektow-tatr/actions/runs/42173508345)
dla tego SHA ma terminalne **SUCCESS**: **1438 PASS / 2 SKIP**. Osobny
obowiązkowy smoke zarządzanego Dockera: **1 PASS** (start, dump, restore,
cleanup), także terminalne SUCCESS. Wszystkie kroki checka zakończone.

Odbiór U07 jest zakończony; status pozostaje wyłącznie w indeksie. Końcowy
commit aktualizuje tylko kartę i indeks. Jego zdalny SHA, terminalne CI oraz
ponowny odczyt preview wskazuje opis PR #40. U08 nie rozpoczęto; bez merge,
taga i wydania.
