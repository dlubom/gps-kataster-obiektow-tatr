# GPS Kataster Obiektów Tatr

Repozytorium utrzymuje git-native katalog punktów terenowych ważnych dla
speleologii i krasu w Tatrach: otworów jaskiń, sztolni, ponorów, wywierzysk i
obiektów pokrewnych.

Źródłem prawdy są pliki YAML w `data/`. Bazy SQLite, GeoJSON, GPX, CSV i
Shapefile są artefaktami generowanymi z tych YAML-i.

## Co tu jest

- `data/objects/` - konkretne punkty terenowe z trwałymi ID projektu.
- `data/caves/` - logiczne rekordy jaskiń / pozycji katalogowych grupujące
  jeden albo więcej obiektów.
- `data/shapes/` - warstwy granic i dolin używane do nadawania prefixów ID.
- `data/sources/` - źródłowe eksporty PIG / TPN i pomocniczy dump PIG do
  ręcznego review.
- `schema/` - JSON Schema dla YAML-i.
- `scripts/` - lokalne komendy walidacji, importu staging i budowy artefaktów.
- [docs/operations.md](docs/operations.md) - praktyczny workflow utrzymania
  danych.

## Szybki start

```bash
uv sync
uv run python scripts/validate.py
uv run python scripts/build_release_artifacts.py
```

Artefakty lokalne powstają w `build/` i nie są commitowane.

## Model danych w skrócie

`Obiekt` to konkretny punkt w terenie. Jedna jaskinia może mieć wiele obiektów,
np. kilka otworów. `Jaskinia` jest encją katalogową/logiczna i trzyma
referencje PIG oraz numery inwentarzowe. TPN `GLOBALID` trzymamy przy obiekcie,
bo opisuje punkt źródłowy.

W V1 każdy obiekt ma kategorię: `jaskinia_otwor`, `sztolnia`, `ponor`,
`wywierzysko` albo `inne`.

## Jak działa `auto`

`best_measurement.mode: auto` deterministycznie wybiera aktualny pomiar:
najpierw własny zweryfikowany, potem TPN, własny nieweryfikowany, PIG, a na
końcu inne nieodrzucone źródła. W remisie wygrywa nowsza data, potem niższe
`horizontal_accuracy_m`, potem stabilny porządek po `measurement.id`. Decyzję
operatorską zapisujemy jako `mode: manual` z `reason`.

W początkowych release'ach większość najlepszych pomiarów może mieć
`verification_status: nieweryfikowany`. To znaczy, że punkt pochodzi z importu
albo przepisanego źródła i nie przeszedł jeszcze projektowego review
terenowego/operatora. Nie oznacza to automatycznie błędu ani braku źródła; do
czasu lepszego pomiaru taki rekord pozostaje najlepszą dostępną lokalizacją.

Pełny workflow pracy na danych jest w
[docs/operations.md](docs/operations.md).

## Walidacja i release

Przed zmianami danych uruchom:

```bash
uv run ruff format --check src tests scripts
uv run ruff check src tests scripts
uv run pytest
uv run python scripts/validate.py
```

Testy mutacyjne krytycznej logiki mozna uruchomic lokalnie:

```bash
uv run mutmut run --max-children 2
uv run mutmut results
```

Publiczny release danych wymaga potwierdzonej licencji źródeł. Lokalne paczki
można budować przez `scripts/build_release_artifacts.py`.
