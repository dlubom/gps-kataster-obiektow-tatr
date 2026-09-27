# PBI-048 — analiza mutacji

Data: 2026-09-27. Bazowy commit: `27ca1479251e94a32df2fb139630446884bdd91a`.
Narzędzie: mutmut 3.5.0, lokalne `mutants/` poza Git. Każdy przebieg
zakończył się exit 0; brak timeoutów, awarii i mutantów bez dobranego testu.

Po pełnej bramce uruchomiono mutacje pięciu funkcji odpowiedzialnych za
rozpoznanie `unresolved`, związanie payloadu, rezerwację ID, utworzenie
obiektu i indeksowanie wierszy. Pierwszy przebieg: **767 unikalnych mutacji,
650 zabitych / 117 ocalałych**. Ocalone warianty powiązane z kontrolą
referencji jaskini, konfliktami celów i powodem ręcznego prefixu skłoniły do
dodania osobnych przypadków pozytywnych i negatywnych.

Drugi przebieg obejmował 82 warianty dispatchu, skrótu raportu, przekazania
payloadu i metadanych decyzji: **69 zabitych / 13 ocalałych**. Po dodaniu
testów jawnych ID w mieszanej partii i niekanonicznego `NaN` uruchomiono
23 istotne warianty ponownie: **18 zabitych / 5 ocalałych**. Licząc każdy
wariant tylko raz i biorąc najnowszy wynik, zakres obejmuje **829 mutacji:
737 zabitych / 92 ocalałe**. Testy zabijają warianty dopuszczające zmianę
raportu/statusu, obcy GLOBALID lub ref jaskini, dodatkowy ref, sprzeczny cel,
pominięcie rezerwacji jawnych ID, brak powodu prefixu i serializację `NaN`.

Ocalałe warianty, pod pełną nazwą funkcji
`gps_kataster_obiektow_tatr.staging_review.<funkcja>__mutmut_<ID>`:

| Funkcja | ID | Analiza |
|---|---|---|
| `x_tpn_report_sha256` | 4, 6, 21 | `None` i `False` mają ten sam efekt dla `ensure_ascii` i `allow_nan`; nazwa kodowania `UTF-8` jest równoważna `utf-8`. Usunięcie `allow_nan=False` i zmiana na `True` są zabijane przez test `NaN`. |
| `x_apply_review_decisions` | 290 | Pusty string zamiast `None` w `unresolved_update` jest tak samo fałszywy przy późniejszym `update_override or ...`; nie zmienia wybranej ścieżki ani zapisu. |
| `x__selected_proposal_ids` | 4, 21, 28 | Zmiany dotyczą wcześniejszego przerwania lub warunku pominięcia błędnej decyzji. Taka partia kończy się błędem przed writerem. Jawne poprawne ID TPN obiektu i PIG jaskini są osobno przetestowane i ich osłabione warianty giną. |
| `x__rows_by_record` | 4, 6, 10, 18 | Różnią obsługę brakującej listy, obcego elementu albo tekst diagnostyczny duplikatu. Nie tworzą poprawnej tożsamości wiersza; decyzja bez niej nie zapisuje YAML. |
| `x__bound_unresolved_payload` | 19, 21, 28, 29, 30, 45, 47, 54, 55, 56, 62, 69, 72, 74, 97, 116, 123, 124, 125, 132, 134, 238 | Zmieniają indeks lub tekst zgłoszonego błędu (w tym gałąź niekanonicznego raportu). Bramka nadal odrzuca materiał i nie zapisuje partii. Mutanty osłabiające zgodność GLOBALID, źródłowego pomiaru, celu wiersza i referencji zostały zabite. |
| `x__apply_unresolved_create_object` | 3, 23, 25, 32, 33, 34, 52, 54, 61, 62, 63, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 97, 99, 106, 107, 108, 118, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 143, 145, 152, 153, 154, 294, 295, 339, 341, 345, 349, 351, 365, 366, 387, 388 | Przeważają indeksy i teksty błędów w gałęziach odrzucenia. `118` jest równoważny kontraktowi resolvera (`ERROR` oznacza brak prefixu); `339/341/345/349/351` dotyczą domyślnych lub powtórnie dodawanych pól jaskini; `387/388` dotyczą przejściowego `AppliedDecision.cave_id` poprawianego przy finalnym powiązaniu i opisu raportu. `294/295/365/366` mogą pogorszyć diagnostykę błędnego schematu, ale writer nie zostaje uruchomiony. Mutanty zmieniające ID, pomiar, powiązanie, nazwę, notatki, kontrolę celu i powód prefixu zostały zabite. |

Wniosek: w sprawdzonym zakresie brak ocalałego wariantu, który
materializowałby zły wiersz lub zapisał niezweryfikowaną partię. Ograniczenie:
testy nie utrwalają dokładnego brzmienia wszystkich komunikatów i opisów
raportu dla błędnych wejść; ich zachowanie diagnostyczne może się zmienić
bez czerwonego testu. Pełna kampania wszystkich modułów należy do PBI-054.
