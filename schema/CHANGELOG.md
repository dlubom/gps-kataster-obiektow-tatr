# Schema changelog

## schema_version: 2 — katalog YAML i model PostgreSQL, 2026-11-01 (PBI-119)

- Katalog używa plików YAML w `data/`. Znacznik `data/catalog.json` ma
  `format: postgresql-yaml`
  i `schema_version: 2`; schemat wykonywalny definiuje `schema/catalog.sql`.
- Tymczasowy PostgreSQL 18/PostGIS 3.6 odpowiada za typy, constraints,
  integralność referencji, geografię, automatyczny wybór Best i współrzędne
  pochodne. Zachowano ID, kolejność historii, źródła oraz ręczne Best
  z uzasadnieniami; historia jest dodatkowo porównywana z bazową rewizją Git.
- Pomiar ma jedną źródłową geometrię `Point` w EPSG:4326 albo EPSG:2180.
  Pozostałe współrzędne wylicza PostGIS; wysokość i datum są osobnymi polami.
  Przynależność obiektu do jaskini zapisuje pojedynczy FK `objects.cave_id`.
- Pliki YAML zapisują tylko źródłowe współrzędne, `cave_id` i
  `membership_ordinal` oraz politykę Best. `object_ids`, współrzędne pochodne
  i ID wybranego auto Best pozostają w modelu odczytu. Bieżące wejścia
  przyjmują wyłącznie v2; adapter historii czyta zaakceptowane v1/v2.
  Adapter YAML odrzuca niejawne konwersje typów i niepoprawne URI referencji/publikacji.
- Dodano publikacje oraz odrębne cytowania jaskiń, obiektów i pomiarów.
  Jawny stan bibliografii `unknown` jest legalny i raportowany ostrzeżeniem;
  `known` wymaga cytowania właściwego poziomu.
- Pełny dump PostgreSQL oraz GeoPackage z warstwami Best i historii zastępują
  SQLite i jego ZIP. Build wymaga restore dumpa i niezależnego odczytu
  GeoPackage; pozostałe formaty konsumenckie zachowują swoje kontrakty.
- Wersja 2 opisuje format zapisu katalogu, a nie wymuszoną zmianę każdego
  dokumentu JSON/YAML. Logiczny model odczytu i JSON Schema zaakceptowanej
  historii zachowują `schema_version: 1`. Wycofano formaty staging/decyzji
  oraz writer i konwersję bieżących wejść legacy.

## schema_version: 1 — rozszerzenie 2026-10-23

- Dodano `Pomiar.method: siec_pomiarowa`: pozycja wyznaczona z sieci
  pomiarowej jaskini, w tym z powiązanych pomiarów powierzchniowych.
  Nie oznacza bezpośredniego GNSS ani weryfikacji terenowej. Zapisany punkt
  dowiązania o nieznanej pierwotnej metodzie pozostaje `source_record`.
- Rozszerzenie enumu bez zmiany pól i schema_version; konsumenci stosujący
  zamkniętą listę metod muszą uwzględnić nową wartość.

## schema_version: 1 - 2026-05-15

- Dodano kontrakty JSON Schema dla plikow YAML `Obiekt`, `Jaskinia` i `Relacja`.
- Ustalono formaty ID: `{PREFIX}-{NNNN}` dla obiektow, `C-{NNNN}` dla jaskin,
  `R-{NNNN}` dla relacji oraz lokalne `m-{NNN}` i `a-{NNN}` dla pomiarow i
  zalacznikow.
- Utrwalono podstawowe enumy domenowe dla kategorii obiektow, zrodel,
  statusow weryfikacji, metod pomiaru, referencji zewnetrznych i typow relacji.
- JSON Schema obejmuje strukture i lokalne warunki pol, ale nie zastepuje
  pozniejszych walidacji cross-reference, geometrii ani algorytmu
  `best_measurement`.
