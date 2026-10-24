# PBI-115 — błędne punkty systemów i czytelne statystyki

> Realizacja uzgodniona z użytkownikiem 2026-10-24 po `/grill me`.
> Plan wykonujemy w bieżącej sesji; zapis utrwala zaakceptowany zakres.

**Cel:** usunąć dwa rekordy katalogowe błędnie potraktowane jako otwory
i pokazać sposób wyznaczenia pozycji niezależnie od źródła danych.

**Baza:** main `7cb6312a5cd7d91fd772e347d7fe079abbb661bb`.
**Spec:** specyfikacja projektu §3–4, §7.2 i §13; decyzje poniżej
doprecyzowują usunięcie błędnie utworzonych obiektów, a nie odrzucanie
prawidłowych pomiarów istniejącego otworu.

## Zakres i decyzje

- Usunąć `KSZ-0009` i `MLZ-0029` wraz z ich pojedynczymi pomiarami.
  Użytkownik odrzucił dodatkowe archiwum oraz przenoszenie pomiaru do Mylnej.
  Źródłowe pliki PIG i historia Git pozostają źródłami pierwotnych wpisów.
- Zachować `C-0095` i `C-0295`, ustawić puste `object_ids`, wyjaśnić
  katalogowy charakter i wskazać istniejące składowe w notes. Docelowy model
  systemów, normalizacja ich powiązań i innych dużych jaskiń: issue #34.
  Nie wdrażać teraz nowego modelu relacji ani grupowania wszystkich systemów.
- Bilans: 1024 obiekty, 1019 pozycji katalogowych, 1926 pomiarów.
  Wszystkie pozostałe obiekty, pomiary i wskazania Best pozostają identyczne.
- Dodać `by_position_method` do obu części `statistics.json` i osobną tabelę
  PL/EN/SK w `statistics.md`. Zachować istniejące pola i schema version 1;
  jest to rozszerzenie addytywne, bez zmiany schematu danych źródłowych.
- Metoda pochodzi z pomiaru w pakowanej SQLite. Wybrane pomiary identyfikuje
  para `object_id` + `measurement_id` z CSV; statystyki nie wybierają Best.
  Brak tej pary w SQLite ma przerwać generowanie raportu.
- Jawna metoda ma pierwszeństwo. `ustalenie` z oboma tagami `lidar`
  i `gnss_anchor` prezentować jako `lidar_gnss`; `source_record` z tagiem
  `survey_anchor` jako `survey_anchor`; pozostałe jako zapisane `method`.
  Sam `gnss_anchor` nie stanowi bezpośredniego pomiaru GNSS.
- `wlasne` prezentować jako „Opracowania własne”. Opisać różnicę źródła,
  sposobu wyznaczenia, weryfikacji i dokładności. GNSS nie nazywać
  geodezyjnym bez udokumentowanego rodzaju pomiaru.
- Mechanizm nieużywania wycofanych ID jest odłożony do issue #33.
- Osobno, na istniejącym PR Georeferencera #5, dopuścić kategorie
  `jaskinia_otwor` i `sztolnia`; pozostałe nadal odrzucać. Oba poprawione
  wcześniej dowiązania planów pozostają. Brak merge, taga i publikacji.

## Wykonanie i weryfikacja

- [ ] Usunąć dwa obiekty, poprawić dwie pozycje katalogowe; porównać
  pozostałe dane bajtowo i potwierdzić bilans oraz brak przeniesionych pomiarów.
- [ ] RED: integracyjny test statystyk z historią i ręcznie wskazanym Best,
  dwiema klasami ustalenia, kotwicą, GNSS i siecią; puste dane i brak pary
  CSV/SQLite. GREEN: minimalna implementacja w `release_statistics.py`.
- [ ] Uzupełnić specyfikację, backlog, context i log PBI-115.
- [ ] Uruchomić Ruff, pełny pytest, walidację YAML i build wszystkich formatów.
  Niezależnie odczytać artefakty, liczniki, metody i Best; sprawdzić odbiorców.
- [ ] Wykonać celowane mutacje nowej klasyfikacji i łączenia pomiarów.
- [ ] Niezależnie przejrzeć końcowy diff; commit, push, draft PR,
  CI dokładnego SHA oraz odczyt paczki preview.

## Najważniejsze przypadki kontrolne

- Starszy ręczny Best ma być liczony zamiast nowszego pomiaru innej metody.
- To samo lokalne `m-001` w różnych obiektach nie może pomylić metod.
- `gnss_anchor` przy sieci ani samodzielnie nie oznacza bezpośredniego GNSS.
- Brak dokładności i status nieweryfikowany nie są dowodem rodzaju GNSS.
- Pusta pozycja katalogowa nie wytwarza punktu w żadnym eksporcie.
- Dwa usunięte rekordy nie mogą pozostać w Best ani Full; Georeferencer
  po poprawce ma rozwiązać wszystkie 814 metadanych, JKTZ wszystkie 87 mapowań.
