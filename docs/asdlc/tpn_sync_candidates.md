# Kandydaci i kwalifikacja nowych rekordów — PBI-098

Rozszerzenie raportu [PBI-097](tpn_sync_comparison.md), według
[planu §6](tpn_sync_plan.md) i [kontraktu §7](tpn_sync_contract.md).
Tylko odczyt; nie zapisuje YAML, ID, powiązań, best ani decyzji.

## CLI i polityka

```bash
uv run --frozen --no-sync --offline python scripts/fetch_tpn_snapshot.py verify \
  data/sources/tpn/snapshots/pbi-096-live-20261019
uv run --frozen --no-sync --offline python scripts/compare_tpn_snapshot.py \
  --snapshot data/sources/tpn/snapshots/pbi-096-live-20261019 \
  --batch-id NOWY-ID --qualify-new \
  --name-similarity-threshold 0.90 --radius-m 100 \
  --output-dir build/tpn-reviews/NOWY-ID
```

Bez `--qualify-new` pozostaje raport PBI-097. Z flagą raport zawiera
`candidate_policy` z wersją/hash, `candidate_source_inputs`,
`candidate_comparison_hash`, `candidate_catalog_gaps`, `duplicate_state_hash`,
`duplicate_resolution_checks` i `qualification_summary`. Każdy bieżący
niepowiązany GUID otrzymuje `candidates` i `new_record_qualification`.
Markdown pokazuje te same dowody przy rekordzie. Obecne powiązane GUID
pozostają w dotychczasowym porównaniu; detektor nie wybiera dla nich innego celu.

Polityka `tpn-candidates-v1`:

- NFC, casefold, zwinięcie odstępów. Pozostają znaki diakrytyczne,
  interpunkcja, liczby, I/II/III, górny/dolny i wszystkie inne oznaczenia.
- Dokładna zgodność niepustych nazw lub typed NR_INWENT/inventory_number
  oraz SYSTEM generuje kandydata niezależnie od odległości. Sprawdzane są
  również SYSTEM ↔ nazwa jaskini/obiektu/źródła.
- Podobieństwo: `1 - Levenshtein(a,b) / max(len(a),len(b))`, domyślnie
  **≥0,90**, próg jawny w `(0,1]`. To dodatkowy sygnał do review, nie tożsamość.
  Zgodność fuzzy pomiędzy I i II nie usuwa rozróżnienia nazw w dowodzie.
- Odległość geodezyjna WGS84 **≤max(radius_m, znane dokładności obu
  punktów)**; radius_m musi być skończone i **≥100 m**. Null pozostaje
  nieznanym parametrem, nie staje się zerem. Granice są włączne.

## Zakres dowodów

Indeks obejmuje osobno wszystkie Obiekty i Jaskinie (również bez otworów),
nazwy lokalne/jaskiń/systemów i typed numery inwentarzowe. Pozycje pochodzą
z **każdego pomiaru**, bez filtrowania source/status/best. Dowód zawiera
ID, status, `is_best`, XY, dokładność, odległość i użyty promień.
Istniejąca historia `source=TPN/source_ref=TPN:<GUID>` także blokuje
nową propozycję przy brakującej typed referencji, bez przyłączania źródła.

Nazwy NAZWA/OTWÓR, NR_INWENT i SYSTEM oraz XY są sprawdzane w całym
bieżącym snapshocie, bazie porównania i snapshotach dowodowych przyjętego
rejestru. Historyczny CSV TPN jest zachowany w indeksie również po
przejściu na bazę accepted_snapshot. Wcześniej widziany GUID nie staje
się nowy po zniknięciu i powrocie. Wszystkie nowe rekordy paczki są
sprawdzane między sobą, symetrycznie i niezależnie od kolejności wejścia.

Dodatkowe nazwy źródłowe pochodzą z historycznego CSV PIG: Nazwa i Inne
nazwy oraz Nr inw. Pełna wartość aliasów pozostaje dowodem; części listy
oddzielone przecinkiem/średnikiem również są sygnałami. ID PIG jest opisem
źródła, nie kluczem otworu. Brak tego pliku blokuje auto przez
`comparison_complete=false`; błędny schemat/wiersz blokuje raport.

Każdy kandydat ma `key`, opis celu, `candidate_basis`, `evidence` i wynik
sprawdzenia pamięci. Wspólny numer/nazwa/XY nie przypisuje obiektu do jaskini.

## Bramka §6

`automatic_proposal` oznacza wyłącznie kwalifikację do przyszłej propozycji
w PR. `target=null`, `proposed_actions=[]`; nie nadaje ID i nie tworzy YAML.
Wszystkie warunki muszą być true i lista kandydatów pusta:

| Warunek | Dowód / blokada |
|---|---|
| new_unique_guid | Nowy względem bazy i historii CSV/snapshotów dowodowych, poprawny/unikalny po verify, bez typed celu. |
| geometry | Punkt jest w granicach PL/SK; zakres/skończoność XY sprawdza snapshot verify. |
| category | Jawna GENEZA: jaskinia/sztolnia/ponor/wywierzysko; brak, inna lub mieszana wartość oraz sprzeczny jawny rodzaj w NAZWA daje review. |
| region | Dokładnie jedna pasująca dolina i prefix. Fallback PL/SK, brak doliny i nakładanie dolin blokują auto. |
| measurement | Znane LAST_EDITED_DATE; bez zastąpienia datą pobrania/utworzenia. |
| name | Niepusta NAZWA, bez roboczego fallbacku. |
| standalone | Brak SYSTEM i osobnego opisu OTWÓR; ich znaczenie wymaga człowieka. |
| comparison_complete | Zweryfikowany kompletny snapshot, dostępny historyczny indeks nazw i brak luk nazw/pomiarów istniejących Obiektów. |
| source_review_clear | Brak lokalnego konfliktu, nieaktualnej pamięci i niepustego kontekstu WER_LOK/UWAGI/OPIS/TATER. |

Nie interpretujemy automatycznie treści kontekstu źródłowego: niepusty
kontekst kieruje do człowieka. To konserwatywna implementacja „niepewność
→ review”; może zatrzymać także poprawny, niesporny rekord. Nie dopisuje
fikcyjnej nazwy, kategorii, dokładności ani przypisania regionu.

`checks` pokazuje wszystkie warunki. `blocks` ma osobny wpis z powodem
i dowodem dla każdego niespełnionego warunku oraz każdej kolizji.
Dowód historycznego GUID pozostaje widoczny także przy nowej nazwie/XY.

## Pamiętane rozstrzygnięcia — wyłącznie czytnik

CLI czyta `data/source_state/tpn/duplicates.json` wyłącznie z tego samego
commitu `refs/remotes/origin/main`, co rejestr PBI-097. Brak pliku oznacza
pustą pamięć. Plik na gałęzi/PR nie jest przyjętą decyzją. Ta karta nie
produkuje pliku, nie stosuje decyzji ani nie przesuwa bazy.

Ścisły JSON: `format=tpn-duplicate-state`, `format_version=1`,
`resolutions` jako lista. Każdy wpis ma dokładnie:

- `pair`: dwa różne posortowane klucze stron z raportu;
- `outcome`: same_opening, different_openings_same_cave, different_objects,
  unresolved; bez automatycznych skutków domenowych;
- `basis`: dokładne `current_basis` z raportu: sides, policy, catalog_hash,
  source_set_hash; `basis_hash` to kanoniczny SHA-256 tego obiektu;
- `evidence`: niepusty opis dowodu, `reviewed_by` i `reviewed_at` (UTC).

Strony wiążą nazwy, referencje, wszystkie lokalizacje, rewizje, cele
oraz preimage. Catalog_hash wiąże także konfigurację/relacje; hash całego
indeksu wiąże konkurentów z paczki i źródeł. Nowy trzeci kandydat,
zmieniona historia, nazwa/XY/referencja/cel lub polityka unieważnia pamięć.
Kontrola jest celowo konserwatywna: zmiana niezwiązanej części indeksu
również wymaga ponownego review. Brak strony też oznacza stale.

Każda pamiętana para ma wynik valid/stale w `duplicate_resolution_checks`,
również gdy dawny sygnał kolizji zniknął. Stale daje unresolved i ponowne
review. Ważne rozstrzygnięcie pokazuje wynik człowieka, ale nie usuwa
sygnału z bramki §6 i nie uruchamia przypisania lub merge.

[Dowody odbioru](verification/PBI-098.md). Następny zakres po osobnym
zleceniu: PBI-099. PBI-100 dopiero dostarczy producenta/stosowanie decyzji.

PBI-099: `--protect-best` można łączyć z `--qualify-new`; dołącza
[audyt ochrony całego katalogu](tpn_sync_best_protection.md), bez zmiany
kwalifikacji i bez stosowania decyzji.
