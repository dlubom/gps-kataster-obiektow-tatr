# Backlog

## Issue #43: Pomiary Marka Jędrzejczaka z poprawionego XLS

Status: przygotowano do wydania v1.3.3 w [PR #44](https://github.com/dlubom/gps-kataster-obiektow-tatr/pull/44).
Zakres obejmuje 12 zweryfikowanych
pomiarów z ręcznym Best, drugi otwór Koziej i archiwum źródeł.
Weryfikacja obejmuje zgodność z arkuszem, zachowanie historii pomiarów
i odczyt eksportów. [Zgłoszenie #43](https://github.com/dlubom/gps-kataster-obiektow-tatr/issues/43).


## PBI-119: Migracja PostgreSQL/PostGIS

Status: do review w [draft PR #40](https://github.com/dlubom/gps-kataster-obiektow-tatr/pull/40).
Katalog jest edytowany w YAML. Tymczasowy PostgreSQL/PostGIS zastępuje SQLite. Reguły, Best i współrzędne pochodne wylicza baza; kontrola
historii porównuje pomiary z zaakceptowaną rewizją Git. Dump i GeoPackage
zastępują SQLite/ZIP, pozostałe formaty zachowują kontrakty odbiorców.
Merge i wydanie pozostają poza zleceniem. Bieżące wyniki weryfikacji są
w opisie PR; [model](../../specyfikacja_gps_kataster_obiektow_tatr_v_2.md),
[diagramy](../architecture/schema.md), [obsługa](../operations.md).

U01: zaimplementowano wspólne, niezmienne dane eksportowe przygotowywane
raz na build. Best, Excel, GeoPackage i statystyki używają tego samego
`ExportData`; historia nie dziedziczy wartości pomiaru Best, a GeoPackage
korzysta z neutralnych deklaracji pól.

U02: zaimplementowano jawne granice źródła YAML, propozycji, istniejącego
katalogu PostgreSQL i zaakceptowanej historii Git. Wspólne kontrole obsługują
build i CLI bez ponownego ładowania sprawdzonego stanu; ówczesne review
usunięto w U12. Zachowano
reguły, diagnostykę i eksporty U01. Odbiór eksportów i CI w opisie PR.

[U03–U11: dalsze uproszczenia](plans/PR-40/README.md) mają osobne karty Spec,
Design i Development oraz wspólną procedurę odbioru. Indeks zawiera statusy,
zależności i prompt do nowej sesji. Są to podzadania PBI-119, wykonywane
pojedynczo na polecenie użytkownika. U03 oznacza kompletność wejścia;
fazy wdrożone jako U02 nie są ponownie zlecane. Wynik kontroli kompletności
jest w [karcie U03](plans/PR-40/tasks/U03-input-completeness.md#odbiór).
Źródłowy model zmian, granice deklaracji staging i odbiór są opisane
w [karcie U04](plans/PR-40/tasks/U04-canonical-proposals.md#odbiór).
Regiony SQL dla grup GPX i odbiór eksportów opisuje
[karta U05](plans/PR-40/tasks/U05-spatial-read-model.md#odbiór).
Wynik atomowego writera i skany ówczesnego review opisuje
[karta U06](plans/PR-40/tasks/U06-write-result.md#odbiór).
Fixtures kanoniczne, bezpośrednie wejścia API/CLI i osobne testy migracji
opisuje [karta U07](plans/PR-40/tasks/U07-production-path-tests.md#odbiór).
Wspólne parsowanie, formatowanie i odrębne kontrakty CSV opisuje
[karta U08](plans/PR-40/tasks/U08-shared-helpers.md#odbiór).
Wspólne kolejne ID, rezerwacje partii i pomiary lokalne dla obiektu opisuje
[karta U09](plans/PR-40/tasks/U09-id-allocation.md#odbiór).
Builder, CLI i paczkowanie używają jednego zestawu artefaktów; lista ścieżek
z separatorem NUL przekazuje 13 ścieżek do workflow bez drugiego spisu. Wspólne argumenty
CLI zachowują politykę diagnostyki; [karta U10](plans/PR-40/tasks/U10-artifacts-and-cli.md#odbiór)
zawiera kontrakt i odbiór. Status pozostaje w indeksie.
Wspólną instalację runtime czterech workflow posiada lokalna composite action;
zdarzenia, uprawnienia, serwisy i rzeczywisty baseline pozostają u odbiorców.
[U11](plans/PR-40/tasks/U11-ci-setup.md#odbiór) opisuje zakres i dowody;
status jest wyłącznie w indeksie.

Zakres po korekcie użytkownika 2026-11-06: [plan czyszczenia](plans/PR-40/next/README.md)
usuwa zakończone importy i zbędne ścieżki. Aktywne karty to U12, U15–U17;
U13/U14 wyłączono z zakresu. Nie wprowadzamy rejestru ID ani nowych zasad
usuwania. Obecna ochrona historii pozostaje bez zmian. [Odbiór U12](plans/PR-40/next/U12-remove-imports.md#odbiór)
opisuje wykonane usunięcie; [U15](plans/PR-40/next/U15-remove-writers-legacy.md)
usuwa writer i bieżące propozycje legacy, zachowując starszą historię.
Statusy i zależności są wyłącznie w nowym indeksie.


## Zadania odłożone

Poniższe tematy pozostają poza serią uproszczeń PR #40. Stan otwartych PR
oraz issues sprawdź przed wznowieniem pracy.

| Zakres | Punkt kontynuacji |
|---|---|
| PBI-118, paczka QGIS | Osobny [PR #39](https://github.com/dlubom/gps-kataster-obiektow-tatr/pull/39); nie włączać do PBI-119. |
| PBI-110, wywierzyska | [Projekt](plans/PBI-110-design.md) do akceptacji; nie przypisywać nierozstrzygniętego punktu Bystrej. |
| Odroczone obiekty TPN | [PBI-113](plans/PBI-113-new-tpn-objects.md); wymagana ocena wskazanych niejednoznaczności. |
| Ponowne użycie wycofanych ID | [Issue #33](https://github.com/dlubom/gps-kataster-obiektow-tatr/issues/33); rejestr wyłączony z bieżącego planu |
| Systemy i historyczne części jaskiń | [Issue #34](https://github.com/dlubom/gps-kataster-obiektow-tatr/issues/34) |
| Położenie głównego otworu Mylnej | [Issue #36](https://github.com/dlubom/gps-kataster-obiektow-tatr/issues/36) |

Decyzje o źródłach oraz ich ograniczenia podsumowuje [kontekst](context.md).
Wdrożone zachowanie opisują specyfikacja i instrukcja operacyjna; historię
wydań — [CHANGELOG](../../CHANGELOG.md) i opisy PR.

## Naprawy main po przegladzie 2026-10-12

PBI-078–086 zakończono w PR #4 i v1.0.3; [odbiór](verification/v1.0.3.md).
Zachowane dowody: [raport R1–R8](reviews/main-review-2026-10-12.md),
[ocena źródeł](reviews/data-decisions-2026-10.md) oraz poniższe logi.

| PBI | Zakres i dowód |
|---|---|
| [078](verification/PBI-078.md) | Rozpoczęcie nowej serii z main |
| [079](verification/PBI-079.md) | Brakujące wejście danych |
| [080](verification/PBI-080.md) | Powtórzone klucze YAML |
| [081](verification/PBI-081.md) | Walidacja całej partii review |
| [082](verification/PBI-082.md) | Zachowanie kontekstu pomiarów TPN |
| [083](verification/PBI-083.md) | Kategorie i rozbieżności katalogu |
| [084](verification/PBI-084.md) | NaN i Infinity |
| [085](verification/PBI-085.md) | Lokalne ID pomiarów |
| [086](verification/PBI-086.md) | Powiązanie obiektu z jaskinią |

PBI-034–077 dotyczą porzuconej serii; nie przenosimy jej zmian ani statusów.
Pełne historyczne karty, kryteria i listy przebiegów są w
[backlogu przed migracją](https://github.com/dlubom/gps-kataster-obiektow-tatr/blob/13d734213328e5491c1a5c3171e2cb0fdcef705c/docs/asdlc/backlog_v1.md).
