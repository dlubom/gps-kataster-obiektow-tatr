# PBI-047 — analiza testów mutacyjnych

Zakres: pięć zmienionych funkcji `tpn_staging` wymienionych poniżej.
Świeży katalog `mutants/`: wcześniejszy stan przeniesiono do ignorowanego
`build/verification/PBI-047-mutants-before-*`. Nie zmieniono zależności.
Na macOS pominięto wyłącznie kosmetyczne `setproctitle`, jak w PBI-042.

```bash
UV_CACHE_DIR=/tmp/gps-kataster-uv-cache uv run --frozen python -c 'import mutmut.__main__ as m; m.setproctitle = lambda *_: None; m.cli()' run --max-children 2 \
  'gps_kataster_obiektow_tatr.tpn_staging.x_build_tpn_staging*' \
  'gps_kataster_obiektow_tatr.tpn_staging.x__build_unresolved_row*' \
  'gps_kataster_obiektow_tatr.tpn_staging.x__build_tpn_measurement*' \
  'gps_kataster_obiektow_tatr.tpn_staging.x__report_to_json_data*' \
  'gps_kataster_obiektow_tatr.tpn_staging.x__row_summary*'
```

Pierwsza kampania: **604 mutanty, 426 killed / 178 survivors**. Po analizie
i dodaniu asercji ponowiono wszystkie 178 ocalałych: **44 killed / 134 survivors**.
Łączny wynik dla unikalnych ID: **470 killed / 134 analyzed survivors**.
Brak timeoutów, awarii i mutantów bez testów w wybranym zakresie.
Ponowienie w mutmut zeruje statusy niewybranych mutantów; wynik łączny
zachowuje zabite ID pierwszej kampanii i zastępuje tylko 178 ponowionych.

Lokalne logi: `build/verification/PBI-047-mutmut.log`,
`PBI-047-mutmut-retry.log`, `PBI-047-mutmut-initial-meta.json` oraz
`PBI-047-mutmut-merged.json`. Poniższe identyfikatory i analiza w Git
pozwalają kontynuować bez tych lokalnych plików.

Dwaj agenci tylko do odczytu przejrzeli AST/diffy ocalałych mutantów.
Dodatkowe asercje chronią liczbę wierszy po odrzuceniu, diagnostykę i jej
powiązanie ze źródłem, kategorię z nazwy oraz cave_id dla matched/new.
Pełna kampania starszej logiki i rozliczenie pozostałych luk należą do PBI-054.

## `tpn_staging.x_build_tpn_staging__` — 95 ocalałych

Pozostały starsze ścieżki diagnostyki i podsumowań: brak GLOBALID, odległość dopasowania, nowe propozycje oraz ich metadane. Mutant 178 zastępuje szczegółowy opis niejednoznaczności ogólnym opisem, zachowując kod i tożsamość wiersza. 173–174 i 179–181 dotyczą fallbacków nieużywanych przez standardowe wyniki matcherów. Mutanty 96/290 zmieniają continue na break w starszych odrzuceniach (brak GLOBALID / nowy punkt poza granicami): to rzeczywiste luki pokrycia starszych gałęzi, nie równoważność. Nowa gałąź odrzucania unresolved (156–158), utrata payloadu i jego identyfikatorów są chronione.

Identyfikatory (prefiks powyżej + `mutmut_N`): 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 114, 128, 130, 131, 173, 174, 178, 179, 180, 181, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 205, 226, 240, 241, 261, 262, 263, 267, 277, 278, 279, 280, 281, 282, 283, 284, 285, 286, 287, 288, 289, 290, 300, 301, 310, 311, 314, 324, 325, 326, 329, 336.

## `tpn_staging.x__build_unresolved_row__` — 8 ocalałych

7 jest równoważny dla standardowego resolvera, który zwraca ERROR wraz z prefix=None; niestandardowe sprzeczne wyniki resolvera nie mają pełnego pokrycia. 26–27 i 33–35 dotyczą nieużywanych w standardowym resolverze tekstów fallbacku. 32/39 zmieniają opis ostrzeżenia, zachowując status, kod, wiersz, GLOBALID i NR_INWENT. Testy odrzucania i zachowania pomiaru zabijają mutanty naruszające podstawową gwarancję.

Identyfikatory (prefiks powyżej + `mutmut_N`): 7, 26, 27, 32, 33, 34, 35, 39.

## `tpn_staging.x__build_tpn_measurement__` — 31 ocalałych

Starsze pola opisu wysokości, metody, urządzenia, tagów, atrybucji weryfikacji i notatek mają niepełne asercje. Nie naruszają sprawdzonych źródłowych ID, dat, obu układów współrzędnych, wysokości, audytu utworzenia ani pominięcia lokalnego ID. Nie nazywamy tych mutantów równoważnymi.

Identyfikatory (prefiks powyżej + `mutmut_N`): 14, 15, 16, 17, 18, 19, 20, 21, 24, 25, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 52, 53, 54, 55, 56, 57, 58, 59, 60.

## `tpn_staging.x__report_to_json_data__` — 0 ocalałych

Wszystkie mutanty zabite po sprawdzeniu również serializacji diagnostyki i liczników.

## `tpn_staging.x__row_summary__` — 0 ocalałych

Wszystkie mutanty zabite po dodatkowej asercji cave_id istniejących formatów matched/new.
