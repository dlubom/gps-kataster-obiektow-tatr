# AS-DLC backlog V1

Stan na: 2026-10-16

## Przegląd lokalizacji — poprawki danych

- [PBI-087](verification/PBI-087.md): PL-0019, odrzucenie błędnego punktu PIG — wykonane 2026-10-16 w [PR #6](https://github.com/dlubom/gps-kataster-obiektow-tatr/pull/6); uzasadnienie w YAML.

## Naprawy main po przegladzie 2026-10-12

Wydanie **v1.0.3 opublikowane 2026-10-15**. PR #4 zmergowany do main
(`89592969298cf04b547a694edf2755eb56209ae3`); CI po merge i workflow release
przeszły. [Potwierdzenia odbioru](verification/v1.0.3.md).
PBI-078–086 zakończone; brak kolejnej gotowej karty tej serii.
Punkt startowy następnej sesji: aktualny `main` po fetch/pull.

Decyzją użytkownika z 2026-10-15 poprzednie gałęzie naprawcze są porzucone.
Zakończona seria powstała na `codex/main-remediation-2026-10` ze świeżego
`origin/main`, SHA `a3dd1a671d3d93cd6958242fc68ddcf1d37cf846`.
PBI-034–077 są zarezerwowane dla historii starej serii i nie są tu
traktowane jako wdrożone. [Decyzja i zakres](remediation_plan.md),
[runbook](remediation_runbook.md), [raport R1–R8](reviews/main-review-2026-10-12.md).

Statusy: `planowane`, `planowane — gotowe`, `w toku`,
`zweryfikowane — do dostarczenia`, `wykonane`, `zablokowane` z powodem.
Kolejność jest celowa: **trzy P1 → problemy danych → pozostałe P2**.
Zależności w tabeli określają kolejność realizacji, nie wszystkie są
zależnościami technicznymi. Każde PBI dostarcza samodzielnie sprawdzalne
zachowanie. PBI-078 obejmował wyłącznie plan; bieżące statusy napraw są poniżej.

| Kolejność | PBI | Priorytet / ustalenie | Zakres | Poprzednik | Status |
|---|---|---|---|---|---|
| 0 | PBI-078 | plan | Plan, trwały raport, nowy punkt kontynuacji | — | wykonane |
| 1 | PBI-079 | P1 / R1 | Odrzucać brakujące wejście przed zapisem eksportów | 078 | wykonane |
| 2 | PBI-080 | P1 / R2 | Odrzucać duplikaty kluczy YAML | 079 | wykonane |
| 3 | PBI-081 | P1 / R3 | Walidować cały wynik review przed zapisem | 080 | wykonane |
| 4 | PBI-082 | dane, P2 / R4 | Zachować i uzupełnić kontekst źródłowy TPN | 081 | wykonane |
| 5 | PBI-083 | dane, P2 / R8 | Kategorie i udokumentowana ocena rozbieżności katalogu | 082 | wykonane |
| 6 | PBI-084 | P2 / R5 | Odrzucać liczby NaN/Infinity | 083 | wykonane |
| 7 | PBI-085 | P2 / R6 | Wymagać unikalnych ID pomiarów w obiekcie | 084 | wykonane |
| 8 | PBI-086 | P2 / R7 | Zachować symetrię powiązań przy link_cave | 085 | wykonane |

### Wspólny kontrakt wykonania

Każda karta dziedziczy bramkę i dostarczenie z [runbooka](remediation_runbook.md)
oraz granice danych z [planu](remediation_plan.md). Testy i dokumentacja
należą do tej samej naprawy. Status zapisujemy tutaj, aktualny punkt
kontynuacji w `context.md`, a dowody w `verification/PBI-NNN.md`.
Zmiany kontraktu [spec v2](../../specyfikacja_gps_kataster_obiektow_tatr_v_2.md)
są jawne; rozszerzenie V1 wymaga odrębnej decyzji.

### PBI-078: Utrwalić nowy plan z aktualnego main

Zakres: ten backlog, plan, runbook, AGENTS, context, przenośne dowody review
i [log PBI-078](verification/PBI-078.md). Wyłącznie dokumentacja i zapis
istniejących obserwacji; bez zmiany kodu, testów, konfiguracji CI lub danych.

- [x] Każde R1–R8 ma dokładnie jedną kartę naprawy, zakres i kryteria odbioru.
- [x] Trzy P1 poprzedzają prace nad danymi i pozostałe P2.
- [x] Historia porzuconej serii jest odróżniona od aktualnego main;
      kontynuacja nie wymaga jej checkoutu ani plików z `build/`.
- [x] Linki, zależności i polecenia odpowiadają świeżej bazie; pełna bramka
      dokumentacyjnego checkpointu i dostarczenie są odnotowane w logu.

Commit: `docs: plan main review remediation (PBI-078)`.

### PBI-079: Zatrzymać build przy brakującym katalogu danych

Status: wykonane 2026-10-15. [Log weryfikacji](verification/PBI-079.md).

Priorytet P1, R1. Spec: §10, §11.1–11.2, §13. Poprzednik: PBI-078.
Dyrektywa: odróżnić brak wejścia od istniejącego, świadomie przygotowanego
pustego zbioru i odrzucać brak przed utworzeniem lub nadpisaniem wyjścia.

Pliki: `src/gps_kataster_obiektow_tatr/data_loader.py`, `validator.py`,
`build_db.py`, `best_measurements_export.py`, `release_artifacts.py`,
odpowiednie CLI w `scripts/`, `tests/test_data_loader.py`,
`tests/test_validator.py`, `tests/test_build_db.py`,
`tests/test_best_measurements_export.py`, `tests/test_release_artifacts.py`.

Interfejs: `load_dataset(data_dir: Path) -> LoadedDataset` dostaje jawny
`DataDirectoryError(ValueError)` dla nieistniejącego root, root będącego
plikiem lub brakującego wymaganego katalogu `objects`, `caves`, `relations`.
Walidator i CLI przekładają to na czytelną diagnostykę i niezerowy exit.
Testy/importowe scenariusze inicjalizacji jawnie tworzą pełną strukturę;
nie osłabiamy domyślnej kontroli. Legalny pusty zbiór z kompletem katalogów
pozostaje obsługiwany; brak nie może być jego automatycznym odpowiednikiem.

- [x] Odtworzyć R1 przez publiczne API i CLI: po poprawce brak root, root
      jako plik i brak każdego z trzech katalogów dają błąd.
- [x] Dla każdego błędnego wejścia istniejący zestaw release zachowuje
      wszystkie bajty, a nieistniejące wyjścia nie powstają.
- [x] Poprawny katalog i jawnie przygotowany pusty fixture przechodzą;
      istniejące importowe testy inicjalizacji działają bez ukrytego fallbacku.
- [x] Uruchomić wskazane moduły pytest, pełną bramkę i mutacje kontroli
      istnienia/rodzaju katalogu; udokumentować kontrakt w operations/spec.
- [x] Dostarczyć `fix: reject missing data inputs (PBI-079)` i dowody.

### PBI-080: Odrzucać powtórzone klucze YAML

Status: wykonane 2026-10-15. [Log weryfikacji](verification/PBI-080.md).

Priorytet P1, R2. Spec: §9.1, §10, §11.1. Poprzednik: PBI-079.
Dyrektywa: wykrywać duplikaty przed normalizacją i utratą poprzedniej
wartości. Obejmować finalne rekordy oraz plik decyzji review.

Pliki: `data_loader.py`, `staging_review.py`, ewentualny wspólny loader
`src/gps_kataster_obiektow_tatr/yaml_io.py`, `tests/test_data_loader.py`,
`tests/test_staging_review.py`, `tests/test_validator.py`.
Interfejsy publiczne `load_dataset(...)` i
`load_review_decisions(decisions_path: Path) -> dict[str, Any]` zachowują
kształt wyniku; błędy pozostają `YamlDataLoadError` / `ReviewDecisionError`
z plikiem, kluczem i pozycją błędu.

- [x] Drugi `measurements`, także z identyczną wartością, daje błąd;
      nie może zastąpić pierwszej historii ani przejść do eksportu/zapisu.
- [x] Sprawdzić klucze zagnieżdżone, klucze decyzji, aliasy oraz merge keys:
      wynik nie może zależeć od cichego nadpisania. Zwykły alias bez kolizji
      pozostaje poprawny; kolizje po rozwinięciu merge keys, także jawne
      nadpisanie odziedziczonej wartości, są odrzucane i opisane w docs.
- [x] Poprawny YAML zachowuje wartości i kolejność list; źródłowe bajty
      pozostają niezmienione. Walidacja/CLI wskazuje wadliwy plik.
- [x] Testy trzech modułów, pełna bramka i celowane mutacje loadera.
- [x] Dostarczyć `fix: reject duplicate YAML keys (PBI-080)` i dowody.

### PBI-081: Walidować kompletną transakcję review przed zapisem

Status: wykonane 2026-10-15. [Log weryfikacji](verification/PBI-081.md).

Priorytet P1, R3. Spec: §8.1, §8.3, §9.1, §11.1. Poprzednik: PBI-080.
Dyrektywa: walidować wejściowe finalne dane oraz cały stan po wszystkich
decyzjach, zanim applier rozpocznie zapis. Zachować obiekty, jaskinie
i relacje w obrazie zbioru; nie walidować tylko pojedynczego nowego pomiaru.

Pliki: `staging_review.py`, `validator.py`, `scripts/importers/apply_review.py`,
`tests/test_staging_review.py`, `tests/test_validator.py`,
`docs/asdlc/staging_review_decisions.md`.
Interfejs: `apply_review_decisions(decision_data, *, staging_reports,
data_dir, write=True) -> StagingReviewResult` nadal zwraca raport;
błąd schematu/domeny daje `has_errors=True`, diagnostykę i `written_paths=()`.
Używa `validate_dataset(...)` z aktualnymi regułami, także dla `write=False`.

- [x] R3: `lat=0` przy niezmienionych PL-1992 zostaje odrzucone przed zapisem.
- [x] Niepoprawny istniejący zbiór, uszkodzony payload, brakujący cel/cave,
      utracona referencja relacji i błąd ostatniej decyzji blokują całą partię.
- [x] Dla błędu hash i lista plików finalnego katalogu są niezmienione;
      żaden wcześniejszy poprawny element partii nie jest zapisany.
- [x] Dry-run i zapis mają zgodną ocenę walidacji; poprawna wielodecyzyjna
      partia działa i po zapisie przechodzi walidację pełnego katalogu.
- [x] Uruchomić testy review/walidatora, pełną bramkę i mutacje warunku
      preflight. Nie deklarować odporności na awarię procesu/I/O, której
      ten zakres nie implementuje. R5–R7 nadal mają osobne karty.
- [x] Dostarczyć `fix: validate review state before writes (PBI-081)`.

### PBI-082: Zachować i odtworzyć kontekst pomiarów TPN

Status: wykonane 2026-10-15.
[Log weryfikacji](verification/PBI-082.md).

Priorytet dane/P2, R4. Spec: §4.3, §7.1, §9, §13. Poprzednik: PBI-081.
Dyrektywa: przenosić `WER_LOK` i `UWAGI` do opisanego kontekstu pomiaru
TPN dla nowych i dopasowanych rekordów; uzupełnić istniejące pomiary
z zachowanego lokalnego CSV, bez ponownego importu punktów.

Pliki: `tpn_staging.py`, `staging_review.py`, nowe jednorazowe narzędzie
`scripts/maintenance/restore_tpn_notes.py`, `tests/test_tpn_staging.py`,
`tests/test_staging_review.py`, `tests/test_best_measurements_export.py`,
nowy `tests/test_restore_tpn_notes.py`, wyłącznie manifestem wskazane
`data/objects/**/*.yml`, `docs/operations.md`, `docs/release_artifacts.md`.
Interfejs narzędzia: `--source PATH --data-dir PATH --report PATH [--apply]`;
domyślnie dry-run. Dopasowanie przez `TPN/source_globalid` oraz
`measurement.source_ref=TPN:{GLOBALID}`, nigdy samą nazwę lub numer wiersza.
Zachować dotychczasowe notes, dodać etykietowane wartości źródłowe bez
zmiany ich sensu. Uzupełnienie finalnych danych obejmuje notes i audit
zmienionego rekordu, bez nowych pomiarów ani zmian współrzędnych/best/statusu.

- [x] Na bazie ponownie policzyć braki; historyczny wynik to 354 wartości
      `WER_LOK` i 25 `UWAGI`, nie stała do wymuszenia.
- [x] Dry-run zapisuje manifest: hash źródła, GLOBALID, obiekt/pomiar,
      pola przed/po i przyczynę zmiany. Niejednoznaczny/brakujący match
      trafia do raportu i nie powoduje zapisu niepewnego rekordu.
- [x] Po zastosowaniu każde objęte manifestem ostrzeżenie istnieje przy
      właściwym pomiarze. Powtórzenie operacji nie duplikuje tekstu.
- [x] Testy obejmują MTW-0047, CHZ-0021, BYW-0015, BYW-0031, brak uwag,
      kolizję identyfikatora, ręczne notes i powtórne uruchomienie.
- [x] Ostrzeżenia wybranego best są czytelne po odczycie CSV, GeoJSON,
      GPX i SQLite; DBF zachowuje poprawny UTF-8 oraz jawnie opisany limit
      długości, bez obietnicy przechowania pełnego długiego tekstu.
- [x] Pełna bramka, kontrola dozwolonych pól danych, testy obszaru oraz
      mutacje dopasowania/ochrony treści. Surowe źródła bez zmian.
- [x] Dostarczyć `fix: preserve TPN location context (PBI-082)`.

### PBI-083: Skorygować kategorie i ocenić rozbieżności danych

Priorytet dane/P2, R8; dodatkowo jawne ryzyka jakości z tego review.
Spec: §2–4, §5.4, §8.3, §9. Poprzednik: PBI-082.
Dyrektywa: skorygować udowodnioną kategorię STR-0024 i utrwalić decyzję
lub jawną niepewność CHZ-0011. Zbadać zgłoszone rozbieżności lokalizacji
bez utożsamiania ostrzeżenia z błędnym punktem.

Pliki: `data/objects/STR/STR-0024.yml`, `data/objects/CHZ/CHZ-0011.yml`
wyłącznie dla uzasadnionej kategorii/notes/auditu, nowy
`docs/asdlc/reviews/data-decisions-2026-10.md`, `tests/test_tpn_staging.py`
dla regresji kategorii, ewentualne jawnie wymienione korekty notes.
Interfejs danych: raport wiąże decyzję z ID, GLOBALID, hashem źródła,
wartością źródłową i uzasadnieniem; nie tworzy nowych encji ani pomiarów.

- [x] STR-0024: źródło TPN row 273/GLOBALID
      `{A5C7088E-A2FE-4898-AE2E-B0A9B420B17D}` ma `GENEZA=sztolnia`;
      korekta kategorii i audit mają ślad dowodowy i nie zmieniają ID.
- [x] CHZ-0011: `GENEZA=jaskinia/sztolnia` wymaga odnotowania obu znaczeń.
      Kategoria wynika z dowodu/decyzji, nie wyszukiwania słowa. Jeśli brak
      podstaw do zmiany, zachować kategorię z jawną nierozstrzygniętą
      pozycją w raporcie, zamiast przedstawiać ją jako poprawioną.
- [x] Raport ocenia 72 historyczne ostrzeżenia odległości i 11 grup
      współdzielących współrzędne best: każde ma ID, dowód i rozstrzygnięcie
      albo konkretną brakującą informację. Ponownie policzyć aktualny zbiór.
      PL-0019 (2,49 km) i MLZ-0045 (1,90 km) mają osobne omówienie źródeł.
- [x] Nie przesuwać punktów, nie scalać obiektów, nie odrzucać pomiarów
      i nie podnosić statusów automatycznie. Potrzebna decyzja terenowa
      pozostaje jawną zaległością, nie blokuje udokumentowanych korekt.
- [x] Testy kategorii, pełna walidacja/build/odczyt kategorii w eksportach
      oraz porównanie danych z manifestem zmian. Surowe źródła bez zmian.
- [x] Dostarczyć `fix: reconcile documented catalog data issues (PBI-083)`.

Dowody i dostarczenie: [log PBI-083](verification/PBI-083.md),
[manifest](verification/PBI-083-manifest.json),
[decyzje danych](reviews/data-decisions-2026-10.md) i pełne dowody JSON.

### PBI-084: Odrzucać NaN i Infinity przed użyciem liczb

Status: wykonane 2026-10-15. [Log PBI-084](verification/PBI-084.md).

Priorytet P2, R5. Spec: §4.3, §6, §11–13. Poprzednik: PBI-083.
Dyrektywa: wymagać skończonych wartości we wszystkich polach liczbowych
pomiaru przed geometrią, wyborem best i eksportem; diagnozować błędy danych.

Pliki: `validator.py`, `coordinates.py`, `pig_staging.py`, `tpn_staging.py`,
wywołujące je build/eksport/review, testy odpowiadających modułów.
Interfejsy: `validate_dataset(...)` zwraca błąd z polem i ID pomiaru;
staging nie proponuje błędnego punktu, review/build/eksport kończą się
kontrolowanie przed zapisem. Brak wartości opcjonalnej (`null`) pozostaje
legalny. Nie zmieniać semantyki dokładności ani jednostek.

- [x] R5: `.nan` w `x_1992` daje błąd przed eksportem; poprawny istniejący
      zestaw plików pozostaje niezmieniony.
- [x] Parametryzowane testy NaN, +Infinity, -Infinity w lat/lon, cache
      PL-1992, wysokości i dokładnościach; także liczby z CSV/XLSX/staging.
- [x] Poprawne liczby i dozwolone `null` przechodzą. GeoJSON poprawnych
      danych daje się odczytać parserem odrzucającym NaN/Infinity.
- [x] Testy obszaru, pełna bramka i mutacje kontroli skończoności;
      wszystkie finalne YAML bez zmian.
- [x] Dostarczyć `fix: reject non-finite measurement values (PBI-084)`.

### PBI-085: Wymagać unikalnych ID pomiarów w obiekcie

Status: wykonane 2026-10-15.
[Log PBI-085](verification/PBI-085.md).

Priorytet P2, R6. Spec: §4.3–4.4, §9, §11–12. Poprzednik: PBI-084.
Dyrektywa: wykrywać kolizję `measurement.id` zanim pomiary zostaną
zindeksowane lub użyte do wyboru best, zapisu review i budowy artefaktów.

Pliki: `validator.py`, `staging_review.py`, `tests/test_validator.py`,
`tests/test_staging_review.py`, `tests/test_build_db.py`,
`tests/test_best_measurements_export.py`.
Interfejs: walidator zwraca diagnostykę z obiektem, lokalnym ID i plikiem;
istniejące publiczne API zachowują sposób raportowania błędów.

- [x] Dwa pomiary o tym samym ID, zarówno identyczne, jak i z różnymi
      współrzędnymi, dają błąd walidacji.
- [x] Kolizja dotykająca best/załącznika nie wybiera arbitralnie pierwszego
      rekordu. Review, SQLite i eksporty blokują zapis przed użyciem ID.
- [x] To samo lokalne `m-001` w dwóch różnych obiektach jest poprawne;
      pomiary z różnymi ID zachowują kolejność i historię.
- [x] Testy obszaru, pełna bramka i mutacje unikalności; dane bez zmian.
- [x] Dostarczyć `fix: validate local measurement identity (PBI-085)`.

### PBI-086: Przenosić powiązanie obiektu i walidować symetrię

Status: wykonane 2026-10-15. [Log PBI-086](verification/PBI-086.md).

Priorytet P2, R7. Spec: §3.1–3.2, §4.1–4.2, §8.3, §11.1.
Poprzednik: PBI-085. Dyrektywa: `link_cave` usuwa członkostwo w starej
jaskini i dodaje je w nowej; walidator sprawdza obie strony powiązania.

Pliki: `staging_review.py`, `validator.py`, `tests/test_staging_review.py`,
`tests/test_validator.py`, `tests/test_build_db.py`,
`docs/asdlc/staging_review_decisions.md`.
Interfejs akcji pozostaje `{action: link_cave, object_id, cave_id}`.
Zmieniają się trzy powiązane rekordy (obiekt, stara i nowa jaskinia)
z zachowaniem istniejącego kontraktu audit; źródła i pomiary bez zmian.

- [x] Po przeniesieniu KSW-0001 z C-0002 do drugiej jaskini tylko nowa
      zawiera go w `object_ids`, a `object.cave_id` wskazuje nową.
- [x] Walidator wykrywa brak członkostwa w wskazanej jaskini, wpis w innej
      jaskini i obiekt wymieniony przez jaskinię bez zgodnego cave_id.
- [x] Powtórny link do tej samej jaskini nie duplikuje członkostwa;
      inni członkowie obu jaskiń i historia pomiarów pozostają bez zmian.
- [x] Brak celu i błąd ostatniej decyzji partii zachowują pliki bez zmian;
      poprawny relink przechodzi preflight PBI-081 i walidację po zapisie.
- [x] Testy obszaru, pełna bramka, kontrola zgodności powiązań SQLite/YAML
      i mutacje symetrii. Finalne dane katalogu bez zmian.
- [x] Ponowić scenariusze R1–R8 po wszystkich naprawach; w logu rozdzielić
      naprawione błędy od nierozstrzygniętych faktów terenowych PBI-083.
- [x] Dostarczyć `fix: preserve cave membership symmetry (PBI-086)`.

## Status realizacji

- PBI-001: wykonane 2026-05-15. Struktura katalogow zostala utworzona, shapefile przeniesione do `data/shapes/`, dodano podstawowy `.gitignore`.
- Pamiec operacyjna: dodano `AGENTS.md` i `docs/asdlc/context.md`, zeby kolejny agent mogl odtworzyc stan projektu bez historii rozmowy.
- PBI-002: wykonane 2026-05-15. Dodano `pyproject.toml`, `uv.lock`, minimalny pakiet pod `src/`, test dymny oraz konfiguracje `ruff` i `pytest`.
- PBI-003: wykonane 2026-05-15. Dodano `config/prefixes.yml` z mapowaniem 18 dolin oraz fallbackami `PL` i `SK`; testy sprawdzaja zgodnosc z `data/shapes/doliny.shp` i format prefixow.
- PBI-004: wykonane 2026-05-15. Dodano JSON Schema dla `Obiekt`, `Jaskinia` i `Relacja`, `schema/CHANGELOG.md`, zaleznosc `jsonschema` oraz testy valid/invalid fixture'ow schematu.
- PBI-005: wykonane 2026-05-15. Dodano minimalne fixture'y domenowe dla obiektow i jaskin oraz testy zgodnosci ze schematem i spojnosci cross-reference.
- PBI-006: wykonane 2026-05-15. Dodano modul konwersji WGS84 <-> EPSG:2180 oparty o PyProj, utrwalono konwencje osi `x_1992 = northing`, `y_1992 = easting` oraz testy round-trip i wykrywania zamiany osi.
- PBI-007: wykonane 2026-05-15. Dodano resolver prefixow czytajacy `config/prefixes.yml` i shapefile z `data/shapes/`; wynik rozroznia trafienie w doline, fallback PL/SK z warningiem oraz punkt poza PL/SK jako error.
- PBI-008: wykonane 2026-05-15. Dodano `scripts/assign_id.py`, ktory przyjmuje `lat lon`, uzywa resolvera prefixow, liczy kolejny numer z `data/objects/{PREFIX}/` i wypisuje propozycje ID razem z ostrzezeniami.
- PBI-009: wykonane 2026-05-15. Dodano loader YAML dla `data/objects/`, `data/caves/` i `data/relations/`, rekordy zachowuja sciezke pliku, a brakujace listy sa normalizowane tylko w pamieci.
- PBI-010: wykonane 2026-05-15. Dodano lokalny walidator danych YAML z kodami regul, poziomami `error` / `warning`, sciezka pliku i opisem; CLI `scripts/validate.py` zwraca kod != 0 tylko przy bledach.
- PBI-011: wykonane 2026-05-15. Wyodrebniono algorytm `best_measurement` do modulu aplikacyjnego, dodano testy priorytetow, dat, dokladnosci, stabilnego remisu, trybu manual oraz ostrzezenia walidatora dla rozjazdu `auto`.
- PBI-012: wykonane 2026-05-16. Dodano profilowanie eksportow CSV PIG i TPN, raport JSON/Markdown w `build/reports/source-profile.*` oraz testy bramek: liczby rekordow, braki, duplikaty i zakresy wspolrzednych; finalne YAML nie sa tworzone.
- PBI-013: wykonane 2026-05-16. Dodano importer staging PIG dla CSV/XLSX, raport JSON/Markdown w `build/staging/pig/`, propozycje `Jaskinia` i wstepnych `Obiekt` z pomiarem PIG oraz testy gwarantujace, ze finalne YAML nie sa zapisywane bez review.
- PBI-014: wykonane 2026-05-16. Dodano importer staging TPN dla CSV/XLSX, dopasowania do finalnych YAML i staging PIG, propozycje pomiarow TPN z `GLOBALID` na obiekcie, `NR_INWENT` na jaskini oraz raport statusow: dopasowane, nowe, nierozstrzygniete i odrzucone.
- PBI-015: wykonane 2026-05-16. Dodano format decyzji operatora, applier staging review i CLI `scripts/importers/apply_review.py`; decyzje `create_cave`, `create_object`, `add_measurement`, `link_cave`, `reject` i `unresolved` materializuja finalne YAML dopiero po poprawnym review.
- PBI-016: wykonane 2026-05-16. Dodano build SQLite `build/katalog.sqlite` z walidowanych YAML, tabelami logicznymi V1, metadanymi licznikow, flagami walidacji i najlepszymi geometriami obiektow w WKT.
- PBI-017: wykonane 2026-05-16. Dodano eksport `best-measurements` z walidowanych YAML do GeoJSON, CSV, GPX i ZIP Shapefile EPSG:2180.
- PBI-018: wykonane 2026-05-16. Eksport release zapisuje `metadata.json` z timestampem, wersjami schematow oraz licznikami obiektow, jaskin, relacji, pomiarow i walidacji.
- PBI-019: wykonane 2026-05-16. Dodano workflow `.github/workflows/validate.yml` uruchamiajacy lokalna bramke `uv sync`, Ruff, pytest i `scripts/validate.py` bez budowania release.
- PBI-020: wykonane 2026-05-16, skorygowane w PBI-029. Dodano lokalny builder artefaktow release oraz workflow `release.yml` dla tagow `v*`; automatyczny build po `main` zostal usuniety.
- PBI-021: wykonane 2026-05-16, skorygowane w PBI-029. Dodano `docs/operations.md` z procedurami recznego pomiaru, walidacji, recznie tagowanego release danych i statusow weryfikacji oraz test dokumentacji.
- PBI-022: wykonane 2026-05-16. Naprawiono kategorie sztolni z TPN: importer rozpoznaje `GENEZA` / nazwe, a 26 istniejacych obiektow `Sztolnia...` ma `category: sztolnia`.
- PBI-023: wykonane 2026-05-16. Dodano ludzkie `README.md`, przeniesiono surowe PIG/TPN XLSX/CSV do `data/sources/`, dodano opis zrodel i skopiowano pelny dump PIG JSONL do review brakujacych otworow.
- PBI-024: wykonane 2026-05-16. Rozdzielono Mrozna na drugi obiekt otworowy z TPN row 982 oraz dodano slowackie jaskinie `Nova Kresanica` i `Obcasna Vyvieracka`.
- PBI-025: wykonane 2026-05-16. Rozstrzygnieto pozostale wielootworowe przypadki TPN, dodano nowe pomiary GNSS/LIDAR, podlaczono Czarna III do Jaskini Czarnej i nazwano bezimienny rekord TPN jako `BEZ_NAZWY_001`.
- PBI-026: wykonane 2026-05-16. Wprowadzono testy mutacyjne przez `mutmut` dla krytycznych modulow, lokalna konfiguracje w `pyproject.toml`, reczny workflow `mutation.yml`, ignorowanie `mutants/` i dokumentacje uruchamiania.
- PBI-027: wykonane 2026-05-16. Doprecyzowano w README i dokumentacji operacyjnej, ze `verification_status: nieweryfikowany` w release jest oczekiwany dla importow PIG/TPN i nie oznacza automatycznie bledu danych.
- PBI-028: wykonane 2026-05-17. Udokumentowano kolumny i pola artefaktow release oraz dodano `object_notes`, `cave_notes` i `measurement_notes` do plaskich eksportow `best-measurements`.
- PBI-029: wykonane 2026-05-17. Przestawiono wydania na reczny semver jak w JKTZ: `CHANGELOG.md`, annotated tag `vX.Y.Z`, release notes z changeloga, link do najnowszego GitHub Release w README oraz brak automatycznego build workflow po `main`.
- PBI-030: wykonane 2026-05-17. Uzupelniono wysokosc recznego pomiaru GNSS gornego otworu Bandziocha Kominiarskiego `LEJ-0002` / `BandziochKom:136` na `1675.02 m`.
- PBI-031: wykonane 2026-05-18. Przejrzano spojnosci AS-DLC/spec/docs/kod dla release: usunieto runtime'owa flage licencyjna, potwierdzono brak automatycznego build workflow po `main` i ujednolicono dokumentacje na reczny semver tag.
- PBI-032: wykonane 2026-05-21. Przygotowano release `v1.0.2` dla zmian PBI-031: changelog, wersja pakietu i test wersji wskazuja faktyczna nowa wersje.
- PBI-033: wykonane 2026-07-11. Przebudowano README pod grotolazow i speleologow, dodano wersje angielska i slowacka oraz opisano role GPS Katastru, Jaskiniowego Katastru Tatr i Georeferencera.

## Przyjęty poziom AS-DLC

Dla tego projektu wybieramy lekki wariant `spec-anchored`:

- specyfikacja w repo jest zrodlem prawdy dla stanu systemu,
- zadania sa malymi PBI, czyli opisami zmiany do wykonania,
- kazde PBI ma jawny zakres, zaleznosci i sposob weryfikacji,
- nie wprowadzamy ciezkiego procesu ani osobnego systemu zarzadzania zadaniami,
- odkrycia z implementacji wracaja do specyfikacji albo do tego backlogu.

## Przeglad aktualnych plikow

Repo ma dzialajacy przeplyw od YAML przez walidacje, build SQLite, eksporty
GIS i reczny tagowany release. Zmiany sa nadal zatwierdzane po kolejnych PBI
albo rownowaznych malych krokach.

| Plik / katalog | Stan | Uwagi |
|---|---:|---|
| `specyfikacja_gps_kataster_obiektow_tatr_v_2.md` | 43 205 B | Specyfikacja draft v2, opisuje model domeny, ID, import, walidacje, build i etapy. |
| `README.md` | istnieje | Ludzkie wejscie do repo: cel projektu, struktura, model i komendy startowe. |
| `data/sources/pig/pig_otwory_jaskin_.xlsx` | 1 arkusz `Export`, 861 wierszy, 15 kolumn | Zrodlo PIG / Jaskinie Polski. |
| `data/sources/pig/pig_otwory_jaskin_.xlsx.-.Export.csv` | 860 rekordow danych | Eksport CSV PIG; kolumny m.in. `ID`, `Nazwa`, `Nr inw.`, `X 1992`, `Y 1992`, `B`, `L`, `Link`. |
| `data/sources/pig/jaskinie_polski_pig_dump.jsonl` | 5388 rekordow JSONL | Pelniejszy dump PIG do recznego sprawdzania opisow jaskin, liczby otworow i nazw otworow. |
| `data/sources/tpn/tpn_otwory_jaskin.xlsx` | 1 arkusz `Export`, 1006 wierszy, 23 kolumny | Zrodlo TPN. |
| `data/sources/tpn/tpn_otwory_jaskin.xlsx.-.Export.csv` | 1005 rekordow danych | Eksport CSV TPN; kolumny m.in. `NR_INWENT`, `NAZWA`, `GLOBALID`, `X1992`, `Y1992`, `Z`. |
| `data/sources/README.md` | istnieje | Opisuje zrodla, zakres dumpu PIG i workflow grep/review dla brakujacych otworow. |
| `data/objects/` | 1009 finalnych YAML | Obiekty terenowe po imporcie/review, w tym `sztolnia`, `wywierzysko` i fallback `SK`. |
| `data/caves/` | 1003 finalne YAML | Jaskinie / pozycje katalogowe; jedna jaskinia moze wskazywac wiele obiektow. |
| `data/shapes/doliny.*` | 18 feature'ow, EPSG:2180 | Polygony dolin, pole kluczowe `NAME`. |
| `data/shapes/granica_polski.*` | 1 feature, EPSG:2180 | Fallback granicy Polski. |
| `data/shapes/granica_slowacji.*` | 1 feature, EPSG:2180 | Fallback granicy Slowacji. |
| `data/shapes/README.md` | istnieje | Opisuje warstwy i algorytm prefixow. |
| `config/prefixes.yml` | 18 dolin + 2 fallbacki | Zrodlo prawdy dla prefixow ID. |
| `tests/test_prefixes.py` | 2 testy | Sprawdza mapowanie `doliny.shp` i format prefixow. |
| `schema/*.schema.json` | 3 schematy | Kontrakty YAML dla `Obiekt`, `Jaskinia` i `Relacja`. |
| `schema/CHANGELOG.md` | istnieje | Wpis dla `schema_version: 1`. |
| `tests/test_schemas.py` | 7 testow | Sprawdza poprawnosc schematow oraz valid/invalid fixture'y PBI-004. |
| `tests/fixtures/*.yml` | 5 fixture'ow | Minimalny zestaw domenowy PBI-005: obiekt, jaskinia, TPN `GLOBALID`, PIG + `NR_INWENT`, reczny `best_measurement`. |
| `tests/test_domain_fixtures.py` | 9 testow | Sprawdza zgodnosc fixture'ow domenowych ze schematami oraz referencje `cave_id` / `object_ids`. |
| `src/gps_kataster_obiektow_tatr/coordinates.py` | istnieje | Konwersja WGS84 <-> EPSG:2180 przez PyProj, z projektowa konwencja osi `x_1992 = northing`, `y_1992 = easting`. |
| `tests/test_coordinates.py` | 5 testow | Sprawdza round-trip kilku punktow tatrzanskich, zgodnosc z osiami PIG/PL-1992 i wykrywanie zamiany osi. |
| `src/gps_kataster_obiektow_tatr/prefix_resolver.py` | istnieje | Resolver prefixow ID: doliny przez point-in-polygon, fallback PL/SK i jawne statusy `ok` / `warning` / `error`. |
| `tests/test_prefix_resolver.py` | 4 testy | Sprawdza punkt w dolinie, punkt w Polsce poza dolinami, punkt po stronie slowackiej i punkt poza PL/SK. |
| `scripts/assign_id.py` | istnieje | CLI i helpery do proponowania kolejnego ID z `lat lon`, resolvera prefixu i plikow w `data/objects/{PREFIX}/`. |
| `tests/test_assign_id.py` | 6 testow | Sprawdza pusty prefix, istniejace pliki, licznik ponad `9999`, warningi resolvera, blad bez prefixu i uruchomienie CLI. |
| `src/gps_kataster_obiektow_tatr/data_loader.py` | istnieje | Loader zrodlowych YAML: obiekty, jaskinie i relacje z `data/`, sciezki plikow dla raportow oraz pamieciowe domyslne puste listy. |
| `tests/test_data_loader.py` | 3 testy | Sprawdza wczytanie fixture'ow, zachowanie sciezek, normalizacje list bez zapisu do YAML oraz blad skladni YAML z czytelna sciezka. |
| `src/gps_kataster_obiektow_tatr/best_measurement.py` | istnieje | Domyslny algorytm `best_measurement.mode: auto`: priorytet zrodel, data, dokladnosc i stabilny remis po `measurement.id`. |
| `src/gps_kataster_obiektow_tatr/source_table.py` | istnieje | Wspolny czytnik tabel zrodlowych CSV/XLSX dla importerow staging. |
| `src/gps_kataster_obiektow_tatr/source_profile.py` | istnieje | Profilowanie CSV PIG/TPN przed importem staging: braki kluczowych pol, duplikaty i zakresy kolumn liczbowych. |
| `src/gps_kataster_obiektow_tatr/pig_staging.py` | istnieje | Importer staging PIG: czyta CSV/XLSX, tworzy propozycje `Jaskinia` i wstepnych `Obiekt` z niskopriorytetowym pomiarem PIG oraz raport JSON/Markdown. |
| `src/gps_kataster_obiektow_tatr/tpn_staging.py` | istnieje | Importer staging TPN: czyta CSV/XLSX, tworzy propozycje pomiarow TPN, dopasowuje do YAML/staging PIG i raportuje statusy review. |
| `src/gps_kataster_obiektow_tatr/staging_review.py` | istnieje | Applier decyzji operatora: materializuje staging do finalnych YAML, dopisuje pomiary TPN, laczy obiekty z jaskiniami i blokuje zapis przy blednych decyzjach. |
| `src/gps_kataster_obiektow_tatr/build_db.py` | istnieje | Build SQLite: waliduje YAML, tworzy tabele logiczne, zapisuje pomiary, referencje, relacje, `metadata`, `validation_flags` oraz najlepsze geometrie obiektow. |
| `src/gps_kataster_obiektow_tatr/best_measurements_export.py` | istnieje | Eksport najlepszych pomiarow: GeoJSON WGS84, CSV WGS84 + EPSG:2180, GPX WGS84, Shapefile ZIP EPSG:2180, notatki obiektu/jaskini/pomiaru oraz `metadata.json`. |
| `src/gps_kataster_obiektow_tatr/release_artifacts.py` | istnieje | Wspolny builder artefaktow release: SQLite, eksporty best-measurements, metadata i `katalog.sqlite.zip`. |
| `tests/test_best_measurement.py` | 11 testow | Sprawdza wszystkie priorytety wyboru, remis dat/dokladnosci/ID oraz fallback do odrzuconych pomiarow. |
| `src/gps_kataster_obiektow_tatr/validator.py` | istnieje | Walidator lokalny: JSON Schema, unikalnosc ID, referencje cross-file, spojnosci wspolrzednych, reguly przestrzenne i ostrzezenia domenowe. |
| `scripts/validate.py` | istnieje | CLI walidatora; wypisuje `kod`, `poziom`, `plik`, `opis` i konczy kodem 1 tylko dla error. |
| `scripts/profile_sources.py` | istnieje | CLI generujace `build/reports/source-profile.json` i `build/reports/source-profile.md` z eksportow CSV PIG/TPN. |
| `scripts/importers/import_pig.py` | istnieje | CLI generujace `build/staging/pig/pig-staging.json` i `.md` bez zapisu finalnych YAML. |
| `scripts/importers/import_tpn.py` | istnieje | CLI generujace `build/staging/tpn/tpn-staging.json` i `.md` bez zapisu finalnych YAML. |
| `scripts/importers/apply_review.py` | istnieje | CLI stosujace plik decyzji operatora do staging PIG/TPN i zapisujace raport review oraz finalne YAML. |
| `scripts/build_db.py` | istnieje | CLI generujace `build/katalog.sqlite` z `data/` albo wskazanego katalogu testowego. |
| `scripts/export_best_measurements.py` | istnieje | CLI generujace `build/exports/best-measurements.geojson`, `.csv`, `.gpx`, `.shp.zip` i `metadata.json`. |
| `scripts/build_release_artifacts.py` | istnieje | Lokalny dry-run buildu/release generujacy pelny zestaw artefaktow: SQLite, eksporty, metadata i ZIP SQLite. |
| `.github/workflows/validate.yml` | istnieje | Workflow CI dla PR i push do `main`: `uv sync`, Ruff, pytest i `scripts/validate.py`; bez build/release. |
| `.github/workflows/mutation.yml` | istnieje | Reczny workflow `workflow_dispatch` uruchamiajacy baseline pytest, `mutmut run` i eksport statystyk mutacyjnych. |
| `.github/workflows/release.yml` | istnieje | Workflow dla tagow `v*`: buduje artefakty i publikuje GitHub Release bez dodatkowej flagi licencyjnej. |
| `CHANGELOG.md` | istnieje | Historia wersji semver i zrodlo notatek GitHub Release. |
| `docs/operations.md` | istnieje | Dokumentacja operacyjna PBI-021/PBI-029: reczny pomiar, walidacja, tagowany release danych, statusy `zweryfikowany` / `odrzucony`. |
| `docs/release_artifacts.md` | istnieje | Przeglad plikow release, kolumn/pol CSV, GeoJSON, Shapefile, GPX, metadata i SQLite oraz decyzja o rozdzieleniu notatek. |
| `docs/asdlc/staging_review_decisions.md` | istnieje | Dokumentuje format pliku decyzji operatora i znaczenie akcji PBI-015. |
| `tests/test_validator.py` | 9 testow | Sprawdza duplikat ID, zly `best_measurement`, brak `manual.reason`, zle wspolrzedne, ostrzezenia PBI-010, warningi `best_measurement` PBI-011 oraz exit code CLI. |
| `tests/test_source_profile.py` | 4 testy | Sprawdza profilowanie brakow, duplikatow, zakresow wspolrzednych, zapis raportow i brak tworzenia finalnych YAML. |
| `tests/test_pig_staging.py` | 5 testow | Sprawdza mapowanie referencji PIG/NR_INWENT na jaskinie, niskopriorytetowe pomiary PIG, czytanie XLSX, raport staging oraz brak finalnych YAML. |
| `tests/test_tpn_staging.py` | 6 testow | Sprawdza dopasowanie TPN do staging PIG, nowe obiekty, nierozstrzygniete duplikaty, XLSX, raporty i CLI bez zapisu finalnych YAML. |
| `tests/test_staging_review.py` | 3 testy | Sprawdza sample staging -> decyzje -> finalne YAML -> `validate.py`, decyzje link/reject/unresolved oraz blokade zapisu przy bledach. |
| `tests/test_build_db.py` | 3 testy | Sprawdza build SQLite na fixture'ach, liczby w `metadata`, najlepsze geometrie, CLI i blokade buildu przy bledach walidacji. |
| `tests/test_best_measurements_export.py` | 4 testy | Sprawdza eksport tylko najlepszych pomiarow do GeoJSON/CSV/GPX/Shapefile ZIP, notatki w plaskich eksportach, snapshot `metadata.json`, CLI oraz blokade przy blednej walidacji YAML. |
| `tests/test_ci_workflow.py` | 5 testow | Sprawdza workflow walidacyjny, brak automatycznego build workflow po `main`, tag-only release i brak dodatkowej flagi licencyjnej. |
| `tests/test_mutation_tooling.py` | 3 testy | Sprawdza zaleznosc i konfiguracje `mutmut`, reczny workflow mutacyjny oraz ignorowanie katalogu `mutants/`. |
| `tests/test_release_artifacts.py` | 2 testy | Sprawdza wspolny lokalny dry-run artefaktow release, w tym `katalog.sqlite.zip` i CLI. |
| `tests/test_operational_docs.py` | 2 testy | Sprawdza, ze dokumentacja operacyjna pokrywa zakres PBI-021 i przypomina, ze `build/` nie jest zrodlem prawdy. |

## Bramka kontekstu

Przed implementacja V1 obowiazuja te stale decyzje:

- `Obiekt` to konkretny punkt terenowy, a `Jaskinia` to encja katalogowa/logiczna.
- TPN `GLOBALID` trafia zasadniczo do `Obiekt.external_refs`.
- PIG `ID`, PIG `Link` i `NR_INWENT` trafiaja zasadniczo do `Jaskinia.external_refs`.
- YAML w `data/` jest zrodlem prawdy; SQLite, GeoJSON, GPX, CSV i Shapefile sa artefaktami.
- Frontend, PWA, stale importy, Geoportal i GitHub API sa poza V1.

## Milestone 0: porzadek repo

### PBI-001: Uporzadkowac strukture katalogow

Zakres:

- utworzyc docelowe katalogi `config/`, `data/shapes/`, `data/objects/`, `data/caves/`, `data/relations/`, `data/attachments/`, `schema/`, `scripts/`, `tests/fixtures/`,
- przeniesc `shapes/*` do `data/shapes/`,
- dodac `.gitignore` dla `build/`, cache'y Pythona i lokalnych artefaktow,
- nie zmieniac jeszcze danych zrodlowych TPN/PIG.

Weryfikacja:

- `rg --files` pokazuje strukture zgodna ze specyfikacja,
- shapefile po przeniesieniu nadal otwieraja sie przez `ogrinfo`.

### PBI-002: Utworzyc minimalny projekt Pythonowy

Status: wykonane 2026-05-15.

Zakres:

- dodac `pyproject.toml`,
- skonfigurowac `uv`, `ruff`, `pytest`,
- dodac minimalny pakiet projektu pod `src/`,
- ustalic jedna komende lokalna dla testow i walidacji.

Weryfikacja:

- `uv sync`,
- `uv run ruff check src tests`,
- `uv run pytest`.

### PBI-003: Dodac konfiguracje prefixow

Status: wykonane 2026-05-15.

Zakres:

- utworzyc `config/prefixes.yml`,
- odwzorowac 18 nazw z `data/shapes/doliny.shp` na prefixy ze specyfikacji,
- dodac fallbacki `PL` i `SK`,
- dodac test wykrywajacy brak mapowania dla polygonu doliny.

Weryfikacja:

- test czy kazdy `NAME` z warstwy dolin ma prefix,
- test czy prefix ma format 2-3 uppercase ASCII.

## Milestone 1: kontrakty danych

### PBI-004: Zdefiniowac JSON Schema dla YAML

Status: wykonane 2026-05-15.

Zakres:

- dodac `schema/object.schema.json`,
- dodac `schema/cave.schema.json`,
- dodac `schema/relation.schema.json`,
- dodac `schema/CHANGELOG.md` z wpisem dla `schema_version: 1`.

Weryfikacja:

- pozytywne fixture'y przechodza walidacje schematu,
- negatywne fixture'y padaja na oczekiwanych polach.

### PBI-005: Dodac minimalne fixture'y domenowe

Status: wykonane 2026-05-15.

Zakres:

- `tests/fixtures/valid-object.yml`,
- `tests/fixtures/valid-cave.yml`,
- `tests/fixtures/object-with-tpn-globalid.yml`,
- `tests/fixtures/cave-with-pig-and-nr-inwent.yml`,
- `tests/fixtures/object-with-manual-best.yml`.

Weryfikacja:

- fixture'y sa zgodne ze schematem,
- cross-reference `cave_id` i `object_ids` da sie sprawdzic walidatorem.

## Milestone 2: geografia i ID

### PBI-006: Wprowadzic konwersje WGS84 <-> EPSG:2180

Status: wykonane 2026-05-15.

Zakres:

- dodac modul konwersji wspolrzednych,
- zachowac konwencje osi ze specyfikacji: `x_1992 = northing`, `y_1992 = easting`,
- dodac tolerancje walidacji spojnosci.

Weryfikacja:

- test round-trip dla kilku punktow z Tatr,
- test wykrywajacy zamiane osi.

### PBI-007: Zaimplementowac resolver prefixu

Status: wykonane 2026-05-15.

Zakres:

- czytac warstwy z `data/shapes/`,
- robic point-in-polygon dla dolin,
- robic fallback PL/SK,
- zwracac warning dla punktu poza dolinami, ale w PL/SK,
- zwracac error dla punktu poza PL/SK.

Weryfikacja:

- test punktu w dolinie,
- test punktu w Polsce poza dolinami,
- test punktu po stronie slowackiej,
- test punktu poza PL/SK.

### PBI-008: Dodac `scripts/assign_id.py`

Status: wykonane 2026-05-15.

Zakres:

- przyjmowac `lat lon`,
- wyliczac prefix,
- znajdowac kolejny numer w `data/objects/{PREFIX}/`,
- wypisywac proponowane ID i ostrzezenia.

Weryfikacja:

- test pustego prefixu daje `PREFIX-0001`,
- test istniejacych plikow daje kolejny numer,
- konflikt ID pozostaje zadaniem walidatora.

## Milestone 3: walidator lokalny

### PBI-009: Loader danych YAML

Status: wykonane 2026-05-15.

Zakres:

- czytac obiekty, jaskinie i relacje z `data/`,
- zachowac informacje o sciezce pliku dla raportow,
- normalizowac brakujace listy do pustych list tylko w kodzie, nie nadpisujac YAML.

Weryfikacja:

- test wczytania fixture'ow,
- test bledu YAML z czytelna sciezka.

### PBI-010: Reguly walidacji error/warning

Status: wykonane 2026-05-15.

Zakres:

- zaimplementowac bledy i ostrzezenia z sekcji 11.1 specyfikacji,
- raportowac kod reguly, poziom, plik i opis,
- zakonczyc proces kodem != 0 tylko dla error.

Weryfikacja:

- testy dla duplikatu ID, zlego `best_measurement`, braku `manual.reason`, zlych wspolrzednych,
- test warningow dla braku `horizontal_accuracy_m`, `category: jaskinia_otwor` bez `cave_id`, zlej lokalizacji referencji PIG/NR_INWENT.

### PBI-011: Algorytm `best_measurement`

Status: wykonane 2026-05-15.

Zakres:

- zaimplementowac priorytet: wlasne zweryfikowane > TPN > wlasne nieweryfikowane > PIG > geoportal/publikacja/inne,
- uwzglednic date, dokladnosc i stabilny tie-breaker po `measurement.id`,
- respektowac `mode: manual`.

Weryfikacja:

- testy wszystkich priorytetow,
- test remisu dat i dokladnosci,
- test warningu gdy `mode: auto` wskazuje inny pomiar niz algorytm.

## Milestone 4: import poczatkowy jako staging

### PBI-012: Profil danych PIG i TPN

Status: wykonane 2026-05-16.

Zakres:

- policzyc puste wartosci w kluczowych kolumnach,
- sprawdzic duplikaty `PIG.ID`, `Nr inw.`, `TPN.GLOBALID`, `NR_INWENT`,
- sprawdzic zakresy wspolrzednych,
- zapisac raport do `build/reports/source-profile.*`.

Weryfikacja:

- raport zawiera liczby rekordow, kolumny, duplikaty i braki,
- zadne finalne YAML nie sa jeszcze tworzone.

### PBI-013: Importer staging PIG

Status: wykonane 2026-05-16.

Zakres:

- czytac CSV/XLSX PIG,
- tworzyc propozycje `Jaskinia`,
- tworzyc wstepny `Obiekt` i pomiar PIG tylko tam, gdzie da sie jednoznacznie przypisac punkt,
- nie zapisywac finalnych plikow bez review.

Weryfikacja:

- staging ma referencje PIG i `NR_INWENT` po stronie jaskini,
- pomiary PIG maja niski priorytet i `verification_status: nieweryfikowany`.

### PBI-014: Importer staging TPN

Status: wykonane 2026-05-16.

Zakres:

- czytac CSV/XLSX TPN,
- tworzyc pomiary TPN z `GLOBALID`,
- dopasowywac po `GLOBALID`, `NR_INWENT`, nazwie i odleglosci,
- raportowac przypadki niejednoznaczne.

Weryfikacja:

- `GLOBALID` trafia do referencji obiektu,
- `NR_INWENT` trafia do referencji jaskini,
- wygenerowany raport pokazuje: dopasowane, nowe, nierozstrzygniete, odrzucone.

### PBI-015: Operator review dla staging

Status: wykonane 2026-05-16.

Zakres:

- przygotowac format raportu decyzji operatora,
- obsluzyc decyzje: nowy obiekt, nowy pomiar obiektu, nowa jaskinia, powiazanie z jaskinia, odrzucenie, nierozstrzygniete,
- wygenerowac finalne YAML dopiero po decyzjach.

Weryfikacja:

- sample staging -> decyzje -> finalne YAML przechodzi `validate.py`;
- bledna decyzja blokuje zapis finalnych YAML.

## Milestone 5: build i eksporty

### PBI-016: Build SQLite

Status: wykonane 2026-05-16.

Zakres:

- czytac zwalidowane YAML,
- budowac `build/katalog.sqlite`,
- tworzyc tabele logiczne ze specyfikacji,
- zapisac najlepsze geometrie obiektow.

Weryfikacja:

- test na fixture'ach tworzy SQLite,
- liczby w `metadata` zgadzaja sie z liczba plikow YAML.

### PBI-017: Eksport `best-measurements`

Status: wykonane 2026-05-16.

Zakres:

- wygenerowac GeoJSON,
- wygenerowac CSV,
- wygenerowac GPX,
- przygotowac Shapefile ZIP, jesli zaleznosci geospatial sa gotowe.

Weryfikacja:

- eksport zawiera tylko najlepsze pomiary,
- CSV ma WGS84 i EPSG:2180,
- GeoJSON ma poprawne `FeatureCollection`.

### PBI-018: Metadata release

Status: wykonane 2026-05-16.

Zakres:

- wygenerowac `metadata.json`,
- zapisac liczby obiektow, jaskin, pomiarow, ostrzezen walidacji, wersje schematu i timestamp buildu.

Weryfikacja:

- test snapshotu `metadata.json` na fixture'ach.

## Milestone 6: CI, release, operacje

### PBI-019: CI walidacyjne

Status: wykonane 2026-05-16.

Zakres:

- dodac `.github/workflows/validate.yml`,
- uruchamiac `uv sync`, `ruff`, `pytest`, `scripts/validate.py`.

Weryfikacja:

- lokalne komendy sa takie same jak w CI,
- workflow nie buduje release'ow.

### PBI-020: Build/release workflow

Status: wykonane 2026-05-16, skorygowane PBI-029 2026-05-17.

Zakres:

- zachowac lokalny builder artefaktow release,
- dodac `release.yml` dla tagow `v*`,
- publikowac artefakty release tylko po recznym pushu taga.

Weryfikacja:

- dry-run lokalny buildu generuje wszystkie oczekiwane pliki,
- release jest tag-only i nie zalezy od runtime'owej flagi licencyjnej.
- repo nie ma automatycznego `build.yml` uruchamianego po pushu na `main`.

### PBI-021: Dokumentacja operacyjna

Status: wykonane 2026-05-16.

Zakres:

- opisac jak dodac nowy pomiar recznie,
- opisac jak uruchomic walidacje,
- opisac jak przygotowac tagowany release danych,
- opisac zasady weryfikacji `zweryfikowany` / `odrzucony`.

Weryfikacja:

- nowa osoba moze na podstawie dokumentu dodac fixture'owy pomiar i przejsc walidacje.

## Milestone 7: poprawki po pierwszym release

### PBI-022: Poprawic kategorie sztolni z TPN

Status: wykonane 2026-05-16.

Zakres:

- importer staging TPN rozpoznaje `category` z `GENEZA` i nazwy obiektu,
- `sztolnia` w `GENEZA` albo nazwie daje `category: sztolnia`,
- istniejace finalne obiekty `Sztolnia...` zostaly przestawione z
  `jaskinia_otwor` na `sztolnia`.

Weryfikacja:

- test importera dla nowej sztolni z TPN,
- kontrola 26 istniejacych obiektow o nazwie zawierajacej `sztoln`,
- `scripts/validate.py` bez errorow.

### PBI-023: Uporzadkowac zrodla i dokumentacje dla ludzi

Status: wykonane 2026-05-16.

Zakres:

- dodac top-level `README.md` z opisem projektu dla GitHuba,
- przeniesc PIG/TPN XLSX i CSV z root do `data/sources/{pig,tpn}/`,
- dodac `data/sources/README.md`,
- skopiowac `jaskinie_polski_pig_dump.jsonl` do `data/sources/pig/`,
- opisac w `docs/operations.md` workflow grep/review dla brakujacych otworow.

Weryfikacja:

- domyslne sciezki importerow i profilowania wskazuja `data/sources/`,
- `rg -n "Mroźna" data/sources/pig/jaskinie_polski_pig_dump.jsonl` znajduje
  rekord PIG z informacja o drugim otworze,
- lokalna walidacja danych przechodzi bez errorow.

### PBI-024: Dopelnic znane brakujace obiekty

Status: wykonane 2026-05-16.

Zakres:

- rozdzielic Jaskinie Mrozna na dwa obiekty otworowe:
  `KSW-0081` i `KSW-0256`,
- dopisac `KSW-0256` do `C-0267.object_ids`,
- dodac slowacka `Nova Kresanica` jako `SK-0001` / `C-1003`,
- dodac `Obcasna Vyvieracka` jako `SK-0002` / `C-1004` z
  `category: jaskinia_otwor`,
- zapisac przeliczenie `E19:55:47.53 N49:13:35.8` na WGS84 decimal:
  lon `19.92986944`, lat `49.22661111`.

Weryfikacja:

- `scripts/assign_id.py` wskazuje prefix `KSW` dla drugiego otworu Mroznej i
  fallback `SK` dla obu slowackich punktow,
- `scripts/validate.py` bez errorow; znane ostrzezenia pozostaja nieblokujace.

### PBI-025: Rozstrzygnac wielootworowe przypadki i nowe pomiary

Status: wykonane 2026-05-16.

Zakres:

- rozdzielic Jaskinie Bandzioch Kominiarski na gorny obiekt `LEJ-0002` i nowy
  dolny obiekt `KSZ-0112`,
- dodac gorny otwor Jaskini Zimnej / Jaskinie Biala jako `KSW-0257`, bez
  tworzenia osobnej jaskini,
- podlaczyc `KSW-0240` jako Jaskinie Czarna III do `C-0699` i usunac
  duplikatowa jaskinie `C-0876`,
- dopisac pomiary GNSS+LIDAR z 2026-05-09 dla glownego otworu Jaskini Czarnej
  i Jaskini Czarnej III, z opisem odczytu Dariusza Lubomskiego z
  `https://cloud.wrogeo.pl/`,
- oznaczyc `Jaskinie Pawlikowskiego` jako system dla Mylnej, Oblazkowej i
  Raptawickiej, dodac pomiary Pawlikowskiego i materializowac polnocny otwor
  Mylnej jako `KSZ-0113`,
- dodac wschodni / SE otwor Jaskini nad Korytem jako `MLZ-0108`,
- dopisac pomiar `Wysoka7Progow` do istniejacej Jaskini Wysokiej `KSW-0189`,
- nazwac bezimienny TPN row 273 / `STR-0024` jako `BEZ_NAZWY_001`.

Weryfikacja:

- `scripts/validate.py` bez errorow,
- finalny katalog ma 1009 obiektow, 1003 jaskinie i 1875 pomiarow,
- znane ostrzezenia walidatora pozostaja nieblokujace:
  `MISSING_HORIZONTAL_ACCURACY`, `MEASUREMENT_OUTSIDE_VALLEYS`,
  `MEASUREMENT_DISTANCE_OUTLIER` i `OBJECT_PREFIX_MISMATCH`.

### PBI-026: Wprowadzic testy mutacyjne

Status: wykonane 2026-05-16.

Zakres:

- dodac `mutmut` jako zaleznosc developerska utrwalona w `uv.lock`,
- skonfigurowac zakres mutacji w `pyproject.toml` dla krytycznych modulow:
  `best_measurement`, `coordinates`, `prefix_resolver`, `validator`,
  staging PIG/TPN oraz `staging_review`,
- dodac reczny workflow `.github/workflows/mutation.yml` uruchamiany przez
  `workflow_dispatch`, bez obciazania standardowego PR CI,
- ignorowac lokalny katalog wynikow `mutants/`,
- opisac uruchamianie w `README.md` i `docs/operations.md`.

Weryfikacja:

- test konfiguracji `mutmut`,
- test workflow mutacyjnego,
- `uv run mutmut run --max-children 2 'gps_kataster_obiektow_tatr.best_measurement*'`
  przechodzi dla `best_measurement` bez przezytych mutantow,
- pelna lokalna bramka Ruff, pytest i `scripts/validate.py` przechodzi bez
  errorow.

### PBI-027: Wyjasnic `nieweryfikowany` w release

Status: wykonane 2026-05-16.

Zakres:

- dopisac w `README.md`, ze poczatkowe release'y moga miec wiekszosc
  najlepszych pomiarow jako `verification_status: nieweryfikowany`,
- dopisac w `docs/operations.md`, ze status oznacza brak projektowego review,
  a nie automatyczny blad danych albo brak proweniencji,
- utrwalic zasade, ze statusow importow PIG/TPN nie zmieniamy hurtowo na
  `zweryfikowany`.

Weryfikacja:

- test dokumentacji operacyjnej sprawdza obecnosc wyjasnienia dla release.

### PBI-028: Udokumentowac kolumny release i dodac notatki do eksportow

Status: wykonane 2026-05-17.

Zakres:

- przejrzec lokalny zestaw release: SQLite, CSV, GeoJSON, GPX, Shapefile ZIP i
  `metadata.json`,
- dodac dokument `docs/release_artifacts.md` opisujacy, ktory plik zawiera
  jakie kolumny albo pola,
- dodac do plaskich eksportow `best-measurements` rozdzielone notatki:
  `object_notes`, `cave_notes`, `measurement_notes`,
- w Shapefile uzyc skroconych nazw DBF: `obj_notes`, `cave_notes`,
  `meas_notes`,
- dopisac notatki do opisu waypointow GPX.

Weryfikacja:

- test eksportu sprawdza notatki w GeoJSON, CSV, GPX i Shapefile,
- pelna lokalna bramka Ruff, pytest, walidacja YAML i build artefaktow release.

### PBI-029: Przestawic release na reczny semver tagowy

Status: wykonane 2026-05-17.

Zakres:

- dodac glowny `CHANGELOG.md` zgodny z Keep a Changelog / semver,
- ustawic formalna wersje projektu na `1.0.0`,
- usunac automatyczny build artefaktow po `main`,
- zostawic publikacje GitHub Release wylacznie po recznym tagu `v*`,
- pobierac notatki GitHub Release z wpisu `CHANGELOG.md` dla danego taga,
- dodac w README link do najnowszego release i link do changeloga,
- zmienic dokumentacje operacyjna z cyklicznej paczki na tagowany release.

Weryfikacja:

- testy workflow sprawdzaja brak `build.yml`, tag-only release i release notes
  z `CHANGELOG.md`,
- testy dokumentacji sprawdzaja link do najnowszego release, changelog i
  tagowany proces wydania,
- pelna lokalna bramka Ruff, pytest, walidacja YAML i build artefaktow release.

### PBI-030: Uzupelnic wysokosc gornego Bandziocha

Status: wykonane 2026-05-17.

Zakres:

- uzupelnic reczny pomiar GNSS `m-003` w `LEJ-0002` o wysokosc `1675.02 m`
  z dostarczonego wpisu `BandziochKom:136`,
- zachowac dolny otwor `KSZ-0112` / `BandziochKom:000` z wysokoscia
  `1451.06 m`,
- odswiezyc lokalne artefakty release, zeby `best-measurements` pokazywaly
  wysokosc obu otworow.

Weryfikacja:

- `uv run python scripts/validate.py` bez errorow,
- `uv run python scripts/build_release_artifacts.py --generated-at 2026-05-17T06:43:08Z`
  bez errorow,
- `build/exports/best-measurements.csv`, GeoJSON i GPX zawieraja `1675.02`
  dla `LEJ-0002`.

### PBI-031: Ujednolicic dokumentacje release i licencji z aktualnym kodem

Status: wykonane 2026-05-18.

Zakres:

- przejrzec specyfikacje, backlog, kontekst AS-DLC, README, dokumentacje
  operacyjna, workflow i testy pod katem aktualnego modelu release,
- usunac runtime'owa bramke licencyjna z `release.yml`,
- zostawic licencje CC BY 4.0 jako stan projektu opisany w `LICENSE` i
  dokumentacji, bez dodatkowej flagi w CI,
- upewnic sie, ze dokumentacja nie opisuje automatycznego release/builda po
  `main`; release pozostaje reczny, semverowy i tagowany.

Weryfikacja:

- workflow release nie zawiera dodatkowej bramki licencyjnej,
- `.github/workflows/build.yml` nie istnieje, a dokumentacja opisuje tylko
  reczny release przez semver tag,
- testy workflow sprawdzaja brak dodatkowej bramki licencyjnej i brak
  automatycznego `build.yml`,
- pelna lokalna bramka Ruff, pytest, walidacja YAML i build artefaktow release.

### PBI-032: Przygotowac release `v1.0.2`

Status: wykonane 2026-05-21.

Zakres:

- zamienic wpis `Unreleased` w `CHANGELOG.md` na `v1.0.2`,
- podbic wersje projektu w `pyproject.toml` i `__version__`,
- zaktualizowac testy wersji i changeloga,
- przeprowadzic PR -> merge -> annotated tag `v1.0.2` -> GitHub Release.

Weryfikacja:

- pelna lokalna bramka Ruff, pytest, walidacja YAML i build artefaktow release,
- po tagu `v1.0.2`: sprawdzenie GitHub Release i najnowszego release.

### PBI-033: Przebudowac README dla uzytkownikow PL/EN/SK

Status: wykonane 2026-07-11.

Zakres:

- postawic potrzeby grotolazow, speleologow i uzytkownikow GIS przed opisem
  implementacji,
- przygotowac rownolegle `README.md` po polsku, `README.en.md` po angielsku i
  `README.sk.md` po slowacku,
- opisac formaty gotowych danych, ich zroznicowana dokladnosc i status
  weryfikacji,
- wyjasnic role trzech powiazanych projektow i jawnie wskazac GPS Kataster jako
  zrodlo wspolrzednych uzywane przez Jaskiniowy Kataster Tatr i Georeferencer,
- zachowac skrocony opis dla developerow i odeslac szczegoly do istniejacej
  dokumentacji technicznej.

Weryfikacja:

- test dokumentacji sprawdza przelacznik PL/EN/SK, linki do repozytoriow i ich
  najnowszych wydan oraz istniejace kontrakty release,
- `git diff --check` nie zglasza bledow formatowania.

## Proponowana kolejnosc startowa

Najmniejsza sensowna sciezka do pierwszego dzialajacego przeplywu:

1. PBI-001: struktura repo.
2. PBI-002: projekt Pythonowy.
3. PBI-003: `config/prefixes.yml`.
4. PBI-004 + PBI-005: schematy i fixture'y.
5. PBI-006 + PBI-007: wspolrzedne i prefixy.
6. PBI-009 + PBI-010 + PBI-011: walidator.
7. PBI-008: `assign_id.py`.
8. PBI-016 + PBI-017: minimalny build i eksport.

Import PIG/TPN warto zaczac dopiero po dzialajacym walidatorze, bo inaczej szybko powstanie duzo danych bez bramek jakosci.
