# Jedno PBI w czystej sesji

Branch: `codex/review-remediation`. Źródło kolejności i statusów:
[backlog](backlog_v1.md#naprawy-po-przegladzie-2026-09-05). Zakres zadań:
[plan](remediation_plan.md). Ustalenia wejściowe:
[przegląd R01–R13](reviews/project-review-2026-09-05.md).

## Gotowy prompt do nowej sesji

> Kontynuuj naprawy z przeglądu 2026-09-05 w tym repozytorium.
> Przeczytaj AGENTS.md, specyfikację, backlog, context.md oraz
> docs/asdlc/remediation_runbook.md i remediation_plan.md. Pracuj na
> codex/review-remediation. Wykonaj dokładnie jedno następne gotowe PBI
> zgodnie z backlogiem, po sprawdzeniu zależności i aktualnego origin.
> Odtwórz błąd, napraw go w zakresie PBI, przeprowadź pełną weryfikację,
> zapisz dowody i następny krok w repo. Commituj i pushuj po małych,
> poprawnie zweryfikowanych krokach. Potwierdź zdalny SHA i CI. Zakończ po
> tym PBI. Bez merge do main i bez tagowania/publikacji release.

Można dopisać konkretny numer: „Wykonaj PBI-036”. To nie zastępuje
sprawdzenia zależności. Dalsza wiadomość „kontynuuj” w trakcie pracy nie
uruchamia automatycznie następnego PBI po domknięciu bieżącego.

## 1. Odtworzenie stanu

1. Sprawdź `pwd`, `git status --short`, branch, `git remote -v` i AGENTS.
   Nie resetuj ani nie czyść cudzych zmian. Przy nieczystym checkoutcie
   ustal pochodzenie zmian i granice stagingu; przerwany własny krok
   można wznowić po odczycie jego logu.
2. `git fetch origin`. Zweryfikuj, że repo jest
   `dlubom/gps-kataster-obiektow-tatr`. Jeżeli branch jest lokalny,
   przełącz się na niego; jeżeli tylko zdalny, utwórz lokalny tracking
   `git switch --track origin/codex/review-remediation`. Nie twórz serii
   ponownie od `main` i nie nadpisuj zdalnego brancha.
3. Na czystym branchu użyj `git pull --ff-only`. Sprawdź
   `git rev-list --left-right --count HEAD...origin/codex/review-remediation`.
   Rozbieżność historii wymaga rozpoznania, a nie force push. Nie mieszaj
   w tle nowych zmian z `main` do zaczętego PBI.
4. Przeczytaj dokumenty kanoniczne, plan, ten runbook, ostatni log
   `docs/asdlc/verification/PBI-NNN.md` i kartę wybranego PBI. Starsze
   wpisy w kontekście są historią; bieżący blok u góry ma pierwszeństwo.
5. Sprawdź commity i dostarczenie poprzedniego kroku na origin. Jeśli
   kod jest już zweryfikowany, ale nie został wypchnięty albo domknięty,
   dokończ dostarczenie zamiast ponownie implementować PBI. Zapisany
   status nie zastępuje sprawdzenia Git.
6. Zależności muszą być `wykonane` i obecne na tym branchu. Wybierz
   najniższe gotowe PBI. Jeżeli zadanie blokuje brak danych/odpowiedzi,
   zapisz ten fakt i wybierz niezależne gotowe zadanie zamiast zgadywać.

## 2. Wykonanie

- Zapisz start: PBI, bazowy SHA, zakres i status `w toku` w backlogu oraz
  logu zadania. Nie potrzebujesz osobnego commitu samej deklaracji startu.
- Przeczytaj wskazane moduły i testy. Odtwórz przypadek z karty jako test,
  pokaż jego oczekiwane niepowodzenie na bazowym kodzie. Następnie zrób
  najmniejszą pełną poprawkę i potwierdź, że ten sam test przechodzi.
- Weryfikuj również poprawną ścieżkę i granice zadania. Nie zastępuj
  istniejących testów słabszymi asercjami, nie dopisuj xfail do znalezionego
  błędu, nie oznaczaj danych jako zweryfikowane bez podstaw.
- Jeżeli PBI ma większy zakres, wydziel ukończony podkrok i zapisz jego
  pozostały zakres w logu. Commit i push podkroku są właściwe po pełnej
  zielonej bramce; nie czekaj do końca całej serii. PBI pozostaje `w toku`.
- Każdy nowy niezależny problem trafia do backlogu. Użytkownik zlecił
  planowanie i późniejsze wykonywanie PBI po kolei, nie nieograniczoną
  zmianę architektury ani hurtowy ponowny import.

## 3. Pełna bramka

Zależności instaluj przez `uv sync --frozen`. Przy ograniczonym cache użyj
`UV_CACHE_DIR` w katalogu tymczasowym, nie zmieniaj lockfile dla samego
obejścia sandboxa. `--offline` można dodać, gdy komplet zależności jest
dostępny; brak zależności nie oznacza powodzenia weryfikacji.

PBI-035 dostarcza wspólny runner. Podczas jego wdrożenia wykonano także
osobno poniższe polecenia i sprawdzono exit code każdego kroku
(historyczna bramka PBI-034/035):

```bash
uv sync --frozen
uv run --frozen ruff format --check src tests scripts
uv run --frozen ruff check src tests scripts
uv run --frozen pytest
uv run --frozen python scripts/validate.py
uv run --frozen python scripts/build_release_artifacts.py \
  --sqlite-output build/verification/PBI-034/katalog.sqlite \
  --output-dir build/verification/PBI-034/exports \
  --generated-at 2026-09-05T12:00:00Z
git diff --check
```

Podmień `PBI-034` na bieżące zadanie; użyj nowego pustego katalogu przebiegu,
jeżeli poprzedni wynik już istnieje. Od PBI-035 pełną bramkę wykonuje:

```bash
uv sync --frozen
uv run --frozen python scripts/verify_project.py
git diff --check
```

Każdy przebieg zapisuje `build/verification/run-*/report.json` i logi;
nowy katalog chroni przed zaliczeniem starych artefaktów. Raport obejmuje
komendy/exit codes, wersje, bazowy HEAD, hash drzewa i całego `data/`
przed/po oraz wyniki readback i sumy artefaktów. Błąd zatrzymuje dalsze
etapy i daje niezerowy wynik, a zmiana źródeł podczas bramki także jest
błędem. Szczegóły i tolerancje: [operations](../operations.md#walidacja).

Runner nie zastępuje testu reprodukcji ani review diffu. Przed jego
wdrożeniem ponowny odczyt artefaktów wykonaj istniejącymi bibliotekami
Python: `sqlite3`, `json`, `csv`, `xml.etree.ElementTree`, `zipfile`, `pyshp`.
Sprawdź SQLite integrity/FK, pliki w archiwach, wszystkie rekordy DBF i
zgodność ID/liczników oraz współrzędnych najlepszego pomiaru z YAML.
Zapisz rzeczywiste wyniki, a nie tylko deklarację, że pliki powstały.

Stan bazowy przeglądu: 1009 obiektów, 1003 jaskinie, 1875 pomiarów, 0 relacji,
0 błędów i 2066 ostrzeżeń: 1875 braków dokładności, 103 poza dolinami,
72 odległości i 16 niezgodności prefixu. To punkt odniesienia, nie
uniwersalne stałe do wymuszenia w testach. Zmianę licznika/reguły trzeba
wyjaśnić. Nie wyciszaj nowych ostrzeżeń ani błędów tylko po to, by zachować
liczbę 2066. Porównuj hash/treść źródeł przed i po bramce, nie wyłącznie
liczby rekordów; poza PBI-051 dane mają pozostać bez zmian.

Dla PBI zmieniającego krytyczną logikę z zakresu mutmut uruchom po zwykłej
bramce testy mutacyjne zmienionych modułów, np.:

```bash
uv run --frozen mutmut run --max-children 2 'gps_kataster_obiektow_tatr.validator*'
uv run --frozen mutmut results
```

Nowy moduł wydzielający krytyczną regułę musi wejść do zakresu mutacji.
Mutant psujący naprawianą gwarancję ma być zabity przez test. Dla pozostałych
ocalałych zapisz analizę i identyfikator; nie udawaj 100% pokrycia na
podstawie samego exit code. Nie wymagaj mutmut dla samej dokumentacji.
Timeout/błąd narzędzia to nie wynik pozytywny; zakończenie krytycznej
weryfikacji pozostaje otwarte. Pełna kampania wszystkich krytycznych
modułów jest częścią PBI-054, a nie każdej drobnej zmiany.

Przed commitem przeczytaj cały diff i sprawdź zakres staged. Po istotnej
zmianie logiki zleć niezależny review agentowi tylko do odczytu; zapisuj
wynik lub jawny brak dostępności. Brak review nie jest równoznaczny z
aprobatą. PBI-054 wymaga dostarczenia niezależnego review serii.

## 4. Commit, push i zapis punktu kontynuacji

Zwykły PBI ma dwa małe checkpointy. Pozwala to zapisać prawdziwy SHA i
wynik dostarczenia kodu bez próby umieszczenia hasha commitu w nim samym.

1. Po pełnej bramce uzupełnij log: bazowy SHA, zakres, test przed/po,
   komendy i wyniki, dane/ostrzeżenia, review, ryzyka. W backlogu ustaw
   `zweryfikowane — do dostarczenia`. Stage tylko pliki tego PBI, commit
   conventional z `(PBI-NNN)`; `git push -u origin codex/review-remediation`
   przy pierwszym puszu, potem zwykły push tej gałęzi. Nie używaj
   `git add .`, force push ani amend opublikowanego commitu.
2. Potwierdź SHA z `git ls-remote --heads origin refs/heads/codex/review-remediation`
   i porównaj go z `git rev-parse HEAD`. Od PBI-035 sprawdź wynik workflow
   validate dla dokładnie tego SHA, nie poprzedniego zielonego runu.
   Przy awarii CI popraw problem, ponów pełną bramkę i push poprawki.
   Przed wdrożeniem PBI-035 branch nie wyzwala CI: wpisz `nie dotyczy —
   trigger zostanie dodany w PBI-035`, nie „CI przeszło”.
3. W małym commicie dokumentacji domknij PBI: wpisz dostarczony SHA kodu,
   wynik push/CI i ewentualny URL runu, status `wykonane`, następne gotowe
   PBI w kontekście. Użyj np. `docs: record PBI-NNN delivery`. Po zmianie
   dokumentacji uruchom pełną bramkę ponownie, commit i push checkpointu.
4. Potwierdź zdalny SHA także dla checkpointu i jego CI, gdy obowiązuje.
   Wynik finalnej odpowiedzi obejmuje oba SHA, faktyczne testy i następne
   PBI. Wpis w logu opisuje wcześniej dostarczony commit kodu; potwierdzenie
   publikacji samego checkpointu wynika z Git, co następna sesja sprawdza
   w kroku 1. Nie twórz nieskończonej serii commitów z własnym SHA.
5. Zakończ sesję po jednym PBI. Nie wykonuj merge, tagu ani release.

Jeżeli push lub CI nie działa, zachowaj commit i stan
`zweryfikowane — do dostarczenia`, zapisz problem i komendę wznowienia.
Nie oznaczaj zadania jako dostarczonego, nie twórz obietnicy powiadomienia
bez mechanizmu monitorowania i nie rozpoczynaj zależnego PBI.

## 5. Rejestr weryfikacji

Każde PBI kopiuje [szablon](verification/TEMPLATE.md) do
`docs/asdlc/verification/PBI-NNN.md`. Krótkie wyniki, dowody i niezbędne
wnioski są w git. Duże logi, bazy i eksporty pozostają w `build/`;
kontynuacja nie może wymagać ich obecności. Po przerwaniu sesji wpisz
dokładnie, co ukończono i co pozostaje, bez deklaracji nieodbytej weryfikacji.
