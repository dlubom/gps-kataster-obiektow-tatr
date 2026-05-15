# gps-kataster-obiektow-tatr — specyfikacja

> **Status**: _draft v2_ — wymagania, model domeny i architektura V1.
> **Zakres**: domena + wymagania + model danych + propozycja stosu technologicznego.
> **Odbiorcy**: zespół techniczny, speleolodzy, TPN, osoby weryfikujące dane terenowe.
>
> Propozycja stosu technologicznego jest rekomendacją. Specyfikacja jest pisana pod podejście **git-native**: źródłem prawdy są pliki YAML w repozytorium, a bazy i eksporty są artefaktami generowanymi.

---

## 1. Kontekst i cel

W Tatrach — po obu stronach granicy — znajduje się ponad 800 jaskiń oraz inne obiekty istotne dla speleologii i krasu: ponory, wywierzyska, sztolnie, nyże, szczeliny i obiekty pokrewne. Dane o nich pochodzą z kilku niespójnych źródeł:

- **TPN** — baza zawiera rekordy punktowe, w tym obiekty nieobecne w innych źródłach. Dla rekordów punktowych istotnym identyfikatorem źródłowym jest `GLOBALID`.
- **PIG / Jaskinie Polski** — katalog jaskiń z numerami inwentarzowymi, linkami i danymi morfometrycznymi. Rekord PIG najczęściej opisuje jaskinię albo pozycję katalogową, niekoniecznie pojedynczy otwór terenowy.
- **Geoportal / GUGiK** — warstwy form krasowych; identyfikacja bywa na poziomie jaskini albo obiektu źródłowego, niekoniecznie konkretnego otworu.
- **Własne ustalenia i pomiary** — GPS, GNSS, smartfon, notatki terenowe, zdjęcia, raporty.
- **Publikacje speleologiczne** — dane literaturowe, czasem bez jednoznacznych współrzędnych albo z dokładnością opisową.

Kluczowy problem domenowy: źródła zewnętrzne często posługują się identyfikacją **per jaskinia / pozycja katalogowa**, a projekt potrzebuje identyfikacji **per konkretny obiekt terenowy**.

Jaskinia może mieć wiele otworów. Każdy otwór jest w tym projekcie osobnym `Obiektem`, z własnym ID, historią pomiarów, współrzędnymi, załącznikami i stanem weryfikacji pomiarów.

Cele projektu:

1. Spięcie w jedną bazę pomiarów GPS/GNSS i ustaleń terenowych dla obiektów tatrzańskich.
2. Nadanie własnego trwałego ID dla każdego konkretnego obiektu terenowego.
3. Oddzielenie encji `Obiekt` od encji `Jaskinia`.
4. Poprawne odwzorowanie zewnętrznych identyfikatorów TPN, PIG, Geoportalu i numerów inwentarzowych.
5. Zachowanie pełnej historii pomiarów i ustaleń.
6. Wskazanie dla każdego obiektu najlepszego aktualnego pomiaru.
7. Umożliwienie pracy git-native: pull request jako jednostka zmiany, review jako weryfikacja.
8. Przygotowanie ścieżki do późniejszego zbierania danych offline w terenie.

---

## 2. Zakres obiektów

| Kategoria | Opis |
|---|---|
| `jaskinia_otwor` | Konkretny otwór jaskini, schroniska, nyży lub innego obiektu jaskiniowego. Jaskinia jako całość jest osobną encją logiczną. |
| `ponor` | Miejsce, gdzie wody powierzchniowe wnikają w system krasowy. |
| `wywierzysko` | Wypływ wody z systemu krasowego na powierzchnię. |
| `sztolnia` | Dawne wyrobisko górnicze istotne dla speleologii lub dokumentacji terenowej. |
| `inne` | Rezerwa na obiekty niesklasyfikowane w V1. Pełna lista podtypów do doprecyzowania później. |

Każdy `Obiekt` ma dokładnie jedną kategorię. Kategoria może się zmienić bez zmiany ID obiektu.

W V1 nie wprowadzamy rozbudowanego cyklu życia obiektu typu `active`, `merged`, `deprecated`. Takie stany zostają do decyzji w kolejnych wersjach. W V1 stan weryfikacji dotyczy przede wszystkim `Pomiaru`.

---

## 3. Podstawowe rozróżnienia domenowe

### 3.1 Obiekt terenowy

`Obiekt` to konkretne miejsce w terenie, które może zostać wskazane współrzędnymi. Przykłady:

- wejście do jaskini,
- drugi otwór tej samej jaskini,
- ponor,
- wywierzysko,
- sztolnia,
- pojedynczy punkt terenowy z bazy TPN.

To jest główna jednostka identyfikacji projektu. Własne ID projektu jest nadawane właśnie `Obiektowi`.

### 3.2 Jaskinia

`Jaskinia` to encja logiczna grupująca jeden lub wiele obiektów terenowych. W szczególności:

- jedna jaskinia może mieć jeden otwór,
- jedna jaskinia może mieć wiele otworów,
- rekord PIG albo numer inwentarzowy najczęściej dotyczy właśnie jaskini / pozycji katalogowej, nie pojedynczego otworu,
- `Jaskinia` nie jest tym samym co `Obiekt`.

### 3.3 Numer inwentarzowy

`NR_INWENT` / `Nr inw.` jest traktowany jako numer inwentarzowy jaskini albo pozycji katalogowej. Nie jest traktowany jako trwałe ID obiektu terenowego.

Uzasadnienie:

- część rekordów TPN nie ma `NR_INWENT`,
- jedna jaskinia może mieć wiele otworów, które współdzielą ten sam numer inwentarzowy,
- PIG identyfikuje rekordy katalogowe, które nie zawsze odpowiadają jednemu konkretnemu otworowi,
- rekordy punktowe TPN mają własny `GLOBALID`, który lepiej pasuje do identyfikacji konkretnego punktu / otworu źródłowego.

Zasada V1:

- `NR_INWENT` przypisujemy zasadniczo do `Jaskinia.external_refs`,
- TPN `GLOBALID` przypisujemy zasadniczo do `Obiekt.external_refs`,
- PIG `ID` i PIG `Link` przypisujemy zasadniczo do `Jaskinia.external_refs`,
- współrzędne z PIG mogą stać się `Pomiarem` konkretnego `Obiektu` dopiero po dopasowaniu do otworu.

---

## 4. Model domeny

### 4.1 `Obiekt`

`Obiekt` jest encją pierwszoklasową i główną jednostką identyfikacji projektu.

| Pole | Typ | Uwagi |
|---|---|---|
| `schema_version` | int | W V1 zawsze `1`. |
| `id` | string | Własne trwałe ID, format opisany w §5. |
| `category` | enum | `jaskinia_otwor` \| `ponor` \| `wywierzysko` \| `sztolnia` \| `inne`. |
| `name_local` | string, opt | Robocza nazwa lokalna obiektu terenowego. W V1 bez rozbudowanego modelu aliasów. |
| `cave_id` | FK → `Jaskinia`, opt | Dla `jaskinia_otwor` zalecane, jeśli znana jest jaskinia / pozycja katalogowa. |
| `id_assignment` | object | Informacja, jak przydzielono ID i prefix. |
| `external_refs` | lista `ExternalReference` | Referencje punktowe / otworowe, np. TPN `GLOBALID`. |
| `measurements` | lista `Pomiar` | Pełna historia pomiarów i ustaleń dla obiektu. |
| `best_measurement` | object | Tryb i wskazanie najlepszego aktualnego pomiaru. |
| `attachments` | lista `Attachment` | Pliki powiązane z obiektem. |
| `notes` | string, opt | Uwagi ogólne. |
| `created_at`, `created_by`, `updated_at`, `updated_by` | audyt | Audyt techniczny w YAML; historia zmian i tak jest w git. |

Przykład `id_assignment`:

```yaml
id_assignment:
  method: auto
  assigned_from_measurement_id: m-001
  assigned_prefix: KSW
  prefix_override_reason: null
```

Dopuszczalne wartości:

| Pole | Wartości | Znaczenie |
|---|---|---|
| `method` | `auto` \| `manual` | Czy prefix wynikał z algorytmu point-in-polygon, czy został wybrany ręcznie. |
| `assigned_from_measurement_id` | string | Pomiar użyty do nadania ID. |
| `assigned_prefix` | string | Prefix utrwalony w ID. |
| `prefix_override_reason` | string, opt | Wymagane, jeśli `method = manual` albo prefix nie zgadza się z aktualnym najlepszym pomiarem. |

### 4.2 `Jaskinia`

`Jaskinia` jest logiczną grupą obiektów terenowych. Nie ma własnych współrzędnych jako źródła prawdy w V1; współrzędne żyją na poziomie `Pomiaru` przypisanego do `Obiektu`.

| Pole | Typ | Uwagi |
|---|---|---|
| `schema_version` | int | W V1 zawsze `1`. |
| `id` | string | Wewnętrzne ID, np. `C-0001`. |
| `name` | string | Nazwa jaskini / pozycji katalogowej. |
| `system_name` | string, opt | Nazwa systemu jaskiniowego, jeśli dotyczy. |
| `external_refs` | lista `ExternalReference` | Numer inwentarzowy, PIG ID, PIG link, inne identyfikatory katalogowe. |
| `object_ids` | lista FK → `Obiekt` | Otwory / obiekty terenowe powiązane z jaskinią. |
| `notes` | string, opt | Uwagi. |
| `created_at`, `created_by`, `updated_at`, `updated_by` | audyt | |

Jedna `Jaskinia` ma 1..N powiązanych `Obiektów`, jeśli znane są jej otwory. W V1 dopuszczamy utworzenie `Jaskinia` przed pełnym rozpoznaniem wszystkich otworów.

### 4.3 `Pomiar`

`Pomiar` oznacza pojedynczy pomiar, import lub ustalenie lokalizacyjne dotyczące konkretnego `Obiektu`.

| Pole | Typ | Uwagi |
|---|---|---|
| `id` | string | Lokalny identyfikator w obrębie obiektu, np. `m-001`. |
| `lat`, `lon` | float, WGS84 deg | Obowiązkowe. WGS84 jest formatem podstawowym dla GPS i eksportów. |
| `x_1992`, `y_1992` | float, EPSG:2180 m | Pochodne / cache przy zapisie. Walidowane względem WGS84. |
| `elevation_m` | float, opt | Wysokość w metrach. |
| `elevation_datum` | enum, opt | `unknown` \| `ellipsoidal` \| `PL-EVRF2007-NH` \| `Kronstadt86` \| `other`. |
| `elevation_source` | enum, opt | `gps` \| `gnss` \| `map` \| `dem` \| `barometric` \| `source_record` \| `unknown` \| `other`. |
| `horizontal_accuracy_m` | float, opt | Szacowana dokładność pozioma. Zastępuje niejednoznaczne `estimated_accuracy_m`. |
| `vertical_accuracy_m` | float, opt | Szacowana dokładność pionowa. |
| `source` | enum | `TPN` \| `PIG` \| `geoportal` \| `wlasne` \| `publikacja` \| `inne`. |
| `source_ref` | string, opt | Dokładne odniesienie do rekordu źródłowego, np. `TPN:{GLOBALID}` albo `PIG:1094`. |
| `observed_at` | datetime, opt | Dokładny czas pomiaru, jeśli znany. |
| `observed_date` | date | Data pomiaru, ustalenia albo stanu źródła. |
| `source_date` | date, opt | Data publikacji / aktualności źródła, jeśli różni się od daty pomiaru. |
| `method` | enum | `gps_receiver` \| `gnss` \| `smartfon` \| `mapa_topo` \| `source_record` \| `ustalenie` \| `inne`. |
| `device` | string, opt | Marka / model urządzenia, jeśli dotyczy. |
| `tags` | lista string | Wolne tagi, np. `weryfikacja_terenowa`. |
| `verification_status` | enum | `nieweryfikowany` \| `zweryfikowany` \| `odrzucony`. |
| `verified_by`, `verified_at` | user, datetime, opt | Wypełniane przy weryfikacji. |
| `notes` | string, opt | Uwagi. |
| `created_at`, `created_by` | audyt | |

Zasady:

- `lat` i `lon` są obowiązkowe w danych źródłowych YAML. Jeśli import daje tylko EPSG:2180, importer przelicza do WGS84.
- `x_1992` i `y_1992` są cache’owane i walidowane.
- `horizontal_accuracy_m` dotyczy dokładności poziomej, a nie wysokości.
- Dla danych PIG/TPN bez znanej dokładności pole `horizontal_accuracy_m` może być puste.
- Pomiar odrzucony nie jest usuwany, tylko dostaje `verification_status: odrzucony` oraz notatkę.

### 4.4 `BestMeasurement`

Każdy `Obiekt` ma wskazanie najlepszego aktualnego pomiaru.

```yaml
best_measurement:
  mode: auto
  measurement_id: m-001
  reason: null
  updated_at: 2026-05-15T10:00:00Z
  updated_by: dl
```

| Pole | Typ | Uwagi |
|---|---|---|
| `mode` | `auto` \| `manual` | Czy wskazanie wynika z algorytmu, czy z decyzji operatora. |
| `measurement_id` | FK → `Pomiar` | Wskazany najlepszy pomiar. |
| `reason` | string, opt | Wymagane dla `manual`. Opcjonalne dla `auto`. |
| `updated_at`, `updated_by` | audyt | Kto i kiedy ustawił wskazanie. |

Zasady walidacji:

- `measurement_id` musi wskazywać istniejący pomiar tego samego obiektu.
- Jeśli `mode = manual`, `reason` jest wymagane.
- Jeśli `mode = auto`, walidator może sprawdzić, czy `measurement_id` zgadza się z algorytmem default.
- W V1 dopuszczamy ręczne wpisanie `measurement_id` także dla `auto`, aby YAML był jednoznaczny.
- W buildzie SQLite można dodatkowo przeliczać pole `computed_best_measurement_id`.

Domyślny algorytm `auto`:

1. Najnowszy własny pomiar o `verification_status = zweryfikowany`.
2. Jeśli brak własnych zweryfikowanych — najlepszy nieodrzucony pomiar z TPN.
3. Jeśli brak TPN — najlepszy nieodrzucony pomiar z własnych danych nieweryfikowanych.
4. Jeśli brak powyższych — najlepszy nieodrzucony pomiar z PIG.
5. Jeśli brak nieodrzuconych — najnowszy jakikolwiek, ale z ostrzeżeniem walidatora.
6. W obrębie tego samego priorytetu źródła wybieramy najnowszy `observed_date` / `observed_at`.
7. Przy remisie dat — niższe `horizontal_accuracy_m`.
8. Przy dalszym remisie — stabilny porządek po `measurement.id`.

Priorytet źródeł w trybie `auto`:

```text
wlasne zweryfikowane > TPN > wlasne nieweryfikowane > PIG > geoportal/publikacja/inne
```

Ręczne wskazanie `mode: manual` zawsze ma pierwszeństwo przed algorytmem.

### 4.5 `ExternalReference`

`ExternalReference` jest typem osadzanym w `Obiekt` i `Jaskinia`.

W V1 nie robimy jednej globalnej tabeli referencji z obowiązkowym `object_id`, ponieważ część identyfikatorów zewnętrznych dotyczy jaskini / pozycji katalogowej, a nie konkretnego otworu.

| Pole | Typ | Uwagi |
|---|---|---|
| `system` | enum | `TPN` \| `PIG` \| `geoportal` \| `NR_INWENT` \| `inne`. |
| `ref_type` | enum | `source_globalid` \| `inventory_number` \| `catalog_id` \| `url` \| `source_row` \| `other`. |
| `external_id` | string | ID w systemie źródłowym. |
| `url` | string, opt | URL do źródła, jeśli istnieje. |
| `scope` | enum, opt | `object` \| `cave` \| `cave_system` \| `inventory_entry` \| `unknown`. |
| `notes` | string, opt | Uwagi. |

Typowe użycie:

| Źródło | Pole | Gdzie trafia | Uzasadnienie |
|---|---|---|---|
| TPN | `GLOBALID` | `Obiekt.external_refs` | Identyfikuje rekord punktowy. |
| TPN | `NR_INWENT` | `Jaskinia.external_refs` | Numer inwentarzowy jaskini / pozycji katalogowej. |
| PIG | `ID` | `Jaskinia.external_refs` | Identyfikator rekordu katalogowego. |
| PIG | `Nr inw.` | `Jaskinia.external_refs` | Numer inwentarzowy. |
| PIG | `Link` | `Jaskinia.external_refs` | Link do rekordu katalogowego. |
| Geoportal | ID warstwy / feature | zależnie od semantyki | Do rozstrzygnięcia per warstwa. |

### 4.6 `Relacja`

`Relacja` opisuje powiązanie między dwoma `Obiektami`.

| Pole | Typ | Uwagi |
|---|---|---|
| `schema_version` | int | W V1 zawsze `1`. |
| `id` | string | ID relacji, np. `R-0001`. |
| `from_object_id`, `to_object_id` | FK → `Obiekt` | |
| `relation_type` | enum | `sasiad` \| `czesc_systemu` \| `mozliwy_duplikat` \| `inne`. |
| `notes` | string, opt | |

Szczegółowa semantyka relacji, rozstrzyganie duplikatów i merge/split obiektów zostają poza zakresem V1.

### 4.7 `Attachment`

`Attachment` to plik albo URL powiązany z obiektem, opcjonalnie z konkretnym pomiarem.

| Pole | Typ | Uwagi |
|---|---|---|
| `id` | string | Lokalny identyfikator w obrębie obiektu, np. `a-001`. |
| `kind` | enum | `raport_gnss` \| `zdjecie` \| `inne`. |
| `measurement_id` | FK → `Pomiar`, opt | Wypełnione, jeśli plik dotyczy konkretnej sesji / pomiaru. |
| `path` | string | Ścieżka względna w repo albo URL zewnętrzny. |
| `caption` | string, opt | Krótki opis. |
| `date` | date, opt | Data powstania pliku. |
| `created_at`, `created_by` | audyt | |

Layout plików:

```text
data/attachments/{PREFIX}/{PREFIX}-{NNNN}/...
```

W V1 dopuszczamy trzymanie małych załączników w repo. Decyzja o Git LFS albo object storage zostaje na później.

---

## 5. System identyfikacji

### 5.1 Format ID

```text
{PREFIX}-{NNNN}
```

- `PREFIX` — 2–3 znaki alfabetyczne, uppercase ASCII.
- `NNNN` — licznik zero-padded do 4 cyfr.
- Po przekroczeniu `9999` rozszerzamy licznik do 5+ cyfr bez renumeracji wcześniejszych ID.
- Licznik jest unikatowy w obrębie prefixu.
- Kategoria obiektu nie jest częścią ID.

Przykłady:

| ID | Interpretacja |
|---|---|
| `CHZ-0001` | Obiekt #1 w Dolinie Chochołowskiej-Zachód. |
| `KSW-0042` | Obiekt #42 w Dolinie Kościeliskiej-Wschód. |
| `LEJ-0003` | Obiekt #3 w Dolinie Lejowej. |
| `PL-0007` | Obiekt #7 w Polsce poza polygonami dolin. |
| `SK-0001` | Obiekt #1 po stronie słowackiej. |

ID raz utrwalone nigdy się nie zmienia.

### 5.2 Tabela prefixów

Źródło prawdy: `config/prefixes.yml`.

| Polygon / kraj | Prefix |
|---|---|
| Dolina Chochołowska - Zachód | `CHZ` |
| Dolina Chochołowska - Wschód | `CHW` |
| Dolina Lejowa | `LEJ` |
| Dolina Kościeliska - Zachód | `KSZ` |
| Dolina Kościeliska - Wschód | `KSW` |
| Dolina Miętusia - Zachód | `MTZ` |
| Dolina Miętusia - Wschód | `MTW` |
| Staników Żleb | `STN` |
| Dolina Małej Łąki - Zachód | `MLZ` |
| Dolina Małej Łąki - Wschód | `MLW` |
| Mały Żlebek, D. za Bramką i Suchy Żleb | `BRA` |
| Dolina Strążyska | `STR` |
| Dolina ku Dziurze i Spadowiec | `DZI` |
| Dolina Białego i nad Capkami | `BIA` |
| Dolina Bystrej - Zachód | `BYZ` |
| Dolina Bystrej - Wschód | `BYW` |
| Dolina Olczyska, Sucha i Chłabowska | `OLC` |
| Dolina Suchej Wody | `SUW` |
| Polska — backup | `PL` |
| Słowacja — backup | `SK` |

### 5.3 Algorytm przydzielania prefixu

Wejście: współrzędne `(lat, lon)` w WGS84.

Przed przydzieleniem prefixu punkt musi przejść podstawową walidację geograficzną: musi leżeć w granicach Polski albo Słowacji. Punkt poza obiema granicami jest błędem danych.

1. Reprojekcja do EPSG:2180.
2. Point-in-polygon na `data/shapes/doliny.shp`.
3. Pierwszy dopasowany polygon → prefix z `config/prefixes.yml`.
4. Jeśli punkt jest poza dolinami, test na `data/shapes/granica_polski.shp` → `PL`.
5. Jeśli punkt jest poza Polską, test na `data/shapes/granica_slowacji.shp` → `SK`.
6. Jeśli brak dopasowania do Polski i Słowacji, jest to błąd danych.
7. Jeśli punkt leży w Polsce albo Słowacji, ale poza polygonami dolin tatrzańskich, ID nie jest przydzielane automatycznie. W V1 jest to warning wymagający ręcznego rozstrzygnięcia albo poprawy danych.

### 5.4 Niezmienność ID

ID raz utrwalone nie zmienia się, nawet jeśli:

- obiekt zostanie przeklasyfikowany,
- późniejszy pomiar wskaże inną dolinę,
- pierwszy pomiar był błędny,
- shapefile dolin zostanie zaktualizowany,
- obiekt okaże się powiązany z inną jaskinią.

Zmiana prefixu jest dopuszczalna wyłącznie przed pierwszym utrwaleniem ID, w trybie draft.

### 5.5 Prefix mismatch

Walidacja prefixu nie może łamać zasady niezmienności ID.

Zasady:

- dla nowego obiektu prefix powinien zgadzać się z pomiarem użytym do nadania ID,
- dla istniejącego obiektu niezgodność prefixu z aktualnym najlepszym pomiarem jest ostrzeżeniem, nie twardym błędem,
- jeśli prefix został nadany ręcznie albo świadomie pozostaje niezgodny z aktualną lokalizacją, wymagane jest `id_assignment.prefix_override_reason`,
- build może generować flagę `prefix_location_mismatch` w SQLite i raportach walidacji.

### 5.6 Przydzielanie kolejnego numeru

W V1 zakładamy mały zespół i praktycznie jedną osobę wprowadzającą dane.

Zasada V1:

- `scripts/assign_id.py lat lon` proponuje prefix i kolejny wolny numer,
- numer jest wyliczany na podstawie istniejących plików w `data/objects/{PREFIX}/`,
- konflikt ID jest wykrywany przez walidator jako błąd,
- nie wprowadzamy osobnego pliku liczników ani bota nadającego ID.

Jeżeli zespół się powiększy, temat wraca w kolejnej wersji.

---

## 6. Układy współrzędnych

System przechowuje współrzędne każdego pomiaru w dwóch układach:

| Układ | EPSG | Jednostki | Rola |
|---|---|---|---|
| WGS84 | 4326 | stopnie dziesiętne | Format podstawowy dla GPS, GPX, GeoJSON i importów terenowych. |
| PL-1992 | 2180 | metry | Format krajowy, używany przez polską geodezję, shapefile referencyjne, QGIS i eksporty krajowe. |

Zasady:

- YAML przechowuje `lat`, `lon`, `x_1992`, `y_1992`.
- WGS84 i PL-1992 muszą być spójne w granicach tolerancji walidatora.
- Konwersja jest deterministyczna i wykonywana przez PyProj.
- Shapefile referencyjne w `data/shapes/` są w EPSG:2180.
- PL-1992 używa polskiej konwencji osi: `X = northing`, `Y = easting`.

Dla importów:

- jeśli źródło daje WGS84, importer wylicza EPSG:2180,
- jeśli źródło daje EPSG:2180, importer wylicza WGS84,
- jeśli źródło daje oba układy, importer sprawdza spójność.

---

## 7. Źródła danych i mapowanie

### 7.1 TPN

TPN jest traktowany jako źródło o wyższym priorytecie niż PIG dla aktualnej lokalizacji obiektu.

Plik TPN zawiera rekordy punktowe. W V1 przyjmujemy:

| Pole TPN | Interpretacja | Mapowanie |
|---|---|---|
| `GLOBALID` | ID rekordu punktowego | `Obiekt.external_refs`, `system: TPN`, `ref_type: source_globalid`. |
| `NR_INWENT` | Numer inwentarzowy | `Jaskinia.external_refs`, `system: NR_INWENT`, `ref_type: inventory_number`. |
| `NAZWA` | Nazwa jaskini / obiektu | `Jaskinia.name` lub `Obiekt.name_local` zależnie od przypadku. |
| `OTWÓR` | Opis / nazwa otworu | Pomocniczo do `Obiekt.name_local` i `notes`. |
| `X1992`, `Y1992` | Współrzędne PL-1992 | Importowane do `Pomiar`, po konwersji także WGS84. |
| `Z` | Wysokość | `Pomiar.elevation_m`, z `elevation_source: source_record`. |
| `DLUGOSC`, `GLEBOKOSC`, `DENIWELACJ` | Dane morfometryczne | W V1 raczej notatka / przyszłe pola jaskini, nie część obiektu terenowego. |
| `SYSTEM` | Informacja o systemie | `Jaskinia.system_name`, jeśli jednoznaczne. |

Zasady:

- TPN `GLOBALID` jest najlepszym kandydatem na zewnętrzną referencję do konkretnego `Obiektu`.
- Jeśli obiekt ma wcześniejszy pomiar z PIG i później zostanie dopasowany rekord TPN, pomiar TPN powinien przejąć rolę aktualnego pomiaru w trybie `best_measurement.mode: auto`, chyba że istnieje ręczne wskazanie `manual` albo późniejszy własny zweryfikowany pomiar.
- Import TPN służy do uaktualnienia i skorygowania szkieletu utworzonego wcześniej z PIG.

### 7.2 PIG / Jaskinie Polski

PIG jest pierwszym źródłem importu początkowego i służy przede wszystkim do zbudowania szkieletu katalogowego: `Jaskinia`, numery inwentarzowe, linki, nazwy i wstępne punkty.

Jakość współrzędnych PIG traktujemy jako niższą niż TPN i własne pomiary terenowe. Pomiary z PIG mają niski priorytet przy wyborze aktualnego najlepszego pomiaru.

Plik PIG zawiera rekordy katalogowe.

| Pole PIG | Interpretacja | Mapowanie |
|---|---|---|
| `ID` | ID rekordu PIG | `Jaskinia.external_refs`, `system: PIG`, `ref_type: catalog_id`. |
| `Nr inw.` | Numer inwentarzowy | `Jaskinia.external_refs`, `system: NR_INWENT`, `ref_type: inventory_number`. |
| `Link` | URL rekordu PIG | `Jaskinia.external_refs`, `system: PIG`, `ref_type: url`. |
| `Nazwa` | Nazwa jaskini / pozycji katalogowej | `Jaskinia.name`. |
| `Inne nazwy` | Aliasy | W V1 do `Jaskinia.notes`; model aliasów później. |
| `X 1992`, `Y 1992`, `B`, `L` | Współrzędne | Mogą utworzyć `Pomiar` konkretnego `Obiektu` po dopasowaniu. |
| `H (wg PIG)` | Wysokość | `Pomiar.elevation_m`, `elevation_source: source_record`. |
| `Długość [m]`, `Głębokość [m]`, `Deniwelacja [m]` | Dane morfometryczne jaskini | W V1 notatka / przyszłe pola `Jaskinia`. |
| `Stan na rok` | Data stanu źródła | `Pomiar.source_date` albo `Jaskinia.notes`. |

Zasady:

- PIG `ID` nie jest ID otworu. Jest referencją do rekordu katalogowego jaskini / pozycji inwentarzowej.
- Import PIG jest wykonywany jako pierwszy, ponieważ daje bazowy katalog jaskiń i numerów inwentarzowych.
- Współrzędne PIG mogą tymczasowo utworzyć pierwszy `Pomiar`, ale taki pomiar dostaje niski priorytet źródłowy.
- Jeśli później pojawi się dopasowany rekord TPN dla tego samego obiektu, pomiar TPN powinien zastąpić PIG jako `best_measurement` w trybie `auto`.
- Pomiar PIG pozostaje w historii i nie jest kasowany.

### 7.3 Geoportal

Mapowanie Geoportalu wymaga decyzji per warstwa, ponieważ nie każda warstwa ma tę samą semantykę.

Zasady V1:

- feature punktowy Geoportalu może stać się `Pomiarem`, jeśli da się go przypisać do konkretnego `Obiektu`,
- ID feature może trafić do `Obiekt.external_refs` albo `Jaskinia.external_refs` zależnie od tego, czy identyfikuje punkt, czy pozycję katalogową,
- jeśli semantyka jest niejasna, referencja dostaje `scope: unknown` i wymaga ręcznej weryfikacji.

### 7.4 Własne pomiary

Własne pomiary mogą pochodzić z:

- odbiornika GPS,
- GNSS,
- smartfona,
- GPX,
- CSV,
- notatek terenowych,
- ręcznego wpisu.

Dla własnych pomiarów wymagane minimum:

```yaml
id: m-001
lat: 49.2423
lon: 19.8145
x_1992: 558123.45
y_1992: 150456.78
source: wlasne
observed_date: 2024-07-15
method: gps_receiver
verification_status: nieweryfikowany
```

---

## 8. Deduplikacja i import

### 8.1 Import staging

Importy masowe nie powinny od razu tworzyć finalnych obiektów bez review.

Workflow:

1. Import do struktury staging albo roboczego raportu.
2. Normalizacja współrzędnych i pól.
3. Próba dopasowania do istniejących `Jaskinia` przez `NR_INWENT`, PIG `ID`, nazwę.
4. Próba dopasowania do istniejących `Obiekt` przez TPN `GLOBALID`, odległość, nazwę otworu.
5. Wygenerowanie propozycji YAML.
6. Review w PR.

### 8.2 Kandydaci na duplikat

Dla nowego pomiaru szukamy kandydatów:

- po identyfikatorze źródłowym, np. TPN `GLOBALID`,
- po `NR_INWENT` / `Jaskinia`,
- po odległości od istniejących obiektów,
- po podobieństwie nazw,
- po kategorii.

Domyślny próg odległości:

```text
max(horizontal_accuracy_1, horizontal_accuracy_2, DEFAULT_DUPLICATE_RADIUS_M)
```

Jeśli dokładności brak, używany jest próg domyślny z konfiguracji.

### 8.3 Decyzja operatora

Operator decyduje:

1. nowy `Obiekt`,
2. nowy `Pomiar` istniejącego `Obiektu`,
3. nowa `Jaskinia`,
4. powiązanie z istniejącą `Jaskinia`,
5. odrzucenie rekordu importu,
6. pozostawienie jako nierozstrzygnięty przypadek.

Pełny model merge/split obiektów zostaje poza V1.

---

## 9. Historia i najlepszy aktualny stan

### 9.1 Historia

Zasady:

- Nie kasujemy fizycznie pomiarów tylko dlatego, że są błędne.
- Błędny pomiar dostaje `verification_status: odrzucony` i notatkę.
- Każdy obiekt ma 1..N pomiarów.
- Historia zmian YAML jest śledzona przez git.
- Review PR jest podstawowym mechanizmem kontroli jakości.

### 9.2 Weryfikacja pomiarów

Statusy:

| Status | Znaczenie |
|---|---|
| `nieweryfikowany` | Pomiar zaimportowany lub dodany, ale jeszcze niepotwierdzony. |
| `zweryfikowany` | Pomiar uznany za poprawny przez operatora / maintainera. |
| `odrzucony` | Pomiar znany, ale błędny albo nieużyteczny. Pozostaje w historii. |

### 9.3 Best current

Najlepszy aktualny pomiar jest wskazywany przez `best_measurement`.

Tryb `auto` jest domyślny i wystarcza dla większości obiektów. Tryb `manual` służy do przypadków, w których nowszy pomiar nie jest najlepszy, np. smartfon wskazał gorszą lokalizację niż wcześniejszy GNSS.

---

## 10. Architektura: repo jako źródło prawdy

Filozofia:

> Dane źródłowe są w git jako YAML. Wszystko inne jest generowane.

Konsekwencje:

- brak backendu w V1,
- brak osobnego systemu kont,
- historia zmian = git log,
- review = pull request,
- walidacja = CI,
- SQLite, GeoJSON, GPX, CSV i Shapefile są artefaktami buildu.

### 10.1 Struktura repo

```text
.
├── config/
│   └── prefixes.yml
├── data/
│   ├── shapes/
│   │   ├── doliny.shp
│   │   ├── granica_polski.shp
│   │   ├── granica_slowacji.shp
│   │   └── README.md
│   ├── objects/
│   │   └── {PREFIX}/
│   │       └── {PREFIX}-{NNNN}.yml
│   ├── caves/
│   │   └── {CAVE-ID}.yml
│   ├── attachments/
│   │   └── {PREFIX}/
│   │       └── {PREFIX}-{NNNN}/
│   └── relations/
│       └── {REL-ID}.yml
├── schema/
│   ├── object.schema.json
│   ├── cave.schema.json
│   ├── relation.schema.json
│   └── CHANGELOG.md
├── scripts/
│   ├── assign_id.py
│   ├── build_db.py
│   ├── export.py
│   ├── validate.py
│   └── importers/
│       ├── import_tpn.py
│       └── import_pig.py
├── build/
│   ├── katalog.sqlite
│   └── exports/
├── tests/
│   └── fixtures/
├── .github/workflows/
│   ├── validate.yml
│   ├── build.yml
│   └── release.yml
└── SPECYFIKACJA.md
```

`build/` jest generowane i gitignored.

### 10.2 Przykład obiektu YAML

```yaml
schema_version: 1
id: KSW-0001
category: jaskinia_otwor
name_local: "Jaskinia Mroźna — wejście na trasę turystyczną"
cave_id: C-0001

id_assignment:
  method: auto
  assigned_from_measurement_id: m-001
  assigned_prefix: KSW
  prefix_override_reason: null

external_refs:
  - system: TPN
    ref_type: source_globalid
    external_id: "{71432220-CA17-4420-ACC8-394596EDF79F}"
    scope: object
    notes: "Rekord punktowy TPN dla konkretnego otworu."

measurements:
  - id: m-001
    lat: 49.2423
    lon: 19.8145
    x_1992: 558123.45
    y_1992: 150456.78
    elevation_m: 1240.0
    elevation_datum: unknown
    elevation_source: source_record
    horizontal_accuracy_m: null
    vertical_accuracy_m: null
    source: TPN
    source_ref: "TPN:{71432220-CA17-4420-ACC8-394596EDF79F}"
    observed_date: 2022-05-25
    source_date: 2022-05-25
    method: source_record
    device: null
    tags: []
    verification_status: nieweryfikowany
    verified_by: null
    verified_at: null
    notes: "Import z rekordu punktowego TPN."
    created_at: 2026-05-15T10:00:00Z
    created_by: dl

best_measurement:
  mode: auto
  measurement_id: m-001
  reason: null
  updated_at: 2026-05-15T10:00:00Z
  updated_by: dl

attachments: []
notes: null
created_at: 2026-05-15T10:00:00Z
created_by: dl
updated_at: 2026-05-15T10:00:00Z
updated_by: dl
```

### 10.3 Przykład jaskini YAML

```yaml
schema_version: 1
id: C-0001
name: "Jaskinia Mroźna"
system_name: null

external_refs:
  - system: NR_INWENT
    ref_type: inventory_number
    external_id: "T.D-08.07"
    scope: cave
    notes: "Numer inwentarzowy wspólny dla jaskini / pozycji katalogowej."

  - system: PIG
    ref_type: catalog_id
    external_id: "1094"
    url: "https://jaskiniepolski.pgi.gov.pl/Details/Information/1094"
    scope: cave
    notes: "Rekord katalogowy PIG."

object_ids:
  - KSW-0001
  - KSW-0002

notes: null
created_at: 2026-05-15T10:00:00Z
created_by: dl
updated_at: 2026-05-15T10:00:00Z
updated_by: dl
```

---

## 11. CI/CD

### 11.1 `validate.yml`

Uruchamiany na PR i push.

Workflow CI używa tego samego toolingu co środowisko lokalne: `uv`, `ruff`, `pytest` i skrypty z repo.

Kroki techniczne:

- instalacja zależności przez `uv sync`,
- `ruff check .`,
- `ruff format --check .`,
- `pytest`,
- testy mutacyjne dla krytycznych modułów, jeśli czas wykonania jest akceptowalny dla PR,
- `scripts/validate.py`.

Walidacje typu error:

- poprawność YAML,
- zgodność z JSON Schema,
- obecność `schema_version: 1`,
- unikalność `Obiekt.id` globalnie,
- unikalność pliku względem ID,
- poprawny format ID,
- `best_measurement.measurement_id` wskazuje istniejący pomiar,
- `best_measurement.mode = manual` ma `reason`,
- `cave_id` wskazuje istniejącą jaskinię,
- `Jaskinia.object_ids` wskazują istniejące obiekty,
- relacje wskazują istniejące obiekty,
- `Attachment.measurement_id` wskazuje pomiar tego samego obiektu,
- lokalny `Attachment.path` istnieje,
- URL w `Attachment.path` ma poprawny format,
- WGS84 ↔ PL-1992 są spójne w tolerancji,
- punkt pomiaru mieści się w granicach Polski albo Słowacji według `data/shapes/granica_polski.shp` i `data/shapes/granica_slowacji.shp`,
- brak duplikatów TPN `GLOBALID` w `Obiekt.external_refs`, chyba że jawnie dopuszczone w przyszłej regule.

Walidacje typu warning:

- punkt pomiaru leży w Polsce albo Słowacji, ale nie trafia w żaden polygon doliny tatrzańskiej,
- prefix istniejącego obiektu nie zgadza się z aktualnym best pomiarem,
- brak `horizontal_accuracy_m`,
- brak `source_ref`,
- pomiar jest daleko od pozostałych pomiarów tego samego obiektu,
- `category: jaskinia_otwor` bez `cave_id`,
- `NR_INWENT` przypisany do `Obiekt.external_refs` zamiast `Jaskinia.external_refs`,
- PIG `ID` przypisany do `Obiekt.external_refs` zamiast `Jaskinia.external_refs`,
- `best_measurement.mode = auto`, ale wskazanie nie zgadza się z algorytmem default.

### 11.2 `build.yml`

Uruchamiany po merge do `main`.

Zadania:

- rebuild `build/katalog.sqlite`,
- wygenerowanie indeksów przestrzennych,
- wygenerowanie GeoJSON dla obiektów i najlepszych pomiarów,
- wygenerowanie pomocniczych raportów walidacyjnych,
- publikacja artefaktów GitHub Actions.

### 11.3 `release.yml`

Uruchamiany na tag `v*`.

Zadania:

- build pełnej bazy,
- eksport najlepszych pomiarów,
- zapakowanie SQLite,
- wygenerowanie `metadata.json`,
- opublikowanie GitHub Release.

---

## 12. Build: SQLite + SpatiaLite

Wybór: SQLite + SpatiaLite.

Powody:

- jeden plik,
- łatwa dystrybucja,
- QGIS otwiera natywnie,
- brak serwera DB,
- indeksy przestrzenne,
- możliwość użycia lokalnie i w CI,
- dobre dopasowanie do modelu read-only.

DB jest artefaktem. Nie jest źródłem prawdy.

### 12.1 Tabele logiczne

Minimalny schemat logiczny:

- `objects`,
- `caves`,
- `measurements`,
- `object_external_refs`,
- `cave_external_refs`,
- `attachments`,
- `relations`,
- `best_measurements`,
- `validation_flags`.

### 12.2 Geometrie

- `measurements.geom_wgs84` — punkt EPSG:4326,
- `measurements.geom_1992` — punkt EPSG:2180,
- `objects.best_geom_wgs84` — geometria z najlepszego pomiaru,
- `objects.best_geom_1992` — geometria z najlepszego pomiaru.

---

## 13. Release i eksporty

Tag release:

```text
v{YYYY}.{MM}.{patch}
```

Przykład:

```text
v2026.05.1
```

Każdy release zawiera:

| Plik | Format | Uwagi |
|---|---|---|
| `best-measurements.geojson` | GeoJSON | WGS84, z PL-1992 w `properties`. |
| `best-measurements.gpx` | GPX | WGS84, do GPS receiverów. |
| `best-measurements.csv` | CSV | Oba układy współrzędnych. |
| `best-measurements.shp.zip` | ESRI Shapefile | EPSG:2180, QGIS / TPN. |
| `katalog.sqlite.zip` | SQLite + SpatiaLite | Pełny snapshot. |
| `metadata.json` | JSON | Liczby obiektów, pomiarów, jaskiń, data buildu, wersja schematu. |

Repo i eksporty są publiczne. Dane projektu są licencjonowane jako **Creative Commons Attribution 4.0 International (CC BY 4.0)**, z zastrzeżeniem że importowane dane zewnętrzne mogą wymagać osobnego potwierdzenia prawnego przed redystrybucją.

W V1 nie wprowadzamy mechanizmu `sensitivity`, ukrywania lokalizacji ani generalizacji eksportów.

---

## 14. Frontend

Frontend nie jest częścią aktualnego zakresu projektu.

W V1 nie budujemy:

- przeglądarki mapowej,
- MapLibre,
- PWA do przeglądu offline,
- edycji przez UI,
- integracji z GitHub API.

Podstawowym sposobem pracy jest repozytorium, pliki YAML, walidacja CI oraz generowane eksporty. Do przeglądania danych wystarczają QGIS, CSV, GeoJSON, GPX i SQLite.

---

## 15. Zbieranie nowych pomiarów

W aktualnym modelu nie planujemy aplikacji terenowej.

Docelowy proces operacyjny:

1. Osoby wykonujące pomiary zbierają dane dowolnymi narzędziami: GPS / GNSS, GPX, CSV, notatka w telefonie, zdjęcie, kartka.
2. Raz w miesiącu jedna wyznaczona osoba dostaje mail z nowymi pomiarami i materiałami.
3. Ta osoba porządkuje dane, dopisuje lub aktualizuje YAML, uruchamia walidację i otwiera PR.
4. Po review i merge generowane są aktualne artefakty.

Nie przewidujemy w tym zakresie:

- PWA do zbierania pomiarów,
- generowania YAML w terenie,
- commitowania przez GitHub API,
- automatycznej integracji z telefonem,
- pluginu QGIS do edycji danych.

---

## 16. Narzędzia CLI i tooling developerski

Projekt jest obsługiwany jako nowoczesny projekt Pythonowy.

Założenia toolingowe V1:

- `uv` do zarządzania środowiskiem, zależnościami, lockfile i uruchamianiem narzędzi,
- `pyproject.toml` jako centralna konfiguracja projektu,
- `ruff` do lintingu i formatowania kodu,
- `pytest` do testów jednostkowych,
- testy mutacyjne dla krytycznej logiki walidacji, geometrii i importu,
- typowanie w kodzie Python, z docelową możliwością uruchamiania type checkera,
- spójne komendy lokalne i CI.

Minimalny zestaw V1:

```text
scripts/assign_id.py lat lon
scripts/validate.py
scripts/build_db.py
scripts/export.py --best
scripts/importers/import_tpn.py
scripts/importers/import_pig.py
```

### 16.1 `assign_id.py`

Zadania:

- przyjmuje `lat lon`,
- wylicza EPSG:2180,
- wykonuje point-in-polygon,
- proponuje prefix,
- znajduje kolejny wolny numer,
- wypisuje proponowane ID.

### 16.2 `validate.py`

Zadania:

- lokalnie wykonuje te same walidacje co CI,
- rozróżnia error i warning,
- generuje czytelny raport.

### 16.3 `build_db.py`

Zadania:

- czyta YAML,
- buduje SQLite + SpatiaLite,
- tworzy indeksy,
- zapisuje `build/katalog.sqlite`.

### 16.4 `export.py --best`

Zadania:

- eksportuje najlepsze pomiary,
- generuje GeoJSON, GPX, CSV, Shapefile.

### 16.5 Standardowe komendy developerskie

Docelowo projekt powinien mieć jeden spójny sposób uruchamiania narzędzi lokalnie i w CI, np. przez `uv run`.

Przykładowe komendy:

```text
uv sync
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run python scripts/validate.py
uv run python scripts/build_db.py
```

Wersje zależności są utrwalane w lockfile, aby lokalne środowisko i CI działały powtarzalnie.

### 16.6 Testy

Wymagane testy V1:

- testy jednostkowe dla parsowania YAML,
- testy JSON Schema,
- testy konwersji WGS84 ↔ EPSG:2180,
- testy point-in-polygon i przydzielania prefixu,
- testy `best_measurement` w trybie `auto` i `manual`,
- testy wykrywania błędów i warningów walidatora,
- testy generowania SQLite na małych fixture’ach,
- testy eksportów `best`.

Fixture’y testowe powinny obejmować co najmniej:

```text
tests/fixtures/
  valid-object.yml
  valid-cave.yml
  object-with-tpn-globalid.yml
  cave-with-pig-and-nr-inwent.yml
  invalid-duplicate-id.yml
  invalid-coordinates.yml
  object-on-border.yml
  object-with-prefix-mismatch.yml
  object-with-manual-best.yml
```

Testy mutacyjne są szczególnie wskazane dla logiki, której błąd mógłby cicho uszkodzić dane:

- wybór najlepszego pomiaru,
- walidacja spójności współrzędnych,
- przypisanie prefixu,
- rozróżnienie error/warning,
- mapowanie referencji TPN/PIG.

---

## 17. Autoryzacja i role

W V1 autoryzacja = GitHub.

| Rola | Znaczenie |
|---|---|
| Reader | Może czytać repo publiczne. |
| Contributor | Może przygotować zmianę / PR. |
| Maintainer | Może merge’ować do `main`. |
| Verifier | Rola społeczna/procesowa; w praktyce osoba, której review pozwala oznaczyć pomiar jako `zweryfikowany`. |

Nie budujemy osobnego systemu kont.

Pole `verified_by` i `created_by` może używać krótkiego identyfikatora osoby, np. `dl`, albo GitHub handle. Szczegółowa polityka nazw użytkowników do ustalenia operacyjnie.

---

## 18. Wersjonowanie schematu

Każdy plik YAML zawiera:

```yaml
schema_version: 1
```

Zasady:

- V1 obsługuje tylko `schema_version: 1`,
- zmiany niekompatybilne wymagają podbicia wersji schematu,
- `schema/CHANGELOG.md` opisuje zmiany,
- migracje danych będą dopisywane dopiero, gdy pojawi się `schema_version: 2`.

---

## 19. Licencja i jawność danych

Repozytorium i dane projektu są publiczne.

Licencja danych własnych:

```text
Creative Commons Attribution 4.0 International (CC BY 4.0)
```

Zasady:

- brak mechanizmu ukrywania lokalizacji w V1,
- brak pola `sensitivity`,
- publiczne eksporty zawierają dokładne współrzędne najlepszych pomiarów,
- dane importowane z TPN, PIG, Geoportalu lub publikacji wymagają potwierdzenia, że mogą być redystrybuowane w ramach publicznego repo / release.

Do doprecyzowania przed dużym importem:

- warunki wykorzystania danych TPN,
- warunki wykorzystania danych PIG / Jaskinie Polski,
- warunki wykorzystania danych Geoportalu,
- sposób atrybucji źródeł w release i dokumentacji.

---

## 20. Etapy realizacji

### V0 — Scaffold

- `SPECYFIKACJA.md`,
- `config/prefixes.yml`,
- `data/shapes/` z referencyjnymi polygonami,
- wstępne pliki TPN/PIG do analizy.

### V1 — MVP git-native

Cel: pierwszy poprawny end-to-end flow od YAML do SQLite i eksportu.

Zakres:

- `git init` + push na GitHub,
- JSON Schema dla `Obiekt`, `Jaskinia`, `Relacja`,
- walidator lokalny i CI,
- `scripts/assign_id.py`,
- `scripts/build_db.py`,
- pierwszy realny `Obiekt`,
- pierwsza realna `Jaskinia`,
- przykład wielu otworów jednej jaskini,
- model referencji TPN/PIG zgodny z §4.5 i §7,
- build SQLite po merge do `main`.

### V2 — Release i regularna aktualizacja

- `release.yml`,
- eksport `best-measurements.*`,
- GitHub Release,
- miesięczny proces aktualizacji na podstawie maila z nowymi pomiarami,
- dokumentacja operacyjna: jak przygotować paczkę danych, jak dopisać pomiary, jak zrobić release.

### Import początkowy — ad hoc

Import TPN i PIG nie jest osobnym etapem produktu ani stałym mechanizmem.

Zakładamy jednorazowe działania ad hoc w tej kolejności:

1. **PIG jako pierwszy import** — buduje szkielet katalogowy: `Jaskinia`, `NR_INWENT`, PIG `ID`, linki, nazwy i wstępne pomiary o niskim priorytecie.
2. **TPN jako drugi import** — dopasowuje rekordy punktowe do obiektów, dodaje TPN `GLOBALID` i przejmuje rolę aktualnego pomiaru tam, gdzie rekord TPN został dopasowany.
3. Ręczne rozstrzygnięcie niejednoznaczności.
4. Zapis wyniku jako normalne pliki `data/objects/` i `data/caves/`.
5. Późniejsze zmiany prowadzone ręcznie przez YAML i PR.

Nie planujemy stałego importera Geoportal ani cyklicznych importów masowych w aktualnym zakresie.

Pomiary z PIG pozostają w historii, ale po dopasowaniu TPN nie powinny być domyślnie wskazywane jako `best_measurement`, chyba że operator ustawi ręczne `mode: manual` z powodem.

---

## 21. Otwarte pytania

Na później:

1. Pełny lifecycle obiektu: `active`, `rejected`, `merged`, `deprecated`.
2. Procedura merge/split duplikatów.
3. Rozbudowany model nazw i aliasów.
4. Pełna lista kategorii / podtypów dla `inne`.
5. Szczegółowa semantyka relacji.
6. Polityka dużych załączników, jeśli zdjęcia i raporty zaczną być liczne albo ciężkie.
7. Formalna procedura potwierdzania licencji źródeł zewnętrznych.
8. Reguły dla systemów transgranicznych PL/SK.
9. Czy dane morfometryczne jaskini wprowadzać jako pola `Jaskinia`, czy zostawić jako referencje do źródeł.

Poza aktualnym zakresem:

- frontend MapLibre,
- PWA do przeglądu offline,
- PWA do zbierania danych terenowych,
- integracja z GitHub API,
- plugin QGIS,
- stałe importy masowe,
- cykliczna synchronizacja z TPN, PIG lub Geoportalem.

---

## 22. Artefakty

Aktualne / planowane artefakty repo:

- `SPECYFIKACJA.md` — ten dokument,
- `config/prefixes.yml` — mapa polygonów na prefixy,
- `data/shapes/` — shapefile referencyjne EPSG:2180,
- `schema/*.schema.json` — walidacja YAML,
- `schema/CHANGELOG.md` — historia zmian schematu,
- `data/objects/` — źródło prawdy dla obiektów terenowych,
- `data/caves/` — źródło prawdy dla jaskiń / pozycji katalogowych,
- `data/relations/` — relacje obiekt-obiekt,
- `data/attachments/` — pliki powiązane,
- `scripts/` — narzędzia lokalne,
- `.github/workflows/` — CI/CD,
- `build/` — artefakty generowane lokalnie i w CI.

