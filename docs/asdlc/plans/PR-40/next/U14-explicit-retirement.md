# U14 — dopuść wyłącznie jawne wycofania

Czytaj [indeks](README.md), [spec bramki](spec.md) i [odbiór](../development.md).
Zależność: U13. Rzeczywiste rekordy nie są usuwane w ramach wdrożenia.

## Pliki i interfejs

Zmień `history.py`, `schema/history.sql`, `validator.py`, `retired_ids.py`,
`tests/test_history.py`, `tests/test_retired_ids.py`, `tests/test_production_entrypoints.py`
i dokumentację §9–11. Zachowaj publiczną bramkę `history_checked_catalog`.
Rozszerz `compare_history(baseline, dataset, *, retirements=(), connection=None)`
o jawne już sprawdzone wpisy kandydata; `check_history` czyta i weryfikuje
baseline/rejestr raz. Puste domyślne retirements nigdy nie osłabia ochrony.

## Kroki i kryteria

- [ ] RED: usunięcie jaskini bez otworów, relacji i nieprzywołanej publikacji
  bez wpisu daje odpowiednio `HISTORY_CAVE_DELETED`, `HISTORY_RELATION_DELETED`,
  `HISTORY_PUBLICATION_DELETED`. Zachowaj dotychczasowe kody obiektu/pomiaru.
- [ ] RED: poprawne wpisy umożliwiają dokładnie te ubytki. Usunięcie obiektu
  obejmuje lokalną historię, a samodzielny pomiar wymaga klucza z ownerem.
  Inny owner, przestarzały baseline, obcy commit, brak powodu i dodatkowy
  niewskazany ubytek nadal blokują całą operację.
- [ ] RED: po wycofaniu środkowego `m-002` stara lista `m-001,m-002,m-003`
  może stać się `m-001,m-003,m-004`. `m-003,m-001` i `m-004,m-001,m-003`
  nadal dają `HISTORY_ORDER_CHANGED`. Pozostający stary pomiar nie może
  zmienić geometrii/wysokości/datum przy okazji legalnego wycofania innego.
- [ ] Zastąp porównanie bezwzględnych indeksów porównaniem zachowanej
  sekwencji i dopisywania po niej. Rozszerz prosty anty-join o encje/rejestr;
  wykorzystaj istniejące połączenie, bez odtwarzania baz z dawnych wydań.
- [ ] Sprawdź manual Best, assigned_from_measurement_id, relacje, cytowania,
  przywołania załączników oraz usunięcie ostatniego pomiaru. Pozostające
  referencje muszą być poprawne; żadnego automatycznego wyboru nowego manual
  Best, przepinania odwołań, kasowania innych rekordów czy transferu pomiarów.
- [ ] Test publicznych CLI: validate, dump, Best, pełny build i preview
  stosują tę samą bramkę; błąd zachowuje istniejące wyjścia bajtowo. Test
  dwóch kolejnych PR dowodzi, że wpis przyjęty na main nie wymaga nowego
  upoważnienia przy każdym buildzie i nadal rezerwuje ID.
- [ ] `uv run --frozen pytest -q tests/test_history.py tests/test_retired_ids.py tests/test_production_entrypoints.py tests/test_ci_baseline.py tests/test_pr_preview.py`;
  pełna bramka, celowane mutacje bramki i eksporty przed/po na niezmienionym
  katalogu. Dokumentacja pokazuje usunięcie + wpis + naprawę referencji w jednym PR.
- [ ] Commit `feat: require explicit catalogue retirements (PBI-119 U14)`;
  dostarcz, odbierz i zakończ po U14. Nie dodawaj ogólnego skip-history/force.
