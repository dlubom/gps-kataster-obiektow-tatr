# Dokumentacja operacyjna

Ten dokument opisuje codzienna prace na danych YAML w V1. Zrodlem prawdy sa
pliki w `data/`; katalog `build/` zawiera tylko artefakty wygenerowane lokalnie.

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

Walidacja, build SQLite, eksporty, importer TPN i review wymagają istniejącego
root danych oraz katalogów `objects`, `caves` i `relations`. Brak ścieżki lub
plik zamiast katalogu daje błąd z jej nazwą i kod wyjścia 1. Walidator używa
kodu `DATA_DIRECTORY_INVALID`; API loadera zgłasza `DataDirectoryError`.
Przy takim błędzie istniejące artefakty pozostają bajtowo niezmienione,
a nowe wyjścia nie powstają.

Przed pierwszym importem lub dla świadomie pustego zbioru przygotuj strukturę
jawnie (dla osobnego katalogu roboczego):

```bash
mkdir -p /sciezka/do/danych/{objects,caves,relations}
uv run python scripts/validate.py --data-dir /sciezka/do/danych
```

Puste katalogi są legalnym zbiorem z zerowymi licznikami. Loader nie tworzy
ich sam; pominięty katalog `relations` jest błędem również przy braku relacji.

## Jednoznaczne klucze YAML

Rekordy obiektów, jaskiń i relacji oraz pliki decyzji review muszą mieć
unikalne klucze w każdej mapie, także wewnątrz pomiarów i list decyzji.
Drugi klucz `measurements` jest błędem również przy identycznej wartości:
nowy pomiar dopisuj do istniejącej listy. Loader odrzuca duplikat przed
normalizacją i wskazuje plik, klucz oraz linię/kolumnę obu wystąpień.
Walidator zgłasza `YAML_INVALID`; CLI kończy się kodem 1.

Zwykłe aliasy (`&wzor` / `*wzor`) i merge keys (`<<`) o rozłącznych kluczach
są dozwolone. Kolizja po rozwinięciu merge jest błędem: dotyczy to również
jawnego nadpisania odziedziczonej wartości, powtórzenia tego samego aliasu
w merge oraz powtórzonego `<<` w tej samej mapie. Przykładowo
`{<<: {source: TPN}, source: PIG}` jest odrzucane. Zapisz docelową wartość
jednoznacznie w jednej mapie zamiast korzystać z priorytetów nadpisywania.

Błędny YAML blokuje build/eksport i zapis finalnych danych review.
Istniejące artefakty i źródłowe bajty są zachowane; poprawny dokument
zachowuje wartości i kolejność list. Jest to reguła parsera, niezależna
od późniejszych kontroli schematu i lokalnych ID pomiarów.

## Dodanie recznego pomiaru

1. Znajdz obiekt w `data/objects/{PREFIX}/{OBJECT_ID}.yml`.
2. Dopisz nowy wpis na koncu `measurements`.
3. Nadaj kolejny lokalny identyfikator `m-NNN`, np. po `m-002` wpisz `m-003`.
4. Uzupelnij oba uklady wspolrzednych:

   - `lat`, `lon` w WGS84,
   - `x_1992`, `y_1992` w projektowej konwencji `x_1992 = northing`,
     `y_1992 = easting`.

5. Dla pomiaru terenowego ustaw zwykle:

   - `source: wlasne`,
   - `method: gps_receiver`, `gnss` albo `smartfon`,
   - `verification_status: nieweryfikowany`, dopoki nie ma review,
   - `horizontal_accuracy_m` i `vertical_accuracy_m`, jezeli sa znane,
   - `source_ref`, np. `teren:2026-05-16:gnss`,
   - `created_at` i `created_by`.

6. Ustaw `best_measurement`:

   - zostaw `mode: auto`, jesli domyslny algorytm ma wybrac najlepszy pomiar,
   - ustaw `mode: manual` tylko gdy swiadomie wskazujesz inny pomiar; wtedy
     `reason` musi jasno wyjasniac decyzje.

7. Zmien `updated_at` i `updated_by` obiektu.
8. Uruchom walidacje.

Pomocniczo, nowe ID obiektu mozna zaproponowac komenda:

```bash
uv run python scripts/assign_id.py 49.2425 19.8147
```

Do przeliczenia wspolrzednych w druga strone mozna uzyc helperow projektu:

```bash
uv run python -c "from gps_kataster_obiektow_tatr.coordinates import wgs84_to_1992; print(wgs84_to_1992(49.2425, 19.8147))"
```

## Cwiczeniowy pomiar testowy

Ten przeplyw pozwala nowej osobie przejsc cwiczenie bez dotykania prawdziwych
danych. Kopiuje jeden zwalidowany obiekt i jaskinie z aktualnego katalogu do
tymczasowego katalogu:

```bash
tmpdir="$(mktemp -d)"
mkdir -p "$tmpdir/objects/KSW" "$tmpdir/caves" "$tmpdir/relations"
cp data/caves/C-0002.yml "$tmpdir/caves/C-0002.yml"
cp data/objects/KSW/KSW-0001.yml "$tmpdir/objects/KSW/KSW-0001.yml"
```

Nastepnie w pliku `$tmpdir/objects/KSW/KSW-0001.yml` dopisz kolejny pomiar:

```yaml
  - id: m-003
    lat: 49.2345931
    lon: 19.8758951
    x_1992: 152267.24
    y_1992: 563744.26
    elevation_m: 1238.0
    elevation_datum: unknown
    elevation_source: gnss
    horizontal_accuracy_m: 0.8
    vertical_accuracy_m: 1.5
    source: wlasne
    source_ref: "teren:fixture:m-003"
    observed_date: "2026-05-16"
    source_date: null
    method: gnss
    device: "Emlid Reach"
    tags:
      - weryfikacja_terenowa
    verification_status: zweryfikowany
    verified_by: dl
    verified_at: "2026-05-16T10:30:00Z"
    notes: "Cwiczeniowy pomiar dodany w kopii fixture."
    created_at: "2026-05-16T10:00:00Z"
    created_by: dl
```

W tym samym pliku ustaw `best_measurement` na nowy pomiar:

```yaml
best_measurement:
  mode: auto
  measurement_id: m-003
  reason: null
  updated_at: "2026-05-16T10:30:00Z"
  updated_by: dl
```

Na koncu uruchom:

```bash
uv run python scripts/validate.py --data-dir "$tmpdir"
```

Walidacja powinna przejsc bez errorow. Moga zostac ostrzezenia dotyczace
starszych pomiarow z importu PIG/TPN, jezeli nie maja `horizontal_accuracy_m`.
Jezeli `best_measurement.mode: auto` wskazuje inny pomiar niz algorytm, popraw
`measurement_id` albo ustaw `mode: manual` z powodem.

## Domyslny algorytm `auto`

`best_measurement.mode: auto` jest deterministycznym wskazaniem najlepszego
aktualnego pomiaru. Priorytet zrodel:

1. najnowszy wlasny pomiar ze statusem `zweryfikowany`,
2. najlepszy nieodrzucony pomiar z TPN,
3. najlepszy nieodrzucony wlasny pomiar `nieweryfikowany`,
4. najlepszy nieodrzucony pomiar z PIG,
5. najlepszy nieodrzucony pomiar z innych zrodel.

W tym samym priorytecie wygrywa nowszy `observed_date` / `observed_at`, potem
nizsze `horizontal_accuracy_m`, a na koncu stabilny porzadek po
`measurement.id`. Jezeli wszystkie pomiary sa odrzucone, algorytm wskaze
fallback i walidator pokaze ostrzezenie. `mode: manual` zawsze ma pierwszenstwo,
ale wymaga pola `reason`.

## Walidacja

Przed commitem uruchom lokalna bramke:

```bash
uv run ruff format --check src tests scripts
uv run ruff check src tests scripts
uv run pytest
uv run python scripts/validate.py
```

`scripts/validate.py` zwraca kod niezerowy tylko dla `error`. Ostrzezenia trzeba
przeczytac i zrozumiec; obecny import PIG/TPN ma znane ostrzezenia
`MISSING_HORIZONTAL_ACCURACY`, bo zrodla nie podaja dokladnosci poziomej.

Jesli lokalny cache `uv` nie jest dostepny w srodowisku sandboxowym, uzyj:

```bash
UV_CACHE_DIR=/private/tmp/uv-cache uv run pytest
```

## Testy mutacyjne

Testy mutacyjne sa lokalna lub recznie uruchamiana bramka dla krytycznej logiki,
ktorej ciche zepsucie mogloby uszkodzic katalog danych:

- wybor najlepszego pomiaru,
- przeliczanie i walidacja wspolrzednych,
- przypisanie prefixu,
- rozroznienie `error` / `warning` w walidatorze,
- staging importu PIG/TPN i materializacja decyzji operatora.

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
czystego checkoutu po review zmian w YAML:

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
   - `katalog.sqlite.zip`.

   Dokladny przeglad kolumn i pol tych plikow jest w
   `docs/release_artifacts.md`.

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

Importer zachowuje `WER_LOK` i `UWAGI` przy pomiarach TPN, zarówno nowych,
jak i dopasowanych. Etykiety `TPN WER_LOK:` oraz `TPN UWAGI:` opisują tekst
źródłowy; nie oznaczają projektowej weryfikacji punktu. Review zachowuje
ten kontekst i ręczne uwagi pomiaru.

Dla istniejących danych jednorazowe narzędzie domyślnie wykonuje dry-run:

```bash
uv run --frozen python scripts/maintenance/restore_tpn_notes.py \
  --source data/sources/tpn/tpn_otwory_jaskin.xlsx.-.Export.csv \
  --data-dir data --report build/tpn-notes-dry.json
```

Raport JSON zawiera hash SHA-256 źródła, GLOBALID, plik, ID obiektu/pomiaru,
wartości źródłowe i notes/audyt przed oraz po zmianie. `record_number` służy
tylko jako odnośnik dowodowy. Dopasowanie wymaga jednocześnie jednoznacznej
referencji `TPN/source_globalid` na obiekcie i `source: TPN` z
`source_ref: TPN:{GLOBALID}` na pomiarze. Niejednoznaczność w źródle,
obiektach lub pomiarach jest raportowana i pomijana, bez dopasowania po
nazwie. Pozostałe jednoznaczne rekordy mogą być uzupełnione.

Po przeglądzie raportu powtórz polecenie z `--apply` i osobnym `--report`.
Opcjonalne `--generated-at 2026-10-15T13:16:44Z` ustala czas audytu dla
odtwarzalnego przebiegu. Zapis ogranicza się do notes właściwego pomiaru
i `updated_at`/`updated_by` obiektu (`maintenance:PBI-082`). Ręczne uwagi
pozostają; obecne etykietowane wartości nie są dopisywane drugi raz.
Manifest jest zapisywany przed finalnymi plikami; raport musi znajdować
się poza katalogiem danych i nie może nadpisać źródła. Nie deklarujemy
rollbacku przy awarii I/O ani ochrony przed równoczesną edycją.

[Manifest PBI-082](asdlc/verification/PBI-082-manifest.json) wskazuje 469
plików i wyłącznie dozwolone pola. [Log](asdlc/verification/PBI-082.md)
wyjaśnia wyniki przed/po i pominięty rekord Smoczej Jamy bez referencji.

## Dopelnianie brakujacych otworow

Gdy staging TPN zostawia `TPN_NR_INWENT_AMBIGUOUS`, czesto oznacza to kilka
otworow tej samej jaskini pod jednym numerem inwentarzowym. Wtedy nie tworz
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
   - dopisz nowe ID do `Jaskinia.object_ids`,
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

NaN i ±Infinity są niedozwolone w lat/lon, cache PL-1992, wysokości
oraz obu dokładnościach, także w historycznym lub odrzuconym pomiarze.
Walidator zwraca `MEASUREMENT_NON_FINITE` z plikiem, obiektem, pomiarem
oraz polem. Kontrola poprzedza geometrię i wybór best. Review (dry-run
oraz zapis), SQLite i eksporty blokują całą operację przed zapisem;
istniejące wyjścia zachowują bajty. Opcjonalne `null`, zera i skończone
wartości zachowują dotychczasową semantykę.

Importery CSV/XLSX wykrywają także przepełnienie zapisu liczby, np.
`1e999`. `PIG_MEASUREMENT_NON_FINITE` pomija obiekt, zachowując jaskinię;
`TPN_MEASUREMENT_NON_FINITE` odrzuca cały wiersz. Diagnostyka podaje
źródłowe pole i numer rekordu/identyfikator. Wadliwy kandydat z istniejącego
YAML lub PIG staging JSON przerywa staging TPN przed dopasowaniem;
CLI kończy się kodem 1 bez raportów. Nie poprawiać tego przez zamianę
niepoprawnej wysokości na brak wartości. Błąd projekcji dla skończonego
wejścia również jest raportowany, bez propagacji nieskończonego wyniku.
