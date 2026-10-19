# Plan integracji TPN — weryfikacja dokumentacji

Data: 2026-10-19. Baza: aktualny main po fetch/pull,
`b98fd3febb400c7ee520046682c1bb16238429ee`.
Gałąź: `codex/tpn-sync-planning`.

## Zakres

Zapis historyczny kroku poprzedzającego PBI-095. Późniejsze przyjęcie
kierunku i doprecyzowanie kontraktu opisuje [odbiór PBI-095](PBI-095.md);
poniższe statusy i ograniczenia dotyczą wyłącznie ówczesnego planowania.

[Projekt](../tpn_sync_plan.md), [PBI-095–103](../tpn_sync_backlog.md),
indeks backlogu i context. Osobny krok planistyczny zamówiony przez
użytkownika; nie jest wykonaniem PBI-095. Wszystkie nowe karty są planowane.
Bez zmiany kodu, schematów, katalogu, spec, AGENTS i konfiguracji workflow.

API i wstępne porównanie sprawdzono na zachowanym lokalnie JSON; źródło,
metoda, ograniczenia i hashe są w projekcie. Pliki robocze w ignorowanym
build nie są wymagane do przeczytania projektu ani ustalenia dalszych prac.
Pierwszy import ma utrwalić snapshoty rozpatrywanych decyzji w Git.

## Weryfikacja

- `.venv/bin/python -m pytest tests/test_operational_docs.py tests/test_release_docs.py`:
  **5 passed**.
- Kontrola lokalnych odnośników planu/backlogu/indeksu/context: **63**
  poprawne przed dodaniem tego logu; dodatkowy odnośnik do logu sprawdzony.
- Kontrola kart: dokładnie PBI-095–103, bez duplikatów, wszystkie dziewięć
  ze statusem planowane; zależności i warunki odbioru zapisane w kartach.
- Ponowny odczyt `tpn-otwory-jaskin.json`: **1035 rekordów**, wszystkie
  zawierają GLOBALID/WER_LOK/UWAGI; SHA-256 zgodny z manifestem pobrania.
- Niezależny builder check świeżego agenta, bez kontekstu autora:
  **brak istotnych pytań przed planowaniem implementacji**.
- `git diff --check`: bez błędów. Przegląd zakresu: wyłącznie dokumentacja
  AS-DLC; brak zmian danych i kodu. Nie uruchamiano kampanii mutacyjnej
  ani dodatkowego builda eksportów dla tego kroku dokumentacyjnego.

## Dostarczenie i kontynuacja

Draft PR do main. Dokładny dostarczony SHA i wynik pełnego workflow validate
są wskazane w opisie PR; lokalne testy dokumentacji nie zastępują CI.
Nie wykonywać merge, tagu ani release w ramach tej dostawy.

Następny krok: uzgodnienie projektu, potem nadanie gotowości wyłącznie
PBI-095. Przed wykonaniem: świeży main, aktualny backlog i spec.
Dalsze karty nie są zgodą na wykonanie importu w tej sesji.

## Uzupełnienie do czystego kontekstu — 2026-10-19

Na polecenie użytkownika dodano [instrukcję przejęcia](../tpn_sync_handoff.md):
stan PR/gałęzi, kolejność dokumentów, dokładne parametry zapytania API,
polecenie pobrania jednej strony i wymagane kontrole kompletności.
JSON pozostał lokalnie poza Git. Instrukcja odróżnia odczyt bieżący od
historycznej migawki; do kontynuacji planowania nie wymaga build ani czatu.
Weryfikacja: **5 testów dokumentacji przeszło**, **78 lokalnych odnośników**
poprawnych, składnia polecenia Bash poprawna, endpoint i wszystkie osiem
parametrów zgodne z manifestem pierwotnego odczytu. Hash lokalnego JSON
zgodny z manifestem; `git diff --check` bez błędów. Zakres: tylko dokumenty.
Końcowy SHA/CI tego uzupełnienia również wskazuje opis PR #12.
