# U04 — jeden model zmian, jawny adapter legacy/staging

Przeczytaj [indeks](../README.md), [spec](../spec.md), [design](../design.md)
i [development](../development.md). Zależność: U03. Realizuje S02; chroni S04/S05.

## Spec

Fazy U02 już istnieją. Pozostała duplikacja reprezentacji: `LoadedDataset`
przenosi źródło i projekcję, staging/review utrzymuje `object_ids` obok
`cave_id` oraz wartości wyliczane, a writer je ponownie usuwa.
Przykładowo przeniesienie otworu nie powinno wymagać równoległej edycji
listy starej/nowej jaskini i członkostwa obiektu.

Wewnętrzne akcje zmian mają pracować na kanonicznych polach źródłowych.
Deklaracje importu trzeba jednak sprawdzić przed normalizacją: sprzeczne
współrzędne, powtórzone członkostwo i nieprawidłowy Best nadal blokują.
Zewnętrzny format raportów staging i decyzji operatora pozostaje zgodny.

## Design

- Wydziel jedną jawną konwersję sprawdzonego legacy/staging do źródłowego
  modelu zmian. Skorzystaj z `catalog_records.source_record`/`dataset_records`,
  ale nie przenoś do adaptera niejawnej naprawy niespójnych deklaracji.
- Akcje `staging_review` zmieniają wyłącznie źródłowe członkostwo,
  geometrię i politykę Best. Przy rzeczywistym dodaniu/przeniesieniu otworu
  przypisz następny ordinal po największym istniejącym, z zachowaniem luk.
  Ponowny `link_cave` do tej samej jaskini zachowuje istniejący ordinal;
  zachowaj również dotychczasową aktualizację audytu obiektu i jaskini.
- Odróżnij wejście zmian od `Catalog.dataset()`/`read_catalog_projection`
  w sygnaturach i nazwach. Mały typ nośnika jest uzasadniony tylko wtedy,
  gdy odbiorca korzysta z jego kontraktu; nie powielaj całego modelu w DTO.
- Końcowa kanoniczna propozycja w pamięci ma osobne wejście do adaptera
  źródłowego/SQL: sprawdzaj pola źródłowe i integralność SQL, bez ponownego
  JSON Schema v1 i deklaracji `object_ids`. Obecne `validated_proposal`
  pozostaje wejściem deklaracji legacy; nie podawaj mu źródłowego modelu
  bez list członkostwa, jakby nadal był legacy.
- Sprawdzenie redundantnych współrzędnych deklaracji przed konwersją
  wykonaj na istniejącym połączeniu katalogu wejściowego (zapytanie o podane
  wartości), bez osobnej bazy. Strukturalne kontrole deklaracji wykonaj
  przed ich odrzuceniem; nie waliduj ich dopiero po normalizacji.
- Wynikowa propozycja przechodzi SQL i historię raz. Zachowaj U02: jedna
  baza dla niezmienionego wejścia, druga tylko dla faktycznej propozycji,
  bez trzeciego ładowania i z cleanup przed zapisem.
- Historyczny adapter Git pozostaje osobną granicą. Nie usuwaj starych
  schematów, ani nie zmieniaj zaakceptowanych historycznych plików.

## Development

Punkt startu U04: head PR `a64340fc87a68f03ba8b2f5c473c59d38c771821`,
osobna baza historii `ad5fa191a36d5a5f45f0b2de523bd39125827573` (bieżąca baza PR).
Potwierdzono U01/U02/U03 w kodzie i 496 testach z poniższej komendy.
Przed U04 `create_cave`/`create_object` sprawdzały schemat staging, ale utrzymywały
deklaracje w modelu zmian; `add_measurement` walidował cały model legacy,
a `link_cave` synchronizował obie listy jaskiń z obiektem. Końcowy stan ponownie
trafiał do `validated_proposal`. PIG/TPN pozostają producentami zewnętrznego stagingu;
konwersja wybranych deklaracji odbywa się w review po ich kontroli. Odczyt Git
pozostaje osobną granicą. U06 (wynik writera) i U07 (przebudowa fixtures)
pozostają poza zakresem.

1. Opisz i scharakteryzuj `create_cave`, `create_object`, `add_measurement`
   i `link_cave` w `staging_review.py`. Testy obejmują legacy i canonical,
   bez zmian/ze zmianą, dry-run i zapis.
2. Prześledź producentów w `pig_staging.py`, `tpn_staging.py`, wejścia
   `validator.validated_proposal`, `postgres.open_proposal` oraz konwersje
   `catalog_records`. Wskaż dokładnie jedną granicę konwersji dla każdego wejścia.
3. Wprowadź adapter i przełącz akcje review. Usuń ich zbędną synchronizację
   `object_ids`, cache współrzędnych i wyliczonego auto Best. Jeśli raport
   nadal potrzebuje tych pól, pobierz je z projekcji zwalidowanej propozycji.
4. Zachowaj pierwotne ścieżki/ID w diagnostyce oraz brak/null, manual Best,
   źródłowy EPSG, cytowania i kolejność historii. Finalizacja notatek staging
   jest osobną polityką i nie może zniknąć przy ekstrakcji adaptera.
5. Usuń martwe ścieżki po migracji odbiorców. Sprawdź brak zmian danych
   i pełną zgodność eksportów; uaktualnij opis faz do faktycznych sygnatur.

```bash
uv run --frozen pytest -q tests/test_staging_review.py tests/test_pig_staging.py tests/test_tpn_staging.py tests/test_validation_phases.py tests/test_catalog_source_model.py tests/test_history.py
```

## Odbiór

- [x] Jedna akcja zmienia jedną reprezentację źródłową; nie utrzymuje
  drugiej listy członkostwa ani wyliczonych współrzędnych.
- [x] Niepoprawne deklaracje legacy/staging są wykrywane przed ich usunięciem.
- [x] Dodanie/przeniesienie otworu zachowuje ordinal z lukami, a ponowienie
  linku do tej samej jaskini nie zmienia istniejącego ordinal, również gdy
  nie jest on największy. Audyt obiektu/jaskini zachowuje dotychczasową semantykę.
- [x] Edycja notatki nie zmienia EPSG, pomiarów, Best ani niezmienionych plików;
  kanoniczna propozycja nie przechodzi ponownie walidacji schematu legacy.
- [x] Wszystkie akcje zachowują dotychczasowy raport, dry-run i atomowy zapis;
  U02 nadal sprawdza liczbę baz, historię i błędy cleanup.
- [x] Nie usunięto wsparcia prawdziwych legacy baseline; bilans konwersji
  i kodu oraz pełna bramka/eksporty/CI spełniają procedurę odbioru.

### Wynik implementacji i odbioru

- `SourceDataset` dziedziczy istniejący kontener rekordów, bez drugiego DTO.
  `source_dataset` usuwa sprawdzone deklaracje/projekcje raz na wejściu review;
  wybrane nowe rekordy używają `source_record`, a dopisywany pomiar konwertuje
  wyłącznie nowy payload. `open_source_proposal` wymaga tego typu i odrzuca
  pola wyliczane; `validated_source_proposal` dodaje ścieżki i integralność SQL.
  `validated_proposal` oraz adapter zaakceptowanego Git nadal obsługują legacy.
- **527 PASS** w sześciu plikach z karty: zachowano 496 wcześniejszych przypadków,
  dodano 31. Pierwsze regresje: **11 FAIL** przed implementacją. Osobny odbiór
  ujawnił i zamknął błędy wyjątku PostGIS, sufiksu `.yaml` i indeksu dopisywanego
  pomiaru (14 przypadków RED → GREEN). Dwa dalsze przypadki chronią kolejność
  kontroli malformed staging przed odczytem członkostwa.
- Niezależny review: brak Critical; ustalenie o wyjątku PostGIS i diagnostykę
  zamknięto regresjami. Indeks pomiaru potraktowano jako obowiązkowy kontrakt
  S02 (błędny indeks wskazywałby inny wpis historii), mimo niższej oceny review.
  Nie odroczono ustaleń U04. Poprawki potwierdzono testami, bez drugiego review.
- Testy potwierdzają **1 bazę bez zmian / 2 ze zmianą**, wspólne połączenie
  wejścia dla deklaracji i połączenie stanu końcowego dla historii. Cleanup
  poprzedza zapis, także po błędzie. Pełna walidacja legacy końcowego katalogu
  spadła z **1 do 0**; nie twierdzimy, że zmniejszyła się liczba baz względem U02.
- Python produkcyjny: **+283/−54, netto +229 linii**; bez zmian białych znaków
  **+277/−48, również +229**. Testy: **+344/−3**. SQL/schematy: **0/0**.
  Redukcja dotyczy reprezentacji i ponownej kontroli, nie wielkości kodu;
  jawne wejście źródłowe i zachowanie diagnostyki wymagają dodatkowego kodu.
- **13/13 formatów zgodnych** przy tym samym czasie `2026-11-05T18:00:00Z`
  i metadanych. Dziewięć plików tekstowych jest identycznych bajtowo. XLSX:
  oba arkusze, wszystkie komórki/typy/formaty oraz XML; Shapefile: składowe,
  pola, rekordy, geometria i CRS; GPKG: integralność, deklaracje i wszystkie
  tabele/wiersze/geometrie/typy/null; oba dumpy odtworzono natywnie i porównano
  15 tabel, oba widoki Best i schemat. Pominięto wyłącznie techniczne nagłówki
  ZIP/dump, datę DBF, `gpkg_contents.last_change`,
  `gpkg_metadata_reference.timestamp` i token `restrict` klienta PostgreSQL.
- **4185/4185 komunikatów identycznych**: kody, severity, ścieżki, opisy
  i kolejność; 0 błędów. Zachowano 1029 obiektów, 1019 jaskiń, 1946 pomiarów
  i 27 manual Best. Brak zmian `data/`, `config/`, `schema/` i CI względem bazy.
- Lokalnie PostgreSQL **18.6**, PostGIS **3.6.4**, GDAL **3.13.3**.
  Smoke zarządzanego Dockera pozostaje wymagany w CI.
- Pełna lokalna bramka zakończona: **1298 PASS / 1 SKIP**, Ruff, historia,
  pełny build, natywne restore dumpa, odczyt GPKG i `git diff --check` PASS.
  Lokalny skip dotyczy wyłącznie zarządzanego Dockera.

### Dostarczenie

- Kod: [`6121b570d278887f19c8328a26bc237afe928809`](https://github.com/dlubom/gps-kataster-obiektow-tatr/commit/6121b570d278887f19c8328a26bc237afe928809),
  potwierdzony jako head zdalnego PR #40. Dla tego SHA terminalne SUCCESS:
  [Validate code and data](https://github.com/dlubom/gps-kataster-obiektow-tatr/actions/runs/42083845143)
  i [PR export preview](https://github.com/dlubom/gps-kataster-obiektow-tatr/actions/runs/42083844958).
  CI: **1297 PASS / 2 SKIP**; oddzielny wymagany smoke Dockera: **1 PASS**.
  Natywne klienty PG przeszły lokalnie, a zarządzany Docker — w CI.
- [Paczka](https://github.com/dlubom/gps-kataster-obiektow-tatr/actions/runs/42083844958/artifacts/13441068353):
  SHA-256 `389625770bf6304dfe5442e6ba49af6687fa9fd453df45ef94ed36989445fe7d`
  zgodny z GitHub; **14/14 sum**, 15 właściwych plików, zgodne head/base/run/próba.
  Merge `622ce31f041f74f17ef89d3ebaec777a9b9f84b7` ma obu rodziców sprawdzonych w Git.
- Odczytano **13/13 formatów** i porównano pełne wartości, typy/null, kolejność,
  deklaracje oraz źródłowe geometrie. Dump: 15 tabel, oba widoki Best i schemat.
  Jedynie pochodne PL-1992 dopuszczały `1e-8 m`; zmierzony maksymalny odstęp
  wyniósł `1.9208528101444244e-9 m`. Źródła, wysokości i dokładności były ścisłe.
- Do porównania GPKG z CI użyto GDAL **3.12.0** z QGIS i jego własnego rejestru
  PROJ: WKT EPSG:2180 potwierdzono względem CI i zależności projektu. Innej
  definicji WKT z lokalnego GDAL 3.13.3 nie uznano automatycznie za równoważną.
  Warianty triggerów GDAL sprawdzono operacjami geometrii/FID/null/insert/delete
  na kopiach w pamięci. Indeksy sprawdzono przez `rtreecheck` i ścisłe odtworzenie
  wszystkich zakresów z geometrii; układ stron i zaokrąglenia float32 indeksu
  nie były utożsamiane ze źródłowymi współrzędnymi. Równoważne cytowanie nazw
  kolumn RTree potwierdzono deklaracjami `PRAGMA` tabel, FK i indeksów.
  Pozostałe normalizacje to
  opisane wyżej metadane techniczne i nagłówki wersji klientów PG.

Końcowe SHA dokumentacji, CI i odbiór jej paczki wskazuje [opis PR #40](https://github.com/dlubom/gps-kataster-obiektow-tatr/pull/40).
U05 i kolejnych zadań nie rozpoczęto; U06 jest tylko odblokowane zależnością.

Zakończ po U04. Następna zalecana karta: [U05](U05-spatial-read-model.md).
Wynik writera i porządki całego zestawu fixtures należą do U06/U07.
