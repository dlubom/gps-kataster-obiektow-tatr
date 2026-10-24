# PBI-114 — dodatkowe pliki GPX według grup dolin

> **For agentic workers:** Use superpowers:executing-plans for this single
> implementation step. The accepted scope below is the design and execution brief.

**Goal:** rozwiązać issue [#20](https://github.com/dlubom/gps-kataster-obiektow-tatr/issues/20)
przez trzy dodatkowe GPX do 500 waypointów, zachowując pełny `best-measurements.gpx`.

**Architecture:** raz wybieramy dotychczasowe Best, klasyfikujemy ich współrzędne
przez istniejący `PrefixResolver` i zapisujemy podzbiory tym samym writerem GPX.
Wydanie i podgląd PR korzystają z tej samej listy artefaktów.

**Tech Stack:** istniejący Python 3.12, PyShp/PyProj, ElementTree i pytest;
bez nowych zależności i zmian schematu lub danych.

**Spec:** §4, §5.4 i §13 specyfikacji projektu; poniższy projekt zatwierdzony
przez użytkownika 24.10.2026, z ponownym podkreśleniem zachowania pełnego GPX.

## Zatwierdzony projekt

| Dodatkowy plik | Regiony położenia aktualnego Best | Stan bazy: punkty |
|---|---|---:|
| `chocholowska-lejowa-koscieliska.gpx` | CHZ, CHW, LEJ, KSZ, KSW | 488 |
| `mietusia-sucha-woda.gpx` | MTZ, MTW, STN, MLZ, MLW, BRA, STR, DZI, BIA, BYZ, BYW, OLC, SUW | 481 |
| `pozostale-pl-sk.gpx` | PL, SK poza polygonami dolin | 57 |

Suma to 1026 punktów bazy `26850e6a82220ad4a11e446b177512a274ed82fe`.
Liczby opisują tę rewizję; nie są stałymi eksportera. Wschód i zachód każdej
doliny pozostają razem. Każdy punkt pełnego GPX trafia do dokładnie jednego
dodatkowego pliku, z identycznymi polami waypointu i tym samym wybranym pomiarem.

Rozważano 15/20 plików dolinowych i prostokątne pasy. Użytkownik wybrał
łączenie całych sąsiednich dolin w trzy grupy; pasy rozcinające doliny odrzucił.

## Global Constraints

- `best-measurements.gpx` zachowuje nazwę, komplet punktów i dotychczasową treść
  przy tym samym wejściu/czasie; pozostałe formaty i `metadata.json` bez zmiany kontraktu.
- Grupowanie wynika ze współrzędnych wskazanego Best oraz bieżących polygonów,
  nie z trwałego prefiksu ID; nie zmienia ID, pomiarów ani Best w YAML.
- Limit 500 dotyczy każdego dodatkowego pliku; pełny GPX nie ma tego limitu.
- Decyzja wykonawcza: przekroczenie limitu lub nierozpoznany region daje
  czytelny błąd przed zapisem plików eksportu. Nie obcinamy i nie dzielimy
  automatycznie dolin; większy katalog wymaga ponownego uzgodnienia grup.
  Builder może wcześniej zbudować SQLite, ale nie publikuje niepełnej paczki.
- Powstają wszystkie trzy dodatkowe pliki, także puste dla małego wejścia.
- Bez merge, taga, nowej wersji i publikacji; dostarczenie jako draft PR.

## Review Focus

- Historyczny prefiks albo pierwszy pomiar nie mogą skierować punktu do złej grupy.
- Powtarzające się nazwy punktów nie mogą powodować ich usuwania.
- Granica 500/501: brak cichego obcięcia i brak nadpisania poprzednich eksportów po błędzie.
- Pusty zbiór oraz puste grupy pozostają prawidłowym GPX i mają stałe nazwy plików.
- Nowe pliki muszą przejść od API przez CLI i builder do podglądu PR i listy plików wydania.

## Task 1: eksport, dystrybucja i odbiór

**Files:** `best_measurements_export.py`, `release_artifacts.py`, oba CLI eksportu/buildu,
`release.yml`, testy eksportów/release/preview, README PL/EN/SK, dokumentacja
artefaktów, spec, backlog/context i `verification/PBI-114.md`.

**Interfaces:** `BestMeasurementsExportResult.grouped_gpx_paths: tuple[Path, ...]`;
`GpxGroupingError(ValueError)` dla błędów grupowania; istniejące API pełnego
eksportu i buildera pozostaje kompatybilne w użyciu.

- [x] Testy RED: trzy grupy z wszystkich 20 regionów, bieżący Best zamiast ID/historii,
  pełna zgodność waypointów, limit 500/501, puste dane, pliki w builderze/preview/CLI.
- [x] Minimalna implementacja i GREEN; czytelna diagnostyka błędu w obu CLI.
- [x] Dodać pliki do wydania i opisać ich zasięg w README PL/EN/SK oraz spec/docs.
- [x] Ruff, pełne pytest, walidacja YAML, pełny build i niezależny odczyt wszystkich
  artefaktów; pełny GPX bajtowo zgodny z bazą przy tym samym czasie.
- [x] Mutacje grupowania/limitu/dystrybucji, review, identyczny manifest danych.
- [x] Commit/push, draft PR [#32](https://github.com/dlubom/gps-kataster-obiektow-tatr/pull/32)
  powiązany z #20 i log odbioru w repozytorium. Odbiór terminalnego CI końcowego
  SHA i pobranej paczki podglądu wskazuje opis PR #32.
