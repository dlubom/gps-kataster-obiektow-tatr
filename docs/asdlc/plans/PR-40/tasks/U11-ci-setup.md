# U11 — wspólne przygotowanie runtime w CI

Przeczytaj [indeks](../README.md), [spec](../spec.md), [design](../design.md)
i [development](../development.md). Zależność: U10. Realizuje S10.

## Spec

Workflow `validate.yml`, `pr-preview.yml`, `release.yml` i `mutation.yml`
powtarzają część przygotowania Python/uv/GDAL/PostgreSQL i zależności.
Usuń wspólną konfigurację instalacji bez zmiany bramek, uprawnień i zdarzeń.
Nie oszczędzaj czasu przez pomijanie obowiązkowej walidacji lub uznawanie
raportu z innego commitu za dowód poprawności kandydata.

## Design

- Wybierz małą lokalną composite action (`.github/actions/.../action.yml`)
  lub istniejący skrypt setup. Obejmuje tylko identyczne przygotowanie;
  różnice, np. Node wyłącznie dla testów publishera, pozostają jawne.
- Workflow nadal deklaruje `permissions`, event, checkout pełnej historii,
  serwis PostgreSQL, `HISTORY_BASE_SHA` i konkretną komendę. Composite action
  nie przyjmuje arbitralnego kodu powłoki z pól PR. W workflow PR zachowaj
  wyłącznie odczyt; nie przekazuj do setupu dodatkowych sekretów/tokenów.
  Tagowy release zachowuje swoje istniejące `contents: write` dla publikacji
  z zaufanego commitu; rozdzielenie tego joba nie należy do ekstrakcji setupu.
- Zachowaj wersje Python/uv/GDAL, digest PostGIS i zgodne klienty PG18
  z bieżącego repo. Nie aktualizuj zależności przy okazji ekstrakcji setupu.
- Chroniony check nadal nazywa się `Validate code and data` i zawsze istnieje.
  Nie wprowadzaj filtrów ścieżek, które pozostawiają required check bez wyniku.
- `publish-pr-preview.yml` pozostaje zaufanym, odrębnym workflow. Nie używa
  lokalnej akcji pobranej z nieufnego head PR z uprawnieniami zapisu.

## Development

1. Porównaj cztery workflow i `scripts/check_project.py`; wypisz dokładnie
   wspólne kroki oraz różnice uprawnień, serwisów, baseline i zależności.
2. Wydziel setup i przełącz odbiorców bez zmiany komend kontroli ani kolejności
   wymaganej do ich wykonania. Nie próbuj przenosić deklaracji serwisów do
   composite action, która ich nie obsługuje.
3. Rozszerz `tests/test_pr_preview.py`, testy baseline i publishera o ochronę
   required check, pinów i granicy zaufania po ekstrakcji. Przetestuj parsowanie
   YAML i rzeczywiste uruchomienie akcji w CI; sam test tekstowych fragmentów
   nie jest pełnym dowodem poprawności workflow.
4. Potwierdź validate + preview na dokładnym nowym head, managed Docker smoke,
   dump/restore i pobraną paczkę. Dla mutation uruchom istniejący bezpieczny
   workflow, jeżeli wspiera tę gałąź; jeżeli nie, odnotuj zakres lokalnego odbioru.
5. Ścieżkę release sprawdź bez publikacji: wspólna akcja już wykonana w CI,
   parser zdarzenia/baseline w testach, lokalny build i lista artefaktów z U10.
   Brak prawdziwego testu taga opisz jako ograniczenie, nie oznaczaj go PASS.
6. Uaktualnij dokumentację runtime i wpisz rzeczywisty bilans YAML/skryptów.

```bash
uv run --frozen pytest -q tests/test_ci_baseline.py tests/test_pr_preview.py tests/test_postgres_runtime.py
node --test tests/test_pr_preview_publisher.cjs
```

## Odbiór

- [x] Wspólna instalacja ma jednego właściciela i wszystkich właściwych
  odbiorców; wyjątki są jawne, wersje/piny pozostały bez zmian.
- [x] Required check, pełna historia Git, poprawny baseline, least privilege
  PR/publisher, dump/restore, GPKG i managed Docker smoke są zachowane.
- [x] Validate/preview mają terminalny sukces dla dostarczonego SHA,
  paczka ma zgodne sumy i head/base/merge; zakres sprawdzenia mutation/release
  jest uczciwie opisany. Nie tworzono taga ani wydania.
- [x] Bilans redukcji i wynik zapisano według procedury; statusy wszystkich
  poprzedników w indeksie odzwierciedlają rzeczywisty stan Git/CI.

Zakończ po U11. Kolejne usprawnienia wymagają osobnego zakresu; zakończenie
serii nie upoważnia do merge, taga ani release.

### Zakres wykonanej ekstrakcji

Baza refaktoru: `66e27253568e9624da3cbd88a550153eeaefe753` (live head PR).
Zaakceptowana baza historii PR: `ad5fa191a36d5a5f45f0b2de523bd39125827573`;
obie podstawy ustalono z aktualnego Git/GitHub. U10 i jego odbiór są wdrożone.

| Właściciel | Przygotowanie / zachowana różnica |
|---|---|
| `.github/actions/setup-runtime/action.yml` | Python 3.12.13, uv 0.11.8, env do klientów PG18 serwisu, GDAL `3.8.4+dfsg-3ubuntu3`, `uv sync --frozen` |
| validate / mutation | Cache uv włączony; Node 24.22.2 pozostaje jawny |
| preview | Cache uv wyłączony; sprawdzenie rodziców merge przed setupem |
| release | Istniejące zdarzenie taga i `contents: write`; lista NUL z U10 |
| wszystkie cztery workflow | Pełna historia bez zapisanych credentials, przypięty serwis PostGIS, jawne rozstrzygnięcie baseline i niezmienione dalsze komendy |
| zaufany publisher | Bajtowo bez zmian, bez lokalnej akcji z PR |

Baseline nadal używa stdlib/Git i jest rozstrzygany przed każdą kontrolą
kandydata. Instalacja zależności mieści się teraz w setupie przed tym krokiem;
nie zmienia to jego wejścia ani zasad akceptacji. Nie przeniesiono bramek,
serwisów, uprawnień, zdarzeń ani sekretów do akcji. Nie zmieniono pinów,
lockfile, danych, konfiguracji, schematu ani kodu aplikacji.

### Odbiór lokalny

- Przed ekstrakcją zestaw karty: **24 PASS / 1 SKIP** w **4,93 s**.
  Nowe regresje: **7 FAIL / 6 PASS**; wykazały brak wspólnego setupu.
- Po ekstrakcji **13 nowych przypadków PASS** w **1,00 s** pytest
  (**1,245 s** czasu całego procesu z `uv`). Obejmują cztery workflow,
  required check, wersje i piny, cache, granicę publishera, rzeczywisty Bash
  zapisujący klientów PG18 bez ewaluacji wejścia oraz CLI baseline dla
  PR/push/tag/dispatch i odmowę eksportu SHA kandydata po błędzie.
- Cała komenda karty: **37 PASS / 1 SKIP** w **5,57 s** pytest
  (**5,706 s** procesu); publisher Node **28 PASS**, **0,124 s** procesu.
  Jedyny lokalny skip to smoke zarządzanego Dockera, wymagany oddzielnie w CI.
- Sparsowane YAML przed/po: zdarzenia, uprawnienia, serwisy, checkout,
  baseline i wszystkie kroki poza wydzielonym setupem są identyczne.
  Faktyczne uruchomienie composite action, pełna bramka i odbiór CI
  są wymagane poniżej; testy YAML same nie zamykają karty.
- Lokalny runtime: PostgreSQL 18.6/PostGIS 3.6.4 i GDAL/PROJ z QGIS 4.0.1.
  Pierwszy test bazowy ujawnił pomieszanie GDAL Homebrew z bazą PROJ QGIS
  (layout 7 vs 6). Minimalny odczyt EPSG potwierdził przyczynę; dobrano
  spójny lokalny runtime, bez poprawiania aplikacji ani pinów CI.

- Po dostosowaniu istniejących obserwatorów inline setupu w testach
  validate/release/mutation: rozszerzony zakres **46 PASS / 1 SKIP**
  w **5,99 s** pytest. Actionlint 1.7.7 zaakceptował cztery zmienione workflow.
  Niezależny review nie zgłosił usterek ani zachowań wyłączonych z oceny.
- Bilans implementacji: YAML workflow/akcji **+64/−100, netto −36**;
  Python produkcyjny, SQL i schematy **0**; testy **+246/−8**. Wynik bez
  whitespace jest taki sam dla YAML. Przeniesiona akcja jest wliczona.

Pełna lokalna bramka na zaakceptowanym baseline: **1548 PASS / 1 SKIP**,
Ruff, walidacja YAML/historii, pełny build, restore dumpa, odczyt GPKG i diff
**PASS**. Pytest **616,97 s**, cała bramka **640,102 s**. Pierwszy przebieg
przerwano po czterech nieaktualnych obserwatorach inline setupu; poprawione
obserwatory zachowują wcześniejsze asercje, końcowy przebieg jest pełny.

### Paczka kodu i ścieżka release

Kod: `59741d25eac47810e8ae554a931e32340e119df0`.
[Preview kodu](https://github.com/dlubom/gps-kataster-obiektow-tatr/actions/runs/42221073950)
**SUCCESS**, próba 1; [paczka 13503322570](https://github.com/dlubom/gps-kataster-obiektow-tatr/actions/runs/42221073950/artifacts/13503322570),
SHA-256 `d7feca3100011c2c07c7678fa7d5e9ff9e2812c0c90bfc7a532305c2bedd5574`.
Pobrany ZIP: **14/14 sum**, 15 nazw, head/base/merge
`6c79a91df43b977302a04bff240d843089fb9127`, run i próba zgodne z Git/API.
Niezależny odczyt i porównanie z lokalnym buildem o tych samych metadanych:
**13/13 formatów**, obejmujące wszystkie dane i deklaracje oraz natywne
odtworzenie obu dumpów. Zachowano 1029 obiektów, 1019 jaskiń, 1946 pomiarów,
27 manual Best, ich historię, typy/null i źródłowe współrzędne.

Normalizacje techniczne: czas GDAL w GPKG, data nagłówka DBF, nagłówki ZIP,
losowe tokeny i komentarze wersji klienta/serwera dumpa. RTree sprawdzono
przez odbudowę granic z geometrii, `rtreecheck` i insert/update/fid/null/delete
na kopiach; nie porównywano fizycznych stron indeksu ani równoważnych
wariantów triggerów GDAL. CRS/WKT/datum i wartości źródłowe są ścisłe.
21982 pochodne wartości EPSG:2180 porównano z tolerancją **1e-8 m**;
maksymalna różnica **1,9208528101444244e-9 m**.

Lokalny build pełnego katalogu z `--artifact-list`: **13/13** zwykłych plików
i ścieżek NUL, restore dumpa i odczyt GPKG PASS (**12,89 s**). Parser zdarzenia
taga oraz shell budowania/listy artefaktów są sprawdzane przez istniejące
rzeczywiste testy CLI U10. **Nie uruchamiano prawdziwego taga/publikacji**;
ta część release nie ma wyniku PASS.

### Ograniczenie mutation

[Workflow mutation](https://github.com/dlubom/gps-kataster-obiektow-tatr/actions/runs/42221107391)
na SHA kodu zakończył się **FAILURE**. Wspólna akcja, Node, resolver baseline,
pełny zestaw bazowy **1547 PASS / 2 SKIP** (1226,12 s) i cleanup przeszły.
`mutmut 3.5.0` przerwał zbieranie statystyk przed kampanią mutacji:
`test_cave_membership_symmetry_is_required[missing-member]` uruchamia CLI
w osobnym interpreterze; instrumentacja widzi `mutmut.config is None`
i zgłasza `AttributeError: 'NoneType' object has no attribute 'max_stack_depth'`.
Wynik stats: **1 FAIL / 22 PASS / 4 deselected**.

Ten sam błąd, test i etap odtworzono na czystym archiwum bazy sprzed U11
`66e27253568e9624da3cbd88a550153eeaefe753`, z osobnym venv,
`uv sync --frozen` i niezmienionym `uv run --frozen mutmut run --max-children 2`:
kod **1**, **1 FAIL / 22 PASS / 4 deselected**, **16,43 s** całego procesu.
U11 nie zmienia konfiguracji mutmut, źródeł instrumentacji ani tego testu.
To istniejące ograniczenie toolingu do osobnego zakresu; nie usunięto testu,
nie dodano filtrów ani nie oznaczono kampanii PASS. Artefakt statystyk
[13505228363](https://github.com/dlubom/gps-kataster-obiektow-tatr/actions/runs/42221107391/artifacts/13505228363)
nie jest dowodem skuteczności mutacji po nieudanym zbieraniu statystyk.

### Wymagany odbiór CI kodu

[Validate code and data](https://github.com/dlubom/gps-kataster-obiektow-tatr/actions/runs/42221074550)
**SUCCESS**, próba **2**, dokładny SHA kodu `59741d25eac47810e8ae554a931e32340e119df0`:
**1547 PASS / 2 SKIP**, pytest **1444,10 s**; oddzielny wymagany managed
Docker smoke **1 PASS** (21,75 s), rzeczywisty baseline, historia i cleanup PASS.
Dwa skips dotyczą smoke uruchamianego oddzielnie i klientów native przy
klientach kontenera. Próba 1 została przerwana po ponad 15 minutach wolnego
pobierania zależności GDAL z `azure.archive.ubuntu.com`; log potwierdza brak
uruchomienia sync/testów. Powtórzono wyłącznie ten job, bez zmian kodu/pinów.

Końcowy commit domyka wyłącznie dokumentację. Kod, testy, dane, zależności
oraz workflow pozostają identyczne z odebranym SHA kodu. Końcowy zdalny head,
terminalne validate/preview i odbiór paczki wskazuje [opis PR #40](https://github.com/dlubom/gps-kataster-obiektow-tatr/pull/40).
Statusy i zamknięcie serii pozostają wyłącznie w indeksie. Nie utworzono taga
ani wydania; prawdziwa ścieżka publikacji release pozostaje nietestowana.
