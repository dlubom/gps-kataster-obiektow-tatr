# Backlog

## PBI-119: Migracja PostgreSQL/PostGIS

Status: do review w [draft PR #40](https://github.com/dlubom/gps-kataster-obiektow-tatr/pull/40).
YAML v2 pozostaje źródłem prawdy. PostgreSQL/PostGIS zastępuje SQLite;
baza odpowiada za reguły, Best i współrzędne pochodne, a Git za baseline historii.
Dump i GeoPackage zastępują SQLite/ZIP. Zakończone importery, writer i
propozycje zmian są usunięte; program służy odczytowi, walidacji i eksportom.

Aktualne zachowanie opisują [model](../../specyfikacja_gps_kataster_obiektow_tatr_v_2.md),
[diagramy](../architecture/schema.md) i [obsługa](../operations.md).
Wyniki weryfikacji są w PR. Merge i wydanie wymagają osobnego polecenia.

## Zadania odłożone

Poniższe tematy pozostają poza serią uproszczeń PR #40. Stan otwartych PR
oraz issues sprawdź przed wznowieniem pracy.

| Zakres | Punkt kontynuacji |
|---|---|
| PBI-118, paczka QGIS | Osobny [PR #39](https://github.com/dlubom/gps-kataster-obiektow-tatr/pull/39); nie włączać do PBI-119. |
| PBI-110, wywierzyska | [Projekt](plans/PBI-110-design.md) do akceptacji; nie przypisywać nierozstrzygniętego punktu Bystrej. |
| Odroczone obiekty TPN | [PBI-113](verification/PBI-113.md); wymagana ocena wskazanych niejednoznaczności. |
| Ponowne użycie wycofanych ID | [Issue #33](https://github.com/dlubom/gps-kataster-obiektow-tatr/issues/33); rejestr wyłączony z bieżącego planu |
| Systemy i historyczne części jaskiń | [Issue #34](https://github.com/dlubom/gps-kataster-obiektow-tatr/issues/34) |
| Położenie głównego otworu Mylnej | [Issue #36](https://github.com/dlubom/gps-kataster-obiektow-tatr/issues/36) |

Decyzje o źródłach oraz ich ograniczenia podsumowuje [kontekst](context.md).
Wdrożone zachowanie opisują specyfikacja i instrukcja operacyjna; historię
wydań — [CHANGELOG](../../CHANGELOG.md) i opisy PR.
