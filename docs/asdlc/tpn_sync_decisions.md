# Decyzje i zastosowanie paczki — PBI-100

Implementacja kontraktu PBI-095 §6–8. Dotyczy snapshotów PBI-096, raportu
PBI-097, kwalifikacji PBI-098 i strażnika PBI-099. Dotychczasowy format
CSV/XLSX `apply_review.py` pozostaje osobną ścieżką. **PBI-100 nie wykonuje
pierwszej paczki produkcyjnej**. Przykłady poniżej pokazują obsługę narzędzi;
nie są decyzjami o rzeczywistych obiektach.

## Przygotowanie i rozpatrzenie

1. Sprawdź aktualny Git/PR i fetch origin. Snapshot musi być zweryfikowany
   i utrwalony w commicie wskazanym przez `base_commit` raportu. Nie zmieniaj
   snapshotu, CSV/XLSX ani polityki `tpn-sync-v1`.
2. Wygeneruj raport CLI PBI-097 z `--qualify-new --protect-best`.
   `accepted_state_commit` wskazuje origin/main; plik stanu z gałęzi nie
   zostaje przez to przyjęty. Nowe obiekty wymagają raportu PBI-098.
3. Przygotuj propozycje w roboczym YAML jako listę. Dla każdego rekordu
   actionable/requires_review wymagane są dokładnie: `change_id`, `target`,
   `preimage`, `actions`, `conflict_acknowledgements`,
   `candidate_acknowledgements`. Dwie ostatnie listy zawierają odpowiednio
   wszystkie rozpatrzone konflikty i klucze kandydatów z raportu. Nie
   rozstrzygają tożsamości automatycznie; końcowy approve ma powód człowieka.
   Wybrany cel niepowiązanego GUID wymaga pełnego preimage wybranego Obiektu,
   Jaskini i istotnych relacji. Powiązany GUID nie może zmienić Obiektu.
4. `prepare` wiąże propozycje z raportem, zapisuje nowy katalog paczki i
   tworzy decyzje pending. Bez `--proposals` przygotowuje puste akcje.

```bash
uv run --frozen --no-sync --offline python scripts/review_tpn_batch.py prepare \
  --changes build/tpn-reviews/NOWY-ID/changes.json --proposals build/proposals.yml
uv run --frozen --no-sync --offline python scripts/review_tpn_batch.py dry-run \
  --batch-id NOWY-ID --reviewer IDENTYFIKATOR-OPERATORA
```

`data/source_reviews/tpn/NOWY-ID/changes.json` zawiera niezmieniony raport
oraz `execution={format: tpn-execution-proposals, format_version: 1, proposals: [...]}`.
Ta jedna wersjonowana sekcja jest wykonywalnym uzupełnieniem formatu changes.
Cała pozostała treść jest odtwarzana ze snapshotu, bazy Git i przyjętego stanu;
nie można podmienić payloadu API, kandydatów, klasyfikacji lub podsumowania
przez przeliczenie samych hashów. Propozycje są danymi, nigdy kodem.

`decisions.yml` ma ścisły format `tpn-decisions` v1 opisany w
[przykładach](tpn_sync_examples.md#3-cztery-decyzje-w-jednej-paczce).
Każdy przypadek wymagający review ma dokładnie jedną decyzję. Nagłówek wiąże
batch, snapshot, surowe bajty kanonicznego changes, commit bazy, cały katalog,
stan i politykę. Akcje approve muszą być identyczne z hashowaną propozycją.
Reject/defer mają puste actions i niepusty powód, autora i czas UTC z Z;
pending ma autora/czas null. Nieznane pola/wersje/akcje, powtórzone klucze
YAML (także przez merge), ID i sprzeczne akcje są błędami całej partii.
JSON zapisany przez narzędzie jest poprawnym YAML; operator może edytować
plik jako YAML. Po zastosowaniu jest zapisywany kanonicznie.

Operator rozstrzyga każdy wpis, edytując wyłącznie status, audyt i reason
oraz usuwając actions przy reject/defer. Zmiana propozycji, bazy lub celu
wymaga nowego raportu/paczki i ponownego review; nie ma cichego odświeżania
ani nadpisania istniejącego changes. Przy zmianie statusu istniejącej
propozycji applier przelicza cały wynik od tej samej bazy.

## Akcje i wskazywanie celów

Wykonywalne schematy i allowlisty są w `tpn_batch_protocol.py`.
Akcje i ich obowiązkowe pola:

| action | Pola poza action |
|---|---|
| append_measurement | object_id, measurement_key, location_hash, best_action |
| update_metadata | target, field, before, after; notes dodatkowo append_text i revision_hash |
| attach_source | target, reference, evidence |
| create_cave | cave_key |
| new_object | object_key, location_hash, initial_best=first_measurement; opcjonalnie cave_key albo category/evidence |
| link_cave | dokładnie jeden z object_id/object_key oraz cave_id |

Target akcji metadata/reference: `{kind: object, id: KSW-9001}`, `{kind: cave,
id: C-9001}` albo dla notes pomiaru `{kind: measurement, id: KSW-9001,
measurement_id: m-001}`. Referencje mają dokładnie system/ref_type/external_id:
TPN/source_globalid wyłącznie na Obiekcie, NR_INWENT/inventory_number na
Jaskini. Wartość musi pochodzić ze wskazanej rewizji. Powód tożsamości jest
w evidence; attach nie dopisuje pomiaru.

Metadata dopuszcza name_local/category/notes Obiektu, name/system_name/notes
Jaskini i notes pomiaru. Nowy fragment `[TPN REVISION_HASH] append_text`
wymaga `after` równego before z dopisanym fragmentem. Jeśli identyczny cały
fragment już występuje w before na granicach wierszy, wymagane jest
`after == before`; propozycja dopisania kopii jest odrzucana. Dotyczy to
także tekstów wielowierszowych i ponownego review tej samej rewizji w nowej
paczce. Sam prefiks lub cytat wewnątrz wiersza nie oznacza równości.
Wiele różnych fragmentów jest łączonych z zachowaniem starego tekstu.
Pozostałe pola można wyczyścić tylko z clear:true i reason,
o ile dopuszcza to schemat domenowy. Nie można tym zmienić współrzędnych,
wysokości, daty, źródła, dokładności ani weryfikacji pomiaru.

Append wymaga rzeczywistej różnicy lokalizacji albo nowego źródła, znanej
daty modyfikacji oraz braku tej lokalizacji w historii TPN, również innych
GUID wcześniej scalonych w Obiekcie. Zmiana samej uwagi/daty nie tworzy
pomiaru. Payload jest wyprowadzony z rewizji: nieweryfikowany/source_record,
unknown accuracy, bez wysokości, z komentarzem o nieznanej dacie terenowej.
Stary pomiar i jego wysokość pozostają. Lokalny m-NNN jest przydzielany
raz po uwzględnieniu wszystkich wcześniejszych akcji partii.

Best_action keep wskazuje obecne measurement_id; select_new wskazuje
measurement_key nowej akcji. Obie wymagają resulting_mode i reason zgodnie
ze strażnikiem PBI-099. Wszystkie akcje jednego Obiektu są oceniane razem;
rozbieżne decyzje best blokują plan. Chronione select_new jest zabronione.
Chronione auto→manual pozostaje zablokowane: **manifest PBI-099 nadal pending**,
bez obejścia flagą i bez migracji. Jawne zaakceptowanie konkretnego manifestu
oraz kontrola jego aktualności muszą poprzedzać osobną migrację.

Nowy Obiekt nie może wskazywać istniejącego object_id jako celu. Nowy otwór
w istniejącej Jaskini używa target `{cave_id: C-9001}`, jej preimage oraz
new_object/object_key i link_cave, bez fikcyjnego preimage nowego Obiektu.
Kolejność akcji jest jawna. Wszystkie ID Obiektów, Jaskiń i pomiarów są
rezerwowane we wspólnym planie, z kontrolą nieistnienia nowych ścieżek.

Pending z akcjami może materializować tylko samodzielną automatic_proposal
PBI-098, wyłącznie create_cave/new_object. Audyt techniczny ma autora
`automatic:tpn-proposal` i deterministyczny czas fetched_at snapshotu;
nie jest audytem człowieka ani datą pomiaru. Approve przelicza go z autorem
rzeczywistej decyzji. Reject/defer usuwa wyłącznie własną, nieedytowaną
propozycję po potwierdzeniu poprzedniego wyniku; edycja człowieka blokuje zapis.

## Zapis i powtarzanie

```bash
uv run --frozen --no-sync --offline python scripts/review_tpn_batch.py apply \
  --batch-id NOWY-ID --reviewer IDENTYFIKATOR-OPERATORA
uv run --frozen --no-sync --offline python scripts/review_tpn_batch.py check \
  --batch-id NOWY-ID
```

`--repo-root` jest opcją globalną przed podkomendą, do izolowanych kopii.
`--reviewer` może wystąpić wielokrotnie: **zaufany operator uruchamiający CLI**
autoryzuje wskazane identyfikatory, porównywane z decyzjami. Sam tekst autora
w pliku nie dowodzi uprawnień ani człowieczeństwa. Lokalna ścieżka nie
buduje nowego systemu kont. CI sprawdza spójność dowodów i wyniku; uprawnienia,
review i wyłącznie ludzki merge zapewnia GitHub. Zaufana automatyzacja
z autoryzacją operatora należy dopiero do PBI-102.

Dry-run i apply używają tego samego planu, walidują pełny katalog przed/po,
łącznie z istniejącymi błędami i historią. Raport zawiera unified diff YAML,
mapy ID, before/after best oraz wiersze rzeczywistego kolektora eksportów
Best i pełne dane historii/cave używane przez SQLite/Full. Nie generuje
binariów do katalogu produkcyjnego. Plan jest ponownie liczony przed zapisem.

Transakcja blokuje równoległy applier przez flock w build. Kopiuje całe data,
sprawdza hashe i readback, synchronizuje pliki/katalogi i publikuje całość
jednym rename exchange (macOS renamex_np / Linux renameat2). Brak wsparcia
odmawia zapisu. Awaria przed punktem zamiany pozostawia starą całość;
po zamianie istnieje nowa całość katalogu, stanu i decyzji. Nie ma okna
częściowego rollbacku ani powrotu po zatwierdzonej zamianie. Awaria sprzątania
po commit point nie jest zgłaszana jako cofnięta transakcja. Nagłe odcięcie
zasilania zależy także od gwarancji systemu plików/urządzenia; testy obejmują
błędy I/O i przerwanie procesu po obu stronach zamiany. Porzucona kopia
w build po SIGKILL jest robocza, bez wpływu na stan czytany przez narzędzia.
Zewnętrzny edytor nie respektujący blokady musi zakończyć pracę przed apply;
hashe danych/config/schema/main są ponownie sprawdzane przed zamianą.

application.json i applications/DECISIONS_HASH.json utrwalają decyzje,
plan, hashe wyników całego data (poza aktywnym katalogiem review) oraz
łańcuch starszych rozstrzygnięć. Ponowienie odbudowuje plan z bazy Git,
potwierdza wynik i jest no-op. Nie stosuje starego preimage do własnego nowego
wyniku. Zmienione źródło/katalog/stan/config lub edycja wyniku daje konflikt.
Starsze archiwa pozostają, także po reject/defer. Bramka wymaga ich obecności.

Rozstrzygnięcia zachowują wejściowe preimage/catalog_hash do audytu, ale
ważność **wszystkich** końcowych statusów sprawdza wynikowe result_hashes/
result_catalog_hash całej partii. Dzięki temu approve innego rekordu nie
unieważnia od razu defer/reject. Kolejka zachowuje stare rewizje i snapshoty;
nowa rewizja nadal wymaga osobnego review. Stan na gałęzi jest kandydatem,
przyjęta baza jest zawsze czytana z origin/main po ludzkim merge.

Bramka workflow validate pobiera historię Git i wywołuje check dla paczek
zmienionych względem SHA bazy zdarzenia. Odrzuca pending, brak decyzji,
niezgodność rzeczywistego diffu/stanu, brak archiwum i stan bez paczki.
Świadome defer przechodzi z trwałą kolejką. Sprawdzenie paczki po jej własnym
merge dopuszcza dawną bazę tylko gdy main zawiera dokładnie ten sam wynik
i decyzje; samo przesunięcie main nie legalizuje starych/edytowanych decyzji.
Nie dodano workflow_dispatch ani schedule. Zakończyć po PBI-100.

## Zatwierdzony suplement D001–D026 w PR #12

Użytkownik po badaniu źródeł zatwierdził wykonanie pozostałych D26 w tym
samym PR. [Zapis zgody](verification/PBI-101-D26-resolution.json) wiąże
nieruchomą bazę Git, snapshot, pierwotny plan, noty i wynikowe hashe.
[Odbiór i przypisania](verification/PBI-101-D26.md) pokazują 23 nowe Obiekty,
21 nowych Jaskiń i 26 nowych pomiarów. Pierwotne decisions/application,
ich archiwa i tabela źródłowa D26 zachowują dokładne bajty.

Kontrola `check` po kontroli przypięć manual odtwarza ten konkretny suplement
z niezmiennej bazy i źródła. Porównuje wygenerowane pliki oraz cały wynik
data; lista hashów receipt nie może zalegalizować obcej zmiany. Nowe D26
otrzymują approve/bindings i lokalizacje zastosowane. Dla pozostałych 614
zmienia się tylko wynikowy kontekst hashów całej partii, z zachowaniem
pierwotnych decyzji, audytu i preimage. Stan gałęzi nadal jest kandydatem.
Ponowne `apply` starej paczki odrzuca późniejszy suplement. Ten ograniczony
odbiór nie dodaje obsługi ogólnych kolejnych paczek ani PBI-102–103.
