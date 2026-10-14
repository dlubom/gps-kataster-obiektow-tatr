# PBI-054: pozostałe rodziny — niezależny przegląd przed finalnym ledgerem

Stan sprawdzony 2026-10-14: lokalny HEAD
`97428eb9950b0fc8bc42b137c01d6d20525e4161`.
`git diff --stat 336e9bbfa860b96361678776f641bb925e923d5c HEAD -- src tests config schema data pyproject.toml uv.lock`
nie wykazuje zmian produktu, testów, konfiguracji, schematów, danych ani zależności.
Punkt startu: historyczna analiza PBI-054 oraz jawne limity059–067; wszystkie
wnioski o obecnych gwarancjach ponownie odniesiono do bieżącego źródła/testów.

Nowy Linux capture: `build/verification/PBI-054-linux-generation/pbi054-cloud/capture.json`,
base97428eb, fingerprint
`66f62c6c2a9ea3edd6346923085837cfc4dba7ca0ae3a4b3e83982b4f42a02b8`.
Dokładne ID/diffy poniżej sprawdzono w tej generacji. Raport NIE nadaje im statusów
końcowego replay. Historyczne Mac/PBI wyniki nie są sumowane z Linux.
Nie uruchomiono mutmut, aktywnego mutanta, replay ani pełnych testów.
Jedynie autoryzowane publiczne próby oryginalnego kodu wykonano w TemporaryDirectory.

## Nowy potwierdzony błąd P2: przepełnienie normalizacji observed_at

Źródło: `src/gps_kataster_obiektow_tatr/best_measurement.py:91–98`, szczególnie98.
Parser łapie ValueError z fromisoformat, ale astimezone(UTC) może rzucić OverflowError.
Schemat `schema/object.schema.json` dopuszcza RFC3339 date-time; sam poprawny rok
lokalny nie gwarantuje, że UTC mieści się w zakresie datetime1–9999.

| observed_at | Schema | validate_data_dir | build_sqlite_database | review write=False/True |
|---|---|---|---|---|
| `2026-05-16T13:30:00+02:00` | 0ERROR | kontrola poprawna | kontrola poprawna | obie kontrole poprawne |
| `9999-12-31T23:59:59-01:00` | 0ERROR | OverflowError | OverflowError | OverflowError w obu |
| `0001-01-01T00:00:00+01:00` | 0ERROR | OverflowError | OverflowError | OverflowError w obu |

Każda z8 awarii ma `date value out of range` i publiczny traceback kończący się
w best_measurement.py98. Review używa nawet pustego `decisions: []`: błąd występuje
w preflight istniejącego katalogu. Bajty danych i uprzednio istniejącego artefaktu
zachowane8/8. To awaria walidatora/buildera/review zamiast kontrolowanej diagnostyki,
bez wykazanej utraty danych. Zalecenie: osobny PBI P2, decyzja o polityce dla
nieprzedstawialnych chwil UTC, diagnoza ERROR i regresje publicznych granic.
Nie naprawiać w bieżącym PBI-054.

Reprodukcja:
`PYTHONDONTWRITEBYTECODE=1 .venv/bin/python /tmp/PBI054-datetime-overflow-probe.py /Users/dariuszlubomski/proj/gps-kataster-obiektow-tatr > /tmp/PBI054-datetime-overflow-probe.log`
Exit0;12public calls,8schema-valid failures,4kontrole pozytywne.
ScriptSHA `e7d4b89965b125345f6527ec9b393bb3b851895800df49fe7de5473214c431fa`.
RawstdoutSHA `61debfbade4d7023ede0b14d0e4075e88cede2a5f9f3ba5521a2c5afab623683`.

## Konkretne luki P3 — oryginalny kod poprawny

Wszystkie ID poniżej mają prefix `gps_kataster_obiektow_tatr.`.
To luki asercji rozróżniających legalne przypadki, nie nowe błędy produktu
wnioskowane z samego istnienia mutanta. Ostateczne statusy wymagają Linux ledgeru.

### Alokacja ID (PBI-072)

Dokładne ID rodziny:
- `pig_staging.x_build_pig_staging__mutmut_8/9` — błędny katalog caves;
- `pig_staging.x__max_existing_cave_number__mutmut_5/6` — błędny prefix C;
- `pig_staging.x__try_build_object_proposal__mutmut_95/96` — błędny katalog objects;
- `tpn_staging.x__seed_cave_number__mutmut_4/5` — błędny katalog caves;
- `tpn_staging.x__max_existing_cave_number__mutmut_5/6` — błędny prefix C;
- `tpn_staging.x__seed_object_numbers__mutmut_11/14` — utrata dotychczasowego maksimum
  kandydatów tego samego prefixu.

Źródła: pig_staging.py101/343/612; tpn_staging.py1119–1142/1280.
Test `tests/test_yaml_paths.py:17–27` sprawdza wspólny helper maksimum oraz rozszerzenia,
lecz nie przekazanie katalogu/prefixu przez publiczny builder. Testy TPN rozróżniają
niektóre numery1/2 i liczniki pomiarów; nie odróżniają najwyższej jaskini bez obiektu
ani maksimum przyszłych PIG propozycji niezależnie od ich kolejności.

| Publiczna fixture | Niezależna asercja odbioru |
|---|---|
| PIG: najwyższa istniejąca pusta C-0040 i standalone KSW-0042, nowy wiersz tego prefixu | nowa C-0041/KSW-0043; istniejące bajty niezmienne |
| TPN: istnieje linked niższy kandydat oraz pusta najwyższa C-0040; źródło ma inną nazwę/ref | nowa jaskinia C-0041 |
| TPN: PIG staging ma przyszłe KSW-0042/KSW-0003; brak ich w final YAML; obie kolejności | nowe KSW-0043, następne0044 w obu kolejnościach |
| Wariant z dwoma prefixami | osobne maksima i przyrost1 każdego prefixu |
| `.yml/.yaml`, granica9999 | zachowanie wszystkich legalnych ID; następny10000 |

Nie obejmować automatycznie tej samej etykietą `tpn_staging._seed_object_numbers12/24/25`
ani `_try_build_new_ids72/73`: wszystkie legalne final Obiekty są w `_load_existing_candidates`,
więc ich ID już wyznaczają maksimum. Taka zmiana odczytu dysku może być maskowana
przez kompletny scan kandydatów, a prefix bez kandydatów nie ma legalnego final obiektu.
Granica: poprawne filename/id i kompletny loader; nie dowolny malformed katalog.
Maksimum z wcześniej oglądanych przyszłych kandydatów pozostaje potrzebne.

### SQLite: notes relacji (PBI-073)

ID `build_db.x__insert_relations__mutmut_15/16/17` gubią `relation.data.get("notes")`.
Źródło poprawnego inserta: build_db.py488–507. PBI063 fixture ma relation_count0;
`tests/test_verify_project.py:63–70` ma jedyną relację z notes=None;
`scripts/verify_project.py:343–346` sprawdza from/to/type, bez notes.

Odbiór: publiczny SQLite build z niepustą notatką z polskimi znakami, wariantem null
i brakiem pola; literalne SQL oczekiwania from/to/type/notes oraz różne końce relacji
(także ich odwrócenie). YAML niezmienione. Counts/FK/WKT nie zastępują tej asercji.

### Review: cztery wymiary tożsamości referencji

Źródło: staging_review.py1944–1950. ID `_dict_identity1–8` gubią system/ref_type,
`13–16` gubią URL; `9–12` gubią external_id (kontrola rodzin już częściowo rozróżnionych
przez065). Fixture `tests/test_staging_source_content.py:215–270` różni wiele wymiarów
naraz i odróżnia continue/break/seen, lecz nie wyłącznie system, type albo URL.

Pary potwierdzone przez publiczny add_measurement + dry-run + final YAML:
base `{system: inne, ref_type: other, external_id: SHARED, url: https://example.test/one}`;
druga referencja zmienia TYLKO jedną wartość:
- system na geoportal;
- ref_type na source_row;
- URL na https://example.test/two;
- kontrolnie external_id na SECOND.

4/4: schema0ERROR, review0ERROR, końcowa walidacja0ERROR,
DUPLICATE_TPN_GLOBALID0, obie referencje zachowane, dry-run bez zmian.
Wymagana typedTPN/source_globalid `{ROW}` jest osobną trzecią referencją; walidator
typedTPN nie kompensuje utraty genericrefs. Schemat pozwala na niezależne system/type,
a uniqueItems odróżnia słowniki różniące się jedną wartością.
Odbiór: te trzy pojedyncze kolizje dla object/cave, kolejność existing/additions,
duplikat tej samej tożsamości pomiędzy nimi oraz dokładna kolejność listy finalnej.
Oryginał już zachowuje wynik; nie zmieniać zasad first-wins dla samych notes/scope.

`PYTHONDONTWRITEBYTECODE=1 .venv/bin/python /tmp/PBI054-reference-legality-probe.py /Users/dariuszlubomski/proj/gps-kataster-obiektow-tatr > /tmp/PBI054-reference-legality-probe.log`
Exit0. ScriptSHA `2dcb13676f373ef6b65a1ed961e6dd8f4a2c8e93162e6b2dee924d9d34b4df99`.
RawstdoutSHA `34b0d0d526d92bb9b2fa5ea62ce3516e801e8c72ed30cd09ca0ce2c34f838b1e`.

### Raport review: audit i liczniki

Źródło: staging_review.py1985–2023; obecna główna asercja serializacji
`tests/test_staging_review.py:1177–1200` sprawdza tylko część pól.
Wskazane dokładne ID `_result_to_json_data`:

| ID | Klucz/treść |
|---|---|
|1/2|reviewed_at|
|3/4|reviewed_by|
|5/6/7|data_dir, także str(None)|
|16/17|decisions[].decision_index|
|18/19|decisions[].action|
|20/21|decisions[].status|
|22/23|decisions[].source|
|24/25|decisions[].record_number|
|26/27|decisions[].object_id|
|28/29|decisions[].cave_id|
|36/37|issues[].severity|
|38/39|issues[].decision_index|
|40/41|issues[].description|
|42/43/44|written_paths, także str(None)|

`_applied_status_counts4/7` zmieniają początkowe liczniki;
`8/9/10/15` tracą liczbę, odejmują, ignorują wcześniejszy status lub dodają2.
Nie są ekwiwalentami ani samą redakcją opisu.

| Scenariusz | Odbiór literalnego JSON/Markdown |
|---|---|
| materialized add_measurement/link_cave | reviewed_at/by/data_dir, indeks/action/status/source/row/object/cave, rzeczywiste written_paths |
| reject/unresolved z powodem i bez powodu | skipped, indeks/source/row, powód albo warning DECISION_REASON_MISSING; bez written_paths |
| ERROR po poprawnej wcześniejszej decyzji | has_errors, dokładne issue code/severity/index, żaden zapis; audit nie udaje zakończenia partii |
| pusty oraz mieszany materialized/skipped | sumy dokładnie0/0 albo zgodne z literalną liczbą decyzji; nie tylko obecność nagłówka |

Analogiczny limit dotyczy audit/count/row JSON i rendererów PIG/TPN;065 nie było
pełnym odbiorem wszystkich raportów. PIG `_report_to_json_data1–7` zmienia
generated_at/source_path/record_count; test_pig_staging208–210 sprawdza liczniki
propozycji i pojedynczy ref, bez pełnego audit. TPN format2 ma mocniejsze asercje
rows/payload/issues/asdict i timestampu; nie przenosić braków PIG na wszystkie pola TPN.
Przed finalną klasyfikacją odróżnić brak informacji od samego escape/case opisu.

## Pozostałe rodziny: wąski powód i granica dopuszczalnego limitu

Poniższe punkty są warunkami klasyfikacji dokładnych non-killed ID z finalnego
ledgeru, a nie akceptacją dowolnego ID funkcji ani twierdzeniem o100% pokryciu.

| Rodzina | Powód i granica |
|---|---|
|059 numery/indeksy|Parser dodatniej liczby i jawny błędny update przed fallbackiem mają literalne regresje. continue→break dla elementu nie-dict może być ograniczony przez wcześniejszy _build_indexes odrzucający CAŁĄ listę. Brak całego rows w tolerowanym pustym raporcie pozostaje realną luką ścieżki; brak opisu duplikatu jest luką diagnostyki, nie globalną ekwiwalencją.|
|060 provenance/cave refs|Utrata exact typedref/source/source_ref jest semantyczna. continue→break dopiero PO ERROR zachowuje blokadę partii, ale skraca pełną diagnostykę. W gałęzi bez jaskini legalne refs=[]/brakNR_INWENT nie wymaga zapisu cave; wymaganyNR nadal maERROR. Setdefault external_refs bywa nieużywany po normalizacji/schema. Nie akceptować zaniku indeksu/code jako kosmetyki.|
|061 DBF|format(int(value)) i format(...,"d") są tym samym dziesiętnym tekstem. Ominiętyrepo_root używa tego samego modułowegoREPO_ROOT. Strictzip różni ochronę przed przyszłą nierówną deklaracją; przy obecnych20polach/20wartościach kontrola jest taka sama. Żadna utrata pola/roundingcarry/preflight nie jest tym limitem.|
|062 matching/category|Prefilter name+radius sprawia, że drugie filtrowanie nazwy w pojedynczym wskazanym wywołaniu nie może zmienić matched/unresolved:1kandydat wraca przed odczytemname,>=2dalejambiguous. Prywatne statusnewspelling niewystawione przez builder. GENEZAdefaultXXXX nie zawiera obecnych słów category i oddziela je separator. Brakopisu to limitopisowy, nie statusu/target/payload. Wielokrotne inventoryrefs są osobnym P2-068.|
|063 SQLite|Literalne populated/null/omitted + oba porządki różnych pomiarów kontrolują wiele pól. Defaultobject_ids/tags nie jest używany po loadernormalizacji. errorcount sum2/niepasującytextERROR daje0 przy publicznym buildzie, który zatrzymujeERROR przed metadanymi. Nie obejmuje inequality!=error, warningcounts ani relationnotes (073). _geom OR/AND dla jednej brakującej osi nie zmienia schema-valid measurement z4wymaganymi skończonymi osiami.|
|064 resolver/geometria|Nowe małe polygony/diagonale/holes/island/bounds/customconfig oraz oba finitecachedaxis odróżniają historyczne luki. Len3 vs>=4 ring zmienia niezamknięte/zdegenerowane SHP, zaś poprawny zamknięty trójkąt ma4punkty. config_path/shapes_dir introspekcja pozostaje osobnym limitem — lokalne argumenty nadal ładują właściwą geometrię. Nie wnioskować poprawności dla uszkodzonych SHP.|
|065 treść źródła|Nie-dict ref jest wcześniej schemaERROR, więc continue/break w append nie usuwa legalnej ref. Utrata pig_id w issue błędnych/brakujących współrzędnych to semantyczna luka diagnostyki, nie ekwiwalent. Z parsing bezreplace działa w3.12.13; nie dowolnyruntime. datetime.now(None) na malformedgenerated_at ma limit daty lokalnej/UTC i nie jest ekwiwalentne. Dalsze straty legalnych notes/dates/refs wymagają własnej oceny.|
|066 loading candidates|Directcave_id i reverse lookup zgadzają się tylko w spójnym legalnym katalogu. Normalizedobject_ids/measurements defaults nie są używane. BrakID jest schema-invalid; builder sam nie wymusza całego schema, więc stoppo takim wpisie nie jest ogólną ekwiwalencją. Missingrows/proposals w starym częściowym JSON pozostaje tolerowaną nieprzetestowaną ścieżką, bez założenia istnienia schema raportu. Kolejność lokalnej/catalogname już rozróżnia062.|
|067 validator|Jeden hyphen schemaID czyni wskazane split/rsplit równoważnymi. Attachment.id required ogranicza default<unknown>. Brakopisu prefixreason nadal limitraportu. Breakprzy non-stringattachmentpath ma wcześniej schemaERROR, ale gubi dalsządiagnozę. Schema-valid zaniki code/severity/path/url/relation-end nie są tym limitem; obecny URLcrash to069.|
|YAML/loader|AliasUTF-8/utf-8 ten samkodek. Deepconstruct kolejność generatorów może zachować wynik alias-free, ale nie klasyfikować dowolnych unsafe/unhashable tags tak samo. Usunięcie mark/sourcepath/wyjaśnienia osłabia diagnostykę; usunięcie argumentu wyjątku przy non-mapping YAML może daćTypeError zamiast obsługiwanegoYamlDataLoadError. Publiczne zachowanie negatywne nie jest ekwiwalentne. Measurementsrequiredschema ogranicza brakdefault normalizacji przed poprawnymbuildem, nie całypublicznyloader.|
|Numeric/coordinates|Unicodeescape00a0/00A0 to identycznyznak. Zmiany prefiksu ścieżki błędu są diagnostyczne, nie zmianą finiteblokady. Historyczne pominięciefinite x/y zostało rozróżnione tests/test_coordinates61–70 z nazwąosi, bool/NaN/Inf/hugeint; nie utrwalać starej luki jako bieżącej.|
|JSON/SQL serializacja|allow_nanFalse/None oba fałszywe; allow_nanTrue nie różni legalnych wcześniej zwalidowanych finitewejść. ensure_ascii/sortkeys zmienia reprezentację, zwykle zachowując decodedJSON; nie twierdzić byteequivalence artefaktu. CaseSQL nie zmienia identyfikatorów SQLite. Format/defaultstr source_observation_hash dla płaskiej JSONscalar signature: separatorcolon nie występuje, defaultstr nieużywany; nie dotyczy dowolnych Pythonobject malformedpayload.|
|Recovery|Listentries i serialized powstają razem, więc strictzip nie różni obecnej długości. restoretmpfilename tworzona/używana konsekwentnie nie zmienia rollbacku, ale nie gwarantuje zewnętrznych nazw manualnych. COMMITTED/committed i committedtmpcase mogą różnić się naLinux; nie są uniwersalną ekwiwalencją Mac. ASCII tekstmarkera nie określa jego tożsamości; marker istnieje dopiero po wszystkichreplace. GwarancjahandledIO jawnie wykluczaSIGKILL/powerloss/fsync/crashatomicity.|
|Czas/archive/best|Python3.12 rozumieZ; tzinfo/utcoffsetOR→AND nie różni datetime ze stringISO, nie niestandardowego tzinfo. Automatycznyclock/microsecond/UTCtext pozostaje luką asercji — fixedgenerated_at determinism nie obejmuje tej ścieżki. astimezoneUTC/local zachowuje sortowaną chwilę TYLKO gdy obie normalizacje są przedstawialne; nowy P2 skrajnych dat wyklucza bezwarunkową ekwiwalencję dla wszystkich schema-valid ISO.|
|Markdown/report|Case/dekoracja PROZY może być limitem, jeżeli machinecode/severity/owner/index/target/content są zachowane. Zanik field/key/count/sourcepath nie jest prozą. Escape pipe/newline wpływa na strukturę tabeli i wymaga osobnej granicy; nie obejmować wszystkichrendererów etykietącosmetic.|
|Portability/defaultencoding|encodingNone/omission równeUTF8 jedynie przy danym UTF8locale/Pythonmode. PyShp explicitUTF8→domyślneUTF8 jest ograniczone przypiętą wersjąReadera. Nie generalizować na inne hosty/locale/deps.|

## Dodatkowa korekta historycznego limitu: sygnatury maskowane przez instrumentację

`data_loader.check_data_directory__mutmut_1` False→True NIE jest ekwiwalentem
przez rzekomy jawny allow_missing w load_dataset. Obecny loader woła
`check_data_directory(data_dir)` bez keyword. Zamrożony Linux tar pokazuje
wrapperdata_loader.py120–123 z oryginalnym defaultFalse i
`kwargs={'allow_missing': allow_missing}`, następnie trampoline do mutanta.
Mutant ma defaultTrue142, ale otrzymuje jawneFalse. To limit instrumentacji,
nie źródłowej semantyki ani braktestu wymagania opt-in.

Ta sama zasada dotyczy literalnych defaultów mutowanych w sygnaturach,
m.in. pointsegment tolerance (064), apply_review_decisions write/initialize,
ReviewWriteError recovery_required, YAMLconstruct_mapping deep i numericnonfinite_paths path.
Przy finalnym non-killed sprawdzić konkretny wrapper w zamrożonej generacji;
nie akceptować sygnatur jako globalnych ekwiwalentów.

## Inventory wykonania — nie finalne wyniki

Nowa generacja ma25pustych mappingów:10export._utc_timestamp,5profile._format_duplicate_example,
10profile._format_row_numbers. Rodziny export/profile mają osobny wcześniej dostarczony raport.
Exporttimestamp jest osiągalny przez publiczny export bezgenerated_at; nie jest deadcode.
`validator.exit_code_for_issues` ma52mappedtests (bezpośrednie067_assert_issues),
PIG/TPNdate_part2/6 i resolve_prefix4. Historyczne no-tests tych trzech rodzin
nie są aktualnym ograniczeniem mappingu. Nie jest to claim killed.

Rekomendacja: PBI-054 pozostaje zablokowane przez068/069 oraz nowy P2normalizacji
daty; brak merge/tag/release. Zamknąć niezależny audit kompletności dopiero po
finalnym ledgerze243critical/10218complete i ocenieniu KAŻDEGO dokładnego non-killed
diffu według granic powyżej. Czekać na ledger follow-up; nie uruchamiać własnej kampanii.
