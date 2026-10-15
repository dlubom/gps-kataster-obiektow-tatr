# Plan napraw main — 2026-10-15

**Cel:** usunąć R1–R8 w kolejności trzy P1 → dane → pozostałe P2.
**Status:** plan wykonany; PR #4 zmergowany, v1.0.3 opublikowane.
Punkt startowy nowej pracy to aktualny `main`; [odbiór](verification/v1.0.3.md).
PBI-078 obejmuje tylko planowanie; realizację i statusy PBI-079–086 określa
[backlog](backlog_v1.md#naprawy-main-po-przegladzie-2026-10-12).
Podczas realizacji wykonawca używał `superpowers:executing-plans`, po jednym
gotowym PBI na sesję, według [runbooka](remediation_runbook.md).

## Baza i decyzja zakresu

2026-10-15 użytkownik polecił rozpocząć nową serię z main i porzucić
poprzednie gałęzie. `codex/main-remediation-2026-10` utworzono po fetch
z `origin/main` = `a3dd1a671d3d93cd6958242fc68ddcf1d37cf846`.
Porzucona `codex/review-remediation` wskazywała
`7ea802ba29d81ba47da080050ce0b3e71b2389d5`.

PBI-034–077 pozostają historycznymi identyfikatorami, bez przenoszenia
statusów lub zakresu na nową bazę. Nie usuwamy refów ani nie wykonujemy
merge/cherry-pick starej serii. Nowe niezależne ustalenia wymagają
reprodukcji na aktualnej gałęzi i własnej karty.

## Kontrakt wspólny

- Zachowujemy YAML jako źródło prawdy i przepływ staging → decyzje →
  walidacja → SQLite/eksporty, bez synchronizacji lub frontendu.
  Obowiązuje [spec v2](../../specyfikacja_gps_kataster_obiektow_tatr_v_2.md),
  zwłaszcza §4, §6–9, §11–13; stos i schema_version 1 pozostają bez zmian,
  chyba że konkretne PBI uzasadni jawną zmianę specyfikacji.
- ID są trwałe; historia pomiarów, surowe CSV/XLSX i geometrie referencyjne
  muszą być zachowane. R1–R3/R5–R7 to reprodukcje luk kodu, nie wykryte
  uszkodzenia obecnego katalogu.
- Finalne dane mogą zmienić wyłącznie PBI-082–083, według manifestów
  plików/pól i dowodów. Pozostałe PBI zachowują `data/` bajtowo.
- Odległość, wspólna geometria i `WERYF` nie uzasadniają automatycznej
  zmiany lokalizacji, best ani statusu. `nieweryfikowany` nie oznacza błędu.
- PBI-081 korzysta z obecnych reguł walidatora; skończoność liczb,
  unikalność pomiarów i symetria mają osobne karty PBI-084–086.
- Doprecyzowania kontraktów należą do spec/docs tego samego PBI.
  Zmiana granic V1 lub decyzja terenowa wymaga odrębnej decyzji.

## Podstawa i odbiór

[Raport R1–R8](reviews/main-review-2026-10-12.md) i
[zapis JSON](reviews/main-review-2026-10-12.json) są przenośną podstawą kart.
Backlog mapuje każde ustalenie na zakres, zależności, interfejs i sprawdzalne
kryteria. Runbook definiuje bramkę, dowody i dostarczenie z CI dla danego SHA.
Praktyki AS-DLC: [PBI Authoring](https://asdlc.io/practices/pbi-authoring),
[Micro-Commits](https://asdlc.io/practices/micro-commits).
