# Development — wykonanie jednej karty

Stosuj do zadania wskazanego przez użytkownika. [Indeks](README.md) określa
status i zależności, [spec](spec.md) — wymagania, [design](design.md) — podział
odpowiedzialności. Polecenia wykonuj z korzenia właściwego checkoutu.

## 1. Odtworzenie kontekstu i izolacja

1. Przeczytaj `AGENTS.md`, główną specyfikację, `docs/asdlc/context.md`,
   `docs/operations.md`, ten zestaw dokumentów i wybraną kartę.
2. Sprawdź `git status --short`, `git worktree list`, `git remote -v`;
   wykonaj `git fetch origin`. Na czystym głównym checkoutcie odśwież `main`
   przez `git switch main` i `git pull --ff-only`. Nie dotykaj cudzych zmian.
3. Odczytaj aktualny stan PR #40, head/base i CI. Dopóki PR jest otwarty,
   te karty są kontynuacją jego aktualnego head `origin/codex/postgres-migration`.
   Utwórz osobną gałąź/worktree z tego head. Nie używaj starego lokalnego
   checkoutu tej gałęzi ani SHA z historycznego opisu jako bieżącej bazy.
   Po scaleniu PR zaczynaj z bieżącego `main` i dostarczaj nowym PR.
   Zamknięty niescalony PR wymaga rozstrzygnięcia dalszej bazy przez użytkownika.
4. Przypnij **dwie różne podstawy**: `REFACTOR_BASE=$(git rev-parse HEAD)`
   do porównania zachowania i kodu oraz zaakceptowany baseline historii
   według `docs/operations.md` / `scripts/ci_baseline.py`. Nigdy nie zastępuj
   rzeczywistego baseline historii commitem kandydata, aby test przeszedł.
5. Potwierdź zależności karty w kodzie i testach. Jeżeli część już wdrożono,
   zawęź kartę do realnej różnicy i zapisz to w jej zakresie przed implementacją.

## 2. Implementacja i pomiar

- Zapisz, które duplikaty/konwersje wyjściowo istnieją, ich odbiorców i testy.
  Dla błędu najpierw odtwórz przypadek przez publiczne API/CLI. Dla refaktoru
  zachowaj niezależny wzorzec zachowania sprzed zmiany.
- Wykonaj kroki karty. Usuń stare ścieżki po przełączeniu wszystkich odbiorców;
  nie zostawiaj nieużywanego wyjątku, aliasu lub wrappera „na wszelki wypadek”.
- Nie poprawiaj danych, nie formatuj całego repozytorium i nie zaczynaj sąsiedniej
  karty. Nowe odkrycia zapisz w odpowiednim przyszłym zadaniu.
- Zmierz `git diff --numstat "$REFACTOR_BASE" -- src scripts schema` oraz
  wariant `git diff --ignore-space-change --numstat "$REFACTOR_BASE" -- src scripts schema`.
  Podaj dodane/usunięte linie produkcyjne i bilans osobno dla Python/SQL/schematów;
  testy i dokumentację licz osobno. Dla faz/IO podaj liczbę odczytów lub baz
  potwierdzoną testem, nie tylko przypuszczenie o szybkości.
- Sprawdź brak niezamierzonych zmian `data/`, `config/`, `schema/` względem
  bazy zadania. Zmiana SQL jest dopuszczona tylko przez kartę, która jej wymaga.

## 3. Weryfikacja

Runtime i zgodne wersje opisuje [instrukcja operacyjna](../../../operations.md).
Nie zakładaj istnienia lokalnego serwera, `.venv` innego worktree ani plików
w `/tmp` z poprzedniej sesji. Wymagane są PostgreSQL 18/PostGIS 3.6 i GDAL.

```bash
uv sync --frozen
# Najpierw testy wskazane w karcie, następnie pełna bramka:
uv run --frozen python scripts/check_project.py --base-ref origin/main
```

W CI i przy innym zdarzeniu użyj jego jawnego zaakceptowanego SHA zamiast
domyślnego `origin/main`. Runner wykonuje Ruff, testy, walidację i historię,
pełny build, odtworzenie dumpa, odczyt GeoPackage oraz `git diff --check`.
Lokalnie pominięty smoke zarządzanego Dockera ma przejść w CI. Nie ukrywaj skipów.

Dla U03/U04/U05/U06/U07/U10, które mogą zmienić wejście, zapis lub eksport,
porównaj pełny build przed/po na tych samych danych, stałym `--generated-at`
i identycznych metadanych wydania. Zachowaj oba katalogi poza źródłami.
Użyj `scripts/build_release_artifacts.py` z jawnymi `--base-ref`, `--history-repo`
i `--output-dir`. Sam hash binarnego dumpa/ZIP nie rozstrzyga zgodności:

| Format | Odbiór |
|---|---|
| CSV, GeoJSON, GPX, JSON, Markdown | Dane, kolejność, precyzja i deklaracje; przy identycznych metadanych także bajty |
| XLSX | Oba arkusze, wartości wszystkich komórek, formaty/liczby, tabela i nagłówki |
| Shapefile ZIP | Składowe, rekordy, geometria, pola i CRS; pomiń tylko techniczny czas ZIP/DBF |
| GeoPackage | `integrity_check`, obie warstwy, typy/null, wszystkie wiersze/geometrie i CRS |
| PostgreSQL dump | Natywne odtworzenie, wszystkie tabele i widoki Best, schemat; losowy token klienta nie jest daną |

Jawnie wymień każdą normalizowaną metadaną; nie maskuj różnic wartości,
kolejności pomiarów, cytowań, 27 ręcznych Best ani brak/null. Liczby katalogu
z punktu odniesienia to 1029 obiektów, 1019 jaskiń i 1946 pomiarów, lecz przy
nowym head najpierw sprawdź, czy legalna zmiana danych ich nie zaktualizowała.

## 4. Odbiór i następna sesja

- Przejrzyj diff według karty i specyfikacji. Testy nie mogą korzystać z helpera,
  który wykonuje walidację zamiast badanego API lub sam wylicza oczekiwany wynik.
- Uaktualnij główną specyfikację i instrukcję operacyjną tylko o faktycznie
  wdrożone zachowanie. Wpisz krótki wynik i pozostałe ograniczenia w karcie;
  zmień status wyłącznie w indeksie, a backlog/context pozostaw z odsyłaczem.
- Commituj zweryfikowany zakres. Przed push ponownie sprawdź zdalny head:
  kontynuację otwartego PR dostarcz fast-forward do jego gałęzi, bez force push.
  Jeśli head ruszył, zintegruj zmiany, sprawdź konflikt zakresu i ponów właściwe
  kontrole. Po scaleniu PR stosuj zwykłą nową gałąź i nowy PR z `main`.
- Potwierdź zdalny SHA i terminalny sukces wymaganego CI dla tego SHA.
  Gdy powstaje preview, pobierz paczkę i sprawdź sumy, provenance head/base/merge
  i odbiór istotnych formatów. `in_progress` nie oznacza zakończenia.
- Wynik końcowy ma podać: zmienione zachowanie, bilans redukcji, testy/skips,
  commit, CI, kartę następnego zadania i ewentualne otwarte ograniczenie.
  Zakończ po wskazanym zadaniu; merge, tag i wydanie wymagają osobnego polecenia.

Sam pakiet niniejszych zleceń jest zmianą dokumentacji: wymaga kontroli linków,
zgodności kart z kodem, `git diff --check` i CI. Nie wymaga implementacji U03
ani ponownego lokalnego pełnego zestawu testów, gdy kod pozostaje identyczny.
