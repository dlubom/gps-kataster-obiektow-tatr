# PBI-098 — plan wykonania

Wykonanie: asdlc, writing-plans i executing-plans, test-first.
Przyjęta specyfikacja: [plan §6](../tpn_sync_plan.md),
[kontrakt §7](../tpn_sync_contract.md), [karta](../tpn_sync_backlog.md).
Użytkownik zlecił implementację; rutynowe parametry i format raportu
ustala wykonawca. Python 3.12, istniejące PyProj/PyYAML, bez zależności.

## Granice i interfejsy

- `tpn_candidates.py`: `CandidatePolicy`, NFC/casefold/odstępy, symetryczna
  odległość Levenshteina / długość dłuższej nazwy. Próg 0,90 włącznie;
  zachowane wszystkie oznaczenia otworów, bez transliteracji/usuwania słów.
  Promień minimum 100 m, max ze znanymi dokładnościami, granica włączna.
- `tpn_changes.compare(..., candidate_policy=None, duplicate_resolutions=None)`:
  opcjonalne rozszerzenie PBI-097, pełne dowody porównań katalogu, jaskiń,
  źródeł bieżących/historycznych i nowych rekordów między sobą.
- CLI PBI-097 `--qualify-new`, `--name-similarity-threshold`, `--radius-m`.
  Odczyt rozstrzygnięć wyłącznie z origin/main, bez producenta decyzji.
  Brak stosowania, alokacji ID, YAML i zmiany best. Ważne rozstrzygnięcie
  opisuje relację, ale nie usuwa sygnału z konserwatywnej bramki §6.
- `PrefixResolver`: jawny wynik wszystkich pasujących dolin do kontroli
  niejednoznaczności; dotychczasowe resolve zachowuje zachowanie.
- `tests/test_tpn_candidates.py`, fixture'y: wszystkie sześć wymaganych
  rodzin oraz komplet warunków auto-propozycji i unieważnienia podstawy.

## Kroki

- [x] RED → GREEN: normalizacja, próg podobieństwa i odległości, dokładności.
- [x] RED → GREEN: nazwy obiektów/jaskiń/źródeł, NR_INWENT/SYSTEM,
  wszystkie pomiary w tym odrzucone, nowe rekordy między sobą.
- [x] RED → GREEN: bramka wszystkich warunków §6, niekompletność → review;
  pamiętane same_opening/different_openings_same_cave/different_objects/
  unresolved, zmiana nazw/referencji/XY/celu/preimage/polityki → stale.
- [ ] Snapshot verify i CLI offline PBI-096/097 z Git, dwa identyczne raporty,
  czysty checkout bez build, niezmienność data/config i readback.
- [x] Ruff/pytest/validate/build/readback, mutacje i przegląd.
- [ ] Status, kontekst i trwały log, commit/push, zdalny SHA i wszystkie
  joby dokładnego CI. Stop po 098. Następny prompt wyłącznie 099.

## Szczególna kontrola

Pusty SYSTEM/NR_INWENT nie koliduje z innym pustym polem. Dalekie homonimy
pozostają kandydatami. Nieprzypisany dawny GUID nie jest nowym obiektem.
Nowy pomiar historyczny lub nowy konkurent unieważnia dawne rozstrzygnięcie,
nawet gdy najlepszy punkt nie zmienił się. Brak daty lub fallback regionu
blokuje automat. Odczyt pamięci z roboczej gałęzi nie akceptuje decyzji.
