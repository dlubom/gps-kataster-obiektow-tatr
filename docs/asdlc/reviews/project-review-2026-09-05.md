# Przegląd projektu — 5 września 2026

Przegląd lokalnego `main`, commit `a3dd1a671d3d93cd6958242fc68ddcf1d37cf846`.
Znalazłem 13 problemów: 3 o priorytecie P1, 9 o priorytecie P2 i 1 o priorytecie P3. Najważniejsze dotyczą cichego pomijania historii YAML, zapisu niepoprawnych danych przez operator review oraz niespójnych powiązań obiekt–jaskinia. To błędy potwierdzone na danych testowych; nie oznacza to, że obecny katalog zawiera wszystkie opisane uszkodzenia.

P1 oznacza naprawę w pierwszej kolejności ze względu na ryzyko uszkodzenia danych. P2 oznacza istotną poprawkę funkcjonalną lub brak walidacji. P3 oznacza poprawkę odtwarzalności artefaktów.

Podczas przeglądu kod, finalne YAML, specyfikacja i backlog nie były zmieniane. Eksperymenty wykonano na kopiach tymczasowych. Raport i dwa krótkie logi zostały następnie utrwalone w repo w ramach PBI-034. Numery ustaleń 1–13 są identyfikatorami R01–R13 w planie napraw; odnośniki do linii opisują commit przeglądu, nie przyszły stan kodu. Bieżący status napraw podaje [backlog](../backlog_v1.md), a ich zakres [plan](../remediation_plan.md).

1. **[P1] Powtórzony klucz YAML po cichu usuwa wcześniejszą wartość z wczytywanych danych.**

   Miejsce: [data_loader.py:130](../../../src/gps_kataster_obiektow_tatr/data_loader.py#L130).

   Loader używa `yaml.safe_load`, który przy dwóch kluczach `measurements:` zachowuje ostatnią listę. Walidator widzi już tylko tę listę, więc nie potrafi wykryć pominięcia wcześniejszej historii. Na poprawnym obiekcie dopisałem wcześniejszy blok `measurements` z innym pomiarem: walidacja zwróciła zero problemów, a SQLite zbudował się z pominięciem tego bloku. Surowy plik nie jest zmieniany przez sam odczyt, ale późniejsze zapisanie obiektu przez review utrwala wynik parsowania.

   Naprawa: loader odrzucający duplikaty kluczy, również zagnieżdżonych, z lokalizacją błędu; zastosowanie tej samej zasady do plików decyzji. Test powinien potwierdzać błąd przed buildem i przed jakimkolwiek zapisem finalnych danych.

2. **[P1] Operator review zapisuje finalne YAML bez walidacji wynikowego katalogu.**

   Miejsce: [staging_review.py:292](../../../src/gps_kataster_obiektow_tatr/staging_review.py#L292).

   Warunek zapisu sprawdza tylko błędy zgłoszone podczas obsługi poszczególnych decyzji. Nie uruchamia walidacji schematu ani zależności dla wynikowych danych. Reprodukcja: zaakceptowanie samego `create_object` z poprawnego staging PIG, bez utworzenia wskazanej jaskini. Wynik: `has_errors=False`, jeden zapisany plik; dopiero osobne `validate.py` zgłasza `CAVE_REFERENCE_MISSING`. To przeczy obietnicy blokowania błędnych decyzji przed zapisaniem finalnych YAML.

   Naprawa: po zastosowaniu całej partii w pamięci zwalidować cały wynikowy katalog i dopiero wtedy rozpocząć zapis. Przy błędzie nie zmieniać żadnego finalnego pliku. Osobno warto zabezpieczyć zapis wielu plików przed częściowym powodzeniem przy błędzie I/O — obecne pętle zapisują pliki kolejno.

3. **[P1] Przeniesienie obiektu do innej jaskini pozostawia sprzeczne powiązania.**

   Miejsca: [staging_review.py:679](../../../src/gps_kataster_obiektow_tatr/staging_review.py#L679), [validator.py:297](../../../src/gps_kataster_obiektow_tatr/validator.py#L297).

   `link_cave` ustawia nowe `Obiekt.cave_id` i dopisuje ID do nowej jaskini, lecz nie usuwa go z `object_ids` starej jaskini. Walidator sprawdza istnienie wskazanych rekordów, ale nie symetrię relacji. Reprodukcja: przeniesienie `KSW-0001` z `C-0001` do `C-0002` kończy się sukcesem, stara jaskinia nadal zawiera ten obiekt, a walidacja zwraca zero problemów. Taki katalog może również zbudować SQLite i dawać sprzeczne odpowiedzi zależnie od kierunku odczytu relacji.

   Naprawa: przy zmianie jaskini aktualizować obie strony, w tym starą jaskinię; walidować równoważność `object.cave_id == cave.id` i obecności obiektu w `cave.object_ids`. Obecny katalog sprawdzony zapytaniami SQL nie ma takich niespójności.

4. **[P2] Walidator nie wykrywa duplikatów lokalnych identyfikatorów pomiarów i załączników ani identyfikatorów jaskiń.**

   Miejsca: [validator.py:115](../../../src/gps_kataster_obiektow_tatr/validator.py#L115), [validator.py:255](../../../src/gps_kataster_obiektow_tatr/validator.py#L255).

   Dwa różne pomiary `m-001` jednego obiektu przechodzą walidację bez ostrzeżeń. Build SQLite kończy się `UNIQUE constraint failed: measurements.object_id, measurements.id`. Sam eksport wybiera pierwszy wpis z tym ID: w reprodukcji wyeksportował wysokość 1240 m, mimo że nowszy wpis miał 999 m. Dwa pliki `C-0001.yml` i `C-0001.yaml` również przechodzą walidację, lecz blokują SQLite na `caves.id`. Dwa różne załączniki z ID `a-001` także nie dają żadnego komunikatu walidatora.

   Naprawa: sprawdzać unikalność ID każdej encji we właściwym zakresie: globalnie dla jaskiń i relacji, lokalnie w obiekcie dla pomiarów i załączników. `uniqueItems` porównujące całe słowniki nie zastępuje unikalności ich ID.

5. **[P2] `NaN` przechodzi walidację współrzędnych i trafia do eksportu.**

   Miejsce: [validator.py:493](../../../src/gps_kataster_obiektow_tatr/validator.py#L493).

   Po ustawieniu `x_1992: .nan` w poprawnym obiekcie walidator nie zgłasza żadnego problemu. Obliczony błąd współrzędnych też jest `NaN`, a porównanie `NaN > tolerance` nie zachodzi. SQLite następnie zgłasza `NOT NULL constraint failed: measurements.x_1992`, natomiast sam eksport zapisuje dosłowne `NaN` w GeoJSON, czyli dokument niezgodny ze standardowym JSON.

   Naprawa: wymagać skończonych wartości wszystkich pól liczbowych przed obliczeniami; odrzucać `NaN` i nieskończoność już przy parsowaniu importów. W serializacji JSON stosować `allow_nan=False` jako dodatkowe zabezpieczenie.

6. **[P2] Nie jest sprawdzana spójność danych o przydzieleniu trwałego ID.**

   Miejsca: [schema/object.schema.json:293](../../../schema/object.schema.json#L293), [validator.py:255](../../../src/gps_kataster_obiektow_tatr/validator.py#L255).

   Obiekt `KSW-0001` z `assigned_from_measurement_id: m-999` i `assigned_prefix: ABC` przechodzi walidację bez problemów, chociaż pomiar nie istnieje, a utrwalony prefix jest inny. Ponadto wszystkie 16 obecnych obiektów z `OBJECT_PREFIX_MISMATCH` mają puste `prefix_override_reason`, mimo wymagania uzasadnienia w specyfikacji §4.1 i §5.5. Niezgodność bieżącej lokalizacji nie jest sama w sobie powodem do zmiany ID.

   Naprawa: sprawdzać referencję do pomiaru przydziału oraz zgodność `assigned_prefix` z ID. Brak wymaganego uzasadnienia zgłaszać osobno od ostrzeżenia o lokalizacji. Uzupełnienie powodów w obecnych danych wymaga ustalenia rzeczywistego uzasadnienia, bez wymyślania go i bez renumeracji obiektów.

   Obiekty wymagające uzupełnienia powodów: `BYZ-0006`, `BYZ-0010`, `BYZ-0014`, `BYZ-0016`, `BYZ-0018`, `BYZ-0020`, `BYZ-0021`, `BYZ-0022`, `BYZ-0037`, `CHZ-0011`, `KSW-0127`, `KSZ-0006`, `MLZ-0045`, `PL-0019`, `STR-0014`, `STR-0019`.

7. **[P2] Kilka aktualizacji TPN w jednej partii dostaje ten sam identyfikator pomiaru.**

   Miejsce: [tpn_staging.py:662](../../../src/gps_kataster_obiektow_tatr/tpn_staging.py#L662).

   `next_measurement_id` jest wyliczany raz przy budowaniu kandydata. Dwa różne rekordy TPN dopasowane do tego samego obiektu otrzymały w reprodukcji `m-002`. Oba wiersze miały status `matched`, ale zaakceptowanie ich razem zakończyło się `MEASUREMENT_ALREADY_EXISTS` i zablokowaniem całej partii. Nie ma rezerwowania kolejnych numerów wewnątrz stagingu ani ponownego przydziału numeru przy wskazaniu innego obiektu przez operatora.

   Naprawa: deterministyczny licznik pomiarów per obiekt dla całej partii albo przydział lokalnego numeru dopiero przy materializacji decyzji.

8. **[P2] Finalne dane i zachowany staging PIG dublują tych samych kandydatów.**

   Miejsce: [tpn_staging.py:133](../../../src/gps_kataster_obiektow_tatr/tpn_staging.py#L133).

   Importer skleja kandydatów z finalnego YAML i PIG staging bez deduplikacji po `object_id`. Po zaakceptowaniu obiektu PIG i pozostawieniu jego raportu w domyślnej lokalizacji ten sam obiekt występuje dwukrotnie. W reprodukcji dopasowania, które były `matched` bez raportu PIG, stały się `unresolved` z `TPN_NR_INWENT_AMBIGUOUS` po udostępnieniu raportu tego samego obiektu.

   Naprawa: scalać kandydatów po trwałym ID; istniejący rekord finalny powinien mieć pierwszeństwo przed jego historyczną propozycją staging.

9. **[P2] Operator nie może rozstrzygnąć wiersza `unresolved` przez wskazanie docelowego obiektu.**

   Miejsca: [tpn_staging.py:204](../../../src/gps_kataster_obiektow_tatr/tpn_staging.py#L204), [staging_review.py:546](../../../src/gps_kataster_obiektow_tatr/staging_review.py#L546).

   Przy wyniku `unresolved` importer zapisuje tylko podsumowanie i pomija propozycję pomiaru oraz obiektu. `add_measurement` wymaga wpisu w `matched_measurements`, zanim odczyta `target_object_id`. Jawne wskazanie istniejącego obiektu przez operatora nadal daje `STAGING_MEASUREMENT_UPDATE_MISSING`. Analogicznie brak propozycji uniemożliwia `create_object` dla takiego wiersza. Mechanizm operator review obsługuje więc akceptację gotowych dopasowań, ale nie domyka rozstrzygania niejednoznaczności opisanego w specyfikacji §8.3.

   Naprawa: zachować znormalizowany pomiar i referencje również dla niejednoznacznych wierszy, umożliwić jawny wybór istniejącego lub nowego obiektu i zwalidować decyzję przed zapisem.

10. **[P2] Obsługa rozszerzenia `.yaml` jest niespójna i prowadzi do ponownego użycia ID.**

    Miejsca: [scripts/assign_id.py:80](../../../scripts/assign_id.py#L80), [staging_review.py:844](../../../src/gps_kataster_obiektow_tatr/staging_review.py#L844).

    Loader i walidator akceptują `.yml` i `.yaml`, ale `assign_id.py` uwzględnia tylko `.yml`. Gdy istnieje `KSW-0001.yaml`, proponuje ponownie `KSW-0001`. Ponadto review zapisuje aktualizowany obiekt zawsze jako `.yml`, nie zachowując jego dotychczasowej ścieżki. Reprodukcja zwykłego `link_cave` dla poprawnego `.yaml` utworzyła obok niego drugi plik `.yml` z tym samym ID; review zgłosił sukces, a walidator wykrył dopiero powstałe duplikaty.

    Naprawa: spójny zestaw dopuszczalnych rozszerzeń we wszystkich narzędziach i zachowanie ścieżek istniejących rekordów przy aktualizacji.

11. **[P2] Obcinanie tekstu w Shapefile może uszkodzić UTF-8.**

    Miejsca: [best_measurements_export.py:311](../../../src/gps_kataster_obiektow_tatr/best_measurements_export.py#L311), [best_measurements_export.py:574](../../../src/gps_kataster_obiektow_tatr/best_measurements_export.py#L574).

    `_truncated_text` ogranicza liczbę znaków, podczas gdy zapis DBF ogranicza liczbę bajtów. Dla notatki zawierającej 253 znaki `a` i końcowe `ó` eksport kończy się sukcesem, ale ponowny odczyt DBF zgłasza `UnicodeDecodeError` z powodu ucięcia znaku w połowie. Problem może dotyczyć też innych pól tekstowych, np. nazwy lokalnej. Obecny pełny Shapefile dał się odczytać w całości; błąd został potwierdzony na dopuszczalnym nowym tekście.

    Naprawa: obcinać zakodowany tekst do limitu bajtów z zachowaniem granic znaków; zastosować do wszystkich pól tekstowych DBF i sprawdzać ponowny odczyt eksportu z polskimi i słowackimi znakami.

12. **[P2] Nieistniejący katalog danych jest traktowany jak poprawny pusty katalog.**

    Miejsce: [data_loader.py:100](../../../src/gps_kataster_obiektow_tatr/data_loader.py#L100).

    `validate_data_dir` dla całkowicie nieistniejącej ścieżki zwraca zero problemów. `build_sqlite_database` dla tej samej ścieżki kończy się sukcesem i tworzy bazę z zerową liczbą obiektów. Literówka w `--data-dir` może więc wygenerować pustą paczkę, a przy użyciu istniejącej ścieżki wyjściowej zastąpić poprawny artefakt.

    Naprawa: rozróżniać nieistniejący katalog wejściowy od świadomie pustego katalogu. CLI walidacji/builda powinno odrzucać błędną ścieżkę, pozostawiając możliwość pracy importerów z nowym katalogiem docelowym.

13. **[P3] ZIP-y nie są deterministyczne nawet przy stałym `--generated-at`.**

    Miejsca: [release_artifacts.py:91](../../../src/gps_kataster_obiektow_tatr/release_artifacts.py#L91), [best_measurements_export.py:325](../../../src/gps_kataster_obiektow_tatr/best_measurements_export.py#L325).

    Dwukrotny build tego samego katalogu z `generated_at=2026-09-05T12:00:00Z` dał inne SHA-256 dla `best-measurements.shp.zip` i `katalog.sqlite.zip`. Pozostałe artefakty, w tym sam SQLite, miały identyczne sumy. `ZipFile.write` przejmuje bieżące czasy modyfikacji plików; DBF również wymaga uwzględnienia daty nagłówka przy odtwarzalności między dniami.

    Naprawa: jawnie ustalać metadane wpisów ZIP i datę nagłówka DBF z jednego czasu buildu. Dodać porównanie sum artefaktów budowanych w różnym czasie zegarowym.

Weryfikacja obecnego katalogu:

- Python 3.12.13; zależności z lokalnego środowiska i zamrożonego lockfile.
- `ruff check src tests scripts`: sukces.
- `ruff format --check src tests scripts`: sukces, 45 plików.
- `pytest -q`: **123 passed in 1.82s**.
- `scripts/validate.py`: kod 0, **0 błędów, 2066 ostrzeżeń**.
- Ostrzeżenia: `MISSING_HORIZONTAL_ACCURACY` 1875, `MEASUREMENT_OUTSIDE_VALLEYS` 103, `MEASUREMENT_DISTANCE_OUTLIER` 72, `OBJECT_PREFIX_MISMATCH` 16.
- Pełny lokalny build release: **1009 obiektów, 1003 jaskinie, 1875 pomiarów**; wygenerowano SQLite, GeoJSON, CSV, GPX, Shapefile ZIP, SQLite ZIP i metadata JSON.
- SQLite: `PRAGMA integrity_check = ok`, `PRAGMA foreign_key_check` bez wyników; sprawdzenie obu kierunków relacji obiekt–jaskinia nie wykazało niespójności w obecnych danych.
- Pełny Shapefile: odczytano 1009 rekordów bez błędu kodowania.
- Źródła CSV/XLSX: zgodne liczby rekordów PIG (860) i TPN (1005). Sprawdzono różnice reprezentacji pól; daty TPN po parsowaniu nie różniły się między formatami. Nie wykonywano ponownej terenowej weryfikacji lokalizacji.
- Źródła wybranych pomiarów: TPN 996, PIG 2, `inne` 9, `wlasne` 2. Statusy: 1007 `nieweryfikowany`, 2 `zweryfikowany`.

Liczba ostrzeżeń i status `nieweryfikowany` opisują znane ograniczenia jakości danych; nie są dowodem, że wszystkie te lokalizacje są błędne. Odstępstwo od SpatiaLite na rzecz geometrii WKT jest zapisane jako świadoma decyzja PBI-016, więc nie zostało zgłoszone jako nowy błąd implementacji. Specyfikacja nadal wymaga dopasowania opisu SQLite do tej decyzji. Dokument operacyjny przy kontroli `metadata.json` wymienia również stare klucze `object_count` itd.; aktualny kontrakt używa `counts.objects`, `counts.caves`, `counts.measurements`, `counts.validation_errors`, `counts.validation_warnings`.

Nie uruchamiano pełnej kampanii mutacyjnej, nie sprawdzano zdalnego GitHub Actions ani zgodności paczki opublikowanej na GitHubie z lokalnym HEAD. Wnioski dotyczą kodu i danych powyższego lokalnego commitu.

Zalecana kolejność napraw: najpierw 1–4, następnie integralność liczb i ID (5–6), przepływ import/review (7–10), eksport i obsługa wejścia (11–12), na końcu deterministyczność paczek (13). Do każdej poprawki potrzebny jest test reprodukujący skutek, którego obecne 123 testy nie wykrywają.

Dowody wykonania: [log reprodukcji podstawowych](project-review-2026-09-05-reproductions.log), [log importu i eksportów](project-review-2026-09-05-extra.log). Logi są historycznymi dowodami z tego przeglądu, nie aktualnym wynikiem bramki. Reprodukcje są opisane przy każdym ustaleniu; kolejne PBI utrwalają je jako testy w `tests/`, bez zależności od katalogów tymczasowych poprzedniej sesji.
