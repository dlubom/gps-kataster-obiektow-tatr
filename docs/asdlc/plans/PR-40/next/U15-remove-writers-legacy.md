# U15 — usuń nieużywane zapisy i stare wejścia

Czytaj [indeks](README.md), [spec](spec.md) i [odbiór](../development.md).
Zależność: U12. Aktualny katalog zachowuje format v2; rejestr ID i nowe
zasady usuwania pozostają poza zakresem.

## Pliki i interfejs

Zmień `catalog_records.py`, `postgres.py`, `validator.py`, `data_loader.py`
oraz testy modeli, faz i fabryki `tests/{sql_test_support,export_test_support}.py`.
Usuń `SourceDataset`, `source_dataset`, `write_dataset`/`WriteResult`,
`open_source_proposal` i ścieżki bieżącego legacy/proposal, o ile po U12
nie mają już produkcyjnych odbiorców. Oddziel historyczne czytanie od
publicznego wejścia; zachowaj rzeczywiste testy baseline v1/v2.

Wynik: `history_checked_catalog` i `ExportData` zachowują kontrakt, a żadne
pozostające narzędzie katalogu nie przepisuje jego źródłowych YAML.
`_exchange_directories` ma odbiorcę w publikacji eksportów: zachowaj go przy
właścicielu tej publikacji. Nie kasuj go razem z writerem źródeł.

## Kroki i kryteria

- [ ] Przejrzyj graf produkcyjnych wywołań po U12. Ustal minimalne
  funkcje/schematy potrzebne wyłącznie do zaufanej historii i ich odbiorców.
- [ ] Przełącz testy żywych zachowań na jawne fixtures v2. Test historycznej
  migracji pozostaje testem starego baseline, nie sposobem przygotowania
  każdego bieżącego eksportu. Usuń testy wycofanych możliwości zapisu.
- [ ] Usuń martwe ścieżki bez aliasów/adopcji legacy przy zwykłym buildzie.
  Nie dopisuj ORM ani nowego formatu pośredniego. Pełne schematy JSON usuń
  tylko tam, gdzie nie czyta ich historyczny adapter; zależności zgodnie z użyciem.
- [ ] Zachowaj typy przed coercion SQL, źródłowe CRS, marker, kontrolę
  kompletności, duplikaty YAML, limity wejścia i blokady symlinków. Zwykły
  build przy niepoprawnym wejściu odmawia przed zapisem wyjścia.
- [ ] Publiczne CLI odrzucają bieżące wejście legacy; starszy zaakceptowany
  baseline pozostaje czytelny. Zachowaj obecne błędy historii dla usunięcia
  obiektu/pomiaru, zmiany chronionych wartości, kolejności i braku baseline.
- [ ] `uv run --frozen pytest -q tests/test_history.py tests/test_catalog_source_model.py tests/test_catalog_input_contract.py tests/test_production_entrypoints.py tests/test_review_output_safety.py tests/test_catalog_publication_regressions.py`;
  pełna bramka i pełne porównanie eksportów. Hash `data/` bez zmian.
- [ ] Zaktualizuj główną spec i operations. Podaj bilans całego kodu wraz
  z ewentualnymi przeniesieniami helperów i pozostałym kosztem historii.
- [ ] Commit `refactor: keep catalogue tools read-only (PBI-119 U15)`;
  dostarcz, odbierz i zakończ po U15.
