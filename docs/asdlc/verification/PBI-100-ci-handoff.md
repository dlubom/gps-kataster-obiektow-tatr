# PBI-100 — odbiór hosted CI zakończony

Data: 2026-10-19. Status: **wykonane**. Ten odbiór zastępuje wcześniejszy
handoff oczekujący na CI. [Pełna weryfikacja PBI-100](PBI-100.md).
Nie rozpoczęto PBI-101; [gotowy prompt osobnego zlecenia](PBI-100-next-task.md).

## Stan przejęcia i rzeczywiste wyniki

PR #12: OPEN/draft, `codex/tpn-sync-planning` → `main`.
Po fetch czysty HEAD = origin = head PR:
`acf00addd4515791ab40df9f308d706f9324ace8`.
Baza main: `b98fd3febb400c7ee520046682c1bb16238429ee`.
Nie zastępowano istniejącej implementacji ani cudzych zmian.

Odczytano REST runs, pełną listę jobs z `filter=all`, kroki i logi, a dla
head dodatkowo check-runs i commit statuses. Workflow `validate` ma jeden
job `Validate code and data`; innych checków head ani legacy statuses nie ma.
Każdy poniższy run: attempt 1, **completed/success**, **1/1 job oraz
14/14 kroków success** (włącznie z setup i cleanup; żaden krok niepominięty).

| Head SHA | Run / job | Wynik z logów |
|---|---|---|
| `c572070017cd4664ddc3d3d8c62e31423af29851` | [39277286418](https://github.com/dlubom/gps-kataster-obiektow-tatr/actions/runs/39277286418) / 118144844972 | 1076 passed, 227,66 s |
| `77025edef4ea573b6641ea2593bc94f248b88124` | [39278211636](https://github.com/dlubom/gps-kataster-obiektow-tatr/actions/runs/39278211636) / 118147521929 | 1077 passed, 226,90 s |
| `acf00addd4515791ab40df9f308d706f9324ace8` | [39280165485](https://github.com/dlubom/gps-kataster-obiektow-tatr/actions/runs/39280165485) / 118152692077 | 1077 passed, 140,85 s |

W każdym log potwierdza Ruff format (78 plików), Ruff check, pytest,
walidację YAML bez błędów oraz końcową bramkę
`review_tpn_batch.py check --changed-from b98fd3febb400c7ee520046682c1bb16238429ee`:
`{"checked_batches":[],"ready":true}`. Brak produkcyjnych paczek jest
oczekiwany; działanie pending/defer i apply sprawdzają testy fixture’ów.
Ostrzeżenia walidatora: 1876 MISSING_HORIZONTAL_ACCURACY,
103 MEASUREMENT_OUTSIDE_VALLEYS, 72 MEASUREMENT_DISTANCE_OUTLIER,
16 OBJECT_PREFIX_MISMATCH — razem 2067, zgodnie z lokalnym odbiorem.

`pull_request` wiąże run z podanym head_sha; checkout testuje syntetyczny
merge do bazy main (odpowiednio 824564c, 23d97fe, 25572b0). To zachowanie
istniejącego workflow, nie merge PR przez wykonawcę. Sprawdzono tę zgodność
w logach Checkout. Python runnera: 3.12.15 / pytest 9.0.3.

## Rozstrzygnięcie opóźnionych statusów i logów

W poprzednim handoffie runy były queued/in_progress, kroki/logi niedostępne,
a próby anulowania zwracały sprzeczne komunikaty o zakończonym przebiegu.
Obecny odczyt potwierdza zakończenie wszystkich trzech runów sukcesem;
nie ma podstaw, by przypisać opóźnienia błędowi PBI-100. Przyczyna dawnych
rozbieżności statusów API pozostaje nieustalona.

Dodatkowo `gh run view 39277286418 --log` zwrócił tylko początkowe kroki,
mimo kompletu success w jobs. Bezpośrednie pobranie
`gh api repos/dlubom/gps-kataster-obiektow-tatr/actions/runs/39277286418/logs`
potwierdziło, że także osobne pliki kroków w ZIP urywają się po Lint,
ale zbiorczy `0_Validate code and data.txt` zawiera pełne 1076 testów,
walidację, bramkę TPN i cleanup. Odbioru nie oparto na skróconym wyjściu gh.
Brak błędów procesu/tracebacków; ostrzeżenie runnera o Node.js 20 w używanych
actions nie blokuje joba i nie uzasadnia zmiany workflow w tym odbiorze.
Nie uruchamiano ponownie CI, nie anulowano runów ani nie zmieniano kodu.

## Ochrona danych i lokalna kontrola odbioru

Ponowny audyt PBI-099 dał bajtowo identyczny manifest SHA-256
`04f9b4e87825cca05d8ebe51e804134837181269bacc274ee0d0d1881c2d27d2`:
**pending**, 9 chronionych obiektów / 6 manual / 3 propozycje auto→manual.
Preimages wszystkich 9 obiektów zgodne. Bez zgody i bez migracji
KSW-0201/m-003, KSW-0240/m-002, KSZ-0112/m-001; strażnik nadal blokuje zmianę.

Ponowiono 9 istniejących testów ochrony, wspólnych preimages i CLI na
izolowanych syntetycznych tmp_path: **9 passed, 5,07 s**. Nie stosowano
żadnych decyzji do katalogu produkcyjnego. Wszystkie 2048 plików data/config
i manifest pozostają identyczne. Zmiana odbioru obejmuje wyłącznie dokumentację;
sprawdzono jej lokalne linki, spójność statusów oraz `git diff --check`.
Wcześniejsze pełne testy, mutacje i readback zachowuje log PBI-100.

Surowe JSON/logi, archiwum i lokalne wyniki:
ignorowany `build/verification/PBI-100-ci-acceptance/`. Do kontynuacji
wystarczają niniejsze podsumowanie, log PBI-100, kod/testy, snapshot i manifest
w Git oraz wskazane przebiegi GitHub; nie trzeba historycznego build.

## Końcowy commit odbioru i granica

Backlogi, context, handoff i prompt wskazują zakończone PBI-100.
Po commit/push dokumentacji trzeba sprawdzić dokładny zdalny SHA = head PR
oraz wszystkie jego joby, kroki i pełne logi. Wynik tego ostatniego przebiegu
jest utrwalany w **opisie PR #12** wraz z pełnym SHA i URL CI; historia Git
identyfikuje commit odbioru. Nie dodajemy kolejnego commitu tylko po to,
by wpisać jego własny hash i ponownie otworzyć obowiązek CI.

Zakończyć po PBI-100. PBI-101–103 pozostają planowane, bez nowego importu,
merge, tagu, release, workflow_dispatch ani harmonogramu.
