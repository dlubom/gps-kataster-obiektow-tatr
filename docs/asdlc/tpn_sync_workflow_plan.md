# PBI-102 — plan ręcznej ścieżki TPN

Zlecenie: 2026-10-21, kontynuacja PR #12. Specyfikacją jest
[karta 102](tpn_sync_backlog.md#pbi-102-przygotowywać-pojedynczy-pr-przez-ręczne-uruchomienie-workflow)
oraz [kontrakt](tpn_sync_contract.md) §8 i [plan](tpn_sync_plan.md) §8–9.

Cel: `workflow_dispatch` przygotowuje jeden draft PR, pozwala zastosować
indywidualne decyzje i jawnie odświeżyć tę samą gałąź. Python/uv, istniejące
compare/prepare/apply/check i GitHub REST; bez nowych zależności.

## Granice i decyzje wykonawcze

- Kod i zależności wyłącznie z dokładnego SHA `main`; workflow odmawia
  uruchomienia z innej gałęzi. PR dostarcza tylko dane. Dwa joby: odczyt
  przygotowuje bundle Git, publikacja sprawdza go i wykonuje zwykły push.
- Publikacja ma tylko contents/pull-requests write. Bez tokena osobistego,
  sekretów, force-push, review approval, auto-merge, merge, tagu i release.
- Jeden wspólny klucz concurrency, cancel-in-progress=false; ponowna kontrola
  main, PR i HEAD bezpośrednio przed zapisem. Osierocona gałąź po awarii
  między push a PR jest odzyskiwana, a nie zastępowana nową paczką.
- `prepare` nie nadpisuje otwartego PR; no-op i niepełne API nic nie publikują.
  Nowe automatic_proposal mogą pokazać YAML z audytem technicznym; wszystkie
  decyzje zaczynają pending. Istniejące rekordy nie są akceptowane przez bota.
- `apply` wymaga numeru PR i dokładnego expected_head oraz uprawnionego
  człowieka uruchamiającego workflow. Końcowe decyzje podpisuje dispatcher
  jako `github:LOGIN`. Uprawnienia są sprawdzane w API, nie w pliku decyzji.
- `refresh` wymaga tych samych jawnych wskazań. Odtwarza paczkę od bieżącego
  main, resetuje decyzje do pending, zachowuje poprzednią gałąź w historii.
  Edytowany proposals.yml jest danymi do ponownego związania i walidacji.
- Próba produkcyjna wymaga przyjętego stanu PBI-101 na main po ludzkim merge.
  Do tego czasu status 102: implementacja do odbioru produkcyjnego.

## Kroki i weryfikacja

- [x] Testy RED dla prepare/no-op/błędu/otwartego PR, apply/replay/pending,
  autoryzacji i stale main/head, refresh oraz odzyskania publikacji.
- [x] `tpn_workflow.py`: deterministyczne propozycje, planowanie na izolowanym
  Git z użyciem istniejącego applier; `tpn_workflow_github.py`: wąski adapter
  REST i kontrolowana publikacja bundle. CLI `scripts/run_tpn_sync.py`.
- [x] `.github/workflows/tpn-sync.yml`: dispatch prepare/apply/refresh,
  odczyt → bundle → publikacja; testy konfiguracji i granicy zaufania.
- [ ] Instrukcja operatora i status/handoff. Pełne pytest, Node, Ruff,
  validate, check istniejącej paczki, celowane mutacje, eksport/readback
  oraz hash całego data/config/schema przed/po.
  Lokalnie 1200 wcześniejszych testów i 26 końcowych nowych PASS; pełny
  pośredni proces miał nieaktualną fixture w pamięci (szczegóły w odbiorze).
  Końcowy pełny zestaw 1226 sprawdza CI dostarczonego niezmiennego SHA.
- [ ] Commit/push w PR #12; odbiór wszystkich jobów/kroków/logów dokładnego
  końcowego SHA i nowego ZIP PR. Bez uznania fixture za produkcyjną próbę.

Przegląd szczególnie sprawdza: edycje kodu/symlinki w PR, podmianę bundle,
zbieżne uruchomienia, opóźnione wyniki po ruchu main/HEAD oraz zamknięcie
bez merge. Każdy z tych przypadków musi zachować main i pracę operatora.
