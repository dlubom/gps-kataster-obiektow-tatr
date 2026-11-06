# PR #40 — plan czyszczenia kodu

> **Dla wykonawcy:** realizuj jedną wskazaną kartę, używając
> `superpowers:executing-plans`. Przygotowanie planu nie zleca implementacji.

**Cel:** ograniczyć program do odczytu YAML, walidacji i eksportów przez
usunięcie zakończonych importów i nieużywanych ścieżek.

**Architektura:** jeden bieżący format źródła v2, tymczasowy PostgreSQL/PostGIS
oraz dotychczasowa bramka historii. Historyczny adapter pozostaje wyłącznie
po stronie odczytu starszego baseline.

**Stos:** obecny Python/uv, YAML, PostgreSQL 18/PostGIS 3.6, GDAL; bez nowych
bibliotek runtime. **Spec:** [kontrakt tej serii](spec.md).

## Zakres i stan

Po ponownym rozważeniu użytkownik ograniczył zakres do czyszczenia kodu.
Nie wprowadzamy rejestru wycofanych ID, formatu v3 ani nowych wyjątków
od ochrony historii. Numery U13/U14 pozostają wycofane z planu, aby nie
pomylić ich z wcześniejszą propozycją. Jej zapis pozostaje w historii Git.

| Karta | Wynik | Status | Zależności |
|---|---|---|---|
| [U12](U12-remove-imports.md) | Usunięte zakończone importy, profiler i naprawa TPN | wykonane; CI w opisie PR | brak |
| U13 / U14 | Rejestr ID i kontrolowane wycofania | wyłączone z zakresu | nie realizować |
| [U15](U15-remove-writers-legacy.md) | Jeden bieżący format v2, usunięte programowe zapisy katalogu | oczekuje | U12 |
| [U16](U16-postgis-validation.md) | Jeden silnik walidacji geografii katalogu | oczekuje | U15 |
| [U17](U17-export-read-model.md) | Decyzja o skróceniu drogi SQL → ExportData | oczekuje | U16 |

To jedyny rejestr statusów tej serii. `gotowe do zlecenia` nie oznacza
rozpoczęcia. U01–U11 pozostają zakończone; nie zmieniamy wymaganego CI
ani polityki merge/tag/release. Issue #33 pozostaje odłożone.

## Globalne ograniczenia i odbiór

- Pracuj w osobnym worktree z aktualnego zdalnego head otwartego PR #40.
  Po merge użyj aktualnego main i nowego PR; zachowaj cudze zmiany.
- Wykonuj [procedurę jednej karty](../development.md). Dopuszczone zmiany
  kontraktów określa spec powyżej; ograniczenia zakończonej serii U03–U11
  dotyczą jej własnego zakresu.
- Uaktualniaj główną specyfikację i operations w karcie wdrażającej zachowanie.
  Obecny pakiet zmienia tylko dokumentację planowania.
- Każda karta kończy się sprawdzalnym wynikiem, bilansem kodu, commitem
  i terminalnym CI dla zdalnego SHA. Kończ po wskazanej karcie.
- Pełna bramka: `uv run --frozen python scripts/check_project.py --base-ref origin/main`
  po `uv sync --frozen`; w CI obowiązuje rzeczywisty SHA zdarzenia.
- Dla U12/U15/U16 odczytaj wszystkie eksporty i porównaj z bazą zadania
  przy tych samych metadanych. Dumpy porównuj semantycznie, z jawną
  normalizacją metadanych. Potwierdź niezmienność całego `data/`.
- Dla zmiany zachowania wykaż test przed/po. Usuwanie martwego kodu nie
  wymaga testów sprawdzających samą nieobecność nazw funkcji.
- Dowody zapisuj według reguł repozytorium. Sam plan wymaga kontroli linków,
  zgodności odwołań, `git diff --check` i CI, nie lokalnego builda niezmienionego kodu.

## Review Focus

- Żywe testy eksportów ukryte w plikach nazwanych review/staging: U12.
- Baseline v1 i bieżący v2, brak plików i symlinki po usunięciu legacy: U15.
- Atomowa publikacja eksportów po usunięciu writera źródeł: U15.
- Brzegi/otwory poligonów, nakładanie i manual Best: U16.
- Historyczny null, źródłowe EPSG i manual Best przy zmianie projekcji: U17.

## Punkt odniesienia planowania

Przegląd: `bd8f6d91b15d59b3874c6da71765a5b2de606ae0`, main
`ad5fa191a36d5a5f45f0b2de523bd39125827573`. To dowody analizy, nie przyszłe
stałe baseline. Produkcyjny Python: 10 682 linie fizyczne; importy/decyzje
3508, profiler/czytnik/CLI 661, naprawa TPN/helper 288. Razem kandydaci
U12 mają 4457 linii przed sprzątaniem zależności. Python PR względem main:
+1126 netto; SQL: +382. Komentarze/puste linie są wliczone. Bilans wykonania
obejmuje cały wynik, osobno testy i dokumentację.

Karty stosują zasadę z [PBI Authoring](https://asdlc.io/practices/pbi-authoring):
zakres, kontekst, zależności i obserwowalne kryteria odbioru.
