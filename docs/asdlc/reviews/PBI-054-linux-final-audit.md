# PBI-054 — końcowy niezależny audit Linux

Werdykt: **odbiór checkpointu dowodów — approve; PBI-054 pozostaje blocked**.
Nie wykazano nowego P1/P2 poza potwierdzonymi błędami oryginału068/069/074.
Nie jest to decyzja merge ani zamknięcie054. P3 są lukami regresji lub jawnymi
ograniczeniami, a nie błędami oryginału wywnioskowanymi z mutantów.

## Kampania i niezależna weryfikacja

Jedna nowa generacja Linux przez oficjalne API mutmut3.5.0, statystyki raz,
pełny controlled directreplay w16 sorted-stride shards. MacENOSPC i nieukończona
Macgeneration2 nie są częścią żadnego bilansu. Nie uruchomiono podczas tego audytu
produktu, pytest, mutmut, replay ani aktywnego mutanta; tylko odczyt, AST, hashe,
Gitshow i pobranie artefaktu CI.

- 10 218 dokładnych wygenerowanych ID w17modułach; niezależny ASTscan frozen source
  potwierdził exactgeneratedset, bez brakujących/dodatkowych ID.
- 8 472 killed /1 721 survived /25 no-tests. Wszystkie10 193 kontrolowane rekordy
  mają dokładnie jednoID i poprawne selectedfunction/count, estimate oraz walllimit.
  Selekcja odtworzona z trwałego mapping/durations; brak powielania list nie gubi informacji.
- Wszystkie16 controls: ta sama uporządkowana union1595testów, baselinepytest0,
  forcedpytest1 i zaobserwowana forcedexception. Każdy record ma exit0/1 i pytestexit
  ten sam; brak raw35/setup/crash/disk outcomes w wyniku. No-tests33 tylko empty mapping.
- Fingerprint `66f62c6c2a9ea3edd6346923085837cfc4dba7ca0ae3a4b3e83982b4f42a02b8`
  niezależnie odtworzony z124 plików i runtimeidentity. Frozen17meta/stats/sourcehash
  zgodne. Python3.12.13 i siedem pinnedpackages; fingerprint/context wszystkich shards
  są identyczne. Runtime worker jest egzekwowany przez wcześniej zreviewowane helpery.
- 105 wejść zgodnych z frozen capture/archive, aktualnymi plikami i Gitshow zarówno
  `97428eb9950b0fc8bc42b137c01d6d20525e4161`, jak i bazą produktu
  `336e9bbfa860b96361678776f641bb925e923d5c`. Siedem workflow/helper plików zgodnych
  z codecheckpoint97428eb. Produkt/testy/config/schema/data/lock nie zmienione.
- Każda z245 referencji listy critical-ids, 243unique, należy do tej generacji i ma
  killed. Referencje według karty:058=36,059=13,062=24,063=31,064=32,065=32,
  066=63,067=14. To dokładnie dostarczona lista, nie twierdzenie że obejmuje całyprogram.
- Live CI [38566650123](https://github.com/dlubom/gps-kataster-obiektow-tatr/actions/runs/38566650123)
  completed/success dla exactSHA97428eb, attempt1: generate+16replay+collect,
  18 unexpired artifacts. WszystkieCompletejob sukces; jeden warunkowy uploadgenerate
  skipped po sukcesie jest spodziewany, pozostałe kroki success.

ZIP11902129900 pobrany niezależnie przez GitHubconnector. DigestZIP
`ec49f3c43403781917cf09ce6181aae1a98a00ae3cba101584b3994895a68d6c`
zgodny z liveAPI. Jedyny innerJSON ma31 103 352bytes i SHA
`84a8df61bf0966ec6cbec0ea2567de78e9317c4eb6e148759e01cdb054060243`,
identyczny lokalnemu rawledgerowi.

Trwała kopia SHA
`405f6bf5358f9cc7c48628439ca4b665d4046f9a560b3252aa4b609a05fdc011`
różni się **tylko** campaign_state i trzema nowymi polami
raw_ci_ledger_sha256/raw_campaign_state_label/label_correction. Pozostałe27pól,
w tym wszystkie outcomes, records, controls, mapping i diffs, są dokładnie równe.
RawlabelCLI jest zachowany jako provenance; poprawiona metoda officialAPIs jest faktyczna.

## Pełny zapis non-killed

`/tmp/PBI054-final-nonkilled-review.json` obejmuje **każdy** z1746ID:
currentstatus, exactdiff+SHA, before/after, originalsourcecontext, source/functionline,
classification, assessment, wąski family/PBIref i currentselectedtestcount/przykłady.
530 rekordów korzysta z wcześniejszego uzasadnienia tylko przy exactdiffmatch;
żaden historyczny status nie jest kopiowany. 299 mają jawne reguły exactID granic,
pozostałe mają konkretne field/branch/presentation coverage assessment; nie są hurtowo
uznane za equivalent. Brak nieprzypisanych ID; brak genericresidual bez nazwanejgranic.

| Moduł | Survived | No-tests | Konkretna granica oceny |
|---|---:|---:|---|
| archive_metadata |10|0| Zparser Python3.12/fixedoffset vs defaulttime literal i hostUTC; ZIP/DBF UTCday |
| best_measurement |1|0| awarecomparison zachowuje chwilę dla przedstawialnych dat; extremes osobnyP2-074 |
| best_measurements_export |287|10| exactfields/typedrefs/fallbacks/GPX/metadata070; keys-onlyemptytemplate; finite/schema guards |
| build_db |35|0| rawpreflight/normalizedtags/paircoords; notesrelacji073; SQLcase; własny tmpbez obcejdelecji |
| coordinates |0|0| wszystkie61IDkilled w tejgeneracji |
| data_loader |14|0| requiredrawmeasurements; malformedrootdiagnostics; bounddefaultallow_missing |
| dbf_numeric |1|0| intformatdefault == d w przypiętymPythonie |
| numeric |2|0| identyczny NBSPescape; bounddefaultpath zamiast źródłowejequivalence |
| pig_staging |220|0| sourceNazwa/optionalrefs; pełnyrow/issueaudit076; concretePrefixResolvernonnullfallback; validIDsplit |
| prefix_resolver |13|0| SHPclosedringmin4; pinnedpyshpUTF8; boundtolerancedefault; publicconfigattrs limit |
| review_writer |43|0| equalentries/serializedlength; konsekwentny scratchpath; JSON/YAMLrepresentation; recoverydoclinkaudit |
| source_profile |142|15| exactJSONkeys/counts/duplicates071; BOM/locale; formatterbraktests; Markdownlayout explicitlimit |
| staging_review |459|0| rawrequiredkeys; max+1 collisionbarrier; finalpendingref/backfill; completepathmap; negativeaudits076 |
| tpn_staging |353|0| symmetrydirect/reversemembership na validcatalog; generatedstatusclosedset; futuremax072; legacyname/date/continuation077 |
| validator |117|0| validID/schemaprimarybarriers; code/severity/path i negativecollectionaudit067/076; customdependencyoverride limit |
| yaml_loader |24|0| SafeLoaderdeepFalse/no pathresolver; bounddeepdefault; unhashable/duplicatekey marks; codec/prose explicitlimit |
| yaml_paths |0|0| wszystkie19IDkilled w tejgeneracji |

Domyślne parametry instrumentacji wymagają osobnego języka: wrapper może wiązać
oryginalny default i przekazać go do mutanta. Tak oceniono allow_missing, write/init,
numericpath, tolerance, recovery_required i deep. **Nie** oznacza to równoważności
źródłowej zmiany default. Review operuje raw_data, więc obecność external_refs/object_ids
w jego targetach wynika z requiredschema, a nie z samej normalizacji loadera.

## Doprecyzowania odbioru istniejących kart070–077

- **070:** archive resolve_timestamp5/11/32: defaultgeneratedtimeprecision/Ztext i
  explicitoffset z hostem nieUTC, literalne ZIPmembertuple/DBFday/metadata.
  Pozostają exactbestexport fields, typedref/fallback i GPX/metadatacases.
- **071:** pełny JSONprofile oraz duplicateexample/rownumberformatter15 no-tests,
  BOM/locale i Markdownstructure; aktualna karta już obejmuje rodzinę, bez nowejpolityki.
- **072:** 10/12 wcześniejszych wskazanych allocatorID są teraz killed;
  `tpn_staging._seed_object_numbers11/14` survived. Dodać także18 dla candidatecounter0000
  oraz `_next_measurement_id2` dla legalnegom-000. Schemapatterny dopuszczają0.
  Nie kopiować historycznego survivorstatus pozostałych10ID.
- **073:** wszystkie trzy `_insert_relations15/16/17` survived; literalne Unicode,
  null i absentnotes oraz from/to/type/fullSQLrow. Karta już pokrywa całą rodzinę.
- **074:** faktP2 to8/8 uncaughtOverflow na schema-validtimestamps przez publiczneAPI.
  Odbiór: bezwyjątku i prawidłowybest na legalnych chwilach, bezsilentdrop/minfallback.
  ERRORrejection to wcześniejsza rekomendacja, **nie** narzucona polityka spec.
- **075:** `_dict_identity1–8/13–16` survived; externalID9–12 jako currentkilledkontrola.
  Object/cave, pojedynczy wymiar, duplicate/distinct/duplicate i dokładna kolejność.
  PIGcatalogrefurl59 to również legalna strata pola: obecność osobnego URLref nie zastępuje
  URLw tej referencji. Zachować first-wins dla samych notes/scope.
- **076:** pełne PIG/TPN/review JSON i Markdown machinefields, counts i literalne
  artifactfilenames; mixedmaterialized/skipped/ERROR; missingrejectrow; positivebeforeERROR;
  provenance/path/index/description; controlledissueconstruction zamiast TypeError;
  komplet dalszych diagnostyk po pomijanym błędnym elemencie; recoverydocpath.
  Canonicalsourceobservationhashseparator13 wymaga niezależnego literaldigest lub pozostaje
  jawnym limitem065, gdy test wylicza expected tym samym helperem. Nie nazywać code/severity,
  ownerpath ani gubienia wartości kosmetyką. Negatywne validatorwarnings/errors poza targetami
  critical067 zachować jako nazwane konkretne limity; rozszerzenie regresji w ramachauditu
  może assertować literalne code/severity/path bez zmiany regułproduktu.
- **077:** poza pierwotnymi4diffami objąć parse_date8–15 (formaty dat), sourceDate3/4
  (CREATED_DAfallback), datePart9 (generated_atZ gdy brakdatźródła), nameprecedence98/100/101
  oraz rowcontinuation290 po badpoint. Karta already names/date/continuation family.

Publiczne customschema_dir/prefix_resolver forwarding (validatoradapter20/24/25,
dataset8) pozostaje **jawnym limitem067**, poza stałą repo konfiguracjąV1. Gdy odbiór
ma gwarantować te parametryAPI, to odrębna mała regresja dependencyforwarding; nie
wnioskować bugoryginału ani automatycznie rozszerzać kart raportowych.

Ścisłe codec/escape/SQLcase lub pinnedparser equivalence mają dokładną granicę.
Serialization/layout/locale, invalidrecordsecondaryissues i privatehelperbypasses nie
są deklaracją byteequivalence ani ogólnej poprawności dla dowolnego input/runtime.

## Odtworzenie audytu i dowody

Obie komendy zakończyły się exit0:

```
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python /tmp/PBI054-final-independent-audit.py > /tmp/PBI054-final-independent-audit.log
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python /tmp/PBI054-final-nonkilled-review.py > /tmp/PBI054-final-nonkilled-review.log
```

Finalne pliki i SHA znajdują się w `/tmp/PBI054-final-independent-files.json`.
Ten dokument potwierdza checkpointdowodów; końcowa pełna bramka i exactSHA CI
nowego docscheckpointu pozostają obowiązkiem dostarczenia, bez merge/tag/release.
