# AS-DLC backlog V1

Stan dokumentacji: 2026-10-21. Ten plik jest indeksem prac; wymagania są
w [specyfikacji](../../specyfikacja_gps_kataster_obiektow_tatr_v_2.md),
a bieżący kontekst w [context.md](context.md).
Nowy zakres wymaga polecenia użytkownika. Domyślnie realizujemy jedną kartę;
zasady weryfikacji i dostawy opisuje [runbook](remediation_runbook.md).

## Integracja publicznego API TPN — PBI-095–103

Statusy, zależności i kryteria odbioru utrzymujemy w jednym miejscu:
[backlog TPN](tpn_sync_backlog.md). [Handoff](tpn_sync_handoff.md) prowadzi
do instrukcji operatora i dowodów. Nie dublujemy tutaj kart ani wyników CI.

## PBI-104: Paczka danych w opisie każdego PR

Status: **wykonane — implementacja i pierwsza paczka odebrane w PR #12**.
[Dowody](verification/PBI-104.md),
[format paczki i publikacja](../release_artifacts.md#paczka-danych-w-opisie-pr).

Zakres i odbiór:

- [x] `pull_request` buduje dziewięć plików release z dokładnego
  syntetycznego merge, także dla draftów bez konfliktu.
- [x] ZIP zawiera manifest head/base/merge/run/attempt oraz sumy SHA-256;
  kontrolny odczyt potwierdza komplet i pochodzenie. Retencja: 14 dni.
- [x] Publisher używa zaufanego kodu gałęzi domyślnej i metadanych API,
  zachowuje opis autora oraz odrzuca nieaktualny SHA/run lub obcy PR.
- [x] Testy pakowania/publikacji i pierwszy odczyt ZIP/opisu PR przeszły.
  CI dostarczonego SHA jest wskazywane w PR.

Pierwszy wpis w PR #12 opublikowano przez kontrolowany bootstrap publishera.
Jego automatyczne działanie dla kolejnych PR wymaga instalacji workflow
na `main` przez ludzki merge. Oficjalny proces tagowanego release pozostaje
odrębny; ta karta nie uruchamia workflow TPN ani harmonogramu.

## Zakończone poprawki i wydania — PBI-087–094

| PBI | Wynik i dowody |
|---|---|
| [087](verification/PBI-087.md) | PL-0019: odrzucenie błędnego punktu PIG, PR #6 |
| [088](verification/PBI-088.md) | Mapy OSM w README PL/EN/SK, PR #7 |
| [089](verification/PBI-089.md) | README dla użytkowników i statystyki wydań |
| [090](verification/PBI-090.md) | Krótszy GPX i Excel Best/Full z historią pomiarów |
| [091](verification/PBI-091.md) | Nazwy obiektów w etykietach GPX |
| [092](verification/PBI-092.md) | Daty przed 1900 w Excelu jako tekst ISO |
| [093](verification/PBI-093.md) | Przygotowanie v1.1.0, PR #7 |
| [094](verification/PBI-094.md) | Przygotowanie v1.1.1 z poprawkami PR #9 |

Publikowane wersje opisuje [changelog](../../CHANGELOG.md).

## Naprawy main po przegladzie 2026-10-12

**PBI-078–086 zakończone**, PR #4 zmergowany do `main`; wydanie
[v1.0.3 odebrane](verification/v1.0.3.md). Brak gotowej karty tej serii.
[Plan i decyzja o porzuceniu starych gałęzi](remediation_plan.md),
[raport R1–R8](reviews/main-review-2026-10-12.md).
PBI-034–077 należą do porzuconej serii i nie oznaczają wdrożonych funkcji.

| PBI | Wynik i dowody |
|---|---|
| [078](verification/PBI-078.md) | Nowy plan od aktualnego main |
| [079](verification/PBI-079.md) | Blokada eksportów przy brakujących danych |
| [080](verification/PBI-080.md) | Odrzucanie powtórzonych kluczy YAML |
| [081](verification/PBI-081.md) | Preflight całej transakcji review przed zapisem |
| [082](verification/PBI-082.md) | Zachowanie i odtworzenie kontekstu pomiarów TPN |
| [083](verification/PBI-083.md) | Kategorie i ocena rozbieżności danych |
| [084](verification/PBI-084.md) | Odrzucanie NaN i Infinity |
| [085](verification/PBI-085.md) | Unikalne ID pomiarów w obiekcie |
| [086](verification/PBI-086.md) | Przenoszenie powiązań i walidacja symetrii |

## Historia V1 — PBI-001–033

Wszystkie poniższe karty wykonano w maju–lipcu 2026. Pełne historyczne
kryteria i protokoły zachowuje
[wersja backlogu sprzed porządkowania](https://github.com/dlubom/gps-kataster-obiektow-tatr/blob/7d970a4546568f08554730fa407cbe5d0867adda/docs/asdlc/backlog_v1.md).
Dostęp offline: `git show 7d970a4:docs/asdlc/backlog_v1.md`.
Są historią wykonania; bieżące wymagania określa specyfikacja.

| PBI | Zakres |
|---|---|
| 001 | Uporzadkowac strukture katalogow |
| 002 | Utworzyc minimalny projekt Pythonowy |
| 003 | Dodac konfiguracje prefixow |
| 004 | Zdefiniowac JSON Schema dla YAML |
| 005 | Dodac minimalne fixture'y domenowe |
| 006 | Wprowadzic konwersje WGS84 <-> EPSG:2180 |
| 007 | Zaimplementowac resolver prefixu |
| 008 | Dodac `scripts/assign_id.py` |
| 009 | Loader danych YAML |
| 010 | Reguly walidacji error/warning |
| 011 | Algorytm `best_measurement` |
| 012 | Profil danych PIG i TPN |
| 013 | Importer staging PIG |
| 014 | Importer staging TPN |
| 015 | Operator review dla staging |
| 016 | Build SQLite |
| 017 | Eksport `best-measurements` |
| 018 | Metadata release |
| 019 | CI walidacyjne |
| 020 | Build/release workflow |
| 021 | Dokumentacja operacyjna |
| 022 | Poprawic kategorie sztolni z TPN |
| 023 | Uporzadkowac zrodla i dokumentacje dla ludzi |
| 024 | Dopelnic znane brakujace obiekty |
| 025 | Rozstrzygnac wielootworowe przypadki i nowe pomiary |
| 026 | Wprowadzic testy mutacyjne |
| 027 | Wyjasnic `nieweryfikowany` w release |
| 028 | Udokumentowac kolumny release i dodac notatki do eksportow |
| 029 | Przestawic release na reczny semver tagowy |
| 030 | Uzupelnic wysokosc gornego Bandziocha |
| 031 | Ujednolicic dokumentacje release i licencji z aktualnym kodem |
| 032 | Przygotowac release `v1.0.2` |
| 033 | Przebudowac README dla uzytkownikow PL/EN/SK |
