# PBI-046 — analiza testów mutacyjnych

Zakres: `tpn_staging.build_tpn_staging`, `staging_review._observation_signature`, `staging_review._source_observation_hash`, `staging_review._next_object_measurement_id`, `staging_review._apply_add_measurement`. macOS: obejście `setproctitle` z runbooka, bez zmian kodu projektu.

Pierwsza kampania: **739 mutantów: 533 zabite, 206 ocalałych**; brak timeoutów, awarii i mutantów bez testów. Po dodaniu testów osobnych liczników, trwałego formatu hash, kodu/severity, notatki i błędnego wiersza TPN ponowiono 25 wybranych ocalałych: **18 zabitych, 7 ocalałych**. Wynik łączny dla unikalnych ID: **551 zabitych, 188 ocalałych**. Ponowienia zastępują pierwszy wynik tych ID. Lokalny zapis narzędzia: `build/verification/PBI-046-mutmut-results.txt`, `PBI-046-mutmut-retry.log`, `PBI-046-mutmut-retry2.log`, `PBI-046-mutmut-retry3.log` (artefakty ignorowane przez Git).

Żaden ocalały mutant nie omija przydziału per faktyczny obiekt, wiązania `source_ref` z GLOBALID, sprawdzenia trwałego hasha, wymagania powodu nowej obserwacji ani zachowania `manual best`. Pełna kampania wszystkich modułów pozostaje w PBI-054.

## `tpn_staging.x_build_tpn_staging__` — 115 ocalałych

Starsze gałęzie ostrzeżeń, podsumowań wierszy oraz propozycji nowych obiektów/jaskiń; zmiana `record_number=None` w matched update korzysta z istniejącego fallbacku GLOBALID. Mutant `195` globalnej rezerwacji oraz `211`/`216`/`227`/`228` gubiące numer wiersza, czas lub GLOBALID zostały zabite dodatkowymi testami.

Identyfikatory (prefiks funkcji powyżej + `mutmut_N`): 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 114, 128, 130, 131, 137, 138, 139, 140, 141, 149, 150, 151, 152, 153, 154, 155, 156, 157, 159, 160, 161, 162, 171, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 215, 229, 230, 232, 241, 250, 251, 252, 256, 266, 267, 268, 269, 270, 271, 272, 273, 274, 275, 276, 277, 278, 279, 280, 289, 290, 299, 300, 303, 313, 314, 315, 317, 318, 324, 325, 328, 329.

## `staging_review.x__source_observation_hash__` — 5 ocalałych

Równoważne dla raportu JSON zawierającego prymitywy: `ensure_ascii=None`, brak nieużywanego `default=str`, separator obiektów przy haszowanej tablicy i zapis nazwy kodowania `UTF-8`. Stabilny wektor Unicode chroni reprezentację mającą znaczenie.

Identyfikatory (prefiks funkcji powyżej + `mutmut_N`): 3, 5, 9, 13, 17.

## `staging_review.x__next_object_measurement_id__` — 8 ocalałych

Domyślne wartości dla brakującej listy, brakującego ID lub pustej listy są nieosiągalne po wymaganej walidacji schematu (`measurements` ma co najmniej jeden wpis z `m-NNN`).

Identyfikatory (prefiks funkcji powyżej + `mutmut_N`): 6, 8, 19, 21, 24, 27, 29, 30.

## `staging_review.x__apply_add_measurement__` — 60 ocalałych

Pozostały głównie starsze komunikaty/indeksy raportu, domyślne wartości dla już zwalidowanych list oraz obronna gałąź `MEASUREMENT_ALREADY_EXISTS`, nieosiągalna po przydziale max+1. Mutanty omijające źródło, trwały hash, wymagany powód, poprawną rezerwację i zapis powodu zostały zabite.

Identyfikatory (prefiks funkcji powyżej + `mutmut_N`): 3, 8, 25, 26, 27, 64, 65, 66, 68, 69, 70, 71, 72, 106, 107, 135, 136, 143, 144, 145, 150, 152, 201, 208, 209, 219, 220, 221, 222, 223, 224, 226, 227, 228, 230, 231, 232, 233, 234, 235, 236, 237, 238, 239, 240, 246, 248, 263, 279, 282, 284, 292, 294, 324, 326, 327, 328, 329, 330, 341.
