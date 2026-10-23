# PBI-111 — pochodzenie pozycji z sieci pomiarowej

Użytkownik zaakceptował 2026-10-23 nazwę `siec_pomiarowa` i realizację
w istniejącym PR #19, wraz z weryfikacją, commitem i pushem.

## Uzgodniony zakres

- `KSZ-0047/m-003`, `KSZ-0090/m-003`, `LEJ-0002/m-003`: metoda
  `siec_pomiarowa`, pozycja wyznaczona z sieci pomiarowej jaskini.
- `KSZ-0064/m-003`: metoda `source_record`, zapisany punkt dowiązania
  sieci Mylnej, bez potwierdzenia pierwotnej metody pomiaru.
- Zachować `source: inne`. Zastąpić błędne GNSS w source_ref, tags,
  elevation_source, notes i uzasadnieniach manual; wskazać historyczne
  źródła JKTZ oraz ograniczenia ich interpretacji.
- Zachować mode manual, ID best, geometrię, wysokości, datum,
  dokładności, daty pomiarów i statusy weryfikacji oraz pozostałą historię.
- Rozszerzyć enum metody w schema_version 1 i specyfikacji; algorytm
  auto i eksporty pozostają bez zmian.

## Rozważone nazwy

Ogólne `ustalenie` nie wyrażało pochodzenia; użytkownik wybrał
`siec_pomiarowa`. Mylna pozostaje `source_record`, ponieważ historyczny
fix jest kotwicą, a nie wynikiem obliczenia z sieci.

## Realizacja i weryfikacja

- [x] Test integracyjny: akceptacja nowej metody, zapis SQLite i eksport,
  manual starszego punktu mimo nowszego TPN. Potwierdzić RED przed schematem.
- [x] Dodać enum, opis semantyki, changelog schematu; poprawić cztery rekordy
  oraz błędną klasyfikację GNSS w backlog/context.
- [x] Potwierdzić GREEN, pełny pytest, Ruff, walidację i eksporty.
- [x] Porównać wszystkie pola z bazą `ea04f3a`; udokumentować ograniczony
  manifest zmian i zgodność z historyczną kompilacją JKTZ.
- Przegląd, commit, push, potwierdzenie HEAD i CI; dokładny wynik dostarczenia
  jest utrzymywany w opisie PR #19.

Dowody: `docs/asdlc/verification/PBI-111-provenance.md`.
