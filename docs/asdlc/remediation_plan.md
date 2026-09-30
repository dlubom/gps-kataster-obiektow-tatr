# Plan napraw po przeglądzie 2026-09-05

Plan bazuje na commicie `a3dd1a671d3d93cd6958242fc68ddcf1d37cf846` i
[raporcie R01–R13](reviews/project-review-2026-09-05.md). Jednostką wykonania
jest jedno PBI w jednej sesji. Historia rozmowy, lokalny `build/`, `/tmp` i
pamięć konta Codexa nie są wymagane do kontynuacji.

Branch całej serii: **`codex/review-remediation`**, zdalne repo: `origin`.
Planowanie to PBI-034; implementacja zaczyna się od PBI-035. Bieżące statusy
są wyłącznie w [backlogu](backlog_v1.md#naprawy-po-przegladzie-2026-09-05).
Instrukcja sesji i domknięcia znajduje się w [runbooku](remediation_runbook.md).
Wyniki każdej sesji trafiają do `docs/asdlc/verification/PBI-NNN.md`.

## Kolejność i zależności

Domyślnie wykonuj najniższy numer PBI, którego zależności są dostarczone na
branch i który nie jest zablokowany. Numer podany przez użytkownika ma
pierwszeństwo, ale nie pozwala pominąć zależności. Nie rozpoczynaj równolegle
dwóch implementacji na tym samym checkoutcie. Osobny agent może czytać i
recenzować wynik; właściciel PBI wykonuje zapis, commit i push.

| PBI | Wynik jednej sesji | Ustalenie | Zależności techniczne |
|---|---|---|---|
| 034 | Plan, raport w git i instrukcja wznowienia | cały przegląd | 033 |
| 035 | Jedna odtwarzalna bramka lokalna i CI na branchu | weryfikacja | 034 |
| 036 | Odrzucanie duplikatów kluczy YAML | R01 | 035 |
| 037 | Unikalność wszystkich identyfikatorów | R04 | 036 |
| 038 | Symetria obiekt–jaskinia i poprawne `link_cave` | R03 | 037 |
| 039 | Spójna obsługa `.yml`/`.yaml` i ścieżek aktualizacji | R10 | 037 |
| 040 | Walidacja wejścia i pełnego wyniku przed zapisem review | R02 | 036, 037, 038, 039 |
| 041 | Ochrona przed częściowym zapisem przy błędzie I/O | uzupełnienie R02 | 040 |
| 042 | Skończone wartości liczbowe w całym przepływie | R05 | 040 |
| 043 | Błąd nieistniejącego katalogu wejściowego | R12 | 040 |
| 044 | Spójność referencji i prefixu przydziału ID | R06, część techniczna | 037, 040 |
| 045 | Jeden kandydat na trwałe ID w finalnych danych i staging | R08 | 040 |
| 046 | Unikalne numery nowych pomiarów w partii decyzji | R07 | 040, 045 |
| 047 | Zachowanie danych wierszy `unresolved` | R09, format staging | 042, 045 |
| 048 | Jawne rozstrzygnięcia operatora dla `unresolved` | R09, materializacja | 038, 040, 041, 046, 047 |
| 049 | Poprawny UTF-8 w każdym polu tekstowym DBF | R11 | 035 |
| 050 | Deterministyczne ZIP-y i nagłówek DBF | R13 | 049 |
| 051 | Udokumentowane przyczyny 16 istniejących rozbieżności prefixu | R06, dane | 044 |
| 052 | Egzekwowanie uzasadnienia bez zmiany trwałych ID | R06, pełna reguła | 044, 051 |
| 053 | Dokumentacja zgodna z wdrożonymi kontraktami | uwagi z raportu | 040, 043, 048, 050 |
| 054 | Końcowa weryfikacja wszystkich R01–R13 i niezależny review | zamknięcie serii | 035–053, 055–061 |
| 055 | Poprawne wiązanie skończonych dużych int w SQLite REAL | uzupełnienie R05 | 042 |
| 056 | Odrzucanie zduplikowanych indeksów staging | nowe ustalenie P2 z PBI-054 | 040, 046, 048 |
| 057 | Wiązanie jawnie wskazanej propozycji z wierszem źródła | nowe ustalenie P2 z PBI-054 | 040, 056 |
| 058 | Regresja dopasowania TPN po GLOBALID | luka mutacyjna z PBI-054 | 045, 047 |
| 059 | Ścisłe dodatnie numery wierszy decyzji i raportów | nowe P2 z ponowienia PBI-054 | 040, 042, 057 |
| 060 | Spójna proweniencja propozycji i ref staging | nowe P2 z ponowienia PBI-054 | 040, 048, 056, 057 |
| 061 | Bezpieczna reprezentacja liczb w DBF | nowe P2 z ponowienia PBI-054 | 049, 050, 055 |

PBI-035 celowo poprzedza naprawy: każda kolejna sesja ma móc zweryfikować
wynik jednym poleceniem. PBI-037–039 przygotowują kontrakty używane przez
bramkę review. Walidacja symetrii i zmiana `link_cave` należą do tego samego
PBI, aby nie wprowadzić pośredniego stanu z niespójnym API.

## Kontrakt odbioru wszystkich PBI

Każda karta poniżej dziedziczy pełną bramkę z runbooka: test reprodukujący
problem przed zmianą, testy obszaru, Ruff, wszystkie testy, walidacja całych
danych, pełny build, ponowny odczyt artefaktów i weryfikacja niezmienności
danych poza dozwolonym zakresem. Dla zmienionej krytycznej logiki dochodzą
testy mutacyjne określone w runbooku. Po puszu wymagane jest potwierdzenie
zdalnego SHA i, od PBI-035, powodzenia CI dla tego commitu.

Nie wystarczy poprawić licznika w teście ani sam tekst błędu. Test ma
wykazać konkretny skutek: niepoprawny rekord odrzucony przed zapisem, brak
zmiany plików przy błędzie, właściwy pomiar wybrany w eksporcie albo plik
otwierający się ponownie. Każde PBI aktualizuje dokumentację kontraktu,
jeżeli zmienia zachowanie użytkowe. PBI-053 sprawdza całość, nie odkłada
obowiązku dokumentowania poprzednich zmian.

Nie zmieniaj ID, współrzędnych, historii, statusów weryfikacji ani powiązań
obecnego katalogu jako skutku poprawki narzędzi. Wyjątkiem jest ściśle
opisane uzupełnienie powodów w PBI-051. Jeżeli nowe reguły wykryją inne
rzeczywiste błędy danych, zapisz je jako osobne zadanie; nie wyłączaj reguły
i nie naprawiaj ich przez arbitralną zmianę lokalizacji.

## Karty wykonawcze

### PBI-034 — Utrwalić plan i sposób kontynuacji

Zakres: ten plan, runbook, aktualny punkt wejścia w `AGENTS.md` i kontekście,
nowe PBI w backlogu, przenośny raport i historyczne dowody przeglądu.
Weryfikacja: kompletne pokrycie R01–R13, poprawne zależności, działające
odnośniki bez lokalnych ścieżek, pełna obecna bramka. Tylko dokumentacja.
Commit: `docs: plan review remediation (PBI-034)`.

### PBI-035 — Ujednolicić pełną bramkę lokalną i CI

Pliki: nowy `scripts/verify_project.py`, testy runnera, `validate.yml`,
`docs/operations.md`, ten runbook. Jedno polecenie
`uv run --frozen python scripts/verify_project.py` ma wykonać Ruff,
wszystkie testy, walidację katalogu, izolowany build release oraz odczyt
SQLite/CSV/GeoJSON/GPX/Shapefile/ZIP/metadata. Raport w `build/verification/`
ma zapisywać komendy, exit codes, wersje, bazowy SHA i hash weryfikowanego
drzewa bez samych raportów. Nie może publikować, commitować ani zmieniać
danych. Dodać uruchamianie CI dla push na `codex/review-remediation`,
zachować PR i `main`; użyć tej samej bramki i `uv sync --frozen`.

Odbiór: wymuszona awaria każdego etapu daje niezerowy wynik całości i nie
jest maskowana przez późniejsze udane polecenie. Liczniki i ID wszystkich
eksportów zgadzają się z YAML; sprawdzane są oba kierunki relacji jaskiń,
wybrany pomiar, osie współrzędnych, integralność SQLite i ZIP-ów. Regresja
nie może przejść na starych plikach z `build/`. Testy runnera nie mogą
rekurencyjnie wywoływać całego pytest. Do wdrożenia runnera obowiązuje
ręczna bramka z runbooka. Nie zwiększać zakresu publikacji release.
Commit: `test: add repeatable project verification (PBI-035)`.

### PBI-036 — Odrzucać duplikaty kluczy YAML

Pliki: `data_loader.py`, `staging_review.py`, ewentualny wspólny loader,
testy loadera/review i CLI. Użyć jednej bezpiecznej polityki parsowania
danych i decyzji, z informacją o pliku i linii. Jawnie ustalić zachowanie
aliasów i klucza scalania YAML; nie zmienić przypadkowo obsługi dat.

Odbiór: drugi `measurements`, drugi zagnieżdżony `id` i drugi `action`
powodują czytelny błąd. Walidator, build, eksport i review nie zapisują
wyniku z pominiętą historią; poprawne pliki wciąż działają. Wszystkie
przypadki są fixture'ami tworzonymi w testach, bez zależności od `/tmp`
przeglądu. Commit: `fix: reject duplicate YAML keys (PBI-036)`.

### PBI-037 — Walidować unikalność ID we właściwych zakresach

Pliki: `validator.py`, testy walidacji/builda/eksportu. Wykrywać duplikaty
ID jaskiń i relacji globalnie, pomiarów i załączników w obrębie obiektu.
Nie redukować list do zbiorów/słowników przed kontrolą duplikatów.

Odbiór: identyczne ID z różnymi polami, duplikaty w `.yml` i `.yaml`,
duplikaty identycznych wpisów oraz poprawne `m-001`/`a-001` w dwóch różnych
obiektach. Niepoprawny przypadek daje błąd domenowy przed SQLite i
eksportem, bez nadpisania istniejącego artefaktu. Test obejmuje wszystkie
cztery rodzaje ID, a nie tylko pomiary.
Commit: `fix: validate all domain identifier scopes (PBI-037)`.

### PBI-038 — Utrzymać symetrię obiekt–jaskinia

Pliki: `validator.py`, `staging_review.py`, testy obu modułów. Sprawdzać
powiązanie w obie strony; jeden obiekt może należeć do najwyżej jednej
jaskini. `link_cave` usuwa obiekt ze starej jaskini, aktualizuje obie
jaskinie i obiekt; ID i pomiary pozostają bez zmian. Dopuścić pustą listę
otworów jaskini i brak `cave_id` zgodnie ze specyfikacją.

Odbiór: A→B nie zostawia wpisu w A, ponowne A→A jest bezpieczne, dwie
jaskinie wskazujące jeden obiekt są błędem, brak wpisu odwrotnego także.
Test obejmuje zapis/readback i SQLite, nie tylko słowniki w pamięci.
Commit: `fix: preserve cave membership consistency (PBI-038)`.

### PBI-039 — Ujednolicić rozszerzenia i zachować ścieżki

Pliki: `assign_id.py`, loader, `staging_review.py`, helpery numeracji
importerów. `.yml` i `.yaml` są obsługiwane konsekwentnie; aktualizacje
zachowują istniejącą ścieżkę, nowe rekordy domyślnie używają `.yml`.
Zachować metadane ścieżek przy ładowaniu danych dla review.

Odbiór: `KSW-0001.yaml` powoduje propozycję `KSW-0002`; update i `link_cave`
nie tworzą sąsiedniego `.yml`; mieszany katalog, licznik >9999 i konflikt
obu rozszerzeń są objęte testami. Przy konflikcie nie zgadywać pliku do
nadpisania. Commit: `fix: preserve YAML paths and ID allocation (PBI-039)`.

### PBI-040 — Walidować review przed materializacją

Pliki: `staging_review.py`, `validator.py`, `apply_review.py`, testy
integracyjne. Sprawdzić wejściowy `LoadedDataset` przed indeksowaniem po
ID. Zastosować decyzje na kopii, a potem sprawdzić pełny wynik wraz z
niezmienionymi relacjami i rzeczywistymi ścieżkami. Walidować stan po
całej partii, nie po każdej przejściowo niekompletnej decyzji.

Odbiór: samo `create_object`, sama jaskinia z nieistniejącym otworem,
uszkodzona propozycja, wejściowe duplikaty oraz uszkodzona relacja blokują
wszystkie zapisy i dają czytelne błędy. Poprawna para cave+object w jednej
partii przechodzi. `write=False` wykonuje identyczne sprawdzenia, lecz nic
nie zapisuje. Istniejący błędny rekord może być naprawiony tylko przez
wyraźnie zaprojektowaną i testowaną ścieżkę, nie przez ciche pominięcie.
Testy błędu porównują bajty całego katalogu przed i po. Przy zmianie
`target_object_id` referencje katalogowe muszą dotyczyć jego faktycznej
jaskini; nie wolno dopisywać ich do starego celu staging.
Commit: `fix: validate complete review transactions (PBI-040)`.

### PBI-041 — Zabezpieczyć zapis partii przed błędami I/O

Pliki: writer review i testy awarii. Najpierw przygotować wszystkie pliki,
potem zastępować je z mechanizmem przywrócenia oryginałów przy obsługiwanym
błędzie zapisu/rename. Nie tracić pliku przez otwarcie go do nadpisania
przed powodzeniem serializacji. Osobno udokumentować granicę gwarancji
przy przerwaniu procesu lub zasilania; nie obiecywać transakcji systemu
plików. Pozostałości recovery mają być wykrywane przed następną operacją.

Odbiór: wymuszony błąd drugiego zapisu i drugiego zastąpienia pozostawia
oryginalne pliki identyczne, nie zostawia połowy nowych rekordów, zgłasza
niepowodzenie. Gdy rollback też zawiedzie, istnieje czytelny raport i
instrukcja odzyskania, zamiast komunikatu sukcesu. Poprawny retry działa.
Commit: `fix: recover from partial review writes (PBI-041)`.

### PBI-042 — Odrzucać NaN i nieskończoności

Pliki: walidator, konwersje, parsery PIG/TPN/profilowania, serializacja
JSON, testy. Wszystkie domenowe liczby muszą być skończone. `null` pozostaje
dozwolone tam, gdzie schemat dopuszcza brak wartości; nie zamieniać błędnej
podanej liczby na pozornie poprawny brak bez zgłoszenia problemu.

Odbiór: `.nan`, `.inf`, `-.inf`, tekstowe `NaN`/`Infinity` w CSV/XLSX,
współrzędne, wysokości i dokładności. Błędny punkt nie może stać się
propozycją finalnego pomiaru, trafić do JSON ani uruchomić niekontrolowanego
wyjątku SQLite. Serializacja JSON z `allow_nan=False` jest dodatkową
ochroną; podstawą jest czytelny błąd przed zapisem.
Commit: `fix: reject non-finite measurement values (PBI-042)`.

### PBI-043 — Odróżnić brak wejścia od pustego celu importu

Pliki: loader, CLI walidacji/builda/eksportu/review, testy. Nieistniejący
`--data-dir` oraz plik zamiast katalogu są błędem dla operacji odczytu i
budowy. Istniejący pusty katalog oraz brak opcjonalnego katalogu relacji
mają osobno opisane zachowanie. Nowy cel importu może być tworzony przez
jawną ścieżkę importera; nie zmieniać globalnie brakującego wejścia na `()`.

Odbiór: zła ścieżka daje niezerowy exit code i nie zmienia istniejących
artefaktów. Import pierwszej poprawnej pary cave+object do nowego celu
działa. Brakujące/błędne wejście jest rozróżnione od katalogu z 0 rekordów.
Commit: `fix: reject missing build inputs (PBI-043)`.

### PBI-044 — Sprawdzać techniczną spójność przydziału ID

Pliki: walidator, testy i specyfikacja §4.1/§5. Sprawdzać istnienie
`assigned_from_measurement_id` w tym obiekcie i zgodność `assigned_prefix`
z trwałym ID. Nie wymagać zgodności prefixu z bieżącym pomiarem ani nie
renumerować utrwalonych ID. Nie włączać jeszcze nowej blokady dla 16
brakujących powodów — tę zależność domykają PBI-051 i PBI-052.

Odbiór: brak `m-999`, niezgodny `ABC`, poprawny historyczny przydział po
zmianie najlepszego pomiaru, manual z istniejącym powodem. Cały katalog
pozostaje poprawny; ten krok nie zamyka samodzielnie R06.
Commit: `fix: validate ID assignment references (PBI-044)`.

### PBI-045 — Deduplikować kandydatów finalnych i staging

Pliki: `tpn_staging.py`, testy. Jeden trwały `object_id` daje jednego
kandydata. Rekord finalny ma pierwszeństwo przed własną historyczną
propozycją PIG. Konflikt różnych tożsamości/proweniencji nie może być
rozwiązany wyłącznie przez przypadkową kolejność wczytywania.

Odbiór: zaakceptowany PIG + zachowany staging nie tworzy fałszywej
niejednoznaczności; zmiana kolejności wejścia nie zmienia wyniku; dwa
rzeczywiście różne obiekty o podobnej nazwie/położeniu pozostają odrębne.
Commit: `fix: deduplicate staging match candidates (PBI-045)`.

### PBI-046 — Nadawać pomiarom unikalne numery w partii

Pliki: importer TPN, review, testy i format decyzji. Rezerwować numery per
faktyczny obiekt docelowy deterministycznie w całej partii. Przy ręcznym
przekierowaniu celu uwzględniać jego istniejące pomiary. Powiązać wpisy
z referencją źródłową; ponowienie tej samej decyzji nie może po prostu
dodać tego samego rekordu źródłowego pod nowym numerem.

Odbiór: dwa dopasowania zaakceptowane razem dają `m-002` i `m-003`, działa
cel z własnym licznikiem i numer >999. Jawnie testować retry oraz
respektowanie manual best. Odróżniać celową nową obserwację źródła od
ponownego wykonania tej samej decyzji na tym samym stagingu.
Commit: `fix: allocate measurement IDs across review batches (PBI-046)`.

### PBI-047 — Zachować znormalizowane dane `unresolved`

Pliki: importer TPN, struktura raportu, testy, dokument formatu staging.
Raport zachowuje znormalizowany pomiar i referencje dla poprawnego
geograficznie, lecz niejednoznacznego wiersza. Nie nadaje przez to zgody na
materializację ani nie zamienia `unresolved` na `matched`. Określić wersję
formatu i czytelną ścieżkę dla starszego raportu bez payloadu.

Odbiór: JSON round-trip zachowuje źródłowe ID, wiersz, datę i współrzędne;
niepoprawna geometria pozostaje odrzucona, a finalne dane nie są tworzone.
Zgodność dotychczasowych matched/new pozostaje utrzymana.
Commit: `fix: retain unresolved staging measurements (PBI-047)`.

### PBI-048 — Materializować jawne rozstrzygnięcie niejednoznaczności

Pliki: review, CLI, dokumentacja decyzji, testy pełnego przepływu. Operator
może wskazać istniejący obiekt albo utworzyć nowy i powiązać go z właściwą
jaskinią; sama obecność payloadu `unresolved` niczego nie zatwierdza.
Przy nowym obiekcie stosować resolver i wolne trwałe ID. Decyzje muszą
wiązać się ze stabilną tożsamością wiersza i konkretnym raportem, aby
regeneracja/przestawienie wierszy nie przeniosła akceptacji na inne dane.

Odbiór: prawdziwie niejednoznaczny wiersz → jawny target → poprawny nowy
pomiar; wariant nowego otworu → prawidłowe dwustronne powiązanie. Brak
decyzji, brak targetu, pomylona tożsamość źródła i starszy raport bez
payloadu nie powodują zapisu. `reject` i `unresolved` pozostają bez zapisu.
Test kończy się walidacją katalogu i buildem, nie samym `has_errors=False`.
Commit: `fix: apply explicit unresolved-row decisions (PBI-048)`.

### PBI-049 — Ograniczać tekst DBF według bajtów UTF-8

Pliki: eksporter i testy. Obsłużyć wszystkie pola tekstowe DBF, w tym
nazwę, uwagi i referencje. Zachować limity pól i granice znaków; nie
skracać pełnych treści w YAML/SQLite/CSV/GeoJSON. Opisać ograniczenie DBF.

Odbiór: 253 `a` + `ó`, wielobajtowe polskie i słowackie nazwy oraz tekst
na granicy długości. Eksport czyta się z powrotem jako UTF-8 i ma te same
ID/liczby rekordów; brak zastępczych znaków ukrywających błąd kodowania.
Commit: `fix: truncate DBF text at UTF-8 boundaries (PBI-049)`.

### PBI-050 — Ustalić deterministyczne metadane artefaktów

Pliki: release builder, eksporter, testy. Z jednego `generated_at` ustalać
daty ZIP i DBF oraz stabilne atrybuty archiwów. Ustalić zachowanie dla dat
poza zakresem ZIP. Nie zmieniać merytorycznej zawartości katalogu.

Odbiór: dwa pełne buildy z różnym zegarem systemowym, mtime i katalogiem
wyjścia, ale tym samym wejściem i `generated_at`, mają identyczne SHA-256
wszystkich siedmiu artefaktów. Testować różne dni bez rzeczywistego sleep.
Sprawdzić jednocześnie readback; nie wystarczy porównać dwóch ZIP-ów
stworzonych w tej samej sekundzie. Zmiana danych zmienia właściwe sumy.
Commit: `fix: make release archives reproducible (PBI-050)`.

### PBI-051 — Ustalić powody historycznych rozbieżności prefixu

Pliki: 16 obiektów wymienionych w R06, dokument dowodów pod
`docs/asdlc/verification/`, ewentualnie tylko ich pola audytu aktualizacji.
Dla każdego porównać pomiar przydziału, best, resolver, historię git i
decyzje zapisane w kontekście. Powód ma opisywać ustalony fakt oraz
zachowanie trwałego ID; nie udawać weryfikacji terenowej lub nieznanej
decyzji operatora. Nie zmieniać metody przydziału, współrzędnych ani ID
tylko po to, żeby wyciszyć walidację.

Odbiór: tabela dowodów dla 16/16 obiektów, sensowne niepuste powody,
diff ograniczony do powodów i uzasadnionego audytu, niezmienione pomiary,
ID i best. Jeśli dla części obiektów brakuje dowodów, zapisać dokładny
brak i zadać tylko niezbędne pytanie operatorowi; status pozostaje
zablokowany/częściowy, R06 pozostaje otwarte. W tym czasie można wykonać
niezależne PBI-053. Nie stosować tekstów typu „zaakceptowano” bez dowodu.
Commit: `data: document retained object prefixes (PBI-051)`.

### PBI-052 — Egzekwować wymagane powody

Pliki: walidator, schemat w zakresie whitespace, testy, specyfikacja.
Po dostarczeniu PBI-051 egzekwować niepuste, niebiałe uzasadnienie dla
manual przydziału i świadomego zachowania niezgodnego prefixu. Sama
niezgodność bieżącej lokalizacji pozostaje warningiem; brak wymaganego
uzasadnienia jest osobnym błędem. Nie dodać wyjątków po ID dla 16 rekordów.

Odbiór: reason brak/null/pusty/spacje, manual/auto, lokalizacja zgodna i
niezgodna. Po uzupełnieniu danych pełna bramka ma 0 błędów, zaś historyczne
`OBJECT_PREFIX_MISMATCH` mogą pozostać. Jeśli dowody PBI-051 są niepełne,
nie wdrażać połowy reguły ani nie oznaczać R06 jako naprawionego.
Commit: `fix: enforce documented prefix overrides (PBI-052)`.

### PBI-053 — Ujednolicić dokumentację z działającym systemem

Pliki: specyfikacja, operations, release_artifacts, staging decisions,
README tylko gdy wskazują zmienione polecenia. Zapisać bieżący wariant
SQLite z WKT zgodnie z decyzją PBI-016, poprawne `counts.*` w metadata,
komendę pełnej bramki i nowe kontrakty import/review. Oddzielić stan
wdrożony od przyszłego SpatiaLite. Nie zmieniać modelu domeny, polityki
licencji ani sposobu publikacji i nie dodawać nowego release/tagu.

Odbiór: polecenia dokumentacji wykonane na kopii fixture, linki istnieją,
klucze zgadzają się z realnym metadata; brak obietnic już odrzuconych
przez implementację. Commit: `docs: align operations with repaired contracts (PBI-053)`.

### PBI-054 — Domknąć przegląd i gotowość do osobnej decyzji o merge

Pliki: raport końcowy i rejestry weryfikacji; ewentualne poprawki mają
osobne małe zadania. Uruchomić bramkę z czystego checkoutu aktualnego
brancha, testy regresji R01–R13, odpowiedni zakres mutacji i sprawdzenie
powtarzalności artefaktów. Zlecić niezależny review końcowego diffu
agentowi do odczytu. Każde otwarte znalezisko ma własny PBI i dowód;
nie zamykać serii przy otwartych P1/P2.

Odbiór: mapa R01–R13 → testy → commity → wyniki, brak niewyjaśnionych zmian
liczników/pomiarów, zielone CI dla finalnego SHA, potwierdzony push,
czysty checkout i krótka rekomendacja. Merge do `main`, tag i publikacja
release pozostają osobną decyzją użytkownika.
Commit: `docs: close remediation verification (PBI-054)`.

### PBI-056 — Odrzucać zduplikowane indeksy staging

Pliki: `staging_review.py`, testy, format raportów/decyzji. Przed
indeksowaniem całego raportu odrzucać powtórzone ID w `proposed_objects`
i `proposed_caves` oraz wielokrotne aktualizacje `matched_measurements`
prowadzące do jednego wiersza TPN, również po fallbacku z `source_ref`.
Nie wolno wybierać ostatniego wpisu według kolejności listy. Duplikat
identyczny i sprzeczny mają blokować całą partię bez zapisu.

Odbiór: reprodukcje z [logu odkrycia](verification/PBI-056.md) są czerwone
na bazie i zielone po naprawie; kolejność wpisów nie wybiera finalnego
pomiaru ani obiektu. Poprawne staging PIG/TPN i jawne decyzje nadal
działają. Pełna bramka, mutacje zmienionych funkcji, odczyt artefaktów,
niezmienione `data/`, push i CI dla dokładnego SHA.
Commit: `fix: reject duplicate staging proposals (PBI-056)`.

### PBI-057 — Wiązać jawną propozycję z właściwym wierszem

Pliki: `staging_review.py`, testy, dokumentacja decyzji. Dla
`create_object`/`create_cave` jawny `object_id`/`cave_id` nie może
materializować propozycji innego wiersza, gdy wybrany wiersz ma już
jednoznaczne ID i tożsamość źródła. Zachować legalne jawne wskazanie
propozycji dla wiersza bez przydzielonego ID (istniejący przypadek TPN).

Odbiór: [reprodukcja](verification/PBI-057.md) z dwóch prawidłowych
wierszy staging PIG odrzuca rozjazd przed zapisem; `applied_decisions`
nie przypisuje row 1 danych `PIG:1693` z row 2. Poprawna ścieżka TPN
z jawnym ID nadal działa. Pełna bramka, mutacje zmienionych funkcji,
niezmienione `data/`, push i CI dla dokładnego SHA.
Commit: `fix: bind staging proposals to source rows (PBI-057)`.

### PBI-058 — Sprawdzić dopasowanie TPN po GLOBALID

Pliki: testy TPN, ewentualnie dokumentacja weryfikacji. Wstępna analiza
kampanii PBI-054 i pełnego pytest pod coverage wykazała, że gałąź
`by_globalid` w `_match_tpn_row` i pomocnicze
`_unique_candidate_outcome` nie są wywoływane przez 900 obecnych testów;
17 mutantów pomocnika ma `no tests`. Dodać regresję pierwszeństwa
GLOBALID nad innym numerem/nazwą/odległością oraz niejednoznacznego
GLOBALID. Nie zakładać błędu kodu bez reprodukcji.

Odbiór: oba przypadki przeszły zwykłe testy i wybrany zakres mutmut;
mutant psujący wybór po GLOBALID jest zabity. Pełna bramka, niezmienione
`data/`, push i CI dla dokładnego SHA.
Commit: `test: cover TPN GLOBALID matching (PBI-058)`.

### PBI-059 — Odrzucać niecałkowite i logiczne numery wierszy

Pliki: parser numeru wiersza w `staging_review.py`, testy i format decyzji.
Native YAML float 1.9 albo bool true nie może zostać zmieniony na row 1.
Ustalić ścisły kontrakt także dla numerów w samym raporcie przed
indeksowaniem; zachować legalne liczby całkowite. [Dowody i odbiór](verification/PBI-059.md).
Błędny typ blokuje całą partię przed zapisem/tworzeniem celu, także dry-run.
Pełna bramka i mutacje parsera. Commit:
`fix: reject invalid staging row numbers (PBI-059)`.

### PBI-060 — Walidować proweniencję propozycji i referencji staging

Pliki: `staging_review.py`, testy i kontrakt raportu/decyzji. Zgodność row ID
i ID propozycji nie zastępuje kontroli source/source_ref i referencji
PIG/TPN/NR_INWENT. Sprawdzać ich zgodność również dla row z przydzielonym
ID oraz dla matched update; zachować dodatkowe legalne/historyczne ref.
[Dowody i odbiór](verification/PBI-060.md). Każdy konflikt lub brak
wymaganej ref blokuje partię bez zapisów; poprawne fallback/unresolved
nadal działają. Pełna bramka i mutacje kontroli. Commit:
`fix: validate staging source provenance (PBI-060)`.

### PBI-061 — Chronić reprezentację liczb w DBF

Pliki: eksporter DBF, testy i opis granic formatu. Skończona liczba
nie może utracić cyfr części całkowitej w polu F/N. Wykryć przepełnienie
według width/decimal przed zastąpieniem artefaktów, z czytelnym błędem.
Zachować pełne wartości źródłowe i brak arbitralnych fizycznych limitów.
[Dowody i odbiór](verification/PBI-061.md). Testować znaki, wszystkie
pola, granice i carry po zaokrągleniu, null i legalne wartości PBI-055;
pełna bramka, readback i mutacje kontroli. Commit:
`fix: reject unrepresentable DBF numbers (PBI-061)`.
