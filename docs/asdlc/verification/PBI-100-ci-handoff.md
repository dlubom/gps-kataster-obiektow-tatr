# PBI-100 — dokończenie odbioru hosted CI

Kod jest dostarczony, ale **PBI-100 nie jest odebrane**. Lokalnie 1077 testów,
15/15 mutacji, Ruff/validate/build i readback 10 artefaktów PASS. Dane/config
2048 plików i manifest PBI-099 zachowane. Czysty klon kodu przeszedł CLI
oraz wspólną bazę preimages. Nie rozpoczynać PBI-101.

Kod: `77025edef4ea573b6641ea2593bc94f248b88124`.
[CI kodu](https://github.com/dlubom/gps-kataster-obiektow-tatr/actions/runs/39278211636):
2026-10-19 około 15:42 UTC nadal in_progress, jedyny job
Validate code and data in_progress, brak kroków/logów w API. Wcześniej queued.
Starszy run `39277286418` dla c572070 nadal był odczytywany jako in_progress;
normalne anulowanie zwróciło „completed”, force-cancel HTTP 409 „not in progress”.
Nie ma potwierdzenia, że którekolwiek anulowanie zostało zastosowane.
Odczyty REST/GraphQL/connectora i świeże nagłówki nie rozstrzygnęły sprzeczności.
Nie zmieniano workflow ani kodu w celu obchodzenia CI.

Końcowy commit tego handoffu także wymaga CI. Jego SHA i bieżący URL/wynik
są w opisie PR #12. Nie zastępować hosted CI wynikami lokalnymi.
Po potwierdzonym success wszystkich jobów dokładnego końcowego SHA:
zapisać odbiór, zmienić status PBI-100 w backlogach/context, commit/push
tej dokumentacji, potwierdzić także jego końcowe CI i dopiero zakończyć.
Nie rozpoczynać PBI-101, merge, tagu, release ani harmonogramu.

## Prompt kontynuacji

```text
Pracuj w /Users/dariuszlubomski/proj/gps-kataster-obiektow-tatr.
Użyj $asdlc. Przejmij PR https://github.com/dlubom/gps-kataster-obiektow-tatr/pull/12.
Nie polegaj na historii czatu. Sprawdź aktualny Git/PR i zachowaj cudze zmiany.
Otwarty PR: kontynuuj codex/tpn-sync-planning. Zmergowany: aktualny main,
nowa gałąź/draft PR, jeśli potrzeba zmian dokumentacji.

Przeczytaj AGENTS.md, dokumenty kanoniczne, wszystkie tpn_sync_* oraz
verification/PBI-100.md, PBI-100-ci-handoff.md i manifest PBI-099.
Dokończ WYŁĄCZNIE odbiór PBI-100: sprawdź rzeczywiste CI aktualnego SHA,
wszystkie joby i logi. Statusy były opóźnione/sprzeczne; nie zakładaj sukcesu.
W razie awarii rozróżnij kod od środowiska, odtwórz problem na izolowanej
fixture i napraw tylko zakres PBI-100. Nie powtarzaj implementacji bez dowodu.

Po success zapisz trwały odbiór, status i kontekst, commit/push oraz potwierdź
wszystkie joby CI dokładnego końcowego SHA, także commitu dokumentacji.
Nie stosuj decyzji do produkcyjnego katalogu i nie wykonuj migracji auto→manual.
Manifest pozostaje pending bez jawnej zgody; ochrona PBI-099 działa nadal.
Zakończ po PBI-100. Bez PBI-101, merge, tagu, release i harmonogramu.
Na koniec podaj gotowy prompt PBI-101 i napisz, co zostało.
```
