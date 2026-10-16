# Realizacja nowej serii z main

Seria zakończona: PR #4 zmergowany, v1.0.3 opublikowane;
[potwierdzenia](verification/v1.0.3.md). Punkt startowy kolejnej sesji: `main`.
`codex/main-remediation-2026-10` jest gałęzią historyczną.
[Backlog i karty](backlog_v1.md#naprawy-main-po-przegladzie-2026-10-12),
[decyzje zakresu](remediation_plan.md), [kontekst](context.md).
Ten protokół zastępuje procedurę porzuconej serii z 2026-09-05.

## Start sesji

1. Sprawdź status, branch i remote. Zachowaj cudze zmiany.
2. Wykonaj `git fetch origin`; na czystym checkoutcie użyj `git switch main`
   i `git pull --ff-only`. Porównaj HEAD z `origin/main`. Nie wznawiaj
   zakończonej gałęzi naprawczej ani nie przenoś zmian z porzuconych gałęzi.
3. Przeczytaj AGENTS, spec, backlog, context, plan, ten runbook i log
   ostatniego PBI. Status potwierdź w Git oraz CI.
4. Brak kolejnego gotowego PBI tej serii; nowa praca wymaga polecenia.
   Nowe zmiany prowadź na gałęzi od aktualnego main i przez PR z review.

Przy prostych poprawkach danych (bez zmian kodu i schematu) wystarczą
uzasadnienia w YAML, opis PR i CI dla dostarczonego SHA. Nie wymagamy
osobnych ani rozbudowanych raportów MD; poniższe wymagania logów PBI
nie dotyczą takich poprawek.

Poniższe sekcje zachowują procedurę odbioru zakończonej serii PBI-079–086.

## Wykonanie i lokalna bramka

- Dla zmiany zachowania zacznij od testu odtwarzającego błąd; zachowaj
  wynik przed poprawką i po niej oraz poprawny przypadek kontrolny.
- Po poprawce uruchom testy obszaru, a następnie pełną bramkę poniżej.
- Nie dziedzicz wyników testów ani mutacji z porzuconej gałęzi.
- Dokumentację i kryteria danych aktualizuj w tym samym PBI.

```bash
uv sync --frozen
uv run --frozen ruff format --check src tests scripts
uv run --frozen ruff check src tests scripts
uv run --frozen pytest
uv run --frozen python scripts/validate.py
uv run --frozen python scripts/build_release_artifacts.py \
  --sqlite-output build/verification/PBI-NNN/katalog.sqlite \
  --output-dir build/verification/PBI-NNN/exports \
  --generated-at 2026-10-15T00:00:00Z
git diff --check
```

Zastąp `PBI-NNN` bieżącym numerem i użyj nowego katalogu przebiegu.
Na tej bazie nie istnieje `scripts/verify_project.py`; nie zakładaj,
że runner ze starej gałęzi jest dostępny. Przy gotowym środowisku można
użyć `uv run --frozen --no-sync --offline`; odnotuj ten wariant i wersje.

Odczytaj ponownie SQLite (integrity/FK), CSV, GeoJSON, GPX, wszystkie rekordy
Shapefile, metadata i ZIP SQLite. Porównaj ID/liczniki oraz współrzędne
best z YAML; zawartość ZIP SQLite ma odpowiadać zbudowanej bazie.
Punktem odniesienia jest raport review, nie stałe liczniki do wymuszania
w testach. Hash `data/` przed/po ma być identyczny poza dozwolonym manifestem
PBI-082–083. Źródłowe CSV/XLSX/JSONL i shapefile pozostają niezmienne zawsze.

Dla krytycznej zmienionej logiki wykonaj celowane mutacje zmienionych
funkcji/reguł i zachowaj ich zakres, wynik oraz analizę ocalałych mutantów.
Test musi zabijać mutanta przywracającego naprawiany błąd. Pending, timeout
i błąd narzędzia oznaczają nieukończoną weryfikację. Sam exit code nie
potwierdza wyniku. Dokumentacja nie wymaga kampanii mutacyjnej.

## Dostarczenie

1. Przejrzyj cały diff, kompletność odbioru i zgodność ze specyfikacją.
   Stage wyłącznie pliki PBI; commit conventional z `(PBI-NNN)`.
2. Pushuj zweryfikowany krok na aktywną gałąź, bez force push.
3. `validate.yml` na tej bazie uruchamia się dla PR i push na main.
   Utrzymuj draft PR do main dla tej gałęzi; nie dodawaj osobnego zadania
   infrastrukturalnego przed trzema P1. Utworzenie PR nie oznacza merge.
4. Potwierdź zdalny SHA gałęzi oraz `headSha` i wynik wszystkich jobów
   workflow `validate` dla tego commitu. Lokalna bramka nie zastępuje CI.
5. Uzupełnij log o dostarczony SHA i URL/wynik CI, zmień status na
   `wykonane` i wskaż kolejny gotowy PBI w kontekście. Jeśli potrzebny jest
   osobny commit dokumentacji, również sprawdź jego zakres, testy właściwe
   zmianie, push i CI. Nie twórz nieskończonej serii wpisów z własnym SHA.
6. Zakończ po bieżącym PBI. Merge, tag i release wymagają osobnego polecenia.

Przy przerwanym dostarczeniu użyj stanu `zweryfikowane — do dostarczenia`.
Log w git ma wskazywać dokładny pozostały krok. Nie używaj samego `build/`,
czatu ani pamięci konta jako punktu kontynuacji.

## Zawartość logu PBI

`docs/asdlc/verification/PBI-NNN.md`: baza SHA, zakres, reprodukcja,
wyniki przed/po, pełna bramka, zmiany danych i ich dowody, przegląd diffu,
ograniczenia, dostarczony commit/CI oraz następny krok. Duże artefakty
zostają w `build/`; konieczne do kontynuacji wnioski i instrukcje są w git.

Po PBI-086 ponów scenariusze R1–R8 i pełny odczyt aktualnych artefaktów.
Zapisz wynik całej nowej serii oraz pozostałe niepewności danych; samo
przejście testów nie rozstrzyga niepewnej lokalizacji w terenie.
