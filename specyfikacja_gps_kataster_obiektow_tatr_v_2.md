# gps-kataster-obiektow-tatr — specyfikacja

> **Status**: _draft v3 / PBI-119_ — model domeny i migracja na PostgreSQL/PostGIS.
> **Zakres**: domena + wymagania + model danych + propozycja stosu technologicznego.
> **Odbiorcy**: zespół techniczny, speleolodzy, TPN, osoby weryfikujące dane terenowe.
>
> Źródłem prawdy są pliki YAML w repozytorium. Tymczasowy PostgreSQL/PostGIS waliduje katalog i wylicza dane eksportów. [Schematy](docs/architecture/schema.md), [instrukcja operacyjna](docs/operations.md).

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
| `created_at`, `created_by`, `updated_at`, `updated_by` | audyt | Audyt techniczny w tabelach; historia zmian i tak jest w git. |

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
| `id` | string | Wewnętrzne ID, np. `C-0001`. |
| `name` | string | Nazwa jaskini / pozycji katalogowej. |
| `system_name` | string, opt | Nazwa systemu jaskiniowego, jeśli dotyczy. |
| `external_refs` | lista `ExternalReference` | Numer inwentarzowy, PIG ID, PIG link, inne identyfikatory katalogowe. |
| `object_ids` | lista wyliczana | Otwory wynikające z `Obiekt.cave_id`; brak drugiego zapisu źródłowego. |
| `notes` | string, opt | Uwagi. |
| `created_at`, `created_by`, `updated_at`, `updated_by` | audyt | |

Jedna `Jaskinia` ma 1..N powiązanych `Obiektów`, jeśli znane są jej otwory. W V1 dopuszczamy utworzenie `Jaskinia` przed pełnym rozpoznaniem wszystkich otworów.

Powiązanie zapisujemy raz, jako `Obiekt.cave_id`. Lista otworów jaskini jest
wyliczana w widoku; nie można utrzymywać dwóch sprzecznych list. FK wymaga
istniejącej jaskini. Brak przypisania obiektu oraz pusta jaskinia są legalne.

### 4.3 `Pomiar`

`Pomiar` oznacza pojedynczy pomiar, import lub ustalenie lokalizacyjne dotyczące konkretnego `Obiektu`.

| Pole | Typ | Uwagi |
|---|---|---|
| `id` | string | Lokalny identyfikator w obrębie obiektu, np. `m-001`. |
| `input_geom` | Point z SRID | Jedyna geometria źródłowa: EPSG:4326 albo EPSG:2180. |
| `lat`, `lon` | float, WGS84 deg | Wyliczane w widoku; dla źródła 4326 zachowują wartości źródłowe. |
| `x_1992`, `y_1992` | float, EPSG:2180 m | Wyliczane: odpowiednio northing oraz easting. |
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
| `method` | enum | `gps_receiver` \| `gnss` \| `smartfon` \| `mapa_topo` \| `source_record` \| `siec_pomiarowa` \| `ustalenie` \| `inne`. |
| `device` | string, opt | Marka / model urządzenia, jeśli dotyczy. |
| `tags` | lista string | Wolne tagi, np. `weryfikacja_terenowa`. |
| `verification_status` | enum | `nieweryfikowany` \| `zweryfikowany` \| `odrzucony`. |
| `verified_by`, `verified_at` | user, datetime, opt | Wypełniane przy weryfikacji. |
| `notes` | string, opt | Uwagi. |
| `created_at`, `created_by` | audyt | |

Zasady:

- `method: siec_pomiarowa` oznacza pozycję wyznaczoną z sieci pomiarowej
  jaskini, również z powiązanych pomiarów powierzchniowych. `source_ref`
  i `notes` wskazują źródłową rewizję, stację oraz sposób dowiązania.
  Nie oznacza to bezpośredniego pomiaru GNSS ani statusu `zweryfikowany`.
  Wysokość wynikowa z sieci ma `elevation_source: other`; datum i dokładność
  pozostają nieznane, jeśli źródło ich nie potwierdza. Zapisany punkt
  dowiązania o nieznanej pierwotnej metodzie ma `method: source_record`
  i `elevation_source: source_record`. Metoda nie zmienia priorytetów auto
  ani ręcznego wyboru best.
- `Pomiar.id` jest unikalny w obrębie jednego obiektu, także dla identycznych
  rekordów oraz pomiarów odrzuconych lub niewskazanych jako best. To samo
  lokalne ID (np. `m-001`) w różnych obiektach jest dozwolone. Kolizja daje
  błąd `DUPLICATE_MEASUREMENT_ID` z plikiem, ID obiektu i pomiaru, przed
  indeksowaniem pomiarów i rozstrzyganiem referencji best/załącznika.
  Review, baza i eksporty blokują wtedy zapis. Nie wybieramy pierwszego
  rekordu, nie usuwamy duplikatu ani nie zmieniamy jego ID automatycznie.
  Poprawna historia zachowuje wartości i kolejność. Bezpośredni selektor
  best odrzuca powtórzone ID przez `ValueError` przed wyborem pomiaru.
- Współrzędne źródłowe mają jawny EPSG:4326 lub 2180. PostGIS wylicza pozostałe reprezentacje; nie zapisujemy drugiego ręcznie edytowanego cache.
- Migracja dotychczasowych danych zachowuje źródłowe `lon` i `lat` w 4326; różnicę względem starego cache kontroluje odbiór migracji.
- Wszystkie pola liczbowe pomiaru (`lat`, `lon`, `x_1992`, `y_1992`,
  `elevation_m`, `horizontal_accuracy_m`, `vertical_accuracy_m`) muszą być
  skończone. NaN i ±Infinity blokują zapis przez constraints lub adapter YAML
  (`SQL_CATALOG_INVALID` z plikiem i diagnostyką). Importery dodatkowo
  zwracają `PIG_MEASUREMENT_NON_FINITE` / `TPN_MEASUREMENT_NON_FINITE`
  ze źródłowym polem. Geometria, wybór Best i eksport nie pracują na
  niepoprawnym stanie. Dotyczy to całej historii, także pomiarów
  odrzuconych i niewybranych jako best. Opcjonalne `null` pozostaje legalne;
  reguła nie zmienia jednostek, zakresów ani znaczenia dokładności.
- `horizontal_accuracy_m` dotyczy dokładności poziomej, a nie wysokości.
- Dla danych PIG/TPN bez znanej dokładności pole `horizontal_accuracy_m` może być puste.
- Pomiar odrzucony nie jest usuwany, tylko dostaje `verification_status: odrzucony` oraz notatkę.

### 4.4 `BestMeasurement`

Każdy `Obiekt` ma wskazanie najlepszego aktualnego pomiaru.

```yaml
best_measurement:
  mode: auto
  manual_measurement_id: null
  reason: null
  updated_at: 2026-05-15T10:00:00Z
  updated_by: dl
```

| Pole | Typ | Uwagi |
|---|---|---|
| `mode` | `auto` \| `manual` | Czy wskazanie wynika z algorytmu, czy z decyzji operatora. |
| `manual_measurement_id` | FK → `Pomiar`, opt | Wskazanie ręczne; NULL dla auto. |
| `reason` | string, opt | Wymagane dla `manual`. Opcjonalne dla `auto`. |
| `updated_at`, `updated_by` | audyt | Kto i kiedy ustawił wskazanie. |

Zasady walidacji:

- W `manual` wskazanie musi dotyczyć pomiaru tego samego obiektu i mieć powód.
- W `auto` nie zapisujemy ID wybranego pomiaru. Widok SQL wylicza go z historii.
- Model odczytu i eksporty nadal pokazują ID wybranego oraz obliczanego Best.
- Uzasadnienie i audyt polityki wyboru są zachowane także przy migracji.

Domyślny algorytm `auto`:

1. Najnowszy własny pomiar o `verification_status = zweryfikowany`.
2. Jeśli brak własnych zweryfikowanych — najlepszy nieodrzucony pomiar z TPN.
3. Jeśli brak TPN — najlepszy nieodrzucony pomiar z własnych danych nieweryfikowanych.
4. Jeśli brak powyższych — najlepszy nieodrzucony pomiar z PIG.
5. Następnie nieodrzucony pomiar z pozostałych źródeł.
6. Jeśli brak nieodrzuconych — najnowszy jakikolwiek, ale z ostrzeżeniem walidatora.
7. W obrębie tego samego priorytetu wybieramy najnowszy czas: `observed_at`, a przy jego braku `observed_date` o północy UTC.
8. Przy remisie czasu — niższe `horizontal_accuracy_m`, z brakiem wartości na końcu.
9. Przy dalszym remisie — stabilny tekstowy porządek po `measurement.id`.

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

### 4.8 Bibliografia

`Publikacja` ma trwałe ID i niepusty pełny opis bibliograficzny. Autorzy,
tytuł, rok, czasopismo/wydawca, numer, DOI/ISBN i URL mogą być dodatkowo
zapisane oddzielnie. URL jest opcjonalny: opis ma pozwalać znaleźć źródło
w literaturze również wtedy, gdy odnośnik nie działa.

Przywołanie publikacji wskazuje jaskinię, konkretny obiekt lub konkretny
pomiar oraz stronę/pozycję/fragment, znaczenie dowodu i ewentualną nazwę
w źródle. Te trzy zakresy mają osobne tabele z FK. Jedna publikacja może
mieć wiele przywołań. Nie dziedziczymy cytowania jaskini na wszystkie otwory.

Jaskinia i obiekt deklarują `bibliography_status: known | unknown`.
`unknown` jest dozwolone także przy utworzeniu nowego rekordu, np. z TPN;
nie oznacza odrzucenia ani nieistnienia obiektu. `known` bez właściwego
cytowania jest błędem. Referencje TPN/PIG zachowujemy niezależnie od tego
statusu. Pochodzenie współrzędnych pozostaje na pomiarze.

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
- build może generować flagę `prefix_location_mismatch` w bazie i raportach walidacji.

### 5.6 Przydzielanie kolejnego numeru

W V1 zakładamy mały zespół i praktycznie jedną osobę wprowadzającą dane.

Zasada V1:

- `scripts/assign_id.py lat lon` proponuje prefix i kolejny wolny numer,
- numer to największy zajęty + 1, bez wypełniania luk; dla obiektów pliki
  są odczytywane z `data/objects/{PREFIX}/`,
- `assign_id` korzysta z `IdSequence`; adapter nazw rozpoznaje pliki `.yml`,
  `.yaml`, `.sql`, ignorując katalogi udające plik ID. Propozycja nie zapisuje
  YAML ani trwałych rezerwacji; wycofane ID nie mają osobnego rejestru (issue #33),
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

- SQL przechowuje jedną geometrię źródłową z EPSG; widoki wyliczają WGS84 i PL-1992.
- WGS84 i PL-1992 pochodzą z tego samego punktu źródłowego; nie zapisujemy dwóch niezależnie edytowanych pozycji.
- W katalogu i eksportach przelicza je PostGIS. PyProj może być używany w adapterach wejściowych i porównaniu historycznych danych.
- Shapefile referencyjne w `data/shapes/` są w EPSG:2180.
- PL-1992 używa polskiej konwencji osi: `X = northing`, `Y = easting`.

Podczas ręcznej oceny źródeł zachowujemy oryginalny układ i wartości.
Walidator sprawdza kompletność i spójność deklaracji; pomocnicze konwersje
odrzucają nieskończone wejścia i wyniki przez `ValueError`.

---

## 7. Źródła danych i mapowanie

### 7.1 TPN

Pomocniczy `scripts/fetch_tpn_data.py [--output PATH] [--timeout SECONDS]`
pobiera całe trzy publiczne warstwy: jaskinie `Topografia___wektor_MIL1/MapServer/6`,
leje `SIPTPN/Geologia_i_gleby/MapServer/3` oraz sztolnie/kopalnie
`SIPTPN/Dziedzictwo_kulturowe/MapServer/13`. Jeden JSON z wcięciami zachowuje
oddzielne warstwy, wszystkie atrybuty bez interpretacji, geometrię WGS84,
metadane JSON/XML, URL-e i przedział pobrania UTC. Licznik i komplet ID są
sprawdzane przed i po pobraniu; każda partia musi zawierać dokładnie żądane ID.
Gotowy plik jest publikowany atomowo bez nadpisania. Domyślny datowany zrzut
trafia do ignorowanego `data/sources/tpn/api/` i nie jest commitowany.
To odczyt źródła, bez importu, porównań, zmian danych/`best` lub harmonogramu.
[Kontrakt PBI-108](docs/asdlc/plans/PBI-108.md),
[obsługa i ograniczenia](docs/operations.md#pobieranie-jaskiń-lejów-i-sztolni-z-api-tpn).

Rozszerzenie PBI-109 dodaje opcjonalne `--simple-dir PATH [--with-nmt]`
oraz `--input RAW_JSON` do ponownego użycia lokalnego zrzutu. `simple.json`
zachowuje wszystkie dane obiektów, identyfikatory i współrzędne WGS84,
pomija otoczkę usług i cztery pola autorów/dat edycji; domeny kodowe
zamienia na opisy, nieznane pola/kody i null pozostają bez interpretacji.
`simple-nmt.json` dodaje `wysokosc_gruntu_nmt_m` i `status_nmt`, odczytując
dotychczasowy NMT w dokładnych punktach TPN dla wszystkich trzech warstw.
Pochodzenie jest oddzielone do lokalnego `nmt-evidence.json`. Surowy zrzut,
Dane katalogu i best pozostają bez zmian. Brak punktu/pokrycia daje null i jawny
status; błąd usługi lub zmiana źródła blokują publikację pliku NMT.
Kontrola źródła jest wspólna dla partii, wynik i dowód pozostają per punkt.
Wszystkie wygenerowane pliki są lokalne i nie są commitowane.
[Kontrakt i dowody](docs/asdlc/verification/PBI-109.md).

Pomocniczy odczyt `scripts/tpn_elevation.py --lat LAT --lon LON [--json]`
zwraca wysokość gruntu z publicznego NMT TPN, bez zapisu do `Pomiar` lub
zmiany `best`. Użytkownik zatwierdził źródło `nmt_05m_mggp_2019` / 0,5 m
przy niepotwierdzonej najnowszości. Legenda warstwy 0 określa wartości jako
„m n.p.m.” (`elevation_reference: sea_level`); dokładny układ wysokości
i dokładność pionowa są `unknown`. Wejście EPSG:4326 nie ustala datum
pionowego. Zakres dat nalotu według opisu „Wysokości” TPN to
`2019-10-14/2019-10-15`; wynik zachowuje odnośnik do tego dokumentu.
Brak danych i błędy nie dają wysokości zastępczej. Zmiana rozpoznanego
modelu wymaga ponownego przeglądu. [Kontrakt PBI-106](docs/asdlc/plans/PBI-106.md).

TPN jest traktowany jako źródło o wyższym priorytecie niż PIG dla aktualnej lokalizacji obiektu.

Plik TPN zawiera rekordy punktowe. W V1 przyjmujemy:

| Pole TPN | Interpretacja | Mapowanie |
|---|---|---|
| `GLOBALID` | ID rekordu punktowego | `Obiekt.external_refs`, `system: TPN`, `ref_type: source_globalid`. |
| `NR_INWENT` | Numer inwentarzowy | `Jaskinia.external_refs`, `system: NR_INWENT`, `ref_type: inventory_number`. |
| `NAZWA` | Nazwa jaskini / obiektu | `Jaskinia.name` lub `Obiekt.name_local` zależnie od przypadku. |
| `OTWÓR` | Opis / nazwa otworu | Pomocniczo do `Obiekt.name_local` i `notes`. |
| `GENEZA` | Charakter naturalny / górniczy | `sztolnia` uzasadnia kategorię `sztolnia`, także bez nazwy. Mieszane `jaskinia/sztolnia` zachowujemy jawnie do review. |
| `X1992`, `Y1992` | Współrzędne PL-1992 | Importowane do `Pomiar`, po konwersji także WGS84. |
| `Z` | Wysokość | `Pomiar.elevation_m`, z `elevation_source: source_record`. |
| `DLUGOSC`, `GLEBOKOSC`, `DENIWELACJ` | Dane morfometryczne | W V1 raczej notatka / przyszłe pola jaskini, nie część obiektu terenowego. |
| `SYSTEM` | Informacja o systemie | `Jaskinia.system_name`, jeśli jednoznaczne. |
| `WER_LOK`, `UWAGI` | Kontekst i zastrzeżenia źródłowe lokalizacji | Etykietowane `TPN WER_LOK:` / `TPN UWAGI:` w `Pomiar.notes`, dla nowych i dopasowanych rekordów. |

Zasady:

- TPN `GLOBALID` jest najlepszym kandydatem na zewnętrzną referencję do konkretnego `Obiektu`.
- Mieszana geneza `jaskinia/sztolnia` nie rozstrzyga kategorii terenowej.
  Zachowaj pełny kontekst źródła i rozstrzygnij kategorię na podstawie dowodów.
- Teksty `WER_LOK` i `UWAGI` zachowują treść źródłową i nie podnoszą statusu
  weryfikacji. Historyczne uzupełnienie opisuje [PBI-082](docs/asdlc/verification/PBI-082.md).
- Pomiary PIG pozostają w historii po dodaniu pomiarów TPN; algorytm Best
  respektuje ręczny wybór i priorytety źródeł.

### 7.2 PIG / Jaskinie Polski

PIG był źródłem importu początkowego i pozostaje materiałem do ręcznej oceny: `Jaskinia`, numery inwentarzowe, linki, nazwy i wstępne punkty.

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
- Początkowy import PIG utworzył bazowy katalog jaskiń i numerów inwentarzowych.
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

## 8. Ocena źródeł i deduplikacja

Początkowe importy PIG/TPN zakończono. Archiwalne XLSX, CSV i JSONL służą
ręcznej ocenie i dokumentują pochodzenie danych. Nowe rekordy i pomiary edytuje
się w YAML oraz sprawdza w PR; nie ma automatycznej materializacji decyzji.

Przy ocenie dopasowania operator uwzględnia identyfikatory źródłowe, numer
inwentarzowy, nazwę, kategorię i położenie. Różnica współrzędnych sama nie
potwierdza tożsamości ani weryfikacji terenowej. Pełny merge/split pozostaje
poza V1.

---

## 9. Historia i najlepszy aktualny stan

### 9.1 Historia

Zasady:

- Nie kasujemy fizycznie pomiarów tylko dlatego, że są błędne.
- Błędny pomiar dostaje `verification_status: odrzucony` i notatkę.
- Każdy obiekt ma 1..N pomiarów.
- Historia zmian YAML jest śledzona przez Git. CI porównuje pełny katalog z zaakceptowaną rewizją bazową; brak, usunięcie lub nadpisanie źródłowej pozycji albo wysokości starego pomiaru blokuje build. Zmiana notatki lub statusu jest dozwolona.
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

Dane są rekordami YAML w Git, po jednym pliku na encję. Schemat SQL i dane odtwarzają
bazę od zera; nie utrzymujemy serwera produkcyjnego ani sekwencji migracji
ręcznie stosowanych do długowiecznej instancji. Edycja odbywa się przez PR.

### 10.1 Struktura repo

```text
schema/catalog.sql        typy, constraints, tabele i widoki
config/prefixes.yml        konfiguracja regionów
 data/                    dane źródłowe
 ├── objects/PREFIX/*.yml  obiekt i jego pełna historia
 ├── caves/*.yml           jaskinie i referencje
 ├── publications/*.yml    bibliografia
 ├── relations/*.yml       relacje obiektów
 ├── attachments/          załączniki
 └── shapes/               niezmienione geometrie referencyjne
scripts/                   walidacja, pobieranie źródeł i eksport
build/                     wyłącznie wyniki generowane
```

Bieżące wejścia przyjmują wyłącznie YAML v2 ze znacznikiem
`catalog.json`: `format: postgresql-yaml`, `schema_version: 2`. Brak lub
niepoprawny znacznik blokuje odczyt; nie ma automatycznej adopcji legacy. Kanoniczne źródło wymaga
katalogów `objects`, `caves`, `relations` i `publications`, także gdy są puste.
Brak lub zwykły plik zamiast katalogu daje `DataDirectoryError` z jego ścieżką
(`DATA_DIRECTORY_INVALID` w walidatorze/CLI), przed otwarciem bazy i zapisem.
Loader nie odtwarza braków. Wejście katalogu PostgreSQL sprawdza znacznik
przed kontrolą układu katalogów.

Historyczny format legacy wymaga trzech pierwszych katalogów; brak
`publications` oznacza pustą bibliografię, ale plik tej nazwy jest błędem.
Kontrola zaakceptowanej rewizji Git zachowuje ten sam podział: odtwarza
wyłącznie katalogi obecne w jej drzewie, również utrwalone plikami pomocniczymi.
Nie uzupełnia niepełnego źródła kanonicznego ani nie pomija jego znacznika.
Ścieżka katalogu w zaakceptowanym commicie musi być drzewem Git; blob w jej
miejscu daje kontrolowane `HISTORY_BASELINE_UNAVAILABLE`.

Loader czyta pliki YAML z kontrolą powtórzonych kluczy. Jeden adapter
mapuje dane i obecność pól na parametry PostgreSQL. Ładowanie odbywa się
w transakcji na ograniczonym koncie; schemat tworzy zaufany kod builda.
Pozycja źródłowa to `input_srid`, `input_x` i `input_y` lub dotychczasowe
`lon` i `lat` w EPSG:4326. Kolejność listy `measurements` wyznacza historię.
Adapter sprawdza typy przed przekazaniem parametrów: bez automatycznej zamiany
tekstu na liczbę, liczby na tekst, bool na liczbę lub zaokrąglania pól całkowitych.
Referencje i publikacje wymagają poprawnego bezwzględnego URI bez sprawdzania
dostępności sieciowej. W źródle nie ma pól wyliczanych: `object_ids`, cache
współrzędnych i wybranego `measurement_id` w trybie auto. Loader zgłasza je
jako błąd. Narzędzia katalogu nie przepisują źródłowych YAML; zmiany
wprowadza się ręcznie i sprawdza przez PR. Źródłowe EPSG, wartości i null
oraz kolejność pomiarów pozostają chronione.

Kontrole mają odrębne granice: odczyt YAML nie zwraca projekcji PostgreSQL,
a walidacja istniejącego katalogu używa jego połączenia bez ponownego ładowania.
Projekcja z polami wyliczanymi nie jest kanonicznym wejściem YAML.
Build i wszystkie CLI współdzielą bramkę źródła, stanu SQL oraz rzeczywistej
zaakceptowanej rewizji Git. Bieżący loader odrzuca dowiązania plików YAML
oraz przekroczenie limitów 8 MiB na plik i 256 MiB na katalog przed parsowaniem.

Wyłącznie adapter historii czyta zaakceptowany baseline v1 lub v2.
Schematy JSON sprawdzają kompletność starszych rekordów przed porównaniem;
nie wymuszają aktualnego cache Auto Best w zaakceptowanej historii.
Usunięcie writera źródeł nie zmienia atomowej publikacji eksportów: helper
podmiany katalogów pozostaje w module `build_db`, przy jej właścicielu.

### 10.2 Edycja i historyczna zgodność

Plik obiektu zachowuje wszystkie jego pomiary, także stare i odrzucone.
Zmiana pozycji lub wysokości wymaga dopisania pomiaru z nowym lokalnym ID.
Dopisanie źródła, notatki lub zmiana statusu nie wymaga zmiany pozycji.
Kopiowanie współrzędnych pochodnych do źródłowych podczas takiej edycji
jest niedopuszczalne; natywne EPSG i wartości są zachowywane.

Ochrona historii odczytuje YAML z zaakceptowanej rewizji Git. Usunięcie
obiektu lub pomiaru, zmiana chronionych wartości, kolejności albo brak baseline
nadal dają błędy blokujące publikację. Nie ma interfejsów zapisu propozycji.

[Diagramy ERD i przepływu](docs/architecture/schema.md) oraz
[instrukcja pracy](docs/operations.md) uzupełniają wykonywalny schemat.

---

## 11. CI/CD

### 11.1 Walidacja

PR i push na main uruchamiają wymagane `Validate code and data`.
Środowisko lokalne i CI używają tego samego przypiętego PostgreSQL/PostGIS
oraz zależności z lockfile. Obowiązują formatowanie, lint, testy,
odtworzenie katalogu i kontrola historii z rzeczywistej rewizji bazowej.

Wspólną instalację Python/uv/GDAL, konfigurację klientów serwisu PG18
oraz zależności z `uv.lock` posiada lokalna akcja `setup-runtime`, używana
przez validate, preview, release i mutation. Zdarzenia, uprawnienia,
pełny checkout, serwisy, baseline i komendy kontroli pozostają jawne
w workflow. Preview zachowuje wyłączony cache uv; Node jest instalowany
wyłącznie dla testów publishera w validate/mutation. Zaufany publisher
preview nie używa lokalnej akcji z head PR. Setup nie pomija żadnej kontroli.

Błędy blokujące obejmują:

- niedozwolony SQL, nieprawidłowe typy/formaty, NULL w obowiązkowym polu,
- duplikaty ID i TPN GLOBALID, nieistniejące lub obce referencje,
- obiekt bez pomiaru albo polityki Best, manual bez powodu,
- `known` bibliografii bez cytowania odpowiedniego zakresu,
- NaN/Infinity, niewłaściwy typ geometrii/EPSG/zakres współrzędnych,
- pomiar poza granicami PL/SK i skonfigurowanymi regionami,
- nieistniejący załącznik lub błędny URL,
- usunięta/nadpisana pozycja historyczna oraz niedostępny baseline,
- nieudane odtworzenie albo odczyt eksportu.

Ostrzeżenia zachowują istniejące znaczenie: nieznana dokładność/źródło,
punkt poza dolinami, rozbieżny prefix, odległe pomiary, brak przypisanej
jaskini, niewłaściwy poziom referencji PIG/NR_INWENT i odrzucony fallback.
Jawne `unknown` bibliografii jest raportowane bez blokowania wpisu.

Timeout, wyjątek lub pominięta wymagana kontrola nie jest wynikiem poprawnym.
Kod PR działa bez sekretów publikacji. Zaufany publisher nie wykonuje kodu PR.

### 11.2 Build i podgląd PR

Jedna zweryfikowana baza dostarcza Best i pełną historię do wszystkich
formatów. `prepare_export_data` przygotowuje raz na build niezmienne Best,
pełną historię, jej wybrane wiersze oraz wspólny czas generowania. Wiersz
historii składa się z metadanych obiektu/jaskini i konkretnego pomiaru;
braków nie uzupełnia pomiar Best. Excel zachowuje prezentację, a nazwy
i typy wspólnych pól GeoPackage określa neutralny moduł `export_data`.
Wyniki powstają w nowym katalogu roboczym; do odbiorcy trafia
wyłącznie kompletny zestaw po restore i odczycie kontrolnym. Awaria nie
zastępuje wcześniejszych poprawnych wyników. Tymczasowa baza jest usuwana
również po błędzie. `build/` pozostaje ignorowany przez Git.

Builder, CLI i paczkowanie konsumują `ReleaseArtifactsResult.artifact_paths`:
8 plików Best oraz 5 dodatkowych plików wydania, w stałej kolejności. Przed
podmianą katalogu sprawdzany jest dokładny zestaw zwykłych plików, bez braków,
nadmiaru, duplikatów, dowiązań i ścieżek poza katalogiem wynikowym. Opcjonalne
`build_release_artifacts.py --artifact-list` zwraca po sukcesie 13 ścieżek
rozdzielonych bajtem NUL na stdout. Workflow używa tej listy jako argumentów
publikacji; nie utrzymuje drugiego spisu ani nie zbiera obcych plików wildcardem.
Lista nie wchodzi do paczki. Domyślny tekst CLI oraz kody, kanały diagnostyki
i rzeczywisty baseline historii pozostają zgodne. Samodzielne Best nadal
odmawia zastąpienia pełnej paczki po walidacji wejścia i historii.
Katalog wyjściowy nie może nakładać się na źródłowe dane (także przez
dowiązanie), być repozytorium lub jego przodkiem ani leżeć w `.git`.
Istniejący katalog może zawierać tylko zwykłe pliki należące do budowanego
zestawu artefaktów. Obcy plik, podkatalog lub dowiązanie blokuje podmianę
i zachowuje całą poprzednią zawartość. Dołączenie takich plików do paczki
wymaga osobnej decyzji; eksport nie usuwa ich ani nie pakuje automatycznie.

### 11.3 Wydanie

Workflow taga `v*` wykonuje tę samą walidację, build i odbiór, a następnie
publikuje pliki. Samo otwarcie ani przejście draft PR nie tworzy wydania.
Merge, tag i publikacja wymagają osobnego polecenia użytkownika.

---

## 12. Build: PostgreSQL/PostGIS i GeoPackage

PostgreSQL/PostGIS przejmuje integralność, wybór auto Best i przeliczenia
geometrii. [DDL](schema/catalog.sql) jest wykonywalnym modelem danych.
Pełny snapshot jest eksportowany przez `pg_dump` w formacie custom.
Odbiór odtwarza go w nowej bazie i porównuje zawartość oraz wynik Best.

GeoPackage jest pochodnym plikiem do GIS z warstwami Best i pełnej historii
pomiarów. Zawiera jawne CRS; wysokość i datum pozostają osobnymi atrybutami.
Jest ponownie odczytywany i porównywany z tym samym stanem PostgreSQL.
Pełny model relacyjny, w tym bibliografia, jest dostępny w dumpie.

Python pozostaje odpowiedzialny za pliki, lifecycle bazy i zapis
formatów konsumenckich. Walidacje, które dotyczą systemu plików lub źródła
zewnętrznego, nie są zastępowane fikcyjnym constraints w bazie.

---

## 13. Release i eksporty

### Paczka do przeglądu PR

Otwarcie, ponowne otwarcie oraz każdy push do PR, także draftu, budują
pełne eksporty przez istniejący builder wydania. Źródłem jest dokładny
syntetyczny merge PR z bazą, ze sprawdzeniem SHA obu rodziców.
ZIP GitHub Actions zawiera pliki wydania, `preview.json` (repozytorium,
numer PR, head/base/merge SHA, run i próba, czas) oraz `SHA256SUMS`.
Retencja wynosi 14 dni; link wymaga logowania GitHub.

Zaufany workflow z domyślnej gałęzi utrzymuje jeden komentarz bota
z aktualnym stanem budowania, błędem albo linkiem i datą wygaśnięcia.
Weryfikuje aktualny head, bazę, merge i próbę; opóźniony wynik nie
zastępuje nowszego. Kod PR ma tylko odczyt repozytorium; publisher
nie pobiera ani nie wykonuje zawartości paczki.
Zmiana samej bazy wymaga nowego buildu (push lub ponowne otwarcie PR).
Konflikt merge uniemożliwia uruchomienie buildu `pull_request`.

Workflow publikujący komentarz musi najpierw znaleźć się na `main`.
W instalacyjnej PR link dodaje operator po sprawdzeniu artefaktu.
Automatyzacja komentarza jest obsługą CI, poza zakresem aplikacyjnej
integracji z GitHub API wykluczonej w §14. Paczka nie publikuje wydania.

### Oficjalne wydanie

Tag release:

```text
v{major}.{minor}.{patch}
```

Przykład:

```text
v1.0.1
```

Każdy release zawiera:

| Plik | Format | Uwagi |
|---|---|---|
| `best-measurements.geojson` | GeoJSON | WGS84, z PL-1992 w `properties`. |
| `best-measurements.gpx` | GPX | WGS84, do GPS receiverów. |
| `chocholowska-lejowa-koscieliska.gpx` | GPX | Dodatkowy podzbiór: całe doliny Chochołowska, Lejowa i Kościeliska; do 500 punktów. |
| `mietusia-sucha-woda.gpx` | GPX | Dodatkowy podzbiór: całe doliny od Miętusiej po Suchą Wodę; do 500 punktów. |
| `pozostale-pl-sk.gpx` | GPX | Dodatkowy podzbiór: PL/SK poza granicami regionów dolin; do 500 punktów. |
| `best-measurements.csv` | CSV | Oba układy współrzędnych. |
| `katalog.xlsx` | Excel | Best: podstawowe pola wybranych punktów z CSV; Full: wszystkie pomiary z danymi obiektu z PostgreSQL, także starsze/odrzucone, z oznaczeniem wyboru. Filtry, typowane liczby i daty, polskie nagłówki. |
| `best-measurements.shp.zip` | ESRI Shapefile | EPSG:2180, QGIS / TPN. |
| `katalog.dump` | PostgreSQL custom | Pełny snapshot relacyjny; wymagany PostgreSQL/PostGIS do odtworzenia. |
| `katalog.gpkg` | GeoPackage | Best i pełna historia pomiarów do GIS. |
| `metadata.json` | JSON | Liczby obiektów, pomiarów, jaskiń, data buildu, wersja schematu. |
| `statistics.md`, `statistics.json` | Markdown, JSON | Automatyczne statystyki tej samej paczki: obiekty, pozycje katalogowe, historia pomiarów, rodzaje, źródła, weryfikacja i dostępność dokładności. Wersja wydania, commit źródeł i czas generowania. |

Excel zachowuje daty dzienne od `1900-01-01` jako daty, a wcześniejsze
jako tekst ISO `YYYY-MM-DD`, bez zmiany wartości źródłowej.

Statystyki liczą te same wybrane wiersze, które trafiają do CSV, a pozycje
katalogowe i historię z tego samego `ExportData`. Nie odczytują CSV, nie
składają historii ani nie wybierają Best ponownie. Brak wskazanego pomiaru
w historii blokuje przygotowanie danych eksportowych. Tabela sposobu
wyznaczenia pozycji jest niezależna od tabeli źródeł.
Zapisana `method` ma pierwszeństwo. Dla `ustalenie` oba tagi `lidar`
i `gnss_anchor` oznaczają prezentację „LiDAR dowiązany GNSS”; dla
`source_record` tag `survey_anchor` oznacza punkt dowiązania o nieznanej
metodzie pierwotnej. Pozostałe metody są prezentowane zgodnie z zapisem.
Sam tag `gnss_anchor` nie oznacza bezpośredniego GNSS. Etykieta GNSS nie
potwierdza geodezyjnego rodzaju pomiaru ani jego dokładności. Rozbicie
`by_position_method` jest addytywnym polem JSON statystyk w wersji 1;
nie zmienia schematu ani priorytetów pomiarów. `wlasne` jest prezentowane
jako „Opracowania własne”, bez zmiany wartości źródłowej.
Markdown zawiera tabele PL/EN/SK i jest dodawany do opisu wydania.
Brak deklarowanej dokładności oznacza wartość nieznaną, nie zero.
Lokalny build bez wersji/commitu jest oznaczany jako podgląd lokalny.

Etykieta punktu GPX (`wpt/name`) używa `Obiekt.name_local`, zachowując nazwę
konkretnego otworu. Brak, `null`, pusta nazwa lub same białe znaki oznaczają
użycie `Obiekt.id`.
Opis (`wpt/desc`) zawsze zawiera jawne `object <ID>`, ID wybranego pomiaru,
źródło, datę i dostępne uwagi. Nazwy nie zastępują trwałych identyfikatorów.

Pełny `best-measurements.gpx` pozostaje bez limitu 500. Trzy dodatkowe pliki
razem zawierają dokładnie te same punkty, każdy w jednej grupie. Przypisanie
wynika z regionu wskazanego Best w `v_measurement_regions`: PostGIS stosuje
`ST_Covers` do geometrii źródłowej i priorytet `boundaries.ordinal`, także
na zewnętrznych granicach i granicach otworów w poligonach. `Catalog.dataset()`
przenosi regiony osobno od rekordów YAML, a `ExportData` wybiera region manual
albo auto Best. Build i standalone GPX nie uruchamiają resolvera Pythona.
Region jest wewnętrzną daną sterującą; nie dodaje kolumn CSV, Full ani GeoPackage.
Trwałe ID i propozycja auto nie zastępują regionu wskazanego manual Best.
Wschód/zachód każdej doliny pozostają razem. Mapowanie grup opisuje
`docs/release_artifacts.md`. Waypointy zachowują wszystkie pola pełnego GPX;
nazwa zbioru w metadanych wskazuje grupę. Powstają także puste pliki grup.
Przekroczenie 500 lub nieznany region blokuje zapis eksportów przed ich
nadpisaniem i zatrzymuje publikację; nie obcinamy punktów ani nie dzielimy
dolin automatycznie. Ponowne grupowanie wymaga decyzji. `metadata.json`
zachowuje dotychczasowy kontrakt. Wszystkie GPX są w buildzie, podglądzie PR
i nowych wydaniach; dane źródłowe i wybór Best pozostają bez zmian.

Repo i eksporty są publiczne. Dane projektu, dokumentacja repozytorium oraz generowane eksporty są licencjonowane jako **Creative Commons Attribution 4.0 International (CC BY 4.0)**. Atrybucję źródeł zachowujemy przez referencje zapisane w YAML i eksportach.

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

Podstawowym sposobem pracy jest repozytorium, pliki YAML, walidacja CI oraz generowane eksporty. Do przeglądania danych wystarczają QGIS, CSV, GeoJSON, GPX i GeoPackage.

---

## 15. Zbieranie nowych pomiarów

W aktualnym modelu nie planujemy aplikacji terenowej.

Docelowy proces operacyjny:

1. Osoby wykonujące pomiary zbierają dane dowolnymi narzędziami: GPS / GNSS, GPX, CSV, notatka w telefonie, zdjęcie, kartka.
2. Wyznaczona osoba porządkuje dostarczone dane, dopisuje lub aktualizuje YAML, uruchamia walidację i otwiera PR.
3. Po review i merge aktualne artefakty można zbudować lokalnie albo opublikować przez ręczny tag release.

Nie przewidujemy w tym zakresie:

- PWA do zbierania pomiarów,
- generowania plików katalogu w terenie,
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
- testy mutacyjne dla krytycznej logiki walidacji i geometrii,
- typowanie w kodzie Python, z docelową możliwością uruchamiania type checkera,
- spójne komendy lokalne i CI.

Minimalny zestaw V1:

```text
scripts/assign_id.py lat lon
scripts/validate.py
scripts/build_db.py
scripts/export_best_measurements.py
scripts/build_release_artifacts.py
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

- czyta YAML i schemat SQL,
- buduje i weryfikuje PostgreSQL/PostGIS,
- tworzy indeksy,
- zapisuje `katalog.dump` i weryfikuje jego odtworzenie.

### 16.4 `export_best_measurements.py`

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

Zwykłe testy builda, eksportów i podglądu podają bezpośrednio kanoniczny YAML
do produkcyjnego API/CLI. Fabryki nie uruchamiają walidatora, SQL ani writera.
Osobne repozytorium Git utrwala zaakceptowany fixture przed uszkodzeniem
kandydata; jego SHA jest jawnym argumentem wejścia. Testy historycznego baseline v1 i v2 mają osobne scenariusze; bieżący
kandydat jest jawnym fixture v2, bez produkcyjnego konwertera źródeł. Wzorce wartości i odczyty
XLSX, GeoPackage, Shapefile oraz dumpa są niezależne od serializera eksportu.

Wymagane testy V1:

- testy odczytu i walidacji katalogu YAML,
- testy JSON Schema,
- testy konwersji WGS84 ↔ EPSG:2180,
- testy point-in-polygon i przydzielania prefixu,
- testy `best_measurement` w trybie `auto` i `manual`,
- testy wykrywania błędów i warningów walidatora,
- testy PostgreSQL/PostGIS oraz odtworzenia dumpa i GeoPackage na małych fixture’ach,
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

Format `postgresql-yaml` ma wersję 2 i jawny znacznik w `data/`. Schemat wykonywalny
jest w `schema/catalog.sql`, a zmiany opisuje `schema/CHANGELOG.md`.
Reprezentacje legacy wersji 1 służą wyłącznie odczytowi zaakceptowanej
historycznej bazy Git. Bieżące API/CLI odrzucają je przed zapisem wyników.
Zmiana niekompatybilna wymaga jawnej migracji, testu historii i odtworzenia.

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
- dane importowane z TPN, PIG, Geoportalu lub publikacji zachowują referencje źródłowe potrzebne do atrybucji w publicznym repo / release.

Do doprecyzowania przy nowych kategoriach źródeł:

- warunki wykorzystania danych TPN,
- warunki wykorzystania danych PIG / Jaskinie Polski,
- warunki wykorzystania danych Geoportalu,
- sposób atrybucji źródeł w release i dokumentacji.

---

## 20. Zakres utrzymania

Katalog jest aktualizowany ręcznie przez PR i wydawany przez tag semver.
Źródła PIG i TPN służą ręcznej ocenie; nowe pomiary i rekordy edytuje się
bezpośrednio w YAML i poddaje review w PR. Pomiary PIG pozostają w historii po dodaniu TPN. Nie planujemy stałego
importera Geoportal ani cyklicznych importów masowych.

---

## 21. Otwarte pytania

Na później:

1. Pełny lifecycle obiektu: `active`, `rejected`, `merged`, `deprecated`.
2. Procedura merge/split duplikatów.
3. Rozbudowany model nazw i aliasów.
4. Pełna lista kategorii / podtypów dla `inne`.
5. Szczegółowa semantyka relacji.
6. Polityka dużych załączników, jeśli zdjęcia i raporty zaczną być liczne albo ciężkie.
7. Szczegółowe zasady atrybucji, jeśli pojawią się nowe kategorie źródeł.
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
- `schema/catalog.sql` — model katalogu i walidacja SQL,
- `schema/*.schema.json` — zachowane schematy legacy i historii,
- `schema/CHANGELOG.md` — historia zmian schematu,
- `data/objects/` — źródło prawdy dla obiektów terenowych,
- `data/caves/` — źródło prawdy dla jaskiń / pozycji katalogowych,
- `data/relations/` — relacje obiekt-obiekt,
- `data/attachments/` — pliki powiązane,
- `scripts/` — narzędzia lokalne,
- `.github/workflows/` — CI/CD,
- `build/` — artefakty generowane lokalnie i w CI.
