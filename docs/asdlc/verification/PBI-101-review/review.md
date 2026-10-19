# PBI-101 — końcowe rozstrzygnięcia jednej paczki

Jawne decyzje użytkownika: **614 approve / 26 defer / 0 pending**. Zapis techniczny i wykonawczy: **agent:codex**, bez podpisu imieniem użytkownika. Zlecono commit/push do PR #12 oraz odbiór końcowego SHA; bez merge i bez PBI-102.

| Zakres | Rozstrzygnięcie | Skutek |
|---|---|---|
| A001–A578 | approve, actions=[] | Przyjęcie rewizji źródła bez zmiany katalogu; 573 auto i 5 manual zachowane |
| B001–B031 | approve append + osobno select_new auto | 31 nowych pomiarów; poprzednia historia bez zmiany wartości i kolejności |
| C001–C005 | approve create_cave + new_object | 5 nowych Obiektów i 5 Jaskiń; pierwszy pomiar best auto |
| D001–D026 | defer | Trwała kolejka z indywidualnymi powodami; bez nowych obiektów, przypisania źródeł ani scalania |

## Podstawa i zachowanie historii

Snapshot pbi-101-live-20261019, 1035 rekordów, hash 481e83a1a113a0596947d40e30d7a186de0f0f51154957c5f48713c4ae3324d8. Utrwalony w Git przed danymi w 60afeca2d17bbc4b5aa690abc83da1d25d89a506. Przyjęta baza wyłącznie origin/main b98fd3febb400c7ee520046682c1bb16238429ee; brak historycznego build jako wejścia.

Pierwszy niezaaplikowany raport z wariantem keep i jego decyzje zachowano bajtowo w [superseded-v1](superseded-v1/README.md). Aktualna rewizja tej samej paczki wiąże zaakceptowany select_new i jawne [zasady precyzji pochodnych](../../tpn_sync_derived_precision.md). Pełne dane API, ich revision/change_id, klasyfikacje, cele, preimages i zbiory kandydatów wszystkich 1035 rekordów są zgodne z pierwszym review.

Nowe pomiary pozostają nieweryfikowane, bez wysokości i znanej dokładności. Daty oznaczają stan źródła, z notą o nieznanej dacie terenowej. Nowe cache PL-1992 są zapisane z precyzją 1 mm; API WGS84 i stare pomiary pozostają bez zmian. Manifest PBI-099 nadal pending; brak migracji chronionych auto→manual.

## Zgody użytkownika

- [B31 i C5](user-decisions-20261019.json): nowe lokalizacje best auto i 5 nowych obiektów.
- [A578](user-decisions-A-20261019.json): przyjąć rewizje bez zmian katalogu.
- [D26 i dostarczenie](user-decisions-D-20261019.json): odroczyć do niezależnego badania, commit/push, końcowe CI i eksporty.

## 31 dopisań i odrębny wybór best

| ID | Obiekt | Dotychczasowy best | Nowy best | Tryb |
|---|---|---|---|---|
| B001 | [MTW-0031](../../../../data/objects/MTW/MTW-0031.yml) — Dziura w Kończystej Niżnia | m-002 | m-003 | auto |
| B002 | [MTZ-0031](../../../../data/objects/MTZ/MTZ-0031.yml) — Studnia za Murem | m-002 | m-003 | auto |
| B003 | [MTW-0043](../../../../data/objects/MTW/MTW-0043.yml) — Schron pod Kończystą | m-002 | m-003 | auto |
| B004 | [MTW-0024](../../../../data/objects/MTW/MTW-0024.yml) — Ciasna Norka | m-002 | m-003 | auto |
| B005 | [MTZ-0027](../../../../data/objects/MTZ/MTZ-0027.yml) — Jaskinia Mała w Mułowej | m-002 | m-003 | auto |
| B006 | [MLZ-0079](../../../../data/objects/MLZ/MLZ-0079.yml) — Średni Lej | m-002 | m-003 | auto |
| B007 | [MTW-0021](../../../../data/objects/MTW/MTW-0021.yml) — Koleba za Kończystą | m-002 | m-003 | auto |
| B008 | [KSW-0241](../../../../data/objects/KSW/KSW-0241.yml) — Gawra we Wysrankach | m-001 | m-002 | auto |
| B009 | [MTW-0020](../../../../data/objects/MTW/MTW-0020.yml) — Szara Studnia | m-002 | m-003 | auto |
| B010 | [PL-0022](../../../../data/objects/PL/PL-0022.yml) — Szpara pod Rysami | m-002 | m-003 | auto |
| B011 | [MTW-0046](../../../../data/objects/MTW/MTW-0046.yml) — Bliźniaczy Komin | m-002 | m-003 | auto |
| B012 | [MTZ-0001](../../../../data/objects/MTZ/MTZ-0001.yml) — Schron z Balkonem | m-002 | m-003 | auto |
| B013 | [MLZ-0012](../../../../data/objects/MLZ/MLZ-0012.yml) — Bliźniacza Studnia | m-002 | m-003 | auto |
| B014 | [MTW-0059](../../../../data/objects/MTW/MTW-0059.yml) — Dziura w Kończystej Turni | m-002 | m-003 | auto |
| B015 | [KSW-0147](../../../../data/objects/KSW/KSW-0147.yml) — Jaskinia przy Sikawce | m-002 | m-003 | auto |
| B016 | [MTW-0033](../../../../data/objects/MTW/MTW-0033.yml) — Szczelina na Drodze Steckiego | m-002 | m-003 | auto |
| B017 | [MTW-0035](../../../../data/objects/MTW/MTW-0035.yml) — Dziura w Żlebku | m-002 | m-003 | auto |
| B018 | [MTW-0039](../../../../data/objects/MTW/MTW-0039.yml) — Nyża pod Progiem w Kończystej | m-002 | m-003 | auto |
| B019 | [MTW-0052](../../../../data/objects/MTW/MTW-0052.yml) — Okap w Kończystej Turni | m-002 | m-003 | auto |
| B020 | [MLW-0020](../../../../data/objects/MLW/MLW-0020.yml) — Koprowa Studnia | m-002 | m-003 | auto |
| B021 | [MTW-0065](../../../../data/objects/MTW/MTW-0065.yml) — Mała Dziura w Kończystej Turni | m-002 | m-003 | auto |
| B022 | [MTZ-0018](../../../../data/objects/MTZ/MTZ-0018.yml) — Jaskinia Marmurowa | m-002 | m-003 | auto |
| B023 | [MLW-0014](../../../../data/objects/MLW/MLW-0014.yml) — Zaspałkowa Szczelina | m-002 | m-003 | auto |
| B024 | [MTW-0063](../../../../data/objects/MTW/MTW-0063.yml) — Jaskinia Niska | m-002 | m-003 | auto |
| B025 | [MTW-0017](../../../../data/objects/MTW/MTW-0017.yml) — Schronik w Kończystej Turni | m-002 | m-003 | auto |
| B026 | [MTW-0060](../../../../data/objects/MTW/MTW-0060.yml) — Dziura Niżnia w Kończystej Turni | m-002 | m-003 | auto |
| B027 | [MLW-0028](../../../../data/objects/MLW/MLW-0028.yml) — Jaskinia Świstacza | m-002 | m-003 | auto |
| B028 | [MTW-0057](../../../../data/objects/MTW/MTW-0057.yml) — Dziura pod Ratuszem | m-002 | m-003 | auto |
| B029 | [STR-0028](../../../../data/objects/STR/STR-0028.yml) — Nyża pod Zachodem Pilotów | m-001 | m-002 | auto |
| B030 | [MTW-0005](../../../../data/objects/MTW/MTW-0005.yml) — Nyża w Kończystej | m-002 | m-003 | auto |
| B031 | [MTW-0062](../../../../data/objects/MTW/MTW-0062.yml) — Schronisko Wschodnie w Kończystej | m-002 | m-003 | auto |

Powód wyboru każdego best i audyt są w aktualnych decisions.yml oraz wynikowym YAML. Priorytet nowego punktu jest jawną decyzją użytkownika, nie deklaracją jego dokładności. Wszystkie dawne wysokości pozostają przy dawnych pomiarach.

## Pięć nowych obiektów

| ID | Obiekt | Jaskinia | Best |
|---|---|---|---|
| C001 | MTZ-0067 — Jaskinia w Kozim Grzbiecie | C-1005 | m-001 auto |
| C002 | STR-0030 — Gawra w Sarniej Skale | C-1006 | m-001 auto |
| C003 | BIA-0009 — Okno przy Źródle | C-1007 | m-001 auto |
| C004 | DZI-0011 — Gawra w Grześkówkach | C-1008 | m-001 auto |
| C005 | MTZ-0068 — Jaskinia Lodowa Ponorowa | C-1009 | m-001 auto |

## Odroczenia

[Lista 26 i indywidualne powody](remaining-26.md). Użytkownik odroczył również wcześniejsze propozycje N/J; żadna z nich nie oznacza przyjęcia nowego obiektu. Pełne rewizje źródła i rozstrzygnięcia zachowuje state.json oraz archiwum zastosowania w aktywnej paczce. Kolejka pozostaje widoczna przy niezmienionym API.

## Weryfikacja

Końcowy odbiór dry-run/apply, preflight, replay, diffu, protected/history i eksportów: [PBI-101](../PBI-101.md). Odbiór exact-SHA CI i readback końcowego commitu utrwala opis PR #12. Nie wykonujemy merge, tagu, release ani PBI-102.
