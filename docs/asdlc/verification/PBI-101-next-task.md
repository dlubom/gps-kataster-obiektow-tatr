# Kontynuacja — wyłącznie niedokończone PBI-101

```text
Pracuj w /Users/dariuszlubomski/proj/gps-kataster-obiektow-tatr. Użyj $asdlc.
Przejmij PR https://github.com/dlubom/gps-kataster-obiektow-tatr/pull/12.
Sprawdź aktualny Git/PR, fetch origin i zachowaj cudze zmiany. Otwarty PR:
kontynuuj codex/tpn-sync-planning. Nie polegaj na historii czatu ani build.

Przeczytaj AGENTS, dokumenty kanoniczne, wszystkie tpn_sync_*, odbiory
095–101, PBI-101-review/review.md, recommendations.json i warunkowy diff,
aktywną paczkę data/source_reviews/tpn/pbi-101-20261019, manifest 099
i PBI-101-ci-handoff.md z rzeczywistym błędem hosted CI.
PBI-100 jest odebrane. PBI-101 pozostaje w toku: użytkownik po obejrzeniu
konkretnych propozycji polecił „Na razie pozostaw wszystko pending”.
640 decyzji ma autora/czas null. Nie ma produkcyjnego apply ani stanu źródła.
Nie zmieniaj tego polecenia w samodzielne approve/reject/defer.

Najpierw odtwórz read-only rozbieżność hosted CI z handoffu: Linux
zwraca changes evidence/schema mismatch przed kontrolą pending, Mac
odtwarza raport kanonicznie i zwraca pending blocks merge. Pozyskaj diff
expected/actual i dowód przyczyny; nie zakładaj, że CI jest czerwone tylko
z powodu pending. Nie zmieniaj polityki ani narzędzi 096–100 i nie osłabiaj
hashów/tolerancji bez jawnego uzgodnienia potrzebnej naprawy. Zachowaj
immutable snapshot/changes i wszystkie decyzje pending. Użytkownik dotąd
nie zatwierdził ani działań domenowych, ani rozszerzenia zakresu naprawy.

Przed zastosowaniem przedstaw istniejące konkretne propozycje A001–A578, B001–B031,
C001–C005, D001–D026 i uzyskaj jawne decyzje użytkownika dla wskazanych ID
lub zakresów i wyjątków. Dodanie pomiaru i keep/select_new rozstrzygaj osobno.
Nie podpisuj decyzji imieniem użytkownika. Manifest 099 pozostaje pending;
chronione auto→manual wymaga osobnej zgody i aktualnych preimages.

Nowy pełny snapshot pbi-101-live-20261019 jest utrwalony w Git od commitu
60afeca2d17bbc4b5aa690abc83da1d25d89a506. Nie pobieraj ponownie pod tym ID,
nie zastępuj wejść ani decyzji otwartego PR. Sprawdź verify, bazę paczki,
preimages i origin/main; przyjęty stan czytaj wyłącznie z main. Jeżeli
zmieniła się podstawa albo użytkownik chce nowszy snapshot, jawnie odśwież
review i pokaż nowe propozycje; stare dowody zachowaj. Po merge PR z pending
nie zakładaj gotowości — sprawdź stan i uzgodnij dalszą ścieżkę PBI-101.

Po decyzjach użyj CLI 096–100; najpierw testy rzeczywistych decyzji na
izolowanej kopii: dry-run/apply, pełny preflight, idempotencja, zgodność
diffu, brak pending i trwała kolejka defer. Zachowaj całą dawną historię,
wysokości, daty, dokładności, statusy, źródła oraz chronione best.
Następnie zastosuj tylko jawnie rozstrzygnięte działania do produkcyjnej
gałęzi, zapisz dowody/status/context, commit/push, sprawdź wszystkie joby,
kroki i pełne logi dokładnego końcowego SHA oraz readback eksportów.

Zakończ po PBI-101. Bez PBI-102, merge, tagu, release i harmonogramu.
Na końcu podaj pozostałe zadania i prompt kolejnego kroku.
```
