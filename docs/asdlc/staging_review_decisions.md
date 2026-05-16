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

`apply_review.py` najpierw sprawdza caly plik decyzji. Jezeli ktorakolwiek
decyzja ma blad, finalne YAML nie sa zapisywane. Niezaleznie od wyniku powstaje
raport:

- `build/staging/review/staging-review.json`
- `build/staging/review/staging-review.md`

Raport zawiera zmaterializowane decyzje, odrzucone/nierozstrzygniete rekordy,
ostrzezenia i liste zapisanych plikow YAML.
