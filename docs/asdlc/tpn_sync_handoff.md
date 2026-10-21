# Integracja TPN — start pracy

Aktualny zakres i odbiór: [backlog TPN](tpn_sync_backlog.md).
Stan katalogu i PR: [context.md](context.md).

## Dokumenty według zadania

| Potrzeba | Dokument |
|---|---|
| Reguły tożsamości, dat, ochrony i decyzji | [Kontrakt](tpn_sync_contract.md), [przykłady](tpn_sync_examples.md) |
| Porównanie snapshotów i stanu | [Porównanie](tpn_sync_comparison.md) |
| Kandydaci duplikatów i nowych obiektów | [Kwalifikacja](tpn_sync_candidates.md) |
| Ochrona historii i best | [Ochrona best](tpn_sync_best_protection.md) |
| Przygotowanie, zastosowanie i kontrola decyzji | [CLI paczki](tpn_sync_decisions.md) |
| Workflow ręczny, miesięczny i odbiór produkcyjny | [Instrukcja operatora](tpn_sync_workflow.md) |
| Dokładność wyliczeń między systemami | [Precyzja pochodnych](tpn_sync_derived_precision.md) |
| Uzasadnienie pierwotnego projektu | [Plan z 2026-10-19](tpn_sync_plan.md) |

## Początek sesji

Sprawdź `git status`, pobierz `origin` i odczytaj live stan wskazanego PR.
Dla nowej pracy zacznij z aktualnego `main`; przy kontynuacji otwartego PR
pracuj na jego gałęzi, zachowując cudze zmiany. Wykonuj tylko zlecony zakres.

Publiczna warstwa źródłowa:
[Topografia___wektor_MIL1 / Jaskinie / 6](https://gis.tpn.pl/server/rest/services/Topografia___wektor_MIL1/MapServer/6).
Pełny snapshot pobiera i sprawdza `scripts/fetch_tpn_snapshot.py`;
[przykłady CLI i dowody](verification/PBI-096.md). Nie zastępuj go ręcznie
złożonymi stronami API ani lokalnym JSON bez kontroli kompletności.
Brak historycznej kopii JSON na komputerze nie blokuje pracy.

Dla istniejącej paczki `pbi-101-20261019` kontrola używa utrwalonych wejść:

```bash
uv run python scripts/review_tpn_batch.py check --batch-id pbi-101-20261019
```

Pełne opcje, preflight i zastosowanie opisuje [instrukcja CLI](tpn_sync_decisions.md).
Nowy GLOBALID nie oznacza automatycznie nowego otworu. Zapis pomiaru,
wybór best i decyzja o tożsamości są osobnymi rozstrzygnięciami człowieka.

## Pliki będące wejściem walidacji

`tpn_sync_contract.md` jest hashowaną polityką. **Nawet redakcyjna zmiana
jego bajtów wymaga jawnej migracji stanu**; nie poprawiaj go przy sprzątaniu
tekstu. Archiwalne kopie polityki i `verification/PBI-101-review/superseded-v1/`
są niezmiennymi zapisami dawnego stanu. Ich historyczne odsyłacze należy
czytać w kontekście commitu archiwizacji.

Zachowaj też dokładne ścieżki i bajty wejść kontroli danych:

- `verification/PBI-099-protection-manifest.json`
- `verification/PBI-099-manual-selection.json`
- `verification/PBI-101-D26-resolution.json`
- `verification/PBI-101-review/remaining-26.json`
- `verification/PBI-101-catalog-notes.json`

Snapshoty, decyzje, receipty, preimages i patche audytowe w `data/` oraz
`verification/` są dowodami odtwarzania, nie nadmiarową dokumentacją.
Pierwotne odroczenia i późniejsze decyzje D26 mają pozostać rozróżnialne.

## Dostawa PR #12 i dalszy odbiór

[Warunek zachowania historii przy merge](verification/PBI-101-D26.md#warunek-zachowania-historii-przy-merge)
wymaga, by przodkami HEAD pozostały commity `83e1d383…`, `d1f958bc…`
i `8c18ee57…`. Squash/rebase zastępujący tę historię psuje odtworzenie
kontroli. Merge wykonuje wyłącznie człowiek na osobne polecenie.

Następny etap to [produkcyjny odbiór PBI-102](verification/PBI-102.md),
po spełnieniu warunków operatora. Dopiero po nim można osobno zatwierdzić
aktywację i [odbiór PBI-103](verification/PBI-103.md).
Nie włączaj `TPN_MONTHLY_ENABLED` ani uprawnień Actions na podstawie samego
istnienia kodu, kontraktu lub pomyślnego testu offline.
