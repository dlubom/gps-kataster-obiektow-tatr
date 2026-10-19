# PBI-101 — hosted CI: rozbieżność odtworzenia raportu

Status: **nieodebrane; PBI-101 w toku**, wszystkie 640 decyzji pending
na jawne polecenie użytkownika. Nie stosować żadnego produkcyjnego
approve/reject/defer. [Paczka i weryfikacja](PBI-101.md),
[propozycje](PBI-101-review/review.md), [kontynuacja](PBI-101-next-task.md).

## Rzeczywisty wynik pierwszej dostawy review

SHA `9a70337725c9098248fb98ec45979fd6fdacb3d4`, zgodny z lokalnym HEAD,
zdalną gałęzią i head otwartego draft PR #12.
[Run 39289000670](https://github.com/dlubom/gps-kataster-obiektow-tatr/actions/runs/39289000670),
[job 118184405176](https://github.com/dlubom/gps-kataster-obiektow-tatr/actions/runs/39289000670/job/118184405176):
completed/**failure**, 1/1 job. Odczytano jobs z filter=all, wszystkie
kroki, pełny log gh i wszystkie 14 plików archiwum logów.

| Kroki | Wynik |
|---|---|
| Setup, Checkout, Python, uv, zależności | 5 success |
| Check formatting, Lint | 2 success |
| Test | success: 1077 passed / 211,14 s |
| Validate YAML data | success: 0 błędów / 2067 ostrzeżeń |
| Verify TPN batch decisions | **failure**, szczegóły poniżej |
| Post Install uv, Post Set up Python | 2 skipped po porażce, bez błędu cache |
| Post Checkout, Complete job | 2 success |

Razem **11 success / 1 failure / 2 skipped**, nie 14 success.
Pełny agregat logu SHA-256:
`7fe729970b18f86783480d0353faedd545f0a03b1d413cb8ecaab41597128724`.
Jedyny błąd procesu: krok Verify TPN batch decisions, exit 1:

```text
TPN_BATCH_INVALID: changes evidence/schema mismatch; regenerate report
```

**To nie jest oczekiwane `pending blocks merge`.** Hosted CI odmawia
wcześniej, przy odtwarzaniu niezmiennego changes w verify_changes.
Nie uznano tego wyniku za sukces ani wyłącznie oczekiwaną blokadę pending.
Nie zmieniano workflow, protokołu, tolerancji, wejść ani decyzji, żeby
obejść porównanie. Nie wykonano rerun/anulowania tego przebiegu.

## Co potwierdzono, a czego jeszcze nie

- Nowy snapshot verify przechodzi offline; hash i wszystkie pliki wejściowe
  pozostały zgodne. Snapshot utrwalono w 60afeca przed przygotowaniem paczki.
  Jego wcześniejszy CI 39287314376 był success, 1/1 job, 14/14 kroków.
- MacOS arm64, Python 3.12.13, pyproj 3.7.2 / PROJ 9.5.1: narzędzie
  odtwarza report bajtowo kanonicznie i dochodzi do pending blocks merge.
  Powtórzono to także w czystym lokalnym klonie dokładnego dostarczonego
  commitu, bez build, z prawdziwym origin/main b98fd3f.
- Linux x86_64 w CI, Python 3.12.15, pyproj 3.7.2: odtworzenie raportu
  nie jest kanonicznie identyczne. Log nie pokazuje różniących się ścieżek
  ani wartości oczekiwanego reportu. Nie przypisywać pewnej przyczyny
  wyłącznie na podstawie komunikatu.
- Sprawdzono wpływ Python hash seed lokalnie: kanoniczne odtworzenie
  z PYTHONHASHSEED=1 jest identyczne. Różnica Decimal/float w pomocniczym
  porównaniu obiektów Pythona nie oznacza różnicy kanonicznego dokumentu.
- Hipoteza do sprawdzenia: odciski wiążą również obliczane floaty projekcji
  i odległości oraz hashe podstaw kandydatów; różnica platformy/środowiska
  może zmieniać ich najniższe cyfry. **Nie potwierdzono**, które wartości
  są inne w tym konkretnym przebiegu. Nie wolno po prostu zaokrąglić lub
  poluzować kontroli wszystkich pól, zwłaszcza surowych XY API.
- Lokalny Docker nie miał działającego demona; nie uzyskano niezależnego
  odtworzenia Linux ani diagnostycznego expected reportu z CI. Nie dodano
  do produkcyjnego workflow kodu diagnostycznego lub uprawnień.

## Dane i eksporty końcowego SHA

Nowy czysty klon 9a70337 bez build: verify snapshotu PASS, pending gate
odtworzona lokalnie. Świeży build z --source-commit równym pełnemu SHA;
statystyki potwierdzają ten commit. Readback 10/10 PASS, 1007 Obiektów,
1001 Jaskiń, 1876 pomiarów; XLSX 1007 Best / 1876 Full. Wszystkie
wcześniejsze pliki domenowe i pomiary zachowane, manifest 099 pending.
Izolowana symulacja dry-run/apply/replay/check/readback nadal jest dowodem
lokalnych narzędzi, **nie zastępuje** tego nieodebranego hosted CI.

## Następny krok i granica

Przed odbiorem zastosowanej paczki trzeba odtworzyć rozbieżność z Linux,
otrzymać diff kanonicznego expected/actual i ustalić przyczynę bez osłabiania
ochron. Potrzebną zmianę narzędzia należy jawnie wydzielić/uzgodnić;
PBI-101 nie stało się ponowną implementacją PBI-096–100. Nie nadpisywać
obecnego snapshotu ani immutable changes, nie przeliczać samych hashów.

Niezależna druga przeszkoda: użytkownik nadal chce wszystkie decyzje
pending. Nawet po usunięciu rozbieżności prawidłowa bramka ma wtedy
odmówić merge. Dokończenie PBI-101 wymaga późniejszych jawnych decyzji,
testów wybranego wariantu, apply/readback i pełnego success CI.

Ten handoff jest nową informacją o odbiorze, nie commitem dla własnego SHA.
Końcowy SHA dokumentacji, URL i rzeczywiste wyniki jego wszystkich kroków
utrwala opis PR #12 po push. Bez PBI-102, merge, tagu, release i harmonogramu.
