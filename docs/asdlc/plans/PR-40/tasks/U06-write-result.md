# U06 — wynik atomowego writera

Przeczytaj [indeks](../README.md), [spec](../spec.md), [design](../design.md)
i [development](../development.md). Zależność: U04. Realizuje S05.

## Spec

`catalog_records.write_dataset` zwraca `None`. Dlatego
`staging_review._write_dirty_records` czyta wszystkie YAML przed i po zapisie,
aby ustalić listę zmienionych plików. Ta informacja powinna powstawać u writera,
który już zna stary i nowy dokument.

Wynik ma opisywać rzeczywiste opublikowane zmiany, nie tylko przekazane dirty ID.
Adopcja legacy może zmienić również nie-dirty rekordy. Błąd przed atomową
podmianą nie zwraca wyniku sukcesu; błąd usunięcia starego drzewa po udanym
swap nie zmienia zapisu w błąd, zgodnie z istniejącym kontraktem.

## Design

- Zwróć mały niezmienny `WriteResult` z uporządkowanymi ścieżkami YAML,
  co najmniej `written_paths` (nowe lub zmienione bajty) i `removed_paths`
  (wcześniejsze YAML nieobecne w opublikowanym snapshotcie). Ścieżki odnoszą
  się do docelowego katalogu, nigdy do usuniętego stagingu.
- Zachowaj publiczną kolejność wyniku review: grupy `caves`, `objects`,
  `relations`, `publications`, a wewnątrz każdej grupy sortowanie ścieżek.
- Wylicz różnicę przy serializacji/kopiowaniu/przeglądzie starego drzewa,
  przed swap. Nie przenieś dwóch pełnych skanów przed/po do nowego helpera.
- Marker, `.gitkeep` i kopiowane assety nie są zmianami encji YAML;
  nie dopisuj ich do publicznego `written_paths` review.
- Review mapuje `written_paths` na dotychczasowy wynik. Nie rozszerzaj jego
  publicznego formatu o usunięcia w tej karcie; writer może je wyrazić dla
  bezpośrednich odbiorców. Akcje review nie usuwają encji.
- Zachowaj `changed` jako wskazówkę dla kopiowania niezmienionych rekordów,
  a nie dowód rzeczywistej różnicy. Dry-run nie wywołuje writera.

## Development

1. Rozszerz testy `write_dataset` o nowy/zmieniony/niezmieniony/usunięty
   rekord, oba sufiksy, ponowny identyczny zapis i adopcję legacy.
   Użyj niezależnego porównania bajtów jako wzorca wyniku.
2. W `catalog_records.py::write_dataset` zbierz wynik w istniejącej pętli
   i zwróć go dopiero po opublikowaniu nowego drzewa.
3. Zastąp skan przed/po w `staging_review.py::_write_dirty_records`.
   Sprawdź wszystkich odbiorców `write_dataset`, również maintenance/testy.
4. Zachowaj `_ordered_like`, niezmienione bajty, assety/symlinki assetów,
   źródłową geometrię, ordinal i reguły atomowego zapisu.
5. Odtwórz błąd serializacji/swap oraz błąd cleanup po swap. W raporcie
   pokaż usunięte pełne skany i bilans kodu; nie obiecuj usunięcia odczytów,
   które nadal są konieczne do zachowania kolejności i porównania bajtów.

```bash
uv run --frozen pytest -q tests/test_catalog_source_model.py tests/test_catalog_yaml.py tests/test_staging_review.py tests/test_catalog_publication_regressions.py tests/test_restore_tpn_notes.py
```

## Odbiór

- [x] Wynik zgadza się z rzeczywistymi zmianami bajtów i usunięciami, jest
  deterministyczny, pusty dla identycznego zapisu i poprawny przy adopcji legacy.
- [x] `written_paths` review zachowuje publiczną semantykę, również dla
  zmienionych podczas migracji rekordów poza dirty ID.
- [x] Nie ma pełnego odczytu YAML po zapisie tylko po to, aby odtworzyć wynik.
- [x] Błędy przed swap zachowują poprzednie pliki, cleanup po swap zachowuje
  sukces; dry-run nie zapisuje. Pełna bramka/porównanie/CI przechodzą.

### Wynik implementacji i odbioru

Baza refaktoru: `b3037b36cc6594af922390a68fb9fbdb412426ae` — bieżący head
otwartego draft PR przy rozpoczęciu. Osobna zaakceptowana baza historii:
`ad5fa191a36d5a5f45f0b2de523bd39125827573`, potwierdzona jako base PR i `origin/main`.
Zależności U01–U05 potwierdzono w kodzie; zakres nie wymagał ich zmian.

`WriteResult` jest zamrożonym kontenerem dwóch krotek ścieżek docelowych.
Writer zbiera stare YAML podczas dotychczasowego kopiowania assetów,
odejmuje opublikowane ścieżki i porównuje serializowane bajty przed swap.
Zwraca wynik po publikacji i cleanup; nie dodaje drugiego skanu do helpera.
Review używa tylko `written_paths`; maintenance i pozostali odbiorcy mogą
nadal ignorować wynik. Publiczny raport nie otrzymuje pola usunięć.
Zachowano `_ordered_like`, sufiksy, kopiowanie niezmienionych bajtów,
assety i ich symlinki, geometrię źródłową, ordinal oraz ochronę historii.

- Bazowy zestaw karty: **321 PASS**. Nowe/rozszerzone przypadki przed zmianą:
  **9 FAIL / 5 PASS**; błędy wskazały brak wyniku lub odczyt po swap.
  Po zmianie: **14 PASS**. Obejmują oba sufiksy, nowy/zmieniony/niezmieniony/
  usunięty plik, niezależny wzorzec bajtów, powtórzenie, adopcję legacy poza
  dirty ID, pierwszy zapis, serializację/swap/cleanup oraz dry-run.
  Pełny zestaw karty po zmianie: **333 PASS**. Niezależne review nie znalazło
  ustaleń Critical/Important/Minor ani zachowań odłożonych bez oceny.
- Pełna bramka `scripts/check_project.py` z powyższą bazą historii:
  **1321 PASS / 1 SKIP**, Ruff format/lint, historia, build, natywne
  odtworzenie dumpa, odczyt GeoPackage i diff PASS. Skip to jawnie wyłączony
  lokalny smoke zarządzanego Dockera; ma przejść oddzielnie w wymaganym CI.
- Pomiar produkcyjnego review na tych samych trzech YAML przed/po:
  **8 → 0** przejść katalogów `rglob` (dwa pełne skany czterech grup),
  **6 → 2** odczytów bajtów dla kanonicznej edycji oraz **6 → 3** dla
  adopcji legacy; po swap **3 → 0**. Publiczne ścieżki przed/po identyczne.
  Odczyty do parsowania/kolejności pól i kopiowania plików nadal występują.
- Pełny build przed/po z tym samym czasem, wersją i commitem metadanych:
  **13/13 formatów zgodnych** po niezależnym odczycie wszystkich wartości,
  typów/null, geometrii, CRS i deklaracji; oba dumpy odtworzone natywnie.
  Normalizowano wyłącznie nagłówki/czasy kontenerów ZIP, datę nagłówka DBF,
  czas utworzenia GeoPackage i losowy token klienta dumpa. Dane tekstowe
  porównano także bajtowo; liczby: **1029 obiektów / 1019 jaskiń / 1946 pomiarów**.
  Wszystkie **4185 diagnostyk** (kod, severity, ścieżka, kolejność i treść)
  są identyczne; normalizacja ścieżki usuwała wyłącznie różny korzeń checkoutu.
- Bilans względem bazy: Python produkcyjny **+31/−14, netto +17**,
  identyczny po pominięciu białych znaków; SQL/schematy **0**.
  Testy: **+223/−3**; dokumentacja: **+113/−11**, liczona osobno od produkcji.
  Usunięto oba pełne skany; mały wynik i księgowanie ścieżek zwiększają kod.
  Brak zmian `data/`, `config/`, `schema/` i workflow.

Kod U06: `c4f4cb43c662cdd8735ce37e2821eb60bc26d94c`, dostarczony fast-forward
do istniejącej gałęzi PR. [Preview](https://github.com/dlubom/gps-kataster-obiektow-tatr/actions/runs/42115609863)
zakończone **SUCCESS** w próbie 2. Pierwsza próba została anulowana po limicie
jobu: mirror Ubuntu pobierał 37,7 MB przez 15 min 28 s przy 40,6 kB/s.
Ponowiono wyłącznie job preview na tym samym SHA, bez zmian workflow.

[Paczka 13456273143](https://github.com/dlubom/gps-kataster-obiektow-tatr/actions/runs/42115609863/artifacts/13456273143)
ma SHA-256 `db7f603e09cada261e17ce6ab77a51147c376aea78989c53dc4cf3dd2d1231a8`
zgodny z GitHub; sprawdzono **14/14 sum**, head/base, merge
`409d4cae4eeeea586a06549e71c002f010dcca52`, jego obu rodziców, run i próbę.
Pełny odczyt **13/13 formatów** porównano z buildem bazy refaktoru o metadanych
preview. Dane źródłowe, typy/null, kolejność, cytowania i manual Best są zgodne
ściśle. **21982** pochodnych wartości EPSG:2180 porównano z tolerancją `1e-8 m`;
maksymalna różnica to `1.9208528101444244e-9 m`.

Między runtime lokalnym i CI dodatkowo normalizowano komentarze wersji
klienta dumpa i składnię równoważnych deklaracji RTree GDAL. Warianty triggerów
sprawdzono na kopiach przez zmianę geometrii/FID, null, usuwanie i dodawanie.
Fizyczne strony indeksu SQLite zastąpił niezależny rebuild z każdej geometrii,
porównanie wszystkich granic oraz `rtreecheck`. W XLSX wartości komórek
porównano wraz z typami/formatami, osobno od zapisu liczby w XML. Pozostałe
wyłączenia technicznych metadanych są wymienione przy porównaniu lokalnym.

[Validate code and data](https://github.com/dlubom/gps-kataster-obiektow-tatr/actions/runs/42115609731)
dla kodu ma terminalny **SUCCESS**: **1320 PASS / 2 SKIP**; oddzielny
wymagany smoke zarządzanego Dockera: **1 PASS** (start, dump, restore i cleanup).
Odbiór, dokumentacja oraz status U06 są zakończone; końcowy commit zmienia
wyłącznie kartę i indeks. Jego zdalny SHA oraz terminalne CI/preview wskazuje
opis PR. Zachowano draft, bez merge, taga i wydania; U07 nie rozpoczęto.

Zakończ po U06. Następna karta: [U07](U07-production-path-tests.md).
