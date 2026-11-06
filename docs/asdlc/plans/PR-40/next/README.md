# PR #40 — plan wycofania dawnych ścieżek i ochrony ID

> **Dla wykonawcy:** realizuj jedną wskazaną kartę, używając
> `superpowers:executing-plans`. Przygotowanie planu nie zleca implementacji.

**Cel:** ograniczyć program do odczytu YAML, walidacji i eksportów oraz
umożliwić jawne wycofanie rekordu bez ponownego nadania jego ID.

**Architektura:** jeden bieżący format źródła, tymczasowy PostgreSQL/PostGIS,
porównanie z zaakceptowanym Git i mały rejestr wycofań. Historyczny adapter
pozostaje wyłącznie po stronie odczytu starszego baseline.

**Stos:** obecny Python/uv, YAML, PostgreSQL 18/PostGIS 3.6, GDAL; bez nowych
bibliotek runtime. **Spec:** [kontrakt tej serii](spec.md).

## Zakres i stan

Użytkownik zaakceptował kierunek 2026-11-06 i potwierdził, że jawne wycofanie
może obejmować pojedynczy pomiar. Szczegóły rejestru są propozycją wykonawczą
do review przed U13. U01–U11 pozostają zakończone i nie są powtarzane.
Nowe karty kontynuują PBI-119; U13/U14 obejmują również issue #33.

| Karta | Wynik | Status | Zależności |
|---|---|---|---|
| [U12](U12-remove-imports.md) | Usunięte zakończone importy, profiler i naprawa TPN | gotowe do zlecenia | brak |
| [U13](U13-reserve-retired-ids.md) | Rejestr, dawne wycofania i trwała rezerwacja ID | do review kontraktu | U12 |
| [U14](U14-explicit-retirement.md) | Jawne usunięcie encji/pomiaru oraz pełna bramka ubytków | oczekuje | U13 |
| [U15](U15-remove-writers-legacy.md) | Jeden bieżący format, usunięte programowe zapisy katalogu | oczekuje | U14 |
| [U16](U16-postgis-validation.md) | Jeden silnik walidacji geografii katalogu | oczekuje | U15 |
| [U17](U17-export-read-model.md) | Decyzja o skróceniu drogi SQL → ExportData | oczekuje | U16 |

To jedyny rejestr statusów U12–U17. `gotowe do zlecenia` nie oznacza rozpoczęcia.
Nie zmieniamy wymaganego CI ani polityki merge/tag/release.

## Globalne ograniczenia i odbiór

- Pracuj w osobnym worktree z aktualnego zdalnego head otwartego PR #40.
  Po merge użyj aktualnego main i nowego PR; zachowaj cudze zmiany.
- Wykonuj [procedurę jednej karty](../development.md). Dla tej serii
  dopuszczone zmiany kontraktu określa spec powyżej; ograniczenia starej
  serii U03–U11 dotyczą jej własnego zakresu, nie uchylają nowego zlecenia.
- Uaktualniaj główną specyfikację i operations w karcie wdrażającej zachowanie.
  Obecny pakiet zmienia tylko dokumentację planowania.
- Każda karta kończy się własnym sprawdzalnym wynikiem, bilansem kodu,
  commitem i terminalnym CI dla zdalnego SHA. Kończ po wskazanej karcie.
- Pełna bramka: `uv run --frozen python scripts/check_project.py --base-ref origin/main`
  po `uv sync --frozen`; w CI obowiązuje rzeczywisty SHA zdarzenia.
- Dla U12–U16 odczytaj wszystkie eksporty i porównaj z bazą zadania przy tych
  samych metadanych; przy U13 zmiana znacznika/rejestru nie zmienia danych
  eksportowanych. Dumpy porównuj semantycznie, z jawną normalizacją metadanych.
- Dla błędu/nowej ochrony wykaż RED → GREEN. Usuwanie martwego kodu nie
  wymaga testów sprawdzających samą nieobecność nazw funkcji.
- Zapisuj trwałe dowody zgodnie z regułami repozytorium, bez kopiowania
  starych wyników jako nowych. Przygotowanie planu wymaga linków, zgodności
  odwołań, `git diff --check` i CI, nie lokalnego builda niezmienionego kodu.

## Review Focus

- Usunięty najwyższy numer oraz ręcznie ponownie wpisane ID: U13.
- Brak rejestru v3, starszy baseline bez rejestru i obcy commit źródłowy: U13/U14.
- Legalne usunięcie środka historii, manual Best i nielegalny drugi ubytek: U14.
- Test/fabryka zależna od usuniętego writera oraz ochrona katalogu eksportu: U15.
- Historyczny null, źródłowe EPSG i manual Best przy zmianie projekcji: U17.

## Punkt odniesienia planowania

Przegląd: `bd8f6d91b15d59b3874c6da71765a5b2de606ae0`, main
`ad5fa191a36d5a5f45f0b2de523bd39125827573`. To dowody analizy, nie przyszłe
stałe baseline. Produkcyjny Python: 10 682 linie fizyczne; importy/decyzje
3508, profiler/czytnik/CLI 661, naprawa TPN/helper 288. Razem kandydaci
U12 mają 4457 linii przed sprzątaniem reszty i dodaniem nowych zabezpieczeń.
Python PR względem main: +1126 netto; SQL: +382. Komentarze/puste linie są
wliczone. Bilans wykonania musi obejmować cały wynik, osobno testy i docs.

Karty stosują zasadę z [PBI Authoring](https://asdlc.io/practices/pbi-authoring):
zakres, kontekst, zależności i obserwowalne kryteria odbioru.
