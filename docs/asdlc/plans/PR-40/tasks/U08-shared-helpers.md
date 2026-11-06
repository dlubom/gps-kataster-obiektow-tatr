# U08 — wspólne parsowanie i formatowanie raportów

Przeczytaj [indeks](../README.md), [spec](../spec.md), [design](../design.md)
i [development](../development.md). Zależność: U02. Realizuje S07.

## Spec

PIG, TPN, profilowanie źródeł i review powtarzają `_parse_decimal`,
`_clean_value`, formatowanie Markdown, daty i UTC. Połącz tylko identyczną
semantykę. `source_profile` i `source_table` nie są automatycznie zamienne:
profil surowych wartości oraz normalizacja tabeli mogą inaczej traktować
białe znaki, puste komórki i nazwy kolumn.

Wynik danych staging, raportów i diagnostyki ma pozostać taki sam.
Nie zmieniaj w tej karcie polityki dopuszczania NaN/Infinity, daty źródłowej,
walidacji typów ani kompletności CSV. Te reguły mają zostać u swoich właścicieli.

## Design

- Wydziel małe funkcje o nazwach opisujących zachowanie w module parsowania
  źródeł oraz module formatowania raportów; skorzystaj z już istniejącego
  `source_table`, jeśli jego kontrakt pasuje. Nie buduj ogólnego `utils`.
- Parser liczby zwraca wartość zgodnie z dotychczasowym kontraktem;
  kontrola skończoności należy do walidacji odbiorcy, jeśli tak działa dzisiaj.
- Zachowaj czytelne rozróżnienie surowego tekstu i oczyszczonego tekstu.
  Różnic nie ukrywaj w kilku booleanach sterujących jedną uniwersalną funkcją.
- Wspólny zegar UTC może być funkcją używaną również w przyszłym U10;
  jawne `generated_at` ma zawsze pierwszeństwo, a data pomiaru nie jest
  automatycznie czasem generowania raportu.

## Development

1. Zestaw definicje i wywołania w `pig_staging.py`, `tpn_staging.py`,
   `staging_review.py`, `source_profile.py`, `source_table.py` i `scripts/`.
   Podziel je według semantyki, nie podobieństwa nazw.
2. Scharakteryzuj `None`, pusty tekst, zwykłe/NBSP spacje, przecinek/kropkę,
   tekst błędny, bool/liczbę, NaN/Infinity; dla Markdown: pionową kreskę,
   backtick, CR/LF oraz pustą wartość. Zachowaj wynik każdego używającego modułu.
3. Wyodrębnij wspólne funkcje i przełącz wszystkie wskazane duplikaty.
   Usuń stare definicje i zbędne importy; nie zostawiaj aliasów bez odbiorcy.
4. Czytniki CSV ujednolić tylko tam, gdzie testy potwierdzają identyczny
   kontrakt separatora, kodowania, BOM, nagłówka i whitespace. Inne zachowanie
   pozostaw jawnie opisane, bez przemycania korekty danych.
5. Porównaj reprezentatywne JSON/Markdown staging i profilowania przy
   stałym czasie; wykonaj pełną bramkę i zmierz redukcję netto.

```bash
uv run --frozen pytest -q tests/test_source_table.py tests/test_source_profile.py tests/test_pig_staging.py tests/test_tpn_staging.py tests/test_staging_review.py tests/test_non_finite_values.py
```

## Odbiór

- [x] Każda usunięta kopia ma konkretny wspólny odpowiednik i wszystkich
  odbiorców; pozostawione podobne helpery mają wskazaną różnicę kontraktu.
- [x] Białe znaki, wartości puste/niefinitywne, daty i Markdown zachowują
  dotychczasowe wyniki; raporty po normalizacji wyłącznie czasu są zgodne.
- [x] Brak zmiany źródeł/CSV/katalogu, reguł domenowych i komunikatów CLI.
- [x] Podano rzeczywistą redukcję kodu, testy, pełną bramkę i exact-SHA CI.

Zakończ po U08. Następna karta: [U09](U09-id-allocation.md), po U04.

## Zakres wdrożony

Baza refaktoru: `e27796fad73eb071b982d48b6ac197af8286fe79`; osobna,
zaakceptowana baza historii: `ad5fa191a36d5a5f45f0b2de523bd39125827573`
(aktualna baza PR/main przy rozpoczęciu). U01–U07 potwierdzono w kodzie.

| Usunięte kopie | Wspólny odpowiednik i odbiorcy |
|---|---|
| `_clean_value` ×5 | `source_parsing.clean_text`: PIG, TPN, review, profil, tabela; także wspólne komórki Markdown |
| `_parse_decimal` ×3 | `source_parsing.parse_decimal`: PIG, TPN, profil |
| `_date_part` ×2 | `source_parsing.date_part_or_today`: PIG, TPN |
| `_markdown_text`, `_markdown_code_or_dash` po ×3 | `report_formatting.markdown_text`, `markdown_code_or_dash`: PIG, TPN, review |
| UTC do sekund ×11 | `report_formatting.utc_timestamp`: review, `build_db`, `export_data`; CLI build_db, build_release_artifacts, export_best_measurements, build_pr_preview, profile_sources, import_pig, import_tpn, restore_tpn_notes |
| Dwa odczyty CSV | `source_table.read_raw_csv_table`: profil i `read_source_table`; drugi jawnie przycina wartości |

Nie pozostały aliasy ani wrappery dawnych helperów. Rozróżnienia zachowane:

- Profil zachowuje surowy tekst CSV. Staging przycina wartości CSV; XLSX
  przycina też nagłówki. CSV nadal zachowuje nagłówki, BOM, CR/LF,
  brakujące/puste i nadmiarowe komórki według poprzedniego kontraktu.
- Parser zachowuje NaN/±Infinity i przepełnienie; importerzy nadal odrzucają je
  domenowo, a profil liczy jako liczby. Bool nie staje się liczbą; konwersja
  tekstu zachowuje wcześniejsze `str`/`strip`.
- PIG interpretuje rok jako 31 grudnia; TPN zachowuje cztery formaty dat,
  pierwszeństwo `LAST_EDI_1` i fallback `CREATED_DA`. Wspólny fallback
  zachowuje dzień timestampu, bez konwersji strefy; błędny timestamp daje
  dzisiejszy dzień UTC. Jawny czas generowania i znane daty źródła wygrywają.
- Markdown staging/review zachowuje escaping `|`, LF, surowy CR i backtick,
  w tym pustą wartość `-` oraz same spacje jako kod `` `-` ``.
  Profilowe przykłady, liczby i numery wierszy mają inne formatowanie.
- CSV w `restore_tpn_notes` pozostaje osobny: zachowuje bajty do hasha,
  wymaga unikalnych nagłówków i odrzuca brakujące/nadmiarowe komórki. Wspólny
  odczyt profilu/tabeli celowo nie usuwa tej odrębnej kontroli.
- Zegary pobrań/odczytów TPN zachowują mikrosekundy, a nazwa zrzutu własny
  format. Nie zmieniono argumentów, pomocy, komunikatów CLI ani alokacji ID.

## Wyniki odbioru lokalnego

- Przed ekstrakcją: **181 PASS** charakterystyki kopii i publicznych odbiorców;
  celowa mutacja obsługi NBSP w pamięci osobnego procesu: **1 FAIL / 173 PASS**.
  Bazowy zestaw karty: **450 PASS**. Po połączeniu identycznych kopii wspólne
  kontrakty są testowane raz, a rzeczywiste renderery/CLI osobno: **67 PASS**.
- Pełne raporty na tych samych zachowanych źródłach i czasie
  `2026-11-06T08:00:00Z`: **8/8 JSON/Markdown identyczne bajtowo**,
  bez normalizacji. PIG: 860 wierszy/860 obiektów/46 diagnostyk;
  TPN: 1005 wierszy/1005 dopasowań/16 diagnostyk. Profil obejmuje oba CSV;
  review dry-run dwie decyzje i ostrzeżenie, również tekst z `|`, backtickiem
  i CR/LF. To porównanie obejmuje pełne propozycje i diagnostykę, nie same liczniki.
- Runtime lokalny: osobny klaster PostgreSQL 18.6/PostGIS 3.6.4 i zgodni
  klienci; GDAL. Docker lokalnie nie odpowiedział na diagnostykę w 10 s;
  własne próby przerwano bez restartu usług. Obowiązkowy smoke zarządzanego
  Dockera musi zakończyć się w CI.

- Zestaw karty po zmianie wraz z nowymi regresjami: **517 PASS**.
  Pełna bramka `uv run --frozen python scripts/check_project.py --base-ref
  ad5fa191a36d5a5f45f0b2de523bd39125827573`: **1506 PASS / 1 SKIP**
  (lokalny smoke zarządzanego Dockera), Ruff, historia, pełny build,
  natywny restore dumpa, odczyt GeoPackage i diff PASS. Zbudowano 13 plików:
  1029 obiektów/1019 jaskiń/1946 pomiarów; 4185 warningów, zero błędów.
- Niezależne review bez uwag. AST 109 zachowanych funkcji jest zgodny po
  podmianie nazw helperów; odrębną granicę CSV sprawdzają regresje.
  CSV nadal **1 → 1 otwarcie** tego samego pliku: nie deklarujemy zysku IO.
- Python produkcyjny: **+216/−314, netto −98**; ten sam bilans po
  `--ignore-space-change`. SQL/schematy **0**; testy **+272/−0**.
  Brak zmian `data/`, `config/`, `schema/`, workflow i zależności.

## Dostarczenie i CI

Kod U08 dostarczono fast-forward jako
`9c615d0a8b8793b3cef6c309dd072c31caa35e49` do otwartego draft PR #40;
zdalny SHA potwierdzono. Wymagane
[Validate code and data](https://github.com/dlubom/gps-kataster-obiektow-tatr/actions/runs/42183456061)
zakończone **SUCCESS** w próbie 2 dla tego SHA: **1505 PASS / 2 SKIP** oraz osobny,
obowiązkowy smoke zarządzanego Dockera **1 PASS** (start, dump, restore,
cleanup). Pierwszą próbę przerwano po ponad 15 minutach powolnego pobierania
pakietów z `azure.archive.ubuntu.com`, przed testami; ponowiono wyłącznie
job walidacji bez zmiany SHA/workflow. Anulowanie nie jest wynikiem zielonym.
Skips standardowego zestawu to smoke uruchamiany osobno i próba
natywnego klienta, gdy CI korzysta z klientów kontenera.

[Preview kodu](https://github.com/dlubom/gps-kataster-obiektow-tatr/actions/runs/42183455782)
zakończone **SUCCESS**, próba 1.
[Paczka 13485714921](https://github.com/dlubom/gps-kataster-obiektow-tatr/actions/runs/42183455782/artifacts/13485714921)
ma SHA-256 `09945f25d77aa0da847acc69bb8d6f453bb2644ffec3ae55344d0b00cf851318`
zgodny z GitHub. **14/14 sum**, 15 nazw plików oraz head/base/merge
`599039f570dd567359f13a028f011f34c9b14863`, run i próba są poprawne;
rodzice rzeczywistego merge sprawdzeni przez Git.

Pełny niezależny odczyt **13/13 formatów** jest zgodny z lokalnym buildem
na tych samych danych, czasie i metadanych preview: CSV, GeoJSON, cztery GPX,
JSON/Markdown, komórki/typy/formaty/tabele i XML XLSX, Shapefile, wszystkie
tabele/deklaracje/geometrie GeoPackage oraz natywnie odtworzony dump ze
wszystkimi tabelami i widokami Best. Źródła są porównane ściśle, również
brak/null, historia i 27 manual Best. Dla 21982 pochodnych wartości
EPSG:2180 maksymalna różnica to `1.9208528101444244e-9 m`, przy absolutnej
tolerancji `1e-8 m`. Porównanie staging/profilowania przed/po nadal jest
bajtowe i nie korzysta z tej tolerancji.

Normalizacje preview dotyczą wyłącznie techniki formatu: nagłówków ZIP,
daty DBF, czasu utworzenia GeoPackage, składni/wersji triggerów i fizycznego
układu RTree po niezależnym odbudowaniu indeksu i próbach insert/update/fid/
null/delete na kopiach, tokena `pg_dump` oraz nagłówków wersji klienta/serwera.
Numeryczne XML XLSX porównano po odczycie wszystkich wartości/typów/formatów;
pozostała struktura XML jest sprawdzana. Nie normalizowano danych źródłowych.

Bilans dokumentacji całego U08: **+167/−12** (Python i testy policzone wyżej).

Indeks zawiera status i prompt U09; U09/U10 nie rozpoczęto. Dokumentacja
kontekstu/backlogu odsyła do tej karty; specyfikacja i instrukcja operacyjna
opisują wdrożone kontrakty. Końcowe SHA dokumentacji i jego terminalne CI/
preview są potwierdzane w opisie PR. Bez merge, taga i wydania.
