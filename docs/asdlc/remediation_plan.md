# Plan napraw main — 2026-10-15

> Wykonawca: użyj `superpowers:executing-plans`, realizując dokładnie jedno
> gotowe PBI z backlogu. Ten dokument i PBI-078 obejmują wyłącznie planowanie.

**Cel:** usunąć osiem ustaleń R1–R8 z przeglądu main, zaczynając od trzech
P1, następnie naprawić problemy danych, a potem pozostałe P2.

**Architektura:** zachować YAML jako źródło prawdy oraz istniejący przepływ
staging → decyzje → walidacja → SQLite/eksporty. Naprawy dotyczą obecnych
modułów i dowodów źródłowych; nie dodają synchronizacji ani nowego frontendu.

**Stos:** Python >=3.12, uv, pytest, Ruff, PyYAML, JSON Schema, PyProj,
pyshp, sqlite3. Schemat danych pozostaje w wersji 1, o ile konkretne PBI
nie wykaże konieczności jawnej zmiany specyfikacji.

**Specyfikacja:** [spec v2](../../specyfikacja_gps_kataster_obiektow_tatr_v_2.md),
szczególnie §4, §6–9 i §11–13. Szczegółowe karty i jedyne bieżące statusy
są w [backlogu](backlog_v1.md#naprawy-main-po-przegladzie-2026-10-12).

## Decyzja o nowym początku

2026-10-15 użytkownik polecił rozpocząć z nowej gałęzi świeżego main
i porzucić istniejące gałęzie. Ta decyzja zastępuje wcześniejszy nakaz
kontynuowania `codex/review-remediation`.

- Nowa gałąź: `codex/main-remediation-2026-10`.
- `git fetch origin` potwierdził bazę main:
  `a3dd1a671d3d93cd6958242fc68ddcf1d37cf846`.
- Porzucona seria `codex/review-remediation` miała przy odczycie origin SHA
  `7ea802ba29d81ba47da080050ce0b3e71b2389d5`.
- PBI-034–077 pozostają historycznymi identyfikatorami starej serii.
  Nie przepisujemy ich statusów „wykonane” na nową gałąź i nie nadajemy
  tych numerów ponownie. Zachowany commit pozwala odczytać historię.
- Porzucenie oznacza wyłączenie z realizacji, nie usuwanie zdalnych refów,
  przepisywanie historii ani automatyczny merge/cherry-pick.
- Otwarte pozycje starej serii nie są automatycznie częścią nowego zakresu.
  Nowe niezależne ustalenie wymaga reprodukcji na tej gałęzi i własnej karty.

## Ograniczenia wspólne

- ID obiektów są trwałe; zachowujemy historię pomiarów, źródłowe CSV/XLSX
  i pliki geometrii referencyjnej.
- R1–R3 i R5–R7 to odtworzone luki kodu. Nie oznaczają, że bieżące YAML
  zawierają syntetyczne uszkodzenia użyte w reprodukcjach.
- Zmiany finalnych danych są dozwolone wyłącznie w PBI-082–083, w granicach
  jawnego manifestu plików/pól i dowodów. Pozostałe PBI zachowują `data/`
  bajt w bajt.
- `nieweryfikowany` nie oznacza błędu. Statusu pomiaru, lokalizacji ani
  `best_measurement` nie zmieniamy automatycznie na podstawie odległości,
  powtarzającej się geometrii lub samego źródłowego pola `WERYF`.
- PBI-081 używa istniejących reguł walidatora; dodatkowe reguły liczb,
  unikalności pomiarów i symetrii należą kolejno do PBI-084–086.
- Każda karta wskazuje kontrakt specyfikacji. Doprecyzowanie zachowania
  trzeba opisać w spec/docs w tym samym PBI. Zmiana granic V1 lub arbitralna
  decyzja terenowa nie jest rutynową decyzją implementacyjną.

## Priorytety i ryzyka do sprawdzenia

1. Różnica między brakującym wejściem a świadomie przygotowanym pustym
   katalogiem; błąd ma zachować istniejące wyjścia — PBI-079.
2. Duplikaty kluczy na dowolnym poziomie YAML, również w decyzjach,
   oraz użycie aliasów/merge keys bez cichego nadpisania — PBI-080.
3. Błąd w ostatniej decyzji partii, relacje w kompletnym zbiorze oraz
   zgodność dry-run i zapisu — PBI-081.
4. Niejednoznaczny GLOBALID, ponowne uzupełnienie uwag i niejednoznaczna
   kategoria; żadnego dopasowania tylko po nazwie — PBI-082–083.
5. NaN/Infinity, kolizje lokalnego ID i przeniesienie już powiązanego
   obiektu; spójny wynik walidacji, SQLite i eksportów — PBI-084–086.

Każde ryzyko ma kryteria testowe w odpowiadającej karcie backlogu.
Procedurę wykonania i dostarczenia określa [runbook](remediation_runbook.md).

## Podstawa planu

- [Przenośny raport przeglądu](reviews/main-review-2026-10-12.md).
- [Zapis obserwacji](reviews/main-review-2026-10-12.json).
- Praktyki AS-DLC: [PBI Authoring](https://asdlc.io/practices/pbi-authoring)
  i [Micro-Commits](https://asdlc.io/practices/micro-commits).

Karty mają dyrektywę, zależności, odniesienie do specyfikacji i sprawdzalny
odbiór. Ich celem są kompletne zachowania, nie osobne zadania na każde pole.
