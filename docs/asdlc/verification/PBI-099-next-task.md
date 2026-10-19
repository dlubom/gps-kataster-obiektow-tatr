# Prompt do następnej sesji — wyłącznie PBI-100

```text
Pracuj w repozytorium:
/Users/dariuszlubomski/proj/gps-kataster-obiektow-tatr

Użyj $asdlc. Przejmij pracę z PR:
https://github.com/dlubom/gps-kataster-obiektow-tatr/pull/12

Nie polegaj na historii czatu. Sprawdź aktualny Git i PR.
Jeśli PR jest otwarty, kontynuuj na codex/tpn-sync-planning.
Jeśli został zmergowany, zacznij z aktualnego main,
utwórz nową gałąź i draft PR. Zachowaj cudze zmiany.

Przeczytaj AGENTS.md, dokumenty kanoniczne, wszystkie tpn_sync_*
w docs/asdlc/ i verification/PBI-095.md–PBI-099.md oraz manifest PBI-099.

Wykonaj wyłącznie PBI-100: decyzje po rekordzie i idempotentne
zastosowanie paczki. Zrealizuj wszystkie kryteria aktualnej karty:
ścisły format i walidacja, związanie decyzji z rewizją/preimages/hashami,
łączne planowanie akcji jednego obiektu i ID całej partii, ochrona
historii/wysokości/statusów, pełny preflight i odporność na awarię zapisu,
idempotencja, zgodność dry-run/apply oraz bramka pending/defer.

Wykorzystaj strażnik PBI-099. Brak zgody na migrację auto→manual
nie znosi ochrony GNSS/geodezji/manual ani nie pozwala zmienić best.
Sprawdź aktualny status manifestu; jego obecność lub commit nie jest
akceptacją. Migracje wykonuj dopiero po mojej jawnej akceptacji
konkretnych propozycji i sprawdzeniu aktualności ich preimages.
Istotne decyzje domenowe uzgodnij ze mną; rutynowe szczegóły rozwiąż sam.

Testuj na fixture'ach i izolowanych kopiach. Bez pierwszego importu
produkcyjnej paczki PBI-101 i bez stosowania przykładowych decyzji do
katalogu. Nie zmieniaj współrzędnych, statusów ani dokładności obecnych
pomiarów. Zachowaj snapshoty i źródła CSV/XLSX. Korzystaj ze snapshotu
w Git oraz CLI PBI-096–099, bez zakładania historycznego build.
Nie uruchamiaj harmonogramu ani porzuconych gałęzi naprawczych.

Zweryfikuj PBI-100, pozostaw trwałe dowody, zaktualizuj status i kontekst,
wykonaj commit/push i potwierdź wszystkie joby CI dokładnego końcowego SHA.
Zakończ po PBI-100. Bez merge, tagu, release i rozpoczęcia PBI-101.
Na koniec podaj analogiczny prompt do następnego zadania.
```
