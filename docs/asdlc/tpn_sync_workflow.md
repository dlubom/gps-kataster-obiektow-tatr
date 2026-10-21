# Ręczny workflow TPN — operator

Workflow **TPN manual batch** (`tpn-sync.yml`) ma wyłącznie
`workflow_dispatch`: `prepare`, `apply`, `refresh`. Nie ma harmonogramu.
[Plan wykonania](tpn_sync_workflow_plan.md), [kontrakt](tpn_sync_contract.md),
[decyzje i akcje](tpn_sync_decisions.md), [odbiór PBI-102](verification/PBI-102.md).

## Instalacja i warunki pierwszej próby

1. Człowiek rozpatruje i scala PR #12, zachowując jego historię oraz
   wskazane commity bazowe. Stan PBI-101 staje się przyjęty dopiero na main.
   Workflow odmawia prepare przed przyjęciem tego stanu. Nie scalać PR
   tylko w celu uruchomienia testu automatyzacji.
2. W Settings → Actions → General → Workflow permissions maintainer
   sprawdza **Allow GitHub Actions to create and approve pull requests**.
   Odczyt 2026-10-21: `default_workflow_permissions=read`,
   `can_approve_pull_request_reviews=false` — możliwość tworzenia PR jest
   wyłączona. Zmiana tego ustawienia wymaga osobnej decyzji maintenera.
   Nazwa ustawienia obejmuje approvals; ten workflow nie wywołuje żadnego
   endpointu review/approval, merge ani auto-merge. Nie potrzebuje PAT/App.
   [Dokumentacja ustawienia](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository).
3. Uruchamiać wyłącznie z **main**. Kod, lockfile i zależności są przypięte
   do SHA main ze zdarzenia. Jeśli main przesunął się po dispatch, rozpocząć
   nowe uruchomienie z bieżącego main. Re-run zachowuje stare zdarzenie.
4. Dispatcher i osoba ponawiająca przebieg muszą być kontami `User` z
   `write`, `maintain` lub `admin`, sprawdzonymi przez API. Przy apply
   odpowiedzialność za wszystkie końcowe decyzje przyjmuje aktualny
   dispatcher (`github:LOGIN`); napis w pliku sam nie daje uprawnień.

Pierwsza próba produkcyjna i akceptacja CI `GITHUB_TOKEN` pozostają do
wykonania po tych warunkach. Testy z atrapą GitHub nie są ich zamiennikiem.

## Przygotowanie i review

Actions → **TPN manual batch** → Run workflow → main → `prepare`.
`pr_number` i `expected_head` pozostają puste.

Pełny snapshot przechodzi kontrole API i offline readback przed publikacją.
No-op nie tworzy gałęzi ani PR. Błąd źródła nie publikuje częściowej paczki.
Znany otwarty PR kończy przebieg jako `existing`, bez zmiany jego danych.
Jest jeden wspólny klucz concurrency dla wszystkich trybów.

Istotna zmiana tworzy jeden draft PR z gałęzi `tpn-sync/gha-RUN_ID`.
Files changed zawiera nowe wejście `data/sources/tpn/snapshots/gha-RUN_ID/`
oraz katalog `data/source_reviews/tpn/gha-RUN_ID/`:

- `report.md` i `changes.json`: źródło przed/po, tożsamość, kandydaci,
  konflikty, stan best i podstawa decyzji;
- `proposals.yml`: jawne propozycje akcji, do edycji i ponownego związania;
- `decisions.yml`: każdy rekord wymagający review ma **pending**;
- `application.json` i `applications/`: odtwarzalny wynik i historia decyzji.

Automatic_proposal może utworzyć samodzielny nowy YAML do review z audytem
`automatic:tpn-proposal`. To nie jest zgoda człowieka. Istniejące rekordy
zaczynają z pustymi akcjami; approve pustej propozycji oznacza świadome
pozostawienie katalogu, nie przyjęcie nowej lokalizacji. Dane punktu zmienia
wyłącznie jawna propozycja z append i osobnym keep/select_new.

## Decyzje i zastosowanie do tej samej gałęzi

1. Sprawdź dane, pełną historię, literaturę i kandydatów. W proposals.yml
   można przygotować akcje według [schematu](tpn_sync_decisions.md).
   Przy zmianie propozycji uruchom `refresh` przed zatwierdzaniem decyzji.
   Źródła, changes i application nie są ręcznym formularzem edycji.
2. W decisions.yml dla każdego rekordu ustaw approve/reject/defer, powód,
   `reviewed_by: github:LOGIN`, `reviewed_at` jako ISO UTC zakończone Z.
   Approve zachowuje dokładne proponowane actions; reject/defer wymaga `[]`.
   Defer jest końcową, trwałą decyzją, pozwalającą odebrać resztę partii.
   Pending nie ma autora/czasu i blokuje merge. Chroniony best nadal wymaga
   reguł PBI-099; workflow nie daje uprawnienia do jego zmiany.
3. Zacommituj decyzje w gałęzi tego PR. Zapisz **nowy pełny HEAD** po edycji.
4. Run workflow z main: `apply`, numer tego PR, `expected_head` równy
   zapisanemu HEAD. Etap stosuje dane przez zaufany applier i dopisuje
   zwykły commit do tej samej gałęzi. Ponowienie zgodnego wyniku jest no-op.
   Ruch HEAD/main, obca edycja wygenerowanych danych, niezgodna podstawa,
   podszycie pod innego autora lub niepoprawna akcja blokują zapis.

Można zastosować rozstrzygniętą część paczki, zachowując pending pozostałych;
CI pozostanie wtedy czerwone. Apply nie jest merge ani akceptacją PR.

## CI i eksporty dokładnego HEAD

Po każdym zapisie `GITHUB_TOKEN` w PR człowiek z write wybiera w merge box
**Approve workflows to run**. Dotyczy to także kolejnego commitu apply
lub refresh. Bot nie zatwierdza tych przebiegów za operatora.
[Aktualne zachowanie GitHub](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow)
sprawdzono 2026-10-21: opened/synchronize/reopened tworzą przebiegi
wymagające zatwierdzenia; push sam nie uruchamia kolejnego workflow.

Sprawdź wszystkie wymagane checki **dokładnego końcowego HEAD**, wszystkie
joby/kroki i logi. Odczyt reguł main 2026-10-21: wymagany `Validate code and data`
od GitHub Actions (app 15368), jedno ludzkie review i rozstrzygnięte wątki.
Pending ma powodować błąd bramki TPN. Sam zielony job przygotowania paczki
nie jest zielonym CI danych.

Po CI pobierz aktualny ZIP z bloku opisu PR. Potwierdź head/base/merge,
run/attempt, digest artefaktu, SHA256SUMS i readback wszystkich formatów,
SQLite z historią oraz Excel Best/Full. Dopiero ten odbiór wraz z review
pozwala człowiekowi osobno zdecydować o merge. Workflow nigdy nie merguje.

## Odświeżenie, zamknięcie i awarie

`refresh` wymaga numeru PR i dokładnego expected_head. To jawna zgoda na
ponowne przygotowanie kandydata od bieżącego main: nowe wejście i katalog
paczki, wszystkie decyzje pending, ponowny przegląd źródła/preimages.
Poprzednie commity pozostają przodkami nowego HEAD; brak force-push.
Edycje proposals.yml są przenoszone tylko po ponownym sprawdzeniu kompletu
change_id, celów, preimages i akcji. Jeśli źródło/main je unieważniły,
przebieg odmawia zapisu. Przywróć propozycje zgodne z bieżącym raportem;
nie kopiuj poprzednich approve do nowej podstawy bez review.

Jeśli świeże porównanie jest no-op, workflow pozostawia otwarty PR bez
zmian. Operator rozstrzyga jego zamknięcie. Zamknięcie bez merge nie
przesuwa main ani przyjętego snapshotu; następne prepare ponownie pokaże
nieprzyjęte zmiany. Zamkniętych gałęzi automat nie nadpisuje ani nie usuwa.

Po awarii przed push main i PR są niezmienione. Po push, ale przed
utworzeniem PR, następne prepare rozpoznaje jedną osieroconą gałąź i
odzyskuje dokładnie jej HEAD, bez nowego źródła/paczki. Przy kilku
osieroconych gałęziach potrzebne jest rozpatrzenie przez operatora.
Jeśli main przesunął się w czasie awarii, operator może otworzyć draft
z zachowanej gałęzi i wykonać jawne refresh z aktualnego main.

Preferowane ponowienie to **nowy dispatch z bieżącego main**. Można też
ponowić oba joby przy niezmienionym main. Samo „Re-run failed jobs” po
awarii publishera nie odtwarza artefaktu nowej próby (nazwa zawiera attempt)
i zakończy się brakiem transferu; nie zmienia to zachowanej gałęzi.

Przed każdym push ponownie sprawdzane są uprawnienia/kontekst, main,
otwarty PR i oczekiwany HEAD. Zwykły push odrzuca rozbieżną gałąź.
Artefakt transferowy jest związany z repo/run/operatorem/SHA i ma hash
bundle. Publisher ponownie odtwarza cały wynik danych; checkoutuje tylko
main, nie wykonuje kodu ani zależności PR. Paczki Actions mają retencję
14 dni; surowe źródło/decyzje i ich historia są w Git gałęzi.
