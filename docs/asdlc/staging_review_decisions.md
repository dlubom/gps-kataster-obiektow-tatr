# Operator review staging - format decyzji

PBI-015 wprowadza jawny plik decyzji operatora. Importery PIG/TPN nadal tworza
tylko staging w `build/staging/*`; finalne YAML pod `data/` powstaje dopiero po
uruchomieniu:

```bash
uv run python scripts/importers/apply_review.py --decisions path/to/decisions.yml
```

Minimalny plik:

```yaml
reviewed_at: "2026-05-16T10:00:00Z"
reviewed_by: dl
decisions:
  - action: create_cave
    source: PIG
    record_number: 1
  - action: create_object
    source: PIG
    record_number: 1
  - action: add_measurement
    source: TPN
    record_number: 1
  - action: link_cave
    object_id: KSW-0001
    cave_id: C-0001
  - action: reject
    source: TPN
    record_number: 2
    reason: "Duplicated source row."
  - action: unresolved
    source: TPN
    record_number: 3
    reason: "Needs field review."
```

## Akcje

| `action` | Znaczenie | Efekt na finalne YAML |
|---|---|---|
| `create_cave` | Nowa `Jaskinia` ze staging PIG/TPN. | Tworzy `data/caves/{CAVE-ID}.yml`. |
| `create_object` | Nowy `Obiekt` ze staging PIG/TPN. | Tworzy `data/objects/{PREFIX}/{OBJECT-ID}.yml`. |
| `add_measurement` | Nowy `Pomiar` dla istniejacego albo wczesniej utworzonego `Obiektu`. | Dopisuje pomiar i referencje TPN, a dla `best_measurement.mode: auto` przelicza wskazanie. |
| `link_cave` | Powiazanie obiektu z jaskinia. | Ustawia `Obiekt.cave_id` i dopisuje obiekt do `Jaskinia.object_ids`. |
| `reject` | Rekord importu odrzucony. | Nie zapisuje finalnego YAML, ale trafia do raportu review. |
| `unresolved` | Rekord zostaje nierozstrzygniety. | Nie zapisuje finalnego YAML, ale trafia do raportu review. |

`source` jest wymagane dla akcji opartych o staging i przyjmuje `PIG` albo
`TPN`. `record_number` wskazuje numer wiersza z raportu staging. `link_cave`
dziala na finalnych ID i nie wymaga `source`.

## Bezpieczenstwo

Plik decyzji jest parsowany bez cichego nadpisywania kluczy. Duplikat
`decisions`, `action`, `object_id` lub dowolnego innego klucza na każdym
poziomie daje `ReviewDecisionError` ze ścieżką, kluczem i linią/kolumną
obu wystąpień; CLI zwraca 1 przed wykonaniem decyzji i zapisem raportu.
Zwykłe aliasy i merge keys o rozłącznych kluczach działają. Kolizje po
merge, także jawne nadpisanie odziedziczonej wartości oraz powtórzony `<<`,
są odrzucane również przy identycznej wartości. Reguła obejmuje także
istniejące finalne rekordy; ich wadliwy YAML daje `FINAL_DATA_INVALID`
w raporcie i diagnostykę CLI bez zapisu finalnych danych.

`apply_review.py` waliduje najpierw cały istniejący zbiór: obiekty, jaskinie
i relacje, z oryginalnymi ścieżkami i surowymi polami YAML. Błędy obecnych
reguł schematu lub domeny dają `FINAL_DATA_INVALID` przed wykonaniem decyzji.
Propozycje nowych obiektów/jaskiń przechodzą dodatkowo kontrolę schematu,
zanim następna decyzja użyje ich pól. `add_measurement` wymaga istniejącego
celu obiektowego i, jeśli wskazano `target_cave_id`, istniejącej jaskini.
Wybrane `object_external_refs` i `cave_external_refs` muszą być listami map;
błędnego kształtu ani elementów nie pomijamy przed walidacją. Błąd typu
zagnieżdżonego pola referencji daje diagnostykę schematu zamiast wyjątku API.

Po wszystkich decyzjach `validate_dataset(...)` ocenia pełny przyszły
zbiór w pamięci, z niezmienionymi relacjami oraz wszystkimi zmienionymi
i niezmienionymi rekordami. Dopiero wtedy rozpoczyna się zapis. Błędy tego
stanu dają `REVIEW_DATA_INVALID`; opis zachowuje kod reguły walidatora,
ścieżkę i szczegóły. Błąd dowolnej decyzji, także ostatniej, lub walidacji
blokuje całą partię: `has_errors=true`, `written_paths=[]`, niezmienione
bajty i lista finalnych plików. `materialized` w liście decyzji oznacza
zastosowanie w pamięci; potwierdzeniem zapisu jest wyłącznie `written_paths`.

`--dry-run` wykonuje te same walidacje i zwraca taką samą ocenę błędów,
bez zapisu finalnych danych. Ostrzeżenia walidatora nie blokują review;
raport review przenosi błędy preflight, a pełny wykaz ostrzeżeń jest dostępny
przez `scripts/validate.py`. Istniejące pliki `.yaml` zachowują swoje ścieżki
przy aktualizacji. Zabezpieczenie dotyczy błędów decyzji i walidacji przed
zapisem; nie zapewnia rollbacku po awarii procesu, dysku ani operacji I/O.
Używa aktualnych reguł walidatora; nowe reguły R5–R7 są w PBI-084–086.
Obraz walidacji zachowuje każdy istniejący plik, także jaskinie o wspólnym ID
w `.yaml` i `.yml`. Nie wprowadza to nowej reguły unikalności jaskiń; zgodnie
z dotychczasowym indeksem decyzja aktualizuje ostatnią ścieżkę w porządku
loadera, a pozostałe rekordy pozostają w pełnym obrazie i na dysku bez zmian.

CLI zwraca 1 i wypisuje diagnostykę dla błędu. Po poprawnym wczytaniu wejść
powstaje raport również dla nieudanej walidacji:

- `build/staging/review/staging-review.json`
- `build/staging/review/staging-review.md`

Raport zawiera zmaterializowane decyzje, odrzucone/nierozstrzygniete rekordy,
ostrzezenia i liste zapisanych plikow YAML.
