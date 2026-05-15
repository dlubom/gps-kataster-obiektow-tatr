# Schema changelog

## schema_version: 1 - 2026-05-15

- Dodano kontrakty JSON Schema dla plikow YAML `Obiekt`, `Jaskinia` i `Relacja`.
- Ustalono formaty ID: `{PREFIX}-{NNNN}` dla obiektow, `C-{NNNN}` dla jaskin,
  `R-{NNNN}` dla relacji oraz lokalne `m-{NNN}` i `a-{NNN}` dla pomiarow i
  zalacznikow.
- Utrwalono podstawowe enumy domenowe dla kategorii obiektow, zrodel,
  statusow weryfikacji, metod pomiaru, referencji zewnetrznych i typow relacji.
- JSON Schema obejmuje strukture i lokalne warunki pol, ale nie zastepuje
  pozniejszych walidacji cross-reference, geometrii ani algorytmu
  `best_measurement`.
