# PBI-101 — przyczyna rozbieżności CI i końcowy odbiór

Status: przyczyna potwierdzona i naprawiona; zastosowana paczka 16beb1e
ma hosted CI 39316520323 success (wszystkie joby/kroki/pełne logi odczytane)
i świeży readback eksportów 10/10 PASS. Wszystkie
640 decyzji człowieka są rozliczone: 614 approve / 26 defer, bez pending.
Wcześniejsze polecenie pozostawienia pending zostało jawnie zastąpione.

Pierwsze CI 39289000670 / 9a70337 oraz 39290287566 / b4720e8 kończyły się
`changes evidence/schema mismatch` przed kontrolą pending. To był rzeczywisty
błąd odtwarzania, nie oczekiwana blokada review. Diagnostyka 6d94f9c/run
[39311292320](https://github.com/dlubom/gps-kataster-obiektow-tatr/actions/runs/39311292320)
po 1078 testach wskazała dokładne pola. 1 job, 11 success / 1 failure /
2 skipped; pełny log i wszystkie 14 członków ZIP odczytano.

Dla pierwszego rekordu wyliczona szerokość CSV na Linuksie wyniosła
49.24432741630521 wobec zapisanej 49.244327416305204. Geodezyjne odległości
różniły się w końcowych cyfrach, a zależne hashe wykazywały rozbieżność.
[Jawne zasady naprawy](../tpn_sync_derived_precision.md) obejmują tylko
pochodne, nie surowe API, stare pomiary ani tolerancje dopasowania.

1082 testów PASS, w tym odtwarzanie przy symulowanym szumie platformy,
stabilny cache nowego pomiaru, niezmieniony promień kandydatów i odmowa
zmiany raw API XY o 1e-18. Pełny raport 1035 rekordów jest kanonicznie
identyczny przy obu znakach szumu projekcji 2e-14 stopnia i odległości
5e-9 m. [Równoważność z przyjętym review](PBI-101-review/review-equivalence.json).

Pierwszy raport i decyzje zachowano bajtowo w superseded-v1; nową rewizję
tej samej paczki wygenerowano CLI z niezmiennego snapshotu i tej samej bazy,
z przyjętym stanem wyłącznie origin/main. Nie przeliczono po prostu hashów
starego payloadu. Zaakceptowane API source/revision/change_id, cele,
preimages, klasyfikacje i zbiory kandydatów pozostały bez zmian.

Końcowy SHA, URL/wynik wszystkich jobów i kroków oraz odczyt pełnych logów
utrwala opis PR #12. Dokumenty odbioru mają osobny commit; jego dokładne CI i świeży readback
wymagają ponownego potwierdzenia przed zakończeniem sesji.
[Trwały odbiór danych](PBI-101-review/delivery-data-proof.json).
Bez PBI-102, merge, tagu, release i harmonogramu.
