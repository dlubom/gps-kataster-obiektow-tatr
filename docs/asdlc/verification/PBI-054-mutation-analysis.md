# PBI-054 — analiza świeżej kampanii mutacyjnej 2026-09-30

Kod produktu: `827a2f86f215080acda3317d4542ef6ebba8d0ae` (identyczny
na checkpointach dowodów). Wszystkie identyfikatory, statusy i dokładne
diffy non-killed są w `PBI-054-mutations.json`. Bieżący checkpoint
zawiera częściowy snapshot przerwanej próby z dwoma procesami;
nie jest wynikiem całej kampanii. Grupy niżej opisują
wpływ ocalenia; **nie deklarują 100% pokrycia ani ekwiwalencji całej grupy**.
Survived to brak wykrycia zmiany przez wybrane testy, no tests to brak
zmapowanego wykonania. Brak awarii narzędzia nie zmienia tej interpretacji.

## Potwierdzone luki wymagające osobnych zadań

- [PBI-062](PBI-062.md): TPN fallback name/distance, właściwy best kandydata,
  odrębne nazwy i typ/system ref. Wszystkie 55 survivors `_match_tpn_row`
  przejrzano; 89 usuwa fallback, 90/91 rozluźniają AND. Mutant 89 zmienia
  matched KSW-0001 w new KSW-0002 w oddzielnej próbie. `_candidate_measurement`
  ma fixture o równych punktach kilku pomiarów; trzeba je rozróżnić.
- [PBI-063](PBI-063.md): SQLite, `_measurement_by_id` 8 (==→!=),
  `_insert_objects` 43–69 (powód prefixu/płaskie współrzędne),
  `_insert_measurements` 52–54 (source_ref) oraz opcjonalna proweniencja,
  metadane, załączniki i ref. Readback counts/FK/WKT nie obejmuje wszystkich
  pozostałych kolumn. To brak asercji, nie wykazany błąd oryginalnego kodu.
- [PBI-064](PBI-064.md): świeży resolver/config/public wrapper. Konstruktor
  był mapowany tylko do testu doliny i testu budowy SQLite, nie do testów
  fallbacków PL/SK korzystających z module-scoped fixture. Usunięcie kraju
  lub prefixu przetrwało; brak kluczy/typów konfiguracji także nie jest
  ekwiwalentem. No-tests publicznego wrappera to osobny limit z tej karty.
- [PBI-065](PBI-065.md): utrata notes/aliasów/sektora/morfometrii/roku/dat
  PIG/TPN i referencji review. `_append_unique_dicts` 9 traci dalsze ref
  po duplikacie, 13 nie aktualizuje seen; `_finalize_staging_record` 4
  gubi notes. PIG `_date_part` 1 (no tests) powoduje wyjątek przy braku roku.
  Osiem prób oryginał→mutant odróżnia wynik 8/8; helper i wyniki odbioru
  są opisane w głównym logu. TPN alternatywne daty/CREATED_DA należą do
  macierzy zachowania dat, nie do ekwiwalentów.

Ocena system/type ref ujawniła dodatkowo błąd oryginalnego kodu
[PBI-066](PBI-066.md); jego trzy próby obejmują builder, dry-run, CLI,
zapis YAML oraz walidację. Cztery rzeczywiste P2 (059–061/066) nadal
blokują odbiór. Mutant nie jest sam w sobie nowym błędem produktu.

## Pozostałe wpływy i granice analizy

**TPN/PIG: ładowanie, alokacja, propozycje.** W `_load_existing_candidates`,
`_load_pig_staging_candidates` i `_infer_tpn_object_category` brakuje
rozróżnionych nazw, GENEZA/ponoru/wywierzyska i sygnałów dopasowania;
macierz 062/066 zachowuje prawdziwe GLOBALID-first. `_try_build_new_ids`,
`_seed_*`, `_max_existing_*`, `_next_measurement_id` i PIG
`_try_build_object_proposal` ujawniają niepełne asercje dla ERROR/WARNING
resolvera, istniejących/rezerwowanych ID, tolerancji i pustych wartości.
Nie wszystkie odczyty maksimum są niezbędne przy załadowanych kandydatach,
ale nie uznano automatycznie za nadmiarowe jaskiń bez obiektu lub kilku
przyszłych ID. `_build_*`, `_parse_*_point`, notatki i ref tracą metadane
lub treść źródła — odpowiednie przypadki idą do 063/065. Oryginalny kod
nie wykazał dodatkowego P1/P2 w tych grupach; po naprawach ponownie
ocenić te limity, bez automatycznej akceptacji wszystkich ID.

**Review: warunki i zapisy.** Ocalenia `_apply_*`, `_bound_unresolved_payload`
i `_decision_source_record` obejmują niewywołane błędne payloady,
rozróżnienie źródeł/numerów, treść diagnostyk i nieużywane defaulty pól
wymaganych przez schemat. Nie są zbiorczo ekwiwalentami. PBI-059/060
obejmują odtworzone nielegalne selektory/proweniencję; 065 treść źródła.
`_apply_cave_references` continue→break po błędzie zachowuje blokadę całej
partii, ale skraca diagnostyki. `_write_dirty_records` 15 ocalonych
fallbacków nie zmienia publicznego przepływu, bo `_proposed_records`
uzupełnia ścieżki wszystkich nowych rekordów przed dopuszczeniem zapisu.
`_check_proposal_schema` 4 nie usuwa kontroli: walidator czyta jawne
raw_data=data, a nie zmienione data=None. `_next_object_measurement_id`
i `_refresh_auto_best_measurement` mają domyślne ścieżki ograniczone
niepustymi pomiarami i wzorem ID wymaganym przez schemat. Zmiany list/ref
muszą być oceniane względem legalnego stanu, nie tylko samej funkcji.

**SQLite.** `_insert_*` tracą pola opcjonalne i audit; pokrycie 063 ma je
odróżnić. `_geom_*` OR→AND w braku jednej współrzędnej jest defensywną
ścieżką wobec wcześniejszej walidacji. `_utc_timestamp` oraz brak mkdir
parents mają niepokryte warianty (automatyczny czas, zagnieżdżone wyjście).
`_json` sort_keys/allow_nan/ensure_ascii to mieszanina wpływów: kolejność
lub tekstowe kodowanie JSON może się zmienić mimo równej struktury;
allow_nan=True nie zmienia legalnego skończonego wejścia po walidacji,
ale nie jest równoważne dla dowolnego wywołania helpera. SQL różniące
się wyłącznie wielkością liter działa tak samo w SQLite.

**Resolver/geometria.** `_load_*` oraz ctor mają wyżej opisaną lukę 064.
Alias UTF-8 i domyślne strict=False zip nie zmieniają wyniku. Trójkątne
ringi/granice i błędne konfiguracje nie są objęte wszystkimi asercjami.
Powtórki `_bounds_contain` 2–6, `_point_is_on_segment` 6/11/12/16 oraz
30–33/37–40, `_ring_contains` 12/22/25 i `_rings_contain` 9 potwierdzają
brak asercji ukośnych krawędzi, drugiego warunku współrzędnych, brzegu,
przecięcia promienia i parzystości. Nie są ekwiwalentami; odbiór 064
obejmuje małe wielokąty/otwory i te granice. Ocalenia `resolve` 15/16,
37/38/57/58/70/71 gubią x/y; 36/56/69 gubią diagnostykę — także 064.
Pozostałe mutacje trzeba rozpatrzyć według dokładnego statusu i diffu
w rejestrze; nie wywodzić poprawności geometrii z samej liczby killed.

**Walidator, loading, YAML, numery i best.** Ocalenia komunikatów/kolejności
issue nie muszą zmieniać blokady zapisu, ale zmieniają raport. Defaulty
repo_root/schema/prefix_resolver ogranicza użycie domyślnego katalogu;
custom konfiguracja stanowi limit testów. `_has_prefix_override_reason`
może mieć kompensację wcześniejszego schema error — nie uznano przez to
wszystkich walidacji za ekwiwalentne. `_valid_http_url` ujawnia brak
rozróżnienia http/https/innego scheme/netloc. No-tests `exit_code_for_issues`
wynika także z wyłączenia subprocess CLI w mutmut; zwykła pełna bramka
sprawdza te CLI, ale ich subprocess nie aktywuje mutanta rodzica.
`numeric.parse_decimal` zmiana wielkości litery w zapisie Unicode escape
nie zmienia znaku. `best_measurement._parse_observed_at` UTC→lokalna strefa
zachowuje tę samą chwilę używaną w sortowaniu; nie twierdzimy, że zmieniony
obiekt datetime ma identyczne pole tzinfo. Pozostałe dokładne diffy i
statusy tych modułów są zachowane w rejestrze do następnej oceny.

Powtórki `coordinate_consistency_error_m` 3/4 usuwają finite guards x/y:
nie zmieniają legalnego skończonego wejścia, ale zmieniają kontrakt
bezpośredniego wywołania helpera. Testy 064 obejmą te dwa przypadki;
wcześniejszy raw preflight całej partii nadal chroni zapis.
`check_data_directory` 1 zmienia default allow_missing, podczas gdy
publiczne load_dataset przekazuje własną jawną flagę; 10/22 zmieniają
tekst błędu. `nonfinite_paths` 1 zmienia początek ścieżki diagnostycznej.
Te limity nie są nowym odtworzonym błędem publicznego przepływu ani
zbiorczą deklaracją ekwiwalencji funkcji.

**Archiwa.** `archive_metadata.resolve_archive_timestamp` ma niepełne
asercje automatycznego czasu i tekstu błędów. Python 3.12 sam rozumie Z
w fromisoformat, więc zmiany zastępowania Z nie zmieniają parsowania
legalnego Z; OR→AND kontroli tzinfo/utcoffset nie zmienia wyniku dla
obiektów datetime tworzonych z obsługiwanych stringów ISO. Nie dotyczy
to dowolnego niestandardowego tzinfo. Domyślny czas z microsecond=1
zmienia tekst timestampu i pozostaje luką asercji. R13 i dwa pełne buildy
kontrolują deterministykę przy podanym generated_at, nie tę ścieżkę.

**Recovery.** `review_writer` ocalenia obejmują YAML/JSON formatting,
encoding zależny od locale, teksty recovery, default flag oraz strict zip.
Listy entries/serialized są tworzone razem, więc zmiana strict nie
zmienia długości w tym przepływie. Nazwy restore/COMMITTED różniące się
wielkością liter mogą działać tak samo na używanym macOS, ale nie są
uniwersalnym ekwiwalentem na case-sensitive systemie. Treść markera nie
jest jego tożsamością. Granica recovery po przerwaniu procesu/zasilania
pozostaje zgodna z dokumentacją; nie potwierdzono nowego błędu tej reguły.

**Raporty, JSON, Markdown, hash.** `source_profile`, liczniki/serializatory
PIG/TPN/review i renderery mają niepełne asercje treści/kluczy, nazw plików,
separatorów, escape i formatowania. Nie uznano zmienionych liczników,
BOM/locale lub danych audytu za ekwiwalenty. `False→None` w opcjach
odczytujących truthiness, identyczne Unicode escape i aliasy UTF-8 mają
konkretne równoważne działanie w danym użyciu. No-tests obu formatters
przykładów duplikatów source_profile to rzeczywisty limit zmapowanych
testów. Te ocalenia nie dowodzą nowego błędu finalnego katalogu; ich ID
pozostają jawne przed kolejnym PBI-054. Nie wymagamy zabijania każdego
mutanta tekstu, nie wyciszamy nieekwiwalentnych zmian raportu.
