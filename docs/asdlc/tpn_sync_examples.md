# TPN: formaty i przykłady kontraktu

Załącznik normatywny do [kontraktu PBI-095](tpn_sync_contract.md).
Manifest PBI-096 obsługuje `fetch_tpn_snapshot.py`; raport changes i odczyt
stanu dostarcza PBI-097 ([CLI/format](tpn_sync_comparison.md)). PBI-098
uzupełnia candidates, a PBI-099 dołącza opcjonalny [audyt best](tpn_sync_best_protection.md).
Te narzędzia porównawcze nie stosują decyzji i zachowują best.
PBI-100 dostarcza [wykonywalny format, CLI i bramkę](tpn_sync_decisions.md),
w tym hashowane execution/proposals. Poniższe przykłady są kontraktem
syntetycznym; wykonywalne uzupełnienia opisuje instrukcja PBI-100.
Nie uruchamiać tych przykładów przez dotychczasowy `apply_review.py`.
Przykładowe identyfikatory i wartości są syntetyczne. Wielkie symbole
`SNAPSHOT`, `REV_*`, `LOC_*`, `HASH_*` zastępują rzeczywiste 64-znakowe
SHA-256 (małe hex); w prawdziwym pliku symbole są niedozwolone.

## 1. Wspólne reguły formatów

Każdy dokument ma `format` i całkowite `format_version: 1`. Nieznana
wersja, nieznane pole wykonawcze, brak pola wymaganego, zły typ, powtórzony
klucz lub ID jest błędem. Daty to tekst ISO UTC z Z. UUID są kanoniczne
według kontraktu, ścieżki względne do repo, bez wyjścia poza repo.
Surowe atrybuty API pozostają danymi; nie są polami wykonawczymi.

Manifest wymaga wszystkich pól poniżej. `files` jest niepustą listą
unikalnych ścieżek/hashów/ról; `pages` ma kolejne offsety, liczby i ID.
Listy ID/stron mogą być odwołaniami do hashowanych plików. Dla poprawnego
snapshotu count przed/po, liczba unikalnych ID oraz suma stron są równe.
`complete: true` jest wynikiem kontroli, nie opcją wymuszającą akceptację.

```yaml
format: tpn-source-manifest
format_version: 1
snapshot_id: example-2026-10
snapshot_hash: SNAPSHOT
policy_version: tpn-sync-v1
policy_hash: HASH_POLICY
source:
  endpoint: https://gis.tpn.pl/server/rest/services/Topografia___wektor_MIL1/MapServer/6
  layer_id: 6
  layer_name: Jaskinie
  geometry_type: esriGeometryPoint
  schema_hash: HASH_SCHEMA
query:
  where: '1=1'
  outFields: '*'
  returnGeometry: true
  outSR: 4326
  orderByFields: OBJECTID
  resultOffset: 0
  resultRecordCount: 2000
  f: json
started_at: '2026-10-19T12:00:00Z'
fetched_at: '2026-10-19T12:00:01Z'
checks:
  count_before: 4
  count_after: 4
  ids_before: [1, 2, 3, 4]
  ids_after: [1, 2, 3, 4]
  feature_count: 4
  unique_globalid_count: 4
  complete: true
  consistency_limit: count_and_ids_not_transactional_attributes
pages:
  - path: data/sources/tpn/snapshots/example-2026-10/page-0.json
    result_offset: 0
    count: 4
    object_ids: [1, 2, 3, 4]
    exceeded_transfer_limit: false
files:
  - {path: data/sources/tpn/snapshots/example-2026-10/page-0.json, role: page, raw_sha256: HASH_PAGE}
  - {path: data/sources/tpn/snapshots/example-2026-10/layer.json, role: schema, raw_sha256: HASH_SCHEMA}
  - {path: data/sources/tpn/snapshots/example-2026-10/count-before.json, role: count_before, raw_sha256: HASH_COUNT_BEFORE}
  - {path: data/sources/tpn/snapshots/example-2026-10/count-after.json, role: count_after, raw_sha256: HASH_COUNT_AFTER}
  - {path: data/sources/tpn/snapshots/example-2026-10/ids-before.json, role: ids_before, raw_sha256: HASH_IDS_BEFORE}
  - {path: data/sources/tpn/snapshots/example-2026-10/ids-after.json, role: ids_after, raw_sha256: HASH_IDS_AFTER}
```

`snapshot_hash` obejmuje również kanoniczny manifest bez własnego pola
snapshot_hash. `files` nie zawiera samego manifestu (unikamy cyklu).
Ścieżki wszystkich kontroli odnoszą się do rzeczywistych odpowiedzi API;
PBI-096 sprawdza ich zgodność z podsumowaniem `checks`.
Wykonywalny manifest dodaje `layer-after.json` z rolą `schema_after`
oraz `policy.md` z rolą `policy`; policy_hash jest SHA-256 dokładnego
tekstu polityki. Walidator odtwarza manifest z plików, odrzucając także
nieznane pola i fałszywe podsumowanie po ponownym przeliczeniu hashów.
[Próba live i dokładna serializacja](verification/PBI-096.md).

## 2. Lista zmian i stan źródła

`changes.json` ma format `tpn-changes`, `format_version`, `batch_id`,
`snapshot_hash`, `policy_version`, `policy_hash`, `base_commit`,
`catalog_hash`, `state_hash`, `baseline` i listę `records`.
`baseline` wskazuje poprzedni przyjęty snapshot lub bootstrap
`{kind: csv_bootstrap, path, raw_sha256}`. `changes_hash` jest hashem
całego pliku changes.json, przechowywanym poza nim w decisions.yml.

Każdy records wymaga unikalnego `change_id`, `globalid`, `revision_hash`,
`location_hash` (null tylko dla source_missing), `classification`,
`source_before`, `source_after`, `target`, `preimage`, `candidates`,
`conflicts`, `proposal_origin`, `proposed_actions`, `best_before` i
`best_after`. before/after zawierają pełny rekord lub odwołanie do
niezmiennego pliku wraz z hashem i GLOBALID; brak rekordu to null.
target jest konkretnym obiektem/jaskinią lub null dla nowego/nieustalonego.
Przy source_missing revision_hash identyfikuje zdarzenie nieobecności
(poprzednia rewizja + nowy snapshot + policy), nie zmyślony rekord źródła.

Klasyfikacje: `unchanged`, `technical_only`, `new_guid`, `unmapped_guid`,
`metadata_changed`, `location_changed`, `local_conflict`, `source_missing`.
Jeden rekord może mieć kilka klasyfikacji; źródłowa i lokalna zmiana są
pokazywane oddzielnie. `technical_only`/`unchanged` bez zaległości są
informacją raportu i nie wymagają sztucznej decyzji ani PR.

Przykładowa pozycja zmiany istniejącego obiektu (pozostałe pola nagłówka
są wspólne dla całej paczki):

```yaml
change_id: existing-2
globalid: 22222222-2222-4222-8222-222222222222
revision_hash: REV_2
location_hash: LOC_2
classification: [location_changed]
source_before: {snapshot_hash: OLD_SNAPSHOT, globalid: 22222222-2222-4222-8222-222222222222}
source_after: {snapshot_hash: SNAPSHOT, globalid: 22222222-2222-4222-8222-222222222222}
target: {object_id: KSW-9002, cave_id: C-9002}
preimage:
  data/objects/KSW/KSW-9002.yml: HASH_OBJECT_2
  data/caves/C-9002.yml: HASH_CAVE_2
candidates: []
conflicts: []
proposal_origin: automatic
proposed_actions:
  - action: append_measurement
    object_id: KSW-9002
    measurement_key: new-location-2
    location_hash: LOC_2
best_before: {mode: auto, measurement_id: m-001}
best_after: {mode: manual, measurement_id: m-001, reason: Zachowanie dotychczasowego best po dopisaniu TPN.}
```

Payload pomiaru jest deterministycznie wyprowadzony ze wskazanej rewizji
zgodnie z mapowaniem kontraktu i widoczny w pełnym raporcie before/after.
Decyzja nie może podać innych współrzędnych pod tym samym location_hash.
`measurement_key` to lokalny symbol planowania partii; rzeczywiste m-NNN
przydzielane jest po zebraniu wszystkich akcji. Raport zawiera tę mapę.

Stan `tpn-source-state` v1 wymaga `accepted_snapshot_hash`, `policy_hash`,
`bindings` (GLOBALID → object_id), `resolutions` i `deferred`.
Każde rozstrzygnięcie zawiera `(globalid, revision_hash)`, status,
cel/preimage/catalog_hash, podstawę polityki, autora/czas/powód, batch,
changes_hash, zastosowane location_hash → measurement_id oraz wynikowe
hashe plików. Odciski starej historii z bootstrapu mają dowód CSV/YAML.
deferred wskazuje trwałe źródło starej rewizji i rozstrzygnięcia duplikatów.
Nowa rewizja deferred tworzy nowy przypadek, zachowując poprzedni zapis
jako zastąpiony; nie przenosi bez sprawdzenia wcześniejszej zgody.
accepted_snapshot_hash na gałęzi jest kandydatem aż do ludzkiego merge.

## 3. Cztery decyzje w jednej paczce

Format `tpn-decisions` v1 wymaga wszystkich pól nagłówka poniżej oraz
listy `decisions`. Każdy wpis ma change_id, globalid, revision_hash,
target, preimage, status, reason i actions. Nagłówek wiąże wszystkie wpisy
ze snapshotem, changes, katalogiem, stanem i polityką; wartości muszą
odpowiadać raportowi. Przed/po konkretnych akcji również jest związane
przez changes_hash; operator zatwierdza widoczny skutek, nie dowolne
działanie o tej samej nazwie. reviewed_by/at identyfikują człowieka dla
końcowych statusów; przy pending są null. Jego uprawnienia sprawdza
zaufany proces, a nie sam napis w pliku.

Przykład: nowy samodzielny obiekt zaakceptowany po automatycznej propozycji,
istniejący z zachowaniem best, konflikt nowego GUID odroczony, błędna
rewizja odrzucona. Symbole i ID nie opisują rzeczywistych decyzji katalogu.

```yaml
format: tpn-decisions
format_version: 1
batch_id: example-2026-10
snapshot_hash: SNAPSHOT
changes_hash: HASH_CHANGES
base_commit: BASE_COMMIT
catalog_hash: HASH_CATALOG
state_hash: HASH_STATE
policy_version: tpn-sync-v1
policy_hash: HASH_POLICY
decisions:
  - change_id: new-1
    globalid: 11111111-1111-4111-8111-111111111111
    revision_hash: REV_1
    target: null
    preimage: {}
    status: approve
    reviewed_by: operator-example
    reviewed_at: '2026-10-19T13:00:00Z'
    reason: Potwierdzony samodzielny obiekt; brak kandydatów duplikatu.
    actions:
      - {action: create_cave, cave_key: new-cave-1}
      - action: new_object
        object_key: new-object-1
        cave_key: new-cave-1
        location_hash: LOC_1
        initial_best: first_measurement
  - change_id: existing-2
    globalid: 22222222-2222-4222-8222-222222222222
    revision_hash: REV_2
    target: {object_id: KSW-9002, cave_id: C-9002}
    preimage:
      data/objects/KSW/KSW-9002.yml: HASH_OBJECT_2
      data/caves/C-9002.yml: HASH_CAVE_2
    status: approve
    reviewed_by: operator-example
    reviewed_at: '2026-10-19T13:00:00Z'
    reason: Zachować nową lokalizację źródła w historii, bez zmiany punktu eksportu.
    actions:
      - action: append_measurement
        object_id: KSW-9002
        measurement_key: new-location-2
        location_hash: LOC_2
        best_action:
          action: keep
          measurement_id: m-001
          resulting_mode: manual
          reason: Zachowanie dotychczasowego best po dopisaniu TPN.
  - change_id: conflict-3
    globalid: 33333333-3333-4333-8333-333333333333
    revision_hash: REV_3
    target: null
    preimage: {}
    status: defer
    reviewed_by: operator-example
    reviewed_at: '2026-10-19T13:00:00Z'
    reason: Dwa pobliskie otwory o tej samej nazwie; potrzebny plan z oznaczeniami otworów.
    actions: []
  - change_id: rejected-4
    globalid: 44444444-4444-4444-8444-444444444444
    revision_hash: REV_4
    target: null
    preimage: {}
    status: reject
    reviewed_by: operator-example
    reviewed_at: '2026-10-19T13:00:00Z'
    reason: Treść tej rewizji dotyczy innego punktu; nie odrzuca to przyszłych rewizji GUID.
    actions: []
```

Puste preimage przy braku wybranego celu nie znosi kontroli kandydatów:
wiążą ją catalog_hash i pełny raport z kandydatami/preimage w changes.
Po rozstrzygnięciu same_opening należy przeliczyć raport, wskazać cel
i jego preimage; `attach_source` nie dopisuje pomiaru automatycznie.
Przykład osobnego wyboru nowego best dla niechronionego obiektu:

```yaml
best_action:
  action: select_new
  measurement_key: new-location-2
  resulting_mode: manual
  reason: Jawnie przyjęta lokalizacja TPN po porównaniu dowodów; data edycji nie dowodzi daty pomiaru.
```

approve może mieć actions puste wyłącznie jako świadome pozostawienie
bieżącego katalogu lub potwierdzenie powiązania bootstrapu, z powodem.
Istniejący obiekt zawsze wymaga jawnego człowieka. Dla nowych propozycji
bot zapisuje pending; człowiek rozstrzyga każdy wpis przed merge.
`link_cave` wymaga dokładnie jednego z object_id/object_key oraz istniejącego
cave_id. object_id oznacza istniejący obiekt: preimage obejmuje jego plik,
docelową Jaskinię i starą Jaskinię, jeśli była przypisana. object_key oznacza
obiekt tworzony wcześniej w tej samej paczce: preimage obejmuje wyłącznie
istniejącą docelową Jaskinię, a po przydziale ID sprawdzamy nieistnienie
nowego pliku obiektu. Nie wymagamy fikcyjnej starej Jaskini ani jej hasha.
Takie powiązanie zawsze zatwierdza człowiek. Przykładowa sekwencja akcji
nowego otworu w istniejącej Jaskini (nagłówek decyzji wskazuje
`target: {cave_id: C-9002}` i preimage pliku `data/caves/C-9002.yml`):

```yaml
actions:
  - action: new_object
    object_key: new-opening-5
    location_hash: LOC_5
    initial_best: first_measurement
  - action: link_cave
    object_key: new-opening-5
    cave_id: C-9002
```

`update_metadata` wymaga celu, ścieżki dozwolonego pola, before,
after, a przy kasowaniu `clear: true` i reason; notes używają append_text
z revision_hash zamiast zastąpienia całego tekstu. `attach_source` wymaga
celu, typed referencji i dowodu tożsamości; NR_INWENT tylko na Jaskini.

## 4. Scenariusze odbioru kontraktu

| Wejście / decyzja | Oczekiwany wynik |
|---|---|
| Ta sama paczka zastosowana drugi raz, wynikowe hashe zgodne | No-op; brak drugiego pomiaru, referencji i notatki. |
| Tylko LAST_EDITED_DATE albo FIELD zmienione | Informacja źródłowa, brak nowego pomiaru i daty w starej historii. |
| Nowe XY, LAST_EDITED_DATE znane, keep | Nowy nieweryfikowany pomiar z komentarzem o dacie; stare XY i best zachowane. |
| Nowe XY, LAST_EDITED_DATE null | Snapshot zachowuje null; dopisanie pomiaru odroczone. |
| Brak Z, stary pomiar ma wysokość | Stara wysokość zachowana; nowy pomiar bez wysokości. |
| WERYF 0 → null | Widoczna rewizja źródła; żadnej zmiany lokalnego statusu. |
| Nowy GUID istniejącego otworu, attach_source | Dopisanie referencji; pomiar wymaga osobnej decyzji i oceny historii. |
| Kilka GUID już scalonych w jednym obiekcie | Zachowanie obiektu i historii; brak odtwarzania dawnych ID. |
| GNSS source inne, auto, select_new | Odrzucenie akcji w ścieżce TPN; także dla GNSS w historii. |
| Dalekie identyczne nazwy lub bliski niewybrany pomiar | Kandydat do review; brak automatycznego utworzenia. |
| Nowy obiekt z istniejącym NR_INWENT/SYSTEM | Ręczne rozstrzygnięcie otworu i Jaskini. |
| Defer i merge pozostałej paczki | Trwała kolejka z dowodami; kolejny cykl nadal widzi odroczenie. |
| Reject i nowa rewizja / zmiana lokalnego celu | Ponowne review; brak trwałego odrzucenia GUID. |
| Zmiana preimage albo błąd ostatniej decyzji | Blokada całego apply przed zapisem. |
| Niepełne API / nieznane pole | Brak poprawnego snapshotu/bazy i brak usuwania danych. |
| Rekord znika z pełnego API | source_missing do review; katalog i historia pozostają. |
| Otwarty PR podczas kolejnego cyklu | Raport zaległości; brak drugiego PR i nadpisania decyzji. |

PBI-095 weryfikuje kompletność i spójność opisu oraz składnię przykładów.
PBI-096–100 dostarczają wykonywalne kontrole i testy tych zachowań.
Odbiór rzeczywistej paczki należy do PBI-101, a otwarty PR/cykl do PBI-102–103.
