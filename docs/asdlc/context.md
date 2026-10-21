# Bieżący kontekst projektu

Stan dokumentacji: 2026-10-21. Przed pracą sprawdź aktualny Git i PR;
poniższy opis nie zastępuje odczytu zdalnej gałęzi.

## Gdzie szukać informacji

- [Specyfikacja](../../specyfikacja_gps_kataster_obiektow_tatr_v_2.md) określa
  model i wymagania; [AGENTS](../../AGENTS.md) zasady pracy i dostawy.
- [Backlog V1](backlog_v1.md) jest indeksem prac. Szczegółowe statusy i
  kryteria integracji są tylko w [backlogu TPN](tpn_sync_backlog.md).
- [Operacje](../operations.md) opisują pomiary, walidację i wydania;
  [artefakty](../release_artifacts.md) formaty eksportów i podgląd PR.
- [Start pracy z TPN](tpn_sync_handoff.md) prowadzi do kontraktu, CLI,
  instrukcji operatora i dowodów. Raporty PBI zapisują historyczny odbiór,
  nie polecenia następnej sesji.

## PR #12

[PR #12](https://github.com/dlubom/gps-kataster-obiektow-tatr/pull/12)
(`codex/tpn-sync-planning` → `main`) zawiera uzgodnienie danych TPN,
narzędzia synchronizacji i paczki eksportów do przeglądu. Do ludzkiego
merge dane i stan źródła na tej gałęzi są kandydatem do przyjęcia.

Katalog po zatwierdzonym suplemencie D26: **1035 Obiektów, 1027 Jaskiń,
1938 pomiarów; 640 approve / 0 defer / 0 pending**. Pierwotne
614 approve / 26 defer / 0 pending opisują wcześniejszy etap tej samej
paczki. Zachowujemy jego archiwum i źródła.

Najważniejsze dowody:

- [Pierwotna paczka PBI-101](verification/PBI-101.md) i
  [rozstrzygnięcia D001–D026](verification/PBI-101-D26.md).
- [Zatwierdzone przypięcia manual](verification/PBI-099-manual-selection.json):
  KSW-0201/m-003, KSW-0240/m-002, KSZ-0112/m-001. Historyczny manifest
  PBI-099 z decyzjami pending pozostaje niezmieniony; późniejsze zgody
  zapisano osobno. MLW-0050/m-001 chroni decyzja D22 w suplemencie D26.
- [Korekta opisów i bibliografii](verification/PBI-101-notes.md) oraz
  [poprawki po review](verification/PBI-100-review-20261021.md).

Uzgodniony podział uwag: pomiar — pochodzenie i ograniczenia lokalizacji;
obiekt — rozpoznanie i stan otworu; jaskinia — aliasy, morfometria i literatura.
`revision_hash` pozostaje w synchronizacji, poza uwagami; pomiary TPN mają tag
`tpn`. Korekta redakcyjna nie zmienia historii pomiarów ani wyborów best.

Do wykonania pozostaje odbiór produkcyjny ręcznego workflow, a następnie
aktywacja i odbiór cyklu miesięcznego. Szczegóły i warunki:
[PBI-102/103](tpn_sync_backlog.md). Harmonogram jest zaimplementowany,
ale wyłączony; `TPN_MONTHLY_ENABLED` nie ustawiono.

Merge wymaga **zachowania historii commitów** wskazanych w
[warunku odtworzenia paczki](verification/PBI-101-D26.md#warunek-zachowania-historii-przy-merge).
Korekta redakcyjna wymaga także przodka `87a19510580364f96a85edea69e0099ffc4f9a4d`.
Squash/rebase zastępujący te commity uniemożliwia odtworzenie historycznych
kontroli. Merge, zmiana uprawnień Actions i aktywacja harmonogramu wymagają
odrębnych poleceń.

## Pozostałe ustalenia

- YAML w `data/` jest źródłem prawdy; bazy i eksporty są generowane.
  `Obiekt` oznacza konkretny punkt terenowy, `Jaskinia` grupę katalogową.
- [Ostrzeżenia lokalizacji i wspólne best](reviews/data-decisions-2026-10.md)
  wymagają oceny źródeł; sama odległość lub bliskość nie dowodzi błędu ani
  duplikatu. Historyczne liczniki tego raportu nie opisują obecnego katalogu.
- [PBI-082](verification/PBI-082.md) wyjaśnia pominięcie starego wiersza 476
  „Smocza Jama” z powodu niepewnego GLOBALID. Nie uzupełniać go przez zgadywanie.
- Seria PBI-078–086 zakończyła się wydaniem
  [v1.0.3](verification/v1.0.3.md); PBI-034–077 dotyczą porzuconych gałęzi.
  Nie wznawiać ich. Nowsze wydania i poprawki wskazuje [backlog](backlog_v1.md).

Ten plik ma pozostać krótkim opisem aktualnego stanu. Wyniki pojedynczych
uruchomień, hashe i historię realizacji zapisuj w odpowiednim raporcie PBI
lub opisie PR, bez dopisywania ich kopii tutaj.
