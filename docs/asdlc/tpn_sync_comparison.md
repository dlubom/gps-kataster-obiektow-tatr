# Porównanie TPN — PBI-097

Implementacja [kontraktu](tpn_sync_contract.md) §2–5. Tylko odczyt katalogu,
snapshotów i przyjętego rejestru; JSON/Markdown są raportami, nie decyzjami.
PBI-098/099/100 dostarczą kandydatów, ochronę best i planowanie/stosowanie akcji.

## Uruchomienie offline

Po sprawdzeniu Git/PR i `git fetch origin`:

```bash
uv run --frozen --no-sync --offline python scripts/fetch_tpn_snapshot.py verify \
  data/sources/tpn/snapshots/pbi-096-live-20261019
uv run --frozen --no-sync --offline python scripts/compare_tpn_snapshot.py \
  --snapshot data/sources/tpn/snapshots/pbi-096-live-20261019 \
  --batch-id NOWY-ID --output-dir build/tpn-reviews/NOWY-ID
```

`--repo-root` pozwala wskazać inny checkout. Wymagany jest lokalny ref
`refs/remotes/origin/main`. CLI odczytuje `data/source_state/tpn/state.json`
**z tego commitu**, nigdy z roboczej gałęzi; raport wskazuje
`accepted_state_commit`. Brak pliku na main uruchamia bootstrap CSV.
Fetch nie jest wykonywany przez porównywarkę. Ludzki merge/autoryzację
zapewnia proces GitHub; narzędzie nie twierdzi, że dowodzi ich na podstawie
nazwy autora. Funkcja biblioteczna `compare(..., state=...)` otrzymuje
już przyjęty stan od wywołującego; jest też interfejsem fixture'ów.

Powstają `changes.json`, `report.md` i `checksums.json`. Docelowy katalog
musi być nowy, pod `build/` lub `data/source_reviews/tpn/`. Istniejący
katalog, symlink, błędny snapshot albo stan blokuje publikację. Zapis ma
readback; błąd usuwa tylko nowo utworzony katalog raportu. CLI nie tworzy
PR ani commitu, także gdy `requires_pr=true`. Przebieg no-op zapisuje
raport z `requires_pr=false`; istniejące defer pozostają w nim widoczne.

## Normalizacja i trzy strony

`tpn-sync-v1` oraz hash niezmienionego tekstu kontraktu wiążą reguły.
Nieznana wersja/hash wymaga migracji, nie cichego przeliczenia stanu.
Snapshot przechodzi pełne verify PBI-096, potem strony są czytane jako
Decimal z ponownym sprawdzeniem ich SHA. JSON do hashów używa dokładnych
liczb dziesiętnych bez wykładnika, końcowych zer i ujemnego zera. Dla
istniejących float YAML/projekcji używa najkrótszej reprezentacji round-trip.
NFC/LF/trim dotyczą tekstów źródłowych, nigdy bajtów YAML ani raw źródła.

CSV ma ścisły historyczny zestaw 23 kolumn; aliasy `CREATED_US/CREATED_DA/
LAST_EDITE/LAST_EDI_1` odpowiadają polom audytu API. Daty CSV pozostają
tekstem historycznym bez deklarowania UTC. W API zachowujemy integer ms,
pełny UTC, dzień stanu źródła, `field_observed_at=null` oraz osobny fetched_at.
Zero to epoka. Brak LAST_EDITED_DATE ma `date_basis=unavailable`; nie jest
zastępowany czasem pobrania. CSV Z pozostaje w `elevation` i raw, a API
ma `location.elevation=absent`. Nie zgadujemy datum ani nie kopiujemy Z.

Raport każdej pozycji zawiera pełne znormalizowane i surowe before/after,
obecny obiekt, Jaskinię i istotne relacje, lokalne rozbieżności pól,
WER_LOK/UWAGI, geodezyjną odległość i aktualny best. Markdown pokazuje
pola źródła w tabelach before/after i czytelny JSON danych lokalnych.
`proposed_actions=[]`, `candidates=[]`, best_after=best_before: brak
symulowanych decyzji. `measurement_needed` oznacza brak rozpoznanej
historii dla różnicy lokalizacji; nie jest zgodą na dopisanie pomiaru.

Tożsamość obiektu pochodzi wyłącznie z typed TPN/source_globalid.
`bindings` rejestru służą do sprawdzenia zgodności, nie zastępują typed
referencji. Kilka GUID jednego obiektu jest legalne. Ten sam GUID w dwóch
obiektach jest konfliktem; brak mapowania nie wybiera celu po nazwie/XY.
Historia wymaga source=TPN i poprawnego source_ref oraz GUID przyłączonego
do tego obiektu. Zgodny punkt PIG nie dowodzi importu TPN. ID, status,
notes, wysokości, wybór best i informacja o scaleniu pozostają bez zmian.
Niejednoznaczna historia daje konflikt zamiast wyboru pierwszego pomiaru.

Bootstrapowe `bootstrap_binding` jest **kandydatem dowodowym**
(`accepted=false`), nie wpisem do rejestru. Zgodność CSV/API/YAML ≤0,1 m
potwierdza wyłącznie konwersję. Późniejsze API/API porównuje dokładne XY.
Zapisany odcisk API z przyjętego rejestru może wskazać ten sam pomiar po
projekcji do float YAML; jego współrzędne i typed źródło nadal muszą się
zgadzać. Zmienione ID pomiaru samo nie uzasadnia nowego ustalenia.
Odciski bootstrapu zachowują również hash CSV i dowód tolerancji.

## Odczytywany rejestr v1

PBI-097 **nie zapisuje tego pliku**. Przyszły producent w PBI-100 musi
wytworzyć stan z decyzji i zachować wcześniejsze dowody w source_reviews.
Ścisły JSON (brak nieznanych pól i duplikatów kluczy):

- Nagłówek: `format=tpn-source-state`, `format_version=1`,
  `accepted_snapshot_hash`, `policy_hash`, `bindings`, `resolutions`, `deferred`.
- `bindings`: mapa canonical GUID → object_id.
- `resolutions`: ostatnie rozstrzygnięcie każdego `(globalid, revision_hash)`.
  Ponowne review tej samej rewizji zastępuje tylko bieżący wpis rejestru;
  stare decyzje i ich dowody pozostają w niezmiennych source_reviews.
  Ta karta nie implementuje takiego zastępowania ani kasowania historii.
- Wymagane pola rozstrzygnięcia: `globalid`, `revision_hash`, `snapshot_hash`,
  `status` (approve/reject/defer), `target` (null lub object_id/cave_id),
  `preimage`, `catalog_hash`, `policy_hash`, `reviewed_by`, `reviewed_at`,
  `reason`, `batch_id`, `changes_hash`, `applied_locations`, `result_hashes`,
  `result_catalog_hash`, `absence`.
- `preimage` i `result_hashes`: mapy względnych ścieżek domenowych → SHA-256.
  catalog_hash obejmuje wszystkie YAML katalogu, config i data/shapes;
  result_catalog_hash oznacza ten sam zakres **po** zaakceptowanych akcjach.
  Przy reject/defer wynikowe hashe mogą być równe wejściowym.
  Approve sprawdza wynikowe hashe, reject/defer wejściowe. Zmiana celu,
  pliku, konfiguracji lub katalogu wymaga ponownego review. Brak target
  nadal wiąże cały catalog_hash. Nieznana polityka blokuje odczyt.
- `applied_locations`: lista `{location_hash, measurement_id,
  source_snapshot_hash, csv_evidence}`. csv_evidence jest null dla API lub
  deskryptorem `{kind: csv_bootstrap, path, raw_sha256}` dla bootstrapu.
  Odcisk jest sprawdzany z pełnym snapshotem, a dowód CSV z jego bajtami
  i współrzędnymi; nie wystarcza sama zgodność lokalnego measurement_id.
- `absence`: null dla istniejącej cechy; dla source_missing obiekt
  `{baseline, previous_revision_hash}`. baseline to deskryptor przyjętego
  snapshotu lub CSV z raportu. Czytnik odtwarza poprzedni rekord i hash
  zdarzenia zniknięcia; pusty snapshot nie legitymizuje dowolnego hasha.
- `deferred`: lista `{globalid, revision_hash, snapshot_hash}`, dokładnie
  odpowiadająca rozstrzygnięciom defer. Trwały snapshot daje pełną dawną
  rewizję; nowa rewizja oznacza superseded, nie usunięcie dowodu.
  Zdarzenia zniknięcia są indeksowane również rewizją. Najnowsze zdarzenie
  nieobecności wybierane jest chronologicznie reviewed_at (przy remisie
  późniejszy wpis listy); wcześniejsze odroczenia zachowują własne źródło.
  Utrzymująca się nieobecność nie tworzy ponownie tego samego PR. Zmiana
  lokalnego celu unieważnia także reject wcześniej znikniętego rekordu.

`state_hash` jest SHA-256 kanonicznego stanu (null przy bootstrapie).
`changes_hash` w checksums.json to SHA-256 dokładnych bajtów changes.json,
łącznie z końcowym LF. PBI-100 ma nadal dostarczyć schemat/validator
wykonywalnych decyzji i kontrolę zgodności całej paczki; raport PBI-097
nie jest zgodą na użycie starego apply_review.py.
