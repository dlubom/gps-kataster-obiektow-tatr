# U13 — zarezerwuj wycofane ID

Czytaj [indeks](README.md), [spec rejestru](spec.md) i [odbiór](../development.md).
Zależność: U12 i review kontraktu. Ta karta jeszcze nie zezwala na nowe
usunięcie zaakceptowanego obiektu/pomiaru; istniejąca blokada pozostaje do U14.

## Pliki i interfejs

Utwórz `src/gps_kataster_obiektow_tatr/retired_ids.py`, `data/retired_ids.yml`
i `tests/test_retired_ids.py`. Zmień `data_loader.py`, `history.py`,
`validator.py`, `scripts/assign_id.py`, `data/catalog.json`, `schema/CHANGELOG.md`
oraz fabryki fixtures v3. Wykorzystaj istniejący `IdSequence.reserved_ids`.

Nowy moduł posiada niezmienne `RetiredId` z polami ze spec i
`load_retired_ids(path: Path) -> tuple[RetiredId, ...]` oraz
`reserved_ids(entries, *, kind, object_id=None) -> frozenset[str]`.
Znaczenie argumentów/typów opisuje spec. Walidator przekłada kontrolowane
błędy odczytu na `RETIRED_IDS_INVALID`, a kolizję aktywnego ID na `RETIRED_ID_REUSED`.
Generator przyjmuje rejestr jawnie; CLI `--retired-ids` domyślnie wskazuje
`objects_dir.parent / 'retired_ids.yml'`, także dla niestandardowej kopii danych.

## Kroki i kryteria

- [ ] Odtwórz brak rezerwacji: aktywne `KSW-0001`, wycofane `KSW-0002`
  muszą dać `KSW-0003`. Test ręcznego ponownego wpisania `KSW-0002` ma
  zgłosić `RETIRED_ID_REUSED`; inne aktywne ID pozostają legalne.
- [ ] Dodaj przypadki duplikatów, brak/plik/symlink, whitespace reason,
  nieznanych pól, typów, SHA, lokalnych `m-001` dwóch obiektów, wszystkich
  rodzajów encji, wycofanego maksimum, pustej przestrzeni i `9999 → 10000`.
- [ ] Wdroż parser i kontrolę aktywne/wycofane bez nowej zależności. Bieżący
  format staje się v3; publiczne CLI odrzucają stare kandydaty. Adapter
  zaakceptowanej historii przyjmuje v1/v2 bez rejestru i kompletne v3.
  Dodaj test braku rejestru v3 oraz niezmienionej poprawności baseline v1/v2.
- [ ] Rozszerz ekstrakcję Git o rejestr. Zaakceptowane wpisy nie mogą zniknąć
  ani zmienić pól chronionych; tekst reason można doprecyzować. Nowy wpis
  wymaga zaakceptowanego źródłowego commita i rzeczywistej tożsamości.
  Użyj danych wejściowych bramki, nie drugiego skanu katalogu w każdym CLI.
- [ ] Test rzeczywistego merge: ID istniejące wyłącznie w pośrednim commicie
  bocznej gałęzi, usunięte przed jej scaleniem, nie staje się rezerwacją.
  Ten commit nie może autoryzować nowego source_commit. Audyt i bramka
  korzystają z tego samego zbioru `--first-parent` opisanego w spec.
- [ ] Przejrzyj zaakceptowaną historię main i oficjalnych wydań. Uzupełnij
  dawne wycofania zgodnie ze spec; zweryfikuj przykłady issue #33. Zachowaj
  zwięzły manifest provenance w `docs/asdlc/verification/PBI-119-retired-ids.md`.
  Nie wybieraj następcy ani nie zmieniaj aktywnego rekordu przy niepewności.
  Nie przedstawiaj niepełnego audytu jako ochrony wszystkich dawnych ID.
- [ ] Uruchom `uv run --frozen pytest -q tests/test_retired_ids.py tests/test_assign_id.py tests/test_history.py tests/test_catalog_input_contract.py tests/test_production_entrypoints.py`.
  Pełna bramka i odbiór eksportów. Jedynymi zmianami danych są nowy rejestr
  i znacznik v3; cztery katalogi encji i archiwalne źródła zachowują bajty.
- [ ] Uaktualnij §5/§10/§18 spec, operations i stan issue #33 w kontekście.
  Commit `feat: reserve retired catalogue identifiers (PBI-119 U13)`;
  dostarcz, odbierz i zakończ po U13.
