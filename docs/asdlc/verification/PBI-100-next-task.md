# Prompt do następnej sesji — wyłącznie PBI-101

```text
Pracuj w repozytorium:
/Users/dariuszlubomski/proj/gps-kataster-obiektow-tatr

Użyj $asdlc. Przejmij pracę z PR:
https://github.com/dlubom/gps-kataster-obiektow-tatr/pull/12

Nie polegaj na historii czatu. Sprawdź aktualny Git i PR.
Jeśli PR jest otwarty, kontynuuj na codex/tpn-sync-planning.
Jeśli został zmergowany, zacznij z aktualnego main, utwórz nową gałąź
oraz draft PR. Zachowaj cudze zmiany i nie wznawiaj gałęzi naprawczych.

Przeczytaj AGENTS.md, dokumenty kanoniczne, wszystkie tpn_sync_* w docs/asdlc/,
verification/PBI-095.md–PBI-100.md i manifest PBI-099. Wykonaj wyłącznie
aktualną kartę PBI-101: pierwsze uzgodnienie danych TPN, bez harmonogramu.
Korzystaj z CLI PBI-096–100; nie zakładaj historycznego build.

Pozyskaj i zweryfikuj NOWY kompletny snapshot API. Utrwal go w Git przed
zastosowaniem danych. Przygotuj jedną paczkę z aktualnego katalogu i stanu
przyjętego wyłącznie na origin/main. Historyczne liczby nie są celem importu.
Pokaż rzeczywiste różnice, kandydatów duplikatów oraz konkretne propozycje
po rekordzie. Istotne decyzje domenowe uzgodnij ze mną; nie podpisuj moim
imieniem decyzji. Produkcyjne approve/reject/defer stosuj dopiero po moim
jawnym rozstrzygnięciu konkretnych propozycji; spory mogą pozostać defer.

Manifest PBI-099 nadal może być pending. Sprawdź jego aktualny status
oraz preimages. Obecność lub commit manifestu nie są akceptacją. Migracje
auto→manual dopiero po mojej jawnej zgodzie na konkretne aktualne propozycje.
Brak zgody nie znosi ochrony GNSS/geodezji/manual ani nie pozwala zmienić best.
Nie omijaj strażnika PBI-099. Nie nadpisuj współrzędnych, wysokości, statusów,
dokładności i dat obecnych pomiarów. Nowe ustalenia TPN pozostają
nieweryfikowane; dodanie historii i wybór best to osobne decyzje.

Testuj najpierw na izolowanej kopii. Sprawdź dry-run/apply, pełne preflight,
idempotencję, zgodność końcowego diffu z decyzjami, brak pending i trwałą
kolejkę defer. Zachowaj poprzednie snapshoty, CSV/XLSX, pomiary i archiwa
rozstrzygnięć. Zmiana bazy lub edycja człowieka wymaga nowego review.

Pozostaw trwałe dowody PBI-101, zaktualizuj status i kontekst, wykonaj
commit/push i potwierdź wszystkie joby CI dokładnego końcowego SHA oraz
readback eksportów. Przygotuj jedną paczkę w draft PR do człowieka.
Zakończ po PBI-101. Bez merge, tagu, release, harmonogramu i rozpoczęcia
PBI-102. Na koniec napisz, co zostało, i podaj prompt następnego zadania.
```
