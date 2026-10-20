# TPN: start z czystego kontekstu

Stan: 2026-10-20. Ten plik wraz z planem i backlogiem w
[PR #12](https://github.com/dlubom/gps-kataster-obiektow-tatr/pull/12)
wystarcza do kontynuacji prac bez historii czatu i lokalnego build.
Kontrakt przyjęto w PBI-095. PBI-096 dostarcza snapshot/CLI, a PBI-097
porównanie tylko do odczytu. PBI-098 dodaje [kandydatów i kwalifikację](tpn_sync_candidates.md).
PBI-099 dodaje [ochronę i audyt best](tpn_sync_best_protection.md).
PBI-100 dostarcza [decyzje i zastosowanie](tpn_sync_decisions.md).
PBI-101 dostarcza pierwszą uzgodnioną paczkę: 614 approve / 26 defer / 0 pending.
Późniejsze decyzje użytkownika realizuje [suplement D26](verification/PBI-101-D26.md):
kandydat stanu 640 approve / 0 defer / 0 pending; pierwotne archiwa bez zmian.
Aktualny status jest w backlogu oraz [logu PBI-101](verification/PBI-101.md);
[CLI i rejestr PBI-097](tpn_sync_comparison.md).

## Repozytorium i wejście w pracę

- Repozytorium: `dlubom/gps-kataster-obiektow-tatr`.
- Lokalnie: `/Users/dariuszlubomski/proj/gps-kataster-obiektow-tatr`.
- PR integracji TPN: **#12**, baza `main`, gałąź `codex/tpn-sync-planning`.
- Sprawdź status i fetch origin, zachowaj cudze zmiany. Sprawdź aktualny
  stan PR #12 przed wyborem gałęzi; kontynuacja otwartego PR ma
  pierwszeństwo przed domyślnym startem z main.
- Jeśli PR jest nadal otwarty, dokumenty są na jego gałęzi, niekoniecznie
  na main. Do kontynuacji tego PR użyj `gh pr checkout 12`; nie twórz
  duplikatu PR ani nie merguj go tylko po to, by przeczytać dokumenty.
- Jeśli PR został zmergowany, korzystaj z aktualnego main. Zamknięcie bez
  merge nie oznacza przyjęcia planu. SHA i CI odczytaj z aktualnego PR.
- Nie wznawiaj porzuconych gałęzi napraw ani ich historycznych PBI-034–077.

Kolejność czytania:

1. [AGENTS](../../AGENTS.md) i wymienione tam dokumenty kanoniczne:
   [spec](../../specyfikacja_gps_kataster_obiektow_tatr_v_2.md),
   [indeks backlogu](backlog_v1.md), [context](context.md),
   [plan napraw](remediation_plan.md), [runbook](remediation_runbook.md).
2. [Plan TPN](tpn_sync_plan.md) — wymagania, wyniki rozpoznania, decyzje
   projektowe oraz ryzyka w obecnym kodzie.
3. [PBI-095–103](tpn_sync_backlog.md) — zakres, zależności i kryteria odbioru.
4. [Kontrakt PBI-095](tpn_sync_contract.md) i [formaty](tpn_sync_examples.md).
5. Odbiory [PBI-095](verification/PBI-095.md), [096](verification/PBI-096.md),
   [097](verification/PBI-097.md), [098](verification/PBI-098.md),
   [099](verification/PBI-099.md), [100](verification/PBI-100.md)
   i aktualny [PBI-101](verification/PBI-101.md).
6. [Końcowe decyzje i zgody](verification/PBI-101-review/review.md),
   verification.json, delivery-data-proof.json, review-equivalence.json
   oraz archiwum superseded-v1 w `verification/PBI-101-review/`.
   [Manifest ochrony PBI-099](verification/PBI-099-protection-manifest.json)
   pozostaje historycznym audytem pending. Późniejsze jawnie zatwierdzone
   trzy przypięcia manual dokumentuje [osobny zapis](verification/PBI-099-manual-selection.json).
   Następnie przeczytaj [wykonanie D26](verification/PBI-101-D26.md) i jego
   [zgodę, bazę i hashe](verification/PBI-101-D26-resolution.json).
   Końcowy SHA i wyniki jego CI odczytaj z opisu PR.

## Publiczne API i dokładne zapytanie

Źródło rozpoznane 2026-10-19, bez tokena i logowania:

- [Opis warstwy i schemat JSON](https://gis.tpn.pl/server/rest/services/Topografia___wektor_MIL1/MapServer/6?f=pjson).
- [Query](https://gis.tpn.pl/server/rest/services/Topografia___wektor_MIL1/MapServer/6/query).
- [Licznik rekordów](https://gis.tpn.pl/server/rest/services/Topografia___wektor_MIL1/MapServer/6/query?where=1%3D1&returnCountOnly=true&f=json).
- [Lista OBJECTID](https://gis.tpn.pl/server/rest/services/Topografia___wektor_MIL1/MapServer/6/query?where=1%3D1&returnIdsOnly=true&f=json).

Dokładne parametry zapytania użytego do pobrania lokalnego JSON:

| Parametr | Wartość |
|---|---|
| where | `1=1` |
| outFields | `*` |
| returnGeometry | `true` |
| outSR | `4326` |
| orderByFields | `OBJECTID` |
| resultOffset | `0` |
| resultRecordCount | `2000` |
| f | `json` |

Przykład ręcznego pobrania **jednej strony** do nowego katalogu roboczego
(wykonuj z katalogu repozytorium; nie nadpisuje kopii z poprzedniej sesji):

```bash
mkdir -p build/exports/tpn-api
TPN_FETCH_DIR=$(mktemp -d build/exports/tpn-api/manual.XXXXXX)
curl --fail --show-error --silent --get \
  'https://gis.tpn.pl/server/rest/services/Topografia___wektor_MIL1/MapServer/6/query' \
  --data-urlencode 'where=1=1' \
  --data-urlencode 'outFields=*' \
  --data-urlencode 'returnGeometry=true' \
  --data-urlencode 'outSR=4326' \
  --data-urlencode 'orderByFields=OBJECTID' \
  --data-urlencode 'resultOffset=0' \
  --data-urlencode 'resultRecordCount=2000' \
  --data-urlencode 'f=json' \
  --output "$TPN_FETCH_DIR/tpn-otwory-jaskin-page-0.json"
```

To polecenie nie zastępuje kompletnego downloadera z PBI-096. Przed użyciem
danych trzeba odczytać schemat i limit usługi, sprawdzić `error` w JSON
(HTTP 200 nie wystarcza), `exceededTransferLimit`, count i pełny zbiór ID
przed/po pobraniu oraz unikalność GLOBALID. Gdy strona nie obejmuje całego
zbioru, pobierz kolejne strony z rosnącym offsetem zgodnie z rzeczywiście
zwróconą liczbą rekordów. Niespójny lub niepełny odczyt nie jest bazą decyzji.

Odpowiedź zawiera `features[].attributes` i `features[].geometry`.
Przy outSR=4326: `x` to długość, `y` szerokość geograficzna. `GLOBALID`
jest tożsamością źródłową otworu, `OBJECTID` technicznym ID usługi.
`WER_LOK` i `UWAGI` mogą być null. Daty ArcGIS są milisekundami od epoki
Unix; data edycji nie jest dowodem daty pomiaru. Brak Z nie kasuje lokalnej
wysokości. Pobieraj wszystkie pola, nie tylko trzy wymienione w zleceniu.
Nie zastępuj tej warstwy uboższą `SIPTPN/Geologia_i_gleby/MapServer/2`.

## Gdzie jest JSON i co daje czysty checkout

Na komputerze wykonującego rozpoznanie pozostały ignorowane pliki:

- `build/exports/tpn-api/2026-10-19/tpn-otwory-jaskin.json`;
- `build/exports/tpn-api/2026-10-19/download-metadata.json`;
- `build/exports/tpn-api/2026-10-19/planning-source-comparison.json`.

**Nie są częścią PR #12.** Użytkownik dopuścił pozostawienie JSON poza Git;
do planowania i PBI-095 nie jest konieczny. Nie zakładaj dostępności tych
plików w nowym checkoutcie. Polecenie wyżej pozwala pobrać bieżący stan API.
Nie odtwarza historycznej migawki: nowe liczniki i SHA mogą się różnić.
Hash z planu służy identyfikacji starego pliku, nie walidacji nowej odpowiedzi.

W odczycie z 2026-10-19 było 1035 rekordów, 21 pól, 1035 niepustych GLOBALID,
502 WER_LOK i 109 UWAGI. Względem zachowanego w repo CSV: 30 nowych GUID,
0 znikniętych, 30 przesunięć ponad 1 m; 12 grup powtarzających się nazw
w API. Plan podaje metodę i hashe, a CSV pozostaje dostępny w repo.
Są to wyniki rozpoznania, nie zaakceptowane zmiany katalogu.
Wejścia decyzji PBI-101 są już utrwalone w Git: pełny snapshot, changes,
decisions, receipt i kandydat stanu. Obecny PR nie jest przyjętą bazą
synchronizacji przed ludzkim merge.

## Pobieranie i kontrola snapshotu — PBI-096

CLI jest zaimplementowane. Z repozytorium:

```bash
uv run --frozen python scripts/fetch_tpn_snapshot.py fetch \
  --snapshot-id NOWY-UNIKALNY-ID --page-size 500 --attempts 2
uv run --frozen python scripts/fetch_tpn_snapshot.py verify \
  data/sources/tpn/snapshots/pbi-101-live-20261019
```

`fetch` wykonuje pełny odczyt i nie przyjmuje innego endpointu ani filtra.
Limit strony jest minimum podanej wartości i limitu API. Próba błędna
ponawia cały odczyt (maksymalnie 3 próby); istniejący snapshot-id zawsze
odmawia nadpisania. `verify` działa offline i odtwarza kontrole z surowych
plików. Nowy snapshot nie przesuwa przyjętej bazy synchronizacji.

Próba live `pbi-096-live-20261019` jest teraz w Git, razem z manifestem,
stronami, kontrolami i dokładnym tekstem polityki. 1035 rekordów, strony
500/500/35; [hash, przedział czasu i weryfikacja](verification/PBI-096.md).
To odrębny odczyt od historycznego JSON opisanego powyżej. Kolejne odczyty
nie muszą mieć takich samych liczników ani hashów. Nie edytuj tej migawki.

Manifest zawiera także `layer-after.json` (rola schema_after) i `policy.md`
(rola policy, policy_hash jego dokładnych bajtów). Wszystkie ścieżki są
względne do repo. Walidator nie ufa podsumowaniom ani complete=true.
Zmiana schematu lub pojawienie się Z/M wymaga jawnej aktualizacji kontraktu.
API nie daje transakcyjnej gwarancji atrybutów, co jest zapisane w manifeście.

## Granica następnego kroku

PBI-101 **wykonane — dane, CI i eksporty odebrane**. Pierwotna paczka
`pbi-101-20261019` ma **614 approve / 26 defer / 0 pending**.
[Końcowe decyzje](verification/PBI-101-review/review.md): A001–A578 przyjęte
bez zmian katalogu/best; B001–B031 append i osobny select_new auto;
C001–C005 nowe Obiekty/Jaskinie; D001–D026 odroczono wówczas do badania.
Utrwalone zgody zastąpiły wcześniejsze polecenie pending. Nie pytać ponownie
o te zakresy ani nie stosować danych ponownie.

Pierwotne CLI apply/check zakończone; wynik: 1012 Obiektów, 1006 Jaskiń,
1912 pomiarów. Zachowano wszystkie 1876 dawnych pomiarów, 1001 dawnych
Jaskiń i 9 chronionych plików. Snapshot, decisions, receipt i kandydat
stanu są w Git. Dawny raport z pending i wariant keep pozostają wyłącznie
w [archiwum superseded-v1](verification/PBI-101-review/superseded-v1/README.md).
[Błąd odtwarzania Linux/Mac został naprawiony](verification/PBI-101-ci-handoff.md);
odbiór danych/CI/eksportów dokumentuje [PBI-101](verification/PBI-101.md).
Dokładny aktualny head oraz wynik wszystkich jobów, kroków i pełnych logów
CI odczytaj na żywo z PR #12.

PR pozostaje draftem do człowieka. Stan gałęzi jest kandydatem; przyjęta
baza nadal pochodzi wyłącznie z origin/main. Użytkownik następnie zatwierdził
D26: [wykonanie i odbiór](verification/PBI-101-D26.md). Wynik suplementu:
1035 Obiektów, 1027 Jaskiń, 1938 pomiarów; 640 approve / 0 defer / 0 pending
w kandydacie stanu. Historyczne 26 defer pozostaje w pierwotnych decyzjach.
Po review 2026-10-20 poprawiono P3 (nieaktualny handoff), a na osobne
zlecenie również P2 (powielanie notatek między cyklami). Test dwóch cykli
potwierdza zachowanie pojedynczego fragmentu oraz odrzucenie kopii w after.
[Zakres i odbiór P2](verification/PBI-101.md#poprawka-p2-po-niezależnym-review-2026-10-20).
Obie poprawki zachowują zaakceptowane dane i zgody.
Merge pozostaje osobną decyzją człowieka; PBI-102–103 nie rozpoczęto.

Historyczny manifest auto→manual zachowano bez zmian. Użytkownik następnie
zatwierdził trzy przypięcia w tym samym PR: KSW-0201/m-003, KSW-0240/m-002
i KSZ-0112/m-001. [Zapis zgody i wykonania](verification/PBI-099-manual-selection.json)
wiąże pierwotne preimages i wynik; dziewięć chronionych obiektów ma manual.
Ochrona działa niezależnie od zgody. Zmieniona propozycja/preimage wymaga
ponownego review. Przyjęty stan czytamy wyłącznie z origin/main, nigdy
z kandydata gałęzi. Nie nadpisywać aktywnego snapshotu ani paczki, nie
używać starego apply_review.py. Bez merge/tagu/release i harmonogramu.

Ustalenia: jeden PR i decyzje po rekordzie, zaległości przed miesięcznym
sprawdzaniem, wyłącznie ludzki merge, kontrola duplikatów, historia i ochrona
GNSS/geodezji niezależnie od source/status/unknown accuracy. Dopisanie pomiaru
nie daje zgody na zmianę best. Data modyfikacji TPN z komentarzem opisuje
stan źródła, gdy data terenowa jest nieznana; jej brak odracza pomiar.

Po każdym wykonanym PBI: spójna dokumentacja, adekwatna weryfikacja,
commit/push, zdalny SHA i CI tego SHA. Jedna karta na sesję, bez samodzielnego
przechodzenia do kolejnej. Merge TPN wykonuje człowiek; brak tagu/release.
