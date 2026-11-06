# U10 — jeden zestaw artefaktów i wspólne elementy CLI

Przeczytaj [indeks](../README.md), [spec](../spec.md), [design](../design.md)
i [development](../development.md). Zależności: U05/U07/U08. Realizuje S09.

## Spec

`ReleaseArtifactsResult.artifact_paths` już wskazuje komplet 13 plików,
a `build_pr_preview.py` korzysta z niego. Workflow `release.yml` ponownie
wymienia pliki ręcznie. Skrypty build/Best/release powtarzają też czas UTC,
argumenty historii i fragmenty obsługi błędów. Wykorzystaj istniejące wspólne
miejsce zamiast projektować drugi rejestr.

Zachowaj dokładne nazwy, kolejność i format 13 artefaktów oraz 8 plików Best.
Preview dodaje tylko `preview.json` i `SHA256SUMS`. Standalone Best nadal
odmawia zastąpienia pełnej paczki, po walidacji wejścia. Flagi CLI, ich
domyślne wartości, exit code i kanały stdout/stderr zachowują kompatybilność.

## Design

- Zdefiniuj pełny zestaw tylko raz, w warstwie artefaktów. Builder zwraca
  ten zestaw, a CLI udostępnia go paczkowaniu w jednoznacznym formacie
  maszynowym. Nie zbieraj plików wildcardem ze starego `build/`.
- Workflow wydania może konsumować jawny manifest/listę wyników builda;
  lista nie może zawierać ścieżek poza katalogiem artefaktów, braków ani
  nadmiarowych plików. Wybierz najmniejszy kontrakt, zachowując 13 publicznych plików.
- Wspólne helpery CLI obejmują identyczne argumenty baseline/data/time oraz
  formatowanie rozpoznanych błędów. Operacje nadal mają własny parser,
  wywołanie i komunikat wyniku; nie twórz frameworka poleceń ani `except Exception`.
- Wykorzystaj zegar U08, jeśli został wydzielony. Usuń martwe wyjątki dopiero
  po sprawdzeniu wszystkich odbiorców, w tym kompatybilności po U07.
- Nie zmieniaj zaufanego publishera preview tak, aby wykonywał kod lub
  manifest z paczki PR. Jego obecna granica uprawnień jest niezależnym kontraktem.

## Development

1. Zinwentaryzuj listy nazw w `release_artifacts.py`, `best_measurements_export.py`,
   `scripts/build_pr_preview.py`, `scripts/build_release_artifacts.py`,
   `.github/workflows/release.yml` i testach publikacji.
2. Ujednolić zestaw i udostępnić go paczkowaniu. Testuj dokładny zbiór,
   brak pliku, dodatkowy plik, ścieżkę poza output i nieudany późny serializer.
3. Prześledź `scripts/build_db.py`, `scripts/export_best_measurements.py`,
   `scripts/build_release_artifacts.py` oraz `scripts/validate.py`.
   Przed ekstrakcją utrwal różnice stdout/stderr i diagnostyki wejścia;
   zachowaj je przy użyciu wspólnych elementów.
4. Usuń powtórzone listy/UTC/nieużywane wyjątki; popraw opisy CLI mówiące
   nadal o źródłowych INSERT-ach SQL. Aktualizuj `docs/release_artifacts.md`
   i `docs/operations.md` tylko o faktycznie wdrożony interfejs.
5. Sprawdź kompletne build i preview, standalone Best oraz odczyt 13 formatów.
   Workflow wydania zweryfikuj bez tagu i publikowania prawdziwego release.

```bash
uv run --frozen pytest -q tests/test_release_artifacts.py tests/test_best_measurements_export.py tests/test_postgres_exports.py tests/test_pr_preview.py tests/test_validation_phases.py tests/test_release_docs.py
node --test tests/test_pr_preview_publisher.cjs
```

## Odbiór

- [x] Builder/CLI/preview/release konsumują jedną definicję zestawu;
  nie ma ręcznej drugiej listy ani wildcardu publikującego obce pliki.
- [x] Błąd walidacji/eksportu zachowuje poprzedni komplet; standalone Best
  zachowuje ochronę pełnej paczki i kolejność błędów.
- [x] CLI zachowuje flagi, kody, kanały i realny baseline; formaty i precyzja
  pozostają zgodne z bazą zadania. Publisher nie wykonuje zawartości PR.
- [x] Bilans kodu, pełna bramka, paczka preview i exact-SHA CI spełniają
  procedurę; wydanie nie zostało opublikowane w ramach testu.

Zakończ po U10. Następna karta: [U11](U11-ci-setup.md).

### Zakres potwierdzony w kodzie

Baza refaktoru: `14290e645b80262679d7fefcf073075290fd033a`; rzeczywista
zaakceptowana baza historii PR: `ad5fa191a36d5a5f45f0b2de523bd39125827573`.
PR #40 jest otwarty/draft; praca odbywa się w osobnym worktree.
Zależności potwierdzono w implementacji i testach: region GPX z SQL (U05),
bezpośrednie wejścia kanoniczne z osobnym Git baseline (U07) i helpery U08.
Zegar UTC był już wspólny po U08; nie dodano drugiego zegara. Usunięto
martwy `BestMeasurementsExportValidationError` oraz alias
`BuildDatabaseValidationError` po sprawdzeniu wszystkich odbiorców w repo.
Rzeczywisty `CatalogValidationError`, `GpxGroupingError` i ich kanały pozostały.

Pełny zestaw nadal definiuje `ReleaseArtifactsResult.artifact_paths`,
korzystający z 8 ścieżek `BestMeasurementsExportResult.artifact_paths`.
Pięć dodatkowych nazw buildera obsługuje też ochronę standalone Best.
`--artifact-list` przekazuje 13 ścieżek zakończonych NUL na stdout po sukcesie.
Lista workflow jest poza katalogiem paczki; nie powstał drugi pełny rejestr.
Wspólny guard sprawdza komplet przed atomową podmianą i podczas pakowania
preview. Zaufany publisher komentarzy i jego uprawnienia są niezmienione.

### Weryfikacja lokalna

- Przed: **143 PASS** wskazanego zestawu karty; pełny build przy stałym czasie
  `2026-11-06T12:00:00Z`, wersji `v1.3.3` i source commit równym bazie refaktoru.
- Nowe regresje na bazie: **6 FAIL / 8 PASS**. Odtworzono brak, nadmiar,
  ścieżkę poza output, symlink i duplikat ścieżki oraz brak interfejsu listy.
  Po wdrożeniu: **14 PASS**. Istniejące regresje późnego serializera nadal
  sprawdzają zachowanie poprzednich bajtów; nie zastąpiono ich mockiem builda.
- Odbiór shell wykonuje rzeczywiste kroki build/publish z `release.yml`:
  build używa produkcyjnego CLI na kanonicznym fixture, ze wskazanym Git baseline;
  wyłącznie sieciowe wywołanie `gh` jest zastąpione zapisem argumentów.
  Spacje/LF w ścieżce są zachowane, obcy plik pominięty, błąd builda blokuje
  dalszy krok i zachowuje wcześniejsze wyjście. Bez tagu ani prawdziwej publikacji.

- Rozszerzony zestaw karty wraz z CLI/workflow: **163 PASS**; Node publisher:
  **28 PASS**. Utrwalone **20/20** przypadków czterech publicznych CLI ma
  identyczne kody i pełne stdout/stderr przed/po. Znormalizowano wyłącznie
  losową ścieżkę osobnego repozytorium fixture.
- Pełny odczyt **13/13 formatów** przed/po: wszystkie wartości, kolejność,
  typy/null, precyzja i deklaracje są identyczne; 9 plików tekstowych również
  bajtowo. XLSX: wszystkie komórki/typy/formaty/tabele i części XML; Shapefile:
  rekordy/geometria/pola/CRS; GeoPackage: integralność, cała zawartość i schemat;
  dump: natywny restore, wszystkie tabele, oba widoki Best oraz DDL.
  Normalizacje: nagłówki ZIP, data DBF, czas utworzenia GeoPackage i losowy
  token klienta dumpa. Czas GeoPackage dotyczy `gpkg_contents.last_change`
  i `gpkg_metadata_reference.timestamp`. Nie normalizowano danych ani CRS.
- Standalone Best: **8/8** plików zgodnych z bazą; lokalne preview: 15 nazw
  i **14/14 sum**. Katalog: 1029 obiektów, 1019 jaskiń, 1946 pomiarów,
  27 manual Best; 0 błędów / 4185 ostrzeżeń.
- Python produkcyjny **+140/−155, netto −15**, także bez różnic whitespace;
  SQL/schematy **0**, testy **+218/−65**, workflow **+14/−19**.
  `data/`, `config/`, `schema/`, zależności i pozostałe workflow są niezmienione.
- Niezależny review: **brak uwag Critical/Important/Minor**; cztery kolejności
  importów, domyślne flagi czterech CLI i diff PASS. Rozstrzygnięcia granic:
  usunięte nazwy wyjątków nie mają odbiorców w repo (zewnętrznych odbiorców
  nie można potwierdzić skanem); kolejność publikacji/cleanup pozostaje zgodna
  z projektem; równoległa ingerencja zewnętrznego procesu nie jest kontraktem
  guardu plików staged. CI i pobrana paczka podlegają osobnemu odbiorowi poniżej.

- Pełna lokalna bramka `scripts/check_project.py --base-ref
  ad5fa191a36d5a5f45f0b2de523bd39125827573`: **1535 PASS / 1 SKIP**,
  Ruff, historia, build, restore dumpa, GeoPackage i diff — PASS.
  Runtime: własny PostgreSQL 18.6/PostGIS 3.6.4, zgodny GDAL/PROJ z QGIS.
  Skip: osobny smoke zarządzanego Dockera, wymagany w CI. Po odbiorze nie
  pozostały tymczasowe bazy ani role katalogu. **101** względnych linków
  zmienionej dokumentacji prowadzi do istniejących plików.

### Dostarczenie i preview kodu

Kod U10 dostarczono fast-forward do draft PR #40 jako
`478365a10c628e9b1af9621ff4893645380de433`; zdalny SHA potwierdzono.
[Preview](https://github.com/dlubom/gps-kataster-obiektow-tatr/actions/runs/42211471174)
zakończone **SUCCESS**, próba 1.
[Paczka 13498838136](https://github.com/dlubom/gps-kataster-obiektow-tatr/actions/runs/42211471174/artifacts/13498838136)
ma SHA-256 `0fa89f141c00204c59d9110c1ee80b317343a6a2bc3d2d9a5630100a5337d0eb`,
zgodny z GitHub. **14/14 sum**, 15 nazw oraz head/base/merge
`1e21b2b82887ce64666aac289f24d90a9d3203e6`, run i próba są poprawne.
Sprawdzono rodziców rzeczywistego merge i zgodność jego kodu/danych z head.

Niezależny pełny odczyt **13/13 formatów** potwierdził zgodność z lokalnym
buildem przy czasie i source commit z manifestu. Źródła, typy/null, cała
historia, kolejność pomiarów, 27 manual Best i WKT/datum są porównane ściśle.
Dla **21982** pochodnych wartości EPSG:2180 maksymalna różnica wyniosła
`1.9208528101444244e-9 m`, przy absolutnej tolerancji `1e-8 m`.

Dodatkowe różnice runtime z CI znormalizowano jawnie: warianty deklaracji
triggerów RTree i układ fizycznych stron indeksu (każdy indeks odbudowano
z geometrii i sprawdzono `rtreecheck` oraz insert/update/fid/null/delete na
kopiach), komentarze wersji klientów dumpa oraz reprezentację numeryczną
XML XLSX po porównaniu wszystkich komórek/typów/formatów. Reszta struktury
XML, deklaracje i wszystkie dane są porównane. Nie normalizowano CRS.
Końcowe CI dokumentacji i odbiór jego paczki wskazuje opis PR; kod i dane
po tej aktualizacji dokumentacji pozostają identyczne z odebranym SHA kodu.

[Validate code and data](https://github.com/dlubom/gps-kataster-obiektow-tatr/actions/runs/42211471203)
zakończone **SUCCESS** dla dokładnego SHA kodu, próba 1: **1534 PASS / 2 SKIP**;
oddzielny wymagany smoke zarządzanego Dockera: **1 PASS**. Historia i końcowy
cleanup kontenerów zakończone sukcesem. Skips zwykłego zestawu dotyczą smoke
uruchamianego osobno i testu klienta native przy klientach kontenera. Nie było
anulowań ani ponowień przebiegów U10. Wynik końcowego SHA dokumentacji i jego
preview jest potwierdzany w opisie PR.

Zlecenie kończy się na U10. U11 nie rozpoczęto; indeks zawiera prompt do
odrębnego zlecenia. PR pozostaje draftem, bez merge, taga ani wydania.
