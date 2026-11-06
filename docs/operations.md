# Dokumentacja operacyjna

Ten dokument opisuje pracę na rekordach YAML w `data/`. Schemat
`schema/catalog.sql` odtwarza tymczasowy PostgreSQL/PostGIS; `build/` zawiera
wyłącznie wygenerowane artefakty. [Model i diagramy](architecture/schema.md).

## Runtime lokalny i CI

Wspólny silnik to `postgis/postgis:18-3.6` przypięty digestem
`sha256:4a43e3c3e5d55b9208240fc71db543b79c638766280c625a425bd0a2390989c4`.
Obraz jest `linux/amd64`; ARM wymaga emulacji tej platformy. Dane PG18
są w `/var/lib/postgresql`. Baza jest jednorazowa, bez wolumenu produkcyjnego.
Wymagane: Python 3.12 (CI 3.12.13), uv (CI 0.11.8), GDAL z `ogr2ogr`
(CI Ubuntu 24.04: `gdal-bin=3.8.4+dfsg-3ubuntu3`) oraz Node 24 (CI 24.22.2).
Plik `.python-version` przypina lokalny interpreter 3.12.13.
Zależności Python instaluje `uv sync --frozen` z `uv.lock`.
[Wersja GDAL w Ubuntu](https://packages.ubuntu.com/noble/gdal-bin).

Przy porównaniu GeoPackage z CI używaj zgodnej bazy definicji CRS GDAL/PROJ
(`PROJ_DATA`), np. narzędzi dostarczanych z QGIS. Sam kod EPSG:2180 nie
uzasadnia pominięcia różnicy WKT lub datum. Odbiór U09 porównuje je ściśle;
różne lokalne bazy CRS rozstrzyga przez dobór runtime, a nie normalizację.

```bash
git fetch origin
uv sync --frozen
uv run --frozen python scripts/check_project.py --base-ref origin/main
```

Runner wykonuje formatowanie, lint, pełne testy, walidację historii, kompletny
build i `git diff --check`. Wszystkie procesy dzielą jeden zarządzany serwer;
każdy katalog/restore dostaje własną losową bazę. Wyniki są w
`build/verification/exports` (można zmienić przez `--output-dir`). Brak Dockera,
timeout startu, błąd kontroli albo cleanup daje błąd procesu. Cleanup dotyczy
wyłącznie własnego kontenera `kataster-<uuid>`. Nie resetuj Docker Desktop ani
innych kontenerów w ramach walidacji.

Builder przygotowuje wspólne, niezmienne dane eksportowe raz po walidacji.
Best, Excel, GeoPackage i statystyki korzystają z tej samej historii, wyboru
PostgreSQL i czasu generowania. Samodzielny eksport Best używa tego samego
przygotowania. Pominięte i null pola starego pomiaru pozostają puste.
Regiony GPX pochodzą z `v_measurement_regions` przez jedno zbiorcze zapytanie
projekcji na istniejącym połączeniu. `ST_Covers` i `boundaries.ordinal` określają
przypisanie, także na granicach poligonów i ich otworów. Niezmienne metadane
odczytu nie trafiają do YAML ani publicznych kolumn. Grupowanie używa regionu
faktycznie wybranego Best; brak/nieznany region i grupa ponad 500 punktów dają
`GpxGroupingError` przed publikacją, zachowując wcześniejsze pliki.
Walidacja geografii korzysta wyłącznie z `v_geography_issues` w PostGIS;
API walidatora nie przyjmuje `prefix_resolver`. Wszystkie pomiary są
sprawdzane względem regionów: poza zasięgiem to error, poza dolinami w PL/SK
to warning. Rozbieżność trwałego prefixu z wybranym Best (także manual)
i odległość par pomiarów ponad 100 m pozostają warningami z lokalizacją
w pliku źródłowym. Resolver Pythona nadal obsługuje propozycje nowych ID.

Samodzielne CLI (`validate.py`, `build_release_artifacts.py`) także uruchamiają
zarządzany kontener, jeśli `KATASTER_DATABASE_URL` nie jest ustawiony. Do
natywnego zgodnego serwera PostgreSQL 18/PostGIS 3.6 ustaw URL administratora
z prawami tworzenia/usuwania tymczasowych baz i ról oraz katalog narzędzi PG18:

```bash
export KATASTER_DATABASE_URL='postgresql://postgres@127.0.0.1:5432/postgres'
export KATASTER_PG_BIN='/path/to/postgresql18/bin'
uv run --frozen python scripts/check_project.py --base-ref origin/main
```

Skonfigurowany zewnętrzny serwer nie jest zatrzymywany. Własne bazy i role są
usuwane. `KATASTER_POSTGRES_CONTAINER` wskazuje kontener serwera, aby dump i
restore używały jego zgodnych klientów; nie ustawiaj go przy serwerze native.
Nie używaj klientów starszego PostgreSQL do dumpa PG18.

Opcjonalny interaktywny silnik: `compose.yaml` ma ten sam obraz i losowy port
loopback, hasło jest wymagane; `tmpfs` zapobiega pozostawieniu katalogu bazy:

```bash
export KATASTER_POSTGRES_PASSWORD="$(openssl rand -hex 24)"
docker compose -p kataster-review up -d --wait
export KATASTER_POSTGRES_CONTAINER="$(docker compose -p kataster-review ps -q postgres)"
export KATASTER_DATABASE_URL="postgresql://postgres:${KATASTER_POSTGRES_PASSWORD}@$(docker compose -p kataster-review port postgres 5432)/postgres"
uv run --frozen python scripts/validate.py --base-ref origin/main
docker compose -p kataster-review down --volumes
unset KATASTER_POSTGRES_CONTAINER KATASTER_DATABASE_URL KATASTER_POSTGRES_PASSWORD
```

CI używa tego samego obrazu jako usługi na Ubuntu 24.04; `pg_dump` i
`pg_restore` działają wewnątrz tej usługi. Oddzielny obowiązkowy test
`KATASTER_DOCKER_SMOKE=1` uruchamia dodatkowy zarządzany kontener, odczytuje
port, ładuje katalog, wykonuje dump/restore i sprawdza usunięcie po błędzie.
Lokalnie test ten jest jawnie pomijany, gdy przełącznik nie jest ustawiony.

Historia CI: PR używa `pull_request.base.sha`, push main — `before`, tag
wydania — pierwszego rodzica commitu przyjętego na `origin/main`. Ręczne
mutacje używają `origin/main`, a na jego tipie pierwszego rodzica. Checkout
pobiera pełne obiekty Git; `scripts/ci_baseline.py` odrzuca brak, zero,
niedostępny commit i baseline równy kandydatowi. Baza jest przekazywana jawnie
do walidatora i buildera; preview używa wymaganego `--base-sha`. Kod PR ma
`contents: read`; osobny zaufany publisher czyta wyłącznie metadane GitHub,
bez pobierania i wykonywania paczki PR. Retencja paczki wynosi 14 dni.

### Wspólny setup GitHub Actions

`validate.yml`, `pr-preview.yml`, `release.yml` i `mutation.yml` wywołują
lokalną composite action `.github/actions/setup-runtime`. Jest jednym
właścicielem instalacji przypiętych Python/uv/GDAL, konfiguracji zgodnych
klientów z kontenera PG18 oraz `uv sync --frozen`. Port i ID serwisu są
przekazywane przez `env`, bez interpolowania wejścia do kodu powłoki.
Preview jawnie wyłącza cache uv; pozostałe trzy workflow zachowują cache.
Node 24.22.2 pozostaje osobnym krokiem tylko w validate/mutation.

Każdy workflow nadal deklaruje zdarzenia, uprawnienia, checkout pełnej
historii bez zachowanych credentials, serwis z przypiętym digestem i komendy
kontroli/publikacji. Po setupie `scripts/ci_baseline.py` rozstrzyga rzeczywisty
baseline, przed testami, walidacją i buildem. Setup instaluje zależności;
nie zastępuje żadnej bramki ani wyniku walidacji innego commitu.
Zaufany `publish-pr-preview.yml` pozostaje odrębny i nie używa tej akcji.
Release zachowuje `contents: write` wyłącznie na istniejącym zdarzeniu taga.
[Zakres i odbiór U11](asdlc/plans/PR-40/tasks/U11-ci-setup.md#odbiór).

### CLI i zestaw artefaktów

`build_db.py`, `export_best_measurements.py`, `build_release_artifacts.py`
i `validate.py` współdzielą argumenty `--data-dir`, `--base-ref` (domyślnie
`origin/main`) i `--history-repo`. Trzy komendy generujące pliki współdzielą
też `--generated-at`; nadal używają zegara UTC U08. Każda operacja zachowuje
własny parser, wywołanie i podsumowanie.

Walidator wypisuje diagnostykę na stdout. Build dumpa i pełnego wydania
wypisują tam rozpoznane błędy walidacji/historii, a pozostałe błędy na stderr.
Best zachowuje swoje `error:` na stderr także dla błędu historii. Kod 1 oznacza
błąd operacji, kod 2 błąd argumentów; ostrzeżenia nie blokują poprawnego wejścia.
Wspólne formatowanie nie zmienia tej polityki ani zaakceptowanego baseline.

`build_release_artifacts.py --artifact-list` udostępnia po sukcesie ten sam
sprawdzony komplet 13 ścieżek co builder, rozdzielony bajtami NUL. Domyślne
komunikaty tekstowe pozostają bez zmian. Lista dla workflow leży poza paczką;
Best nadal chroni pełne wydanie po kontroli wejścia i historii.
Wskazuj osobny katalog wynikowy: źródłowe `data/`, jego podkatalogi
i przodkowie, korzeń repozytorium oraz `.git` są odrzucane, także przez
dowiązania. Istniejące wyjście może zawierać tylko zwykłe pliki bieżącego
zestawu artefaktów. Obce pliki, podkatalogi i dowiązania zatrzymują eksport
bez nadpisania; wybierz inny katalog lub samodzielnie uporządkuj zawartość.
Każde bieżące wejście wymaga `catalog.json` z `format: postgresql-yaml`
i `schema_version: 2` oraz czterech katalogów encji. Legacy bez znacznika
jest odrzucane przed bazą i publikacją wyjścia; nie jest automatycznie migrowane.
[Kontrakt paczkowania](release_artifacts.md#oficjalna-paczka-wydania),
[odbiór U10](asdlc/plans/PR-40/tasks/U10-artifacts-and-cli.md#odbiór).

## Pobieranie jaskiń, lejów i sztolni z API TPN

```bash
uv run --frozen python scripts/fetch_tpn_data.py
uv run --frozen python scripts/fetch_tpn_data.py --output data/sources/tpn/api/moj-zrzut.json
```

Domyślnie powstaje nowy `data/sources/tpn/api/tpn-<UTC>.json` w katalogu
repozytorium, także przy uruchomieniu skryptu z innego katalogu roboczego.
Wskazany `--output` jest ścieżką względem bieżącego katalogu lub absolutną.
Katalog `data/sources/tpn/api/` jest ignorowany przez Git: zrzuty pozostają
lokalnymi plikami i **nie są commitowane**. Sam skrypt nie wykonuje operacji Git.
`--timeout` ogranicza każde żądanie HTTP (domyślnie 30 sekund).

Jeden JSON UTF-8 z wcięciami zawiera `schema_version: 1`, `started_at`,
`finished_at` (UTC) i osobne `layers.jaskinie`, `layers.leje_krasowe`,
`layers.sztolnie_kopalnie`. Każda warstwa zachowuje:

- `source_url`, wszystkie `request_urls`, pełne `metadata` JSON i `metadata_xml`;
- `object_ids`, `record_count` oraz scalony źródłowy `feature_set`;
- wszystkie `feature_set.features[].attributes`, także nowe pola, null
  i daty źródłowe w formacie API, bez mapowania do modelu katalogu;
- `feature_set.features[].geometry` żądaną w EPSG:4326: `x` to długość,
  `y` szerokość geograficzna. Źródłowe Z/M, jeśli dostępne, są zachowywane;
  nie przypisujemy im datum pionowego. Brak geometrii pozostaje brakiem.
  Pusty punkt ArcGIS (`{"x": null}`, także z `"y": null`) zachowujemy
  bez zmian; nie jest błędem współrzędnych.

Pełne metadane warstwy zawierają m.in. aliasy, typy i domeny kodowe pól,
opisy oraz układy źródłowe. `SHAPE` jest opisem pola geometrii w metadanych,
nie dodatkowym atrybutem rekordu. Metadane nie są przeliczane do WGS84;
układ zwróconych punktów określa `feature_set.spatialReference`.

Źródła: [jaskinie](https://gis.tpn.pl/server/rest/services/Topografia___wektor_MIL1/MapServer/6),
[leje](https://gis.tpn.pl/server/rest/services/SIPTPN/Geologia_i_gleby/MapServer/3),
[sztolnie i kopalnie](https://gis.tpn.pl/server/rest/services/SIPTPN/Dziedzictwo_kulturowe/MapServer/13).
Są pobierane w całości, bez filtrów geograficznych lub deduplikacji między
warstwami. Nie każdy lej jest potwierdzoną formą krasową, a nazwy sztolni
mogą opisywać rejon; zachowujemy źródłowe zastrzeżenia.

Skrypt porównuje niezależny licznik i listę ID przed/po oraz komplet każdej
partii. To nie jest transakcja serwera: zmiana atrybutów istniejącego ID
w trakcie pobierania może pozostać niewykryta. Przedział UTC opisuje pobranie,
nie datę pomiaru. Obecnie trzy warstwy nie deklarują załączników ani relacji;
skrypt zachowuje te deklaracje, ale nie pobiera plików załączników.

Gotowy wynik jest publikowany atomowo, dopiero po pobraniu trzech warstw.
Istniejący plik (również utworzony równolegle) nie zostanie nadpisany.
HTTP/API error, niepełny zbiór, błędna odpowiedź lub błąd zapisu daje kod 1
i diagnostykę na stderr, bez częściowego pliku wynikowego.
Bez importu, porównań, zmian YAML i `best` lub automatyzacji.
[Kontrakt i odbiór PBI-108](asdlc/plans/PBI-108.md).

### Uproszczone pliki i wysokość NMT

Do czytania danych użyj wersji simple. Możesz ją utworzyć z istniejącego
zrzutu bez ponownego pobierania warstw:

```bash
uv run --frozen python scripts/fetch_tpn_data.py \
  --input data/sources/tpn/api/tpn-20261022T162014287693Z.json \
  --simple-dir data/sources/tpn/api/simple-20261022 --with-nmt
```

Pomiń `--with-nmt`, aby utworzyć tylko `simple.json`, całkowicie offline.
Można też połączyć pobranie nowego źródła z uproszczeniem:
`scripts/fetch_tpn_data.py --simple-dir data/sources/tpn/api/nowy-simple --with-nmt`.
`--input` wyklucza `--output` i wymaga `--simple-dir`.
Wybierz nowy katalog docelowy; istniejące pliki nigdy nie są nadpisywane.
Surowy zrzut i pliki simple muszą mieć różne ścieżki. Kolizja, również
przez ścieżkę względną lub dowiązanie katalogu, przerywa polecenie przed
pobieraniem danych i tworzeniem plików.

- `simple.json`: trzy listy (`jaskinie`, `leje_krasowe`, `sztolnie_kopalnie`),
  jeden płaski rekord na obiekt, wszystkie atrybuty poza `CREATED_USER`,
  `CREATED_DATE`, `LAST_EDITED_USER`, `LAST_EDITED_DATE`, plus `lat`/`lon` WGS84.
  Nazwy pól, ID, null, uwagi i nieznane/przyszłe atrybuty są zachowane.
  Znane kody są zastąpione opisami z domen zapisanych w surowym zrzucie;
  nieznane kody pozostają źródłowymi wartościami. Np. `WERYF: "1"` lejów
  staje się `WERYF: "odnaleziony"`. Nie interpretujemy `TATER` ani `FIELD`.
  Dodatkowe składowe geometrii (np. źródłowe Z/M) zachowuje
  `geometria_dodatkowa`; nie stają się one wysokością NMT.
- `simple-nmt.json`: te same rekordy i dodatkowo `wysokosc_gruntu_nmt_m`
  (metry n.p.m. według legendy TPN) oraz `status_nmt`: `ok`, `brak_danych`
  lub `brak_wspolrzednych`. W dwóch ostatnich przypadkach wysokość jest
  `null`; żaden rekord nie znika i nie zastępujemy braku zerem.
- `nmt-evidence.json`: osobny techniczny zapis pochodzenia — SHA-256
  wejściowego pliku, ID rekordów i pełne wyniki istniejącego czytnika NMT:
  źródło, model, daty, raw value, URL-e i hashe. Nie ma tych metadanych
  w dwóch plikach do czytania.

Surowy zrzut pozostaje niezmienny. NMT jest odczytywany dla dokładnego
punktu źródłowego każdego rekordu, bez filtrowania lub łączenia warstw.
Wysokość dotyczy **gruntu**, a nie gwarantowanej wysokości otworu w ścianie.
Dokładny układ pionowy i dokładność są nieznane; najnowszość modelu
`nmt_05m_mggp_2019` jest niepotwierdzona. Zaokrąglenie w pliku simple do
dwóch miejsc dziesiętnych służy czytelności, nie określa dokładności.
Pełna liczba z API pozostaje w osobnym dowodzie.

Czytnik sprawdza usługę, XML modelu i legendę raz na partię, następnie
wykonuje jedno żądanie na każdy punkt. Wypisuje postęp na stderr.
Tylko faktyczne `NO_DATA` oznacza brak pokrycia; błąd HTTP/API, wadliwa
odpowiedź lub zmiana modelu przerywają odczyt (exit 1). Plik simple może
już istnieć, ale `simple-nmt.json` powstaje atomowo dopiero po odczycie
całej partii i zapisaniu osobnego dowodu. Każdy plik jest publikowany
oddzielnie, bez transakcji obejmującej całą grupę plików.
Zrzut i wersje simple w `data/sources/tpn/api/` pozostają lokalne,
ignorowane przez Git; nie trafiają do paczki katalogu ani do wydania.
[Zakres i weryfikacja PBI-109](asdlc/verification/PBI-109.md).

## Wysokość gruntu z publicznego NMT TPN

```bash
uv run --frozen python scripts/tpn_elevation.py --lat 49.2320 --lon 19.9816
uv run --frozen python scripts/tpn_elevation.py --lat 49.2320 --lon 19.9816 --json
```

Jeden punkt WGS84 w stopniach dziesiętnych; wynik jest wyłącznie odczytem.
Lokalny skill: [`tpn-elevation`](../.agents/skills/tpn-elevation/SKILL.md).
`--json` zachowuje surową wartość API, metadane, źródłowe URL-e i hashe.
`--timeout` określa limit pojedynczego żądania (domyślnie 20 sekund).

Źródło: publiczny NMT TPN `nmt_05m_mggp_2019`, siatka 0,5 m.
Wynik jest publikowany jako **m n.p.m. według legendy TPN**. JSON oddziela
`elevation_reference: sea_level` od `elevation_datum: unknown`: dokładny
układ pionowy (np. Kronsztadt86 lub PL-EVRF2007-NH) nie jest zadeklarowany.
Odczyt sprawdza nagłówek legendy warstwy 0 i zachowuje jej URL oraz hash.
[Dokumentacja TPN](https://geoportaltatry.pl/informacje_o_usludze/topografia.pdf),
strona 4 „Wysokości”, podaje nalot 14–15.10.2019 r., 12 pkt/m² i raster
0,5 m utworzony w TerraSolid z modelu trójkątowego po klasyfikacji LiDAR.
`source.data_date` zachowuje zakres `2019-10-14/2019-10-15` z odnośnikiem
do tego opisu. Skrypt wykonuje cztery żądania HTTP.
Najnowszość jest **niepotwierdzona**, dokładność pionowa i interpolacja
pozostają **unknown**. Siatka i liczba cyfr nie określają dokładności.
To wysokość gruntu w modelu, nie gwarantowana wysokość otworu jaskini.

Brak danych i błędy dają niezerowy exit oraz diagnostykę na stderr.
`SOURCE_CHANGED` oznacza potrzebę ponownego przeglądu metadanych modelu;
skrypt nie przypisuje nowemu źródłu parametrów starego. Bez automatycznej
zmiany modelu, YAML lub `best`. [Kontrakt i źródła](asdlc/plans/PBI-106.md).

## Struktura wejścia danych

Katalog wymaga znacznika `data/catalog.json` z `format: postgresql-yaml`
i `schema_version: 2` oraz katalogów `objects`, `caves`, `relations` i
`publications`. Obiekty zapisuje się w `objects/PREFIX/ID.yml`, pozostałe
encje w odpowiednich katalogach jako `ID.yml`; rozszerzenie `.yaml` także
jest obsługiwane i zachowywane przy edycji. Puste katalogi zachowują
`.gitkeep`. Jeden plik zawiera encję, jej pomiary, referencje i załączniki.
Brak któregokolwiek z czterech katalogów albo plik zamiast katalogu blokuje
odczyt przed uruchomieniem bazy oraz przygotowaniem i zapisem wyjścia.
Walidator/CLI zgłasza `DATA_DIRECTORY_INVALID` z właściwą ścieżką; build
zachowuje `DataDirectoryError`. Istniejące YAML
i artefakty pozostają bez zmian. Nie twórz katalogów podczas odczytu,
aby ukryć niepełne wejście. Błędny/brakujący znacznik domyślnego źródła
nadal ma pierwszeństwo w diagnostyce kanonicznego CLI.

Legacy bez znacznika, używane przez historyczne rewizje i wewnętrzne propozycje,
wymaga `objects`, `caves` i `relations`. Może nie mieć `publications`;
nieobecność oznacza pustą bibliografię, lecz istniejący plik tej nazwy jest
błędem. Odczyt Git nie naprawia zaakceptowanej rewizji: bierze układ z jej
rzeczywistych ścieżek, w tym katalogi utrwalone plikami pomocniczymi.

W YAML jawne `null` i pominięcie klucza to odrębne stany. Daty i czasy
zapisuj jako cytowane ciągi. Loader odrzuca powtórzone klucze i przekazuje
wartości do PostgreSQL jako parametry na ograniczonym koncie.

Adapter sprawdza strukturę i typy przed konwersjami sterownika: liczba w polu
tekstu, tekst w polu liczby, bool zamiast liczby i ułamkowe pole całkowite są
błędami. Referencje i publikacje wymagają poprawnego bezwzględnego URI;
sprawdzenie składni nie pobiera strony ani nie potwierdza jej dostępności.

Zapisuj `cave_id` i dodatnie `membership_ordinal` przy obiekcie. Kolejność
jest unikalna w jaskini i może zawierać luki; przeniesienie dopisuje obiekt
za jej ostatnim numerem. `object_ids` jest wyliczane wyłącznie do odczytu.
W pomiarze podaj jedną reprezentację źródłową: `lon`/`lat` albo komplet
`input_srid`/`input_x`/`input_y`. Pola `x_1992`/`y_1992` są wyliczane.
W `mode: auto` pomiń `measurement_id`; ręczny wybór zachowuje to pole.
Kanoniczny loader odrzuca pola wyliczane, aby edycja nie była ignorowana.

### Przydzielanie ID

`id_allocation.IdSequence` obsługuje `assign_id`: numer jest największym
istniejącym + 1, bez wypełniania luk. `file_ids` rozpoznaje rzeczywiste pliki
`.yml`, `.yaml` i `.sql`; loader katalogu nie przyjmuje plików SQL. Propozycja
nie zapisuje YAML ani trwałej rezerwacji. Nie ma rejestru wycofanych ID ani
ochrony przed równoległym przydziałem; kolizje blokuje walidacja.

Buildery i CLI używają `utc_timestamp` z dokładnością do sekundy; jawny
`--generated-at` ma pierwszeństwo.

### Granice walidacji w Pythonie

| Punkt wejścia | Stan i wykonane kontrole |
|---|---|
| `load_yaml_dataset` | Rekordy v2 z surowymi polami i ścieżkami; znacznik, katalogi, limity rozmiaru, blokada dowiązań YAML, składnia i unikalne klucze. Bez bazy i kontroli domeny/historii. |
| `read_catalog_projection` | Zawsze projekcja PostgreSQL po kontroli wejścia przez adapter. Zawiera pola wyliczane; bez pełnej walidacji domeny i Git. |
| `validate_catalog` | Kontrola już załadowanego stanu SQL, ścieżek i załączników. Bez odczytu YAML, odbudowy projekcji ani kolejnej bazy. |
| `validated_catalog_source` | Źródło YAML i kontrola stanu SQL; zwraca jedno połączenie, jedną projekcję i diagnostykę. Bez historii Git. |
| `history_checked_catalog` | Wspólna bramka builda i kanonicznego CLI: powyższe kontrole oraz wymagany `base_ref` z zaakceptowanej rewizji. Historia używa tego samego połączenia. |

`validate_data_dir` raportuje kontrole kanonicznego wejścia v2 i SQL;
nie wykonuje kontroli Git. Wyłącznie adapter historii czyta starszy baseline
v1; `history_schema.py` zachowuje potrzebne schematy JSON i diagnostykę.
Polecenie `scripts/validate.py` zawsze dodaje rzeczywistą bazę historii.
Pusty katalog jest poprawny strukturalnie, ale zastąpienie nim niepustej
zaakceptowanej bazy narusza ochronę historii. `schema/history.sql` porównuje
źródłowe wartości i kolejność pomiarów z danymi odczytanymi z Git:

```bash
uv run python scripts/validate.py --data-dir data --base-ref origin/main
```

Brak wskazanej rewizji oraz Git blob zamiast drzewa `data` dają
`HISTORY_BASELINE_UNAVAILABLE`, bez publikacji wyników. CI podaje SHA rzeczywistej bazy PR albo
poprzedniego stanu main; nie buduje baseline z danych kandydata.

## Jednoznaczne klucze YAML

YAML jest formatem katalogu i historycznych fixture'ów.
Klucze każdej mapy muszą być unikalne, także
wewnątrz pomiarów. Parser wskazuje plik, klucz oraz obie
lokalizacje duplikatu. Zwykłe aliasy i merge keys o rozłącznych kluczach są
legalne; kolizje po rozwinięciu są błędem, także przy identycznej wartości.

Narzędzia katalogu czytają YAML, walidują i publikują eksporty. Nie ma
programowego writera źródeł ani interfejsów propozycji. Źródła edytuj ręcznie
w YAML i sprawdzaj w PR. Atomowa publikacja eksportów nadal zachowuje
poprzednie wyniki przy awarii przed podmianą katalogów.

## Pozycja z sieci pomiarowej jaskini

`method: siec_pomiarowa` oznacza pozycję wyznaczoną z sieci pomiarowej
jaskini, również z powiązanych ciągów powierzchniowych. W `source_ref`
i `notes` zapisz rewizję źródła, stację i kotwicę sieci. Nie oznaczaj
punktu jako GNSS tylko dlatego, że kotwica pochodziła z GNSS. Wynikowa
wysokość ma `elevation_source: other`; nieznane datum i dokładności
pozostają nieznane. Zapisany punkt dowiązania o niepotwierdzonej pierwotnej
metodzie ma `method: source_record`, `elevation_source: source_record`.
Nowa metoda nie zmienia statusu weryfikacji, priorytetu auto ani manual best.

## Dodanie recznego pomiaru

1. Otwórz `data/objects/{PREFIX}/{OBJECT_ID}.yml`. Dopisz pozycję na końcu
   listy `measurements` i nadaj jej kolejne wolne lokalne `id` (`m-NNN`).
2. Podaj `input_srid` (4326 albo 2180) oraz `input_x` i `input_y`. Dla 4326
   X to długość, Y to szerokość. Dla 2180 X to easting, Y to northing.
   Możesz też podać `lon` i `lat` w EPSG:4326. Wysokość i datum są osobne.
3. Uzupełnij źródło, `source_ref`, datę, metodę, autorstwo i znane dokładności.
   W `best_measurement` wybierz `mode: auto` lub `mode: manual` z `measurement_id`
   oraz niepustym `reason`. Zaktualizuj audyt obiektu i uruchom walidację.

Korekta pozycji albo wysokości wymaga nowego pomiaru. Błędny stary pomiar
można oznaczyć jako odrzucony i objaśnić notatką. Zmiana notatki lub statusu
nie przelicza i nie zastępuje jego źródłowej geometrii.

Nowe ID obiektu można zaproponować poleceniem:

```bash
uv run python scripts/assign_id.py 49.2425 19.8147
```

## Bibliografia i nowe obiekty

Obiekt i jaskinia mają niezależny `bibliography_status`: `known` albo `unknown`.
Jawne `unknown` jest dozwolone także przy tworzeniu nowego wpisu, np. z TPN.
`known` wymaga cytowania we właściwej tabeli: `cave_citations` lub
`object_citations`. Pomiary mogą osobno wskazywać `measurement_citations`.

Publikację zapisujemy w `data/publications/` z pełnym cytowaniem tekstowym,
aby dało się ją znaleźć także bez działającego URL. Przywołanie wskazuje
publikację i lokalizator, np. strony, tabelę albo pozycję wykazu. Cytowania
jaskini nie kopiujemy automatycznie na wszystkie otwory. Referencje TPN/PIG
pozostają osobnymi informacjami o pochodzeniu i identyfikatorach.

## Cwiczeniowy pomiar testowy

Kopiuj cały katalog: ochrona historii powinna widzieć wszystkie istniejące
pomiary, również te spoza ćwiczonego obiektu.

```bash
catalogue_demo_dir="$(mktemp -d)"
cp -R data "$catalogue_demo_dir/data"
```

W kopii `objects/KSW/KSW-0001.yml` dopisz pomiar na końcu `measurements`
i nadaj mu nowe lokalne `m-NNN`. Dodaj w `notes` informację o ćwiczeniu,
wartości testowe, datę i pochodzenie zgodnie z regułami powyżej.

```bash
uv run python scripts/validate.py --data-dir "$catalogue_demo_dir/data" \
  --base-ref origin/main
```

Ostrzeżenia o nieznanej dokładności i bibliografii są legalne. Dla próby
negatywnej usuń stary pomiar w kopii: ochrona historii powinna przerwać
walidację. Ćwiczeniowej kopii nie commituj ani nie używaj do wydania.

## Domyslny algorytm `auto`

`best_measurement.mode: auto` jest deterministycznym wskazaniem najlepszego
aktualnego pomiaru. Priorytet zrodel:

1. najnowszy wlasny pomiar ze statusem `zweryfikowany`,
2. najlepszy nieodrzucony pomiar z TPN,
3. najlepszy nieodrzucony wlasny pomiar `nieweryfikowany`,
4. najlepszy nieodrzucony pomiar z PIG,
5. najlepszy nieodrzucony pomiar z innych zrodel.

W tym samym priorytecie wygrywa nowszy czas w UTC: `observed_at`, a przy
jego braku `observed_date` o północy. Następnie niższe `horizontal_accuracy_m`
(brak wartości na końcu), a na końcu stabilny tekstowy porządek po
`measurement.id`. Jezeli wszystkie pomiary sa odrzucone, algorytm wskaze
fallback i walidator pokaze ostrzezenie. `mode: manual` zawsze ma pierwszenstwo,
ale wymaga pola `reason`.

## Walidacja

Przed commitem uruchom lokalna bramke:

```bash
uv sync --frozen
uv run --frozen python scripts/check_project.py --base-ref origin/main
```

`scripts/validate.py` zwraca kod niezerowy tylko dla `error`. Ostrzezenia trzeba
przeczytac i zrozumiec. Błędy constraints są mapowane na kody domenowe
(np. `DUPLICATE_MEASUREMENT_ID`) albo `SQL_CATALOG_INVALID`. Historia raportuje
`HISTORY_BASELINE_UNAVAILABLE`, `HISTORY_OBJECT_DELETED`,
`HISTORY_MEASUREMENT_DELETED`, `HISTORY_MEASUREMENT_CHANGED` i
`HISTORY_ORDER_CHANGED`. Pomiary z początkowego importu PIG/TPN mają znane ostrzezenia
`MISSING_HORIZONTAL_ACCURACY`, bo zrodla nie podaja dokladnosci poziomej.

Jesli lokalny cache `uv` nie jest dostepny w srodowisku sandboxowym, uzyj:

```bash
UV_CACHE_DIR=/private/tmp/uv-cache uv run --frozen python scripts/check_project.py --base-ref origin/main
```

## Testy eksportów i zaakceptowane fixtures

`tests/export_test_support.py` tworzy jawny kanoniczny YAML oraz osobny commit
Git. Zwykły test importuje badane API z modułu produkcyjnego; helper nie
waliduje, nie konwertuje ani nie naprawia kandydata. Najpierw przygotuj poprawny
fixture i wywołaj `accept_source`, potem zmień tylko kandydata i przekaż
zachowane `base_ref`/`history_repo`. `cli_args` formatuje wyłącznie te argumenty.
Puste istniejące katalogi są utrwalane w kopii Git; brakujące nie są dodawane.

`tests/test_legacy_migration.py` sprawdza bieżący fixture v2 względem
rzeczywistego starszego commitu; nie wywołuje konwertera ani writera katalogu.
`make_legacy_history_baseline` w `sql_test_support.py` utrwala v1 w Git,
a `write_canonical_history_source` kopiuje jawne pliki v2 z fixtures.
Schematy JSON i ich zależności pozostają potrzebne do odczytu historii.
Odczyty konsumenckie nadal używają openpyxl, pyshp, SQLite/GDAL i natywnego
restore. [Zakres i odbiór U07](asdlc/plans/PR-40/tasks/U07-production-path-tests.md#odbiór).

## Testy mutacyjne

Testy mutacyjne sa lokalna lub recznie uruchamiana bramka dla krytycznej logiki,
ktorej ciche zepsucie mogloby uszkodzic katalog danych:

- wybor najlepszego pomiaru,
- przeliczanie i walidacja wspolrzednych,
- przypisanie prefixu,
- rozroznienie `error` / `warning` w walidatorze.

Konfiguracja `mutmut` znajduje sie w `pyproject.toml` i ogranicza zakres do
wybranych modulow oraz powiazanych testow jednostkowych. Testy CLI oparte o
`subprocess` zostaja w zwyklej bramce `pytest`, bo `mutmut` uruchamia mutowany
pakiet w osobnym katalogu roboczym.

Pelny przebieg uruchom:

```bash
uv run mutmut run --max-children 2
uv run mutmut results
```

`mutmut` zapisuje stan pracy w `mutants/`. Ten katalog jest ignorowany przez
git, zeby wyniki lokalnych eksperymentow nie trafialy do commitow.

## Tagowany release danych

Oficjalna paczka danych powinna byc publikowana recznie przez tag `vX.Y.Z` z
czystego checkoutu po review zmian w YAML i osobnej zgodzie na wydanie:

1. Zaktualizuj repo i upewnij sie, ze nie ma przypadkowych zmian:

   ```bash
   git status --short
   ```

2. Upewnij sie, ze `CHANGELOG.md` ma nowy wpis `## [vX.Y.Z] - YYYY-MM-DD`.
3. Uruchom pelna bramke walidacyjna z poprzedniej sekcji.
4. Zbuduj artefakty release lokalnie jako dry-run:

   ```bash
   uv run python scripts/build_release_artifacts.py
   ```

5. Sprawdz `build/exports/metadata.json`, zwlaszcza liczniki:

   - `object_count`,
   - `cave_count`,
   - `measurement_count`,
   - `validation_error_count`,
   - `validation_warning_count`.

6. Paczka lokalna znajduje sie w `build/exports/`:

   - `best-measurements.geojson`,
   - `best-measurements.csv`,
   - `best-measurements.gpx`,
   - `best-measurements.shp.zip`,
   - `metadata.json`,
   - `katalog.dump` i `katalog.gpkg`,
   - grupowe GPX, `katalog.xlsx` oraz statystyki JSON/Markdown.

   Dokladny przeglad kolumn i pol tych plikow jest w
   `docs/release_artifacts.md`.

   Samodzielny `scripts/export_best_measurements.py` zapisuje osiem plików
   Best. Jeśli katalog docelowy zawiera dump, GeoPackage, Excel lub statystyki
   pełnego wydania, odmawia zapisu i zachowuje wszystkie pliki. Przebuduj wtedy
   całą paczkę przez `scripts/build_release_artifacts.py` albo wskaż osobny
   `--output-dir`, np. `build/best-only`.

7. Zacommituj zmiany, przeprowadz review w PR i po merge do `main` utworz
   annotated tag:

   ```bash
   git tag -a vX.Y.Z -m "vX.Y.Z - krotki opis"
   ```

8. Wypchnij tag:

   ```bash
   git push origin vX.Y.Z
   ```

   GitHub Actions publikuje release wylacznie po pushu taga `v*` i bierze
   notatki z odpowiadajacego wpisu `CHANGELOG.md`.

Repozytorium, dokumentacja i generowane eksporty danych sa licencjonowane jako
Creative Commons Attribution 4.0 International, zgodnie z plikiem `LICENSE`.
Referencje zrodlowe zapisane w YAML i eksportach trzeba zachowywac jako
atrybucje danych.

W poczatkowych paczkach danych duzy udzial statusu
`verification_status: nieweryfikowany` jest oczekiwany. Import z PIG/TPN tworzy
pomiary zrodlowe, a nie potwierdzone pomiary terenowe projektu. Taki status w
release oznacza: "najlepsza dostepna lokalizacja z zachowana proweniencja, ale
jeszcze bez projektowej weryfikacji operatora". Nie nalezy zmieniac tych
statusow hurtowo na `zweryfikowany`; robimy to tylko po realnym review albo
pomiarze terenowym.

## Statusy weryfikacji pomiarow

| Status | Kiedy uzyc |
|---|---|
| `nieweryfikowany` | Domyslnie dla importu PIG/TPN, nowego pomiaru terenowego przed review i wpisu przepisanego z notatek. Status jest normalny w release, dopoki projekt nie potwierdzil punktu niezaleznie. |
| `zweryfikowany` | Po sprawdzeniu przez operatora/maintainera; dla pomiaru wlasnego oznacza, ze mozna mu ufac w wyborze `best_measurement`. |
| `odrzucony` | Dla pomiaru znanego, ale blednego albo nieuzytecznego. Nie usuwaj go z historii; dodaj notatke wyjasniajaca powod. |

Pomiar odrzucony moze zostac w `measurements`, ale zwykle nie powinien byc
wskazany jako `best_measurement`. Jezeli wszystkie pomiary sa odrzucone,
walidator moze wskazac to jako ostrzezenie.

## Odtworzenie kontekstu TPN (PBI-082)

Jednorazowa naprawa została zakończona. Zachowane etykiety `TPN WER_LOK:` i
`TPN UWAGI:` opisują źródło, a nie weryfikację terenową. [Manifest](asdlc/verification/PBI-082-manifest.json)
i [log](asdlc/verification/PBI-082.md) dokumentują przebieg i pominięte przypadki.
Nowe ustalenia należy wprowadzać ręcznie w YAML i oceniać w PR.

## Dopelnianie brakujacych otworow

Kilka otworow tej samej jaskini moze miec jeden numer inwentarzowy. Wtedy nie tworz
automatycznie nowej jaskini tylko dlatego, ze jest drugi punkt.

1. Znajdz rekord PIG po nazwie albo numerze inwentarzowym:

   ```bash
   rg -n "Mroźna" data/sources/pig/jaskinie_polski_pig_dump.jsonl
   ```

2. W znalezionym JSONL sprawdz szczegolnie pola `other_entrances`,
   `entrance_access_description`, `cave_description`, `documentation_history`
   oraz opisy `images`.
3. Jesli opis potwierdza dodatkowy otwor istniejacej jaskini:

   - dodaj nowy `Obiekt` z wlasnym ID,
   - ustaw `cave_id` na istniejaca jaskinie,
   - ustaw kolejność `membership_ordinal`; lista `Jaskinia.object_ids` jest wyliczana,
   - zachowaj TPN `GLOBALID` na obiekcie i PIG / `NR_INWENT` na jaskini,
   - w notatkach zapisz, z ktorego wiersza TPN i z ktorego pola PIG wynika
     rozstrzygniecie.

4. Jesli opis mowi o osobnej jaskini albo obiekcie nie-jaskiniowym, utworz
   osobna `Jaskinia` tylko dla `jaskinia_otwor`; dla `ponor`, `wywierzysko`,
   `sztolnia` albo `inne` `cave_id` moze zostac `null`, o ile nie ma logicznej
   pozycji katalogowej do powiazania.
5. Uruchom `uv run python scripts/validate.py` i przeczytaj nowe ostrzezenia.

## Commit operacyjny

Po przejsciu bramki:

```bash
git status --short
git diff --stat
git add docs/asdlc/backlog_v1.md docs/asdlc/context.md data schema src scripts tests
git commit -m "docs: add operational workflow"
```

Dobierz `git add` do faktycznego zakresu zmiany. Nie dodawaj `build/`, chyba ze
backlog jawnie zmieni zasade traktowania artefaktow generowanych.

## Skończone liczby pomiarów (PBI-084)

NaN i ±Infinity są niedozwolone w geometrii źródłowej, wysokości
oraz obu dokładnościach, także w historycznym lub odrzuconym pomiarze.
Adapter/SQL odrzuca je jako `SQL_CATALOG_INVALID` z plikiem i diagnostyką
constraints; historyczna nazwa `MEASUREMENT_NON_FINITE` dotyczy pomocniczych
kontroli modelu legacy. Kontrola poprzedza eksport i wybór Best na danych
uznanych za poprawne. PostgreSQL i eksporty blokują operację przed zapisem;
istniejące wyjścia zachowują bajty. Opcjonalne `null`, zera i skończone
wartości zachowują dotychczasową semantykę.

## Rollback formatu PostgreSQL

Przed scaleniem zamknięcie draft PR pozostawia main bez zmian. Po scaleniu
rollback jest osobnym PR/migracją: zachowaj wszystkie nowe rekordy YAML i surowe
źródła, odtwórz snapshot na przypiętym silniku, przenieś nowe pomiary oraz
uzasadnienia i porównaj całą historię z ostatnim zaakceptowanym SHA.
Samo przywrócenie dawnych plików utraciłoby nowe pomiary. Przed podmianą
formatu ponów pełną bramkę, porównanie eksportów i niezależny odczyt. Nie
nadpisuj opublikowanych assetów starego wydania; korekta wymaga nowej wersji.
