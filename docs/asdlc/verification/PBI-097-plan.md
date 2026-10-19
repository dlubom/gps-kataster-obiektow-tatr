# PBI-097 — plan wykonania

Wykonanie: `superpowers:executing-plans`, test-first. Przyjęty projekt:
[kontrakt](../tpn_sync_contract.md) §2–5 i [karta](../tpn_sync_backlog.md).
Zlecenie obejmuje wykonanie tej karty; rutynowe wybory techniczne poniżej
nie wymagają ponownej akceptacji projektu.

Cel: deterministyczny raport CSV/API/YAML oraz kolejnych cykli, bez apply.
Python 3.12, istniejące PyYAML/PyProj, bez nowych zależności.

## Granice i interfejsy

- `tpn_normalization.py`: kanoniczny JSON dziesiętny, NFC, odciski rewizji
  i lokalizacji, ścisły adapter historycznego CSV i zweryfikowanego API.
- `tpn_source_state.py`: tylko odczyt i walidacja przyjętego rejestru v1.
  CLI czyta rejestr z `refs/remotes/origin/main`, nigdy z roboczej gałęzi.
  Rejestr nie powstaje ani nie przesuwa bazy w tej karcie. Testy modelują
  jego przyjęcie jako zmianę main; autoryzacja ludzkiego merge należy do
  procesu GitHub, nie jest wywnioskowana z tekstu autora w pliku.
- `tpn_changes.py`: `compare(repo_root, snapshot_path, *, batch_id,
  base_commit, state=None)`; typed indeks, preimage/katalog, bootstrap,
  historia, różnice źródłowe i lokalne, ważność rozstrzygnięć i odroczenia.
- `scripts/compare_tpn_snapshot.py`: odczyt PBI-096, JSON i Markdown do
  nowego katalogu raportu. Brak zapisu stanu, katalogu lub propozycji YAML.
- `tests/test_tpn_normalization.py`, `tests/test_tpn_changes.py`:
  syntetyczne przypadki i odczyt snapshotu z Git bez sieci.

## Kroki i dowody

- [x] RED → GREEN: NFC/LF/null, 0 != null, dokładne XY API, przecinek CSV,
  tolerancja bootstrapu ≤0,1 m, błędne pola/liczby/UUID/polityka.
- [x] RED → GREEN: typed GUID, wiele GUID/obiekt, obce source_ref,
  konflikty GUID i pomiarów, historia/notes/best bez mutacji, zniknięcie
  tylko po verify całego snapshotu; before/after JSON i Markdown.
- [x] RED → GREEN: dwa cykle, odrębna przyjęta baza, defer/reject,
  nowa rewizja, zmieniony cel/polityka, powrót do historii, no-op.
- [x] CLI na Git snapshot + powtórzenie bajtowe raportu, próba z czystego
  checkoutu. Hash wszystkich istniejących data/config przed/po.
- [x] Ruff, pełny pytest, validate, build i readback eksportów według runbooka;
  celowane mutacje krytycznych reguł i końcowy przegląd.
- [ ] Trwały log, status/backlog/context/handoff, commit/push do PR #12,
  zdalny SHA i wszystkie joby jego CI. Stop po 097, prompt dla 098.

## Szczególna kontrola

Dokładność float w hashach (liczby źródłowe czytane jako Decimal), zgubione
odroczenia po zmianie przyjętej bazy, zaufanie stanowi z PR, pomiary obcego
źródła przy zgodnym XY oraz tłumienie konfliktu na nieaktualnym preimage.
Każdy przypadek otrzymuje test zachowania. Bootstrapowe powiązania są
dowodami/kandydatami, nie zaakceptowanym stanem. `proposed_actions=[]`,
`candidates=[]` do kolejnych kart; raport nie przewiduje zmiany best.
