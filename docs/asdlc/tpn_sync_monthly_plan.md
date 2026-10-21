# PBI-103 — miesięczne sprawdzanie TPN

Zlecenie 2026-10-21: „PBI-103 z PR 12”. Baza implementacji:
`6a0342c103f999896a534e100aad699876e9a2c0`. Specyfikacją jest
[karta 103](tpn_sync_backlog.md#pbi-103-sprawdzać-źródło-co-miesiąc-i-otwierać-pr-do-review),
kontrakt §8 i plan TPN §9. Użytkownik potwierdził **1. dzień miesiąca,
03:17 UTC** (04:17 zimą / 05:17 latem w Polsce).

Wykonanie w bieżącym PR, Python/uv i istniejący dwustopniowy workflow.
Nie zmieniamy danych ani zależności. Wspólny kod prepare dla dispatch/schedule,
jeden klucz concurrency, osobny publisher z dotychczasowymi kontrolami.

Decyzja wykonawcza: przygotować kod, ale wymagać repozytoryjnej zmiennej
`TPN_MONTHLY_ENABLED=true` przed działaniem schedule. Bez zmiennej wynik
`disabled`, bez sieci i publikacji. Jest to blokada aktywacji do odbioru
ręcznej ścieżki PBI-102; samo dodanie cron do PR nie zamyka tej zależności.
Zmienna nie jest ustawiana przez ten PBI. Schedule może tylko prepare;
apply/refresh pozostają jawnymi operacjami człowieka.

## Wykonanie i odbiór

- [x] Testy RED w `tests/test_tpn_monthly.py` i konfiguracji workflow:
  brak aktywacji, brak wejść dispatch w schedule, no-op/zmiana/błąd,
  ten sam wynik ręczny, otwarty PR przez dwa miesiące, close bez merge,
  nowy przyjęty main i defer, nowa rewizja po defer.
- [x] `tpn_workflow.py`: opcjonalny raport odczytu oraz tryb inspekcji
  otwartego PR bez commitów i zastosowania danych. `tpn_workflow_github.py`:
  związanie zdarzenia z transferem, blokada schedule i raport zaległości.
  `tpn_workflow_reporting.py`: JSON/Markdown, metadane przebiegu i snapshot.
  CLI: podsumowanie także disabled/error. Ten sam kod dla obu zdarzeń.
- [x] `tpn-sync.yml`: cron `17 3 1 * *`, domyślne prepare przy schedule,
  diagnostyka z `always()` i retencją 14 dni; writer tylko przy publish.
- [x] Runbook aktywacji po odbiorze 102, wyłączenie/wznowienie GitHub,
  aktualizacja statusów bez deklarowania odbioru produkcyjnego.
- [ ] Testy obszaru i pełna bramka: pytest, Node, Ruff, validate, check TPN,
  eksport/readback i niezmienność data/config/schema; niezależny review.
- [ ] Commit/push do PR #12, potwierdzenie zdalnego SHA, wszystkich jobów,
  kroków i logów CI oraz świeżego ZIP dla tego HEAD.

Przegląd koncentruje się na wyłączeniu aktywacji także między plan/publish,
podmianie typu zdarzenia, niepełnym API przy otwartym PR, braku nadpisania
pracy operatora i przyjęciu wyłącznie main jako bazy. Próba fixture jest
próbą implementacji; rzeczywisty schedule/PR/token wymaga odbioru 102.
