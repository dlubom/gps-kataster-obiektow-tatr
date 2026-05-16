# Dokumentacja operacyjna

Ten dokument opisuje codzienna prace na danych YAML w V1. Zrodlem prawdy sa
pliki w `data/`; katalog `build/` zawiera tylko artefakty wygenerowane lokalnie.

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

## Miesieczna paczka danych

Miesieczna paczka powinna byc generowana z czystego checkoutu po review zmian
w YAML:

1. Zaktualizuj repo i upewnij sie, ze nie ma przypadkowych zmian:

   ```bash
   git status --short
   ```

2. Uruchom pelna bramke walidacyjna z poprzedniej sekcji.
3. Zbuduj artefakty release:

   ```bash
   uv run python scripts/build_release_artifacts.py
   ```

4. Sprawdz `build/exports/metadata.json`, zwlaszcza liczniki:

   - `object_count`,
   - `cave_count`,
   - `measurement_count`,
   - `validation_error_count`,
   - `validation_warning_count`.

5. Paczka lokalna znajduje sie w `build/exports/`:

   - `best-measurements.geojson`,
   - `best-measurements.csv`,
   - `best-measurements.gpx`,
   - `best-measurements.shp.zip`,
   - `metadata.json`,
   - `katalog.sqlite.zip`.

6. Publiczny release tagiem `v*` wymaga potwierdzenia licencji zrodel przez
   `SOURCE_LICENSE_CONFIRMED=true`. Bez tego wolno robic lokalny dry-run, ale
   nie nalezy publikowac paczki jako oficjalnego release.

## Statusy weryfikacji pomiarow

| Status | Kiedy uzyc |
|---|---|
| `nieweryfikowany` | Domyslnie dla importu PIG/TPN, nowego pomiaru terenowego przed review i wpisu przepisanego z notatek. |
| `zweryfikowany` | Po sprawdzeniu przez operatora/maintainera; dla pomiaru wlasnego oznacza, ze mozna mu ufac w wyborze `best_measurement`. |
| `odrzucony` | Dla pomiaru znanego, ale blednego albo nieuzytecznego. Nie usuwaj go z historii; dodaj notatke wyjasniajaca powod. |

Pomiar odrzucony moze zostac w `measurements`, ale zwykle nie powinien byc
wskazany jako `best_measurement`. Jezeli wszystkie pomiary sa odrzucone,
walidator moze wskazac to jako ostrzezenie.

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
