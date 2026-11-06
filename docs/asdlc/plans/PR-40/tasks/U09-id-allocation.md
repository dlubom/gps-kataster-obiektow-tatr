# U09 — wspólny mechanizm kolejnych ID

Przeczytaj [indeks](../README.md), [spec](../spec.md), [design](../design.md)
i [development](../development.md). Zależności: U04/U08. Realizuje S08.

## Spec

W bazie zadania `pig_staging` i `tpn_staging` miały kopie `_max_existing_number`,
`scripts/assign_id.py` miał osobny `iter_existing_object_numbers`, a TPN
osobno wyznaczał `_next_measurement_id`. Mechanizm kolejnego numeru jest teraz
wspólny, z różnymi jawnymi przestrzeniami identyfikatorów.

Zachowaj formaty obiektu `PREFIX-NNNN`, jaskini `C-NNNN` i pomiaru `m-NNN`.
Nowy numer to największy zajęty + 1, bez ponownego używania luk. Pomiary
numeruje się osobno dla każdego obiektu. Rezerwacje kandydatów bieżącej
partii zapobiegają kolizjom przed zapisem, bez modyfikowania źródeł w dry-run.
Trwała rezerwacja wycofanych ID z issue #33 pozostaje poza zakresem.

## Design

- Wspólny mały mechanizm przyjmuje istniejące poprawne ID oraz ID już
  zarezerwowane przez bieżący importer. Parser/formater i wyznaczenie kolejnego
  numeru są wspólne; dobór przestrzeni i kolejność kandydatów należą do odbiorcy.
- Odczyt plików jest jednym adapterem. Uwzględnij istniejącą kompatybilność
  suffixów `.yml`, `.yaml`, `.sql` w skanerze nazw, bez rozszerzania loadera
  katalogu o ponowną obsługę SQL. Katalog udający nazwą plik nie rezerwuje ID.
- Nie łącz przestrzeni `C`, prefiksów obiektów i lokalnych pomiarów.
  Nie wprowadzaj globalnego singletona ani stanu rezerwacji poza partią.

## Development

1. Scharakteryzuj oba `_max_existing_number`, `assign_id.next_object_number`
   i przydzielanie ID w partii PIG/TPN; wskaż różnice filtrowania ścieżek.
2. Dodaj przypadki: pusty zbiór, luki, duplikaty, mieszane prefixy/suffixy,
   podobne błędne nazwy, katalog o nazwie `PREFIX-9999.yml`, większa szerokość
   numeru, kilka nowych kandydatów i dwa obiekty z lokalnym `m-001`.
3. Wydziel mechanizm w `src/gps_kataster_obiektow_tatr/` i przełącz
   `pig_staging.py`, `tpn_staging.py`, `scripts/assign_id.py` oraz ich odbiorców.
   Zastosuj jedną politykę ignorowania nazw niebędących plikami.
4. Sprawdź deterministyczną kolejność przydziału w tej samej partii i brak
   kolizji z istniejącymi/proponowanymi encjami. Porównaj raporty przed/po;
   jedyna planowana korekta to ignorowanie katalogu udającego plik ID.
5. Usuń stare skanery i formatery bez odbiorców; uaktualnij opis przydziału,
   nie dopisując gwarancji trwałych tombstone'ów.

### Ustalony zakres przed implementacją

Baza refaktoru: `6054fc9cf12dd8c90826cd0d879a0e49b6657b7b`.
Osobny zaakceptowany baseline historii PR: `ad5fa191a36d5a5f45f0b2de523bd39125827573`.
Zależności U04 (`SourceDataset` / propozycja źródłowa) i U08 (wspólne parsery
i raportowanie) potwierdzono w kodzie i testach; ich kontrakty pozostają bez zmian.

Wyjściowo są trzy skanery nazw: PIG/TPN nie sprawdzają `is_file()`,
`assign_id` sprawdza. Wszystkie rozpoznają `.yml`, `.yaml`, `.sql` i biorą
maksimum, bez wypełniania luk. Importery ponownie skanują prefix przez
gorliwy argument `setdefault`; TPN dodatkowo skanuje go przy seedowaniu
kandydatów. Formattery obiektów/jaskiń i parsery numerów także się powtarzają.

Regresje uruchomione przed zmianą: **5 FAIL** zgodnie z oczekiwaniem.
Trzy przypadki wskazują katalog udający plik; dwa kolejne odtwarzają kolizję
ID pomiaru: kolejne dopasowania do tego samego obiektu dostają np.
`m-004`, `m-004`, zamiast `m-004`, `m-005`.
Rozstrzygnięcie: rezerwacje S08 obejmują też tę kolizję bieżącej partii.
To druga jawna korekta względem opisu kroku 4; zachowanie duplikatu naruszałoby
kontrakt U09. Kolejność dopasowań, dane pomiarów i lokalność ID pozostają bez zmian.
Wspólna polityka błędnych nazw używa pełnego dopasowania ID i dokładnego
suffixu. Ignoruje też nazwę z LF po `.yml`/`.yaml`, którą dawne PIG/TPN
przyjmowały przez kotwicę regex `$`; jest to zgodne z dotychczasowym `assign_id`.
Przypadek jest jawnie objęty regresjami obu importerów.

```bash
uv run --frozen pytest -q tests/test_assign_id.py tests/test_pig_staging.py tests/test_tpn_staging.py tests/test_staging_review.py tests/test_prefixes.py
```

## Odbiór

- [x] Jeden mechanizm wyznacza kolejne numery; wszyscy trzej odbiorcy go używają.
- [x] Istniejące ID i rezerwacje partii nie kolidują; różne obiekty legalnie
  zachowują to samo lokalne ID pomiaru; luki nie są wypełniane.
- [x] Dry-run nie rezerwuje trwale ani nie zapisuje YAML; brak nowych zależności
  od bazy do skanowania nazw.
- [x] Raporty zachowują kolejność i format ID; różnica dla fałszywego pliku
  jest jawnie przetestowana. Bilans, pełna bramka i CI spełniają procedurę.

### Wyniki lokalne

- `IdSequence` jest właścicielem parsera i maksimum + 1; `format_id` formatera,
  `file_ids` adaptera nazw. Importery utrzymują odrębne sekwencje `C`, każdego
  prefixu i każdego obiektu z pomiarami `m`. Usunięto stare skanery, seedery,
  parsery i formattery; nie pozostały aliasy ani ścieżki zgodności bez odbiorców.
- Zestaw karty: **392 → 408 PASS**. Nowe przypadki pokrywają pusty zbiór,
  luki, duplikaty, istniejące i proponowane ID, mieszane przestrzenie/suffixy,
  błędne nazwy, katalog zamiast pliku, licznik powyżej szerokości i ponowienie
  tej samej partii bez zapisu. Regresje przez publiczne API: **5 FAIL → 5 PASS**;
  zestaw `assign_id`/PIG/TPN: **159 PASS**. Asercje używają literalnych ID,
  prawdziwych plików/CSV/staging JSON i sprawdzają niezmienione bajty wejścia.
- Wszystkie **8 raportów JSON/Markdown** porównano przy
  `2026-11-06T12:00:00Z`, na katalogu oraz pustym wejściu z propozycjami PIG.
  **6/8 zgodnych bajtowo**, bez normalizacji. W dwóch JSON TPN różnią się
  wyłącznie trzy zarezerwowane ID; po sprawdzeniu tych konkretnych pól cała
  reszta struktur jest identyczna:

  | Wejście | Wiersz TPN | Obiekt | Przed → po |
  |---|---|---|---|
  | katalog | 156 | MLZ-0087 | `m-003` → `m-004` |
  | katalog | 999 | MLZ-0089 | `m-003` → `m-004` |
  | puste + PIG | 476 | KSW-0065 | `m-002` → `m-003` |

  Katalog: PIG 860 jaskiń/860 obiektów/46 diagnostyk, TPN 1005 dopasowań/
  16 diagnostyk. Puste + PIG: TPN 858 dopasowań/142 nowe obiekty/263 diagnostyki.
  Zawartość pomiarów, kolejność oraz cztery raporty Markdown są niezmienione.
- Pomiar rzeczywistych `Path.iterdir` na pełnym katalogu, osobno od loadera:
  **PIG 860 → 19** skanów prefixów, **TPN 1029 → 0** (wszystkie wiersze
  dopasowane, bez nowych obiektów). Skan jaskiń: **1 → 1** w obu importerach.
  Regresje małej partii potwierdzają jeden skan danego katalogu na uruchomienie,
  także przy kilku kandydatach. Nie jest to pomiar przyspieszenia całego builda.
- Python produkcyjny **+120/−146, netto −26**, identycznie bez różnic whitespace.
  SQL/schematy **0**, testy **+234/−7**. Bez zmian `data/`, `config/`, `schema/`,
  workflow ani zależności.
- Niezależne review: brak uwag krytycznych/istotnych; dodatkowy publiczny
  probe wspólnego obiektu z YAML (`m-003`) i PIG (`m-009`) dał kolejno
  `m-010`, `m-011`. Drobna uwaga odłożona: utrwalić ten konkretny scenariusz
  łączenia rezerwacji jako osobną regresję (ogólny mechanizm `reserve` i oba
  źródła są już testowane). Nie rozszerzano U09 o trwałe/międzyprocesowe
  rezerwacje ani merge/wydanie. Pełna bramka, CI i paczka są odbierane osobno.
- Pełna lokalna bramka `scripts/check_project.py --base-ref
  ad5fa191a36d5a5f45f0b2de523bd39125827573`: **1522 PASS / 1 SKIP**,
  Ruff, historia, build 13 formatów, natywny restore dumpa, odczyt GeoPackage
  i `git diff --check` — PASS. Katalog: 1029 obiektów, 1019 jaskiń,
  1946 pomiarów, 0 błędów / 4185 ostrzeżeń. Runtime: osobny PostgreSQL
  18.6/PostGIS 3.6.4; lokalny smoke zarządzanego Dockera pominięty (Docker
  nie odpowiedział w 10 s); obowiązkowy osobny smoke odebrano w CI.

### CI kodu

[Validate code and data](https://github.com/dlubom/gps-kataster-obiektow-tatr/actions/runs/42201316889)
zakończone **SUCCESS** dla `487375c7f4876ece64ffe2c9d9160b4ade1a5edd`, próba 1:
**1521 PASS / 2 SKIP** i osobny smoke zarządzanego Dockera **1 PASS**
(start, dump, restore, cleanup). Historia oraz końcowe sprzątanie kontenerów
również zakończone sukcesem. Skips zwykłego zestawu dotyczą smoke uruchamianego
osobno i testu klienta native przy klientach kontenera. Żaden przebieg U09
nie był anulowany ani ponawiany.

### Odbiór preview kodu

Kod U09 dostarczono fast-forward do otwartego draft PR #40 jako
`487375c7f4876ece64ffe2c9d9160b4ade1a5edd` (zdalny SHA potwierdzony).
[Preview](https://github.com/dlubom/gps-kataster-obiektow-tatr/actions/runs/42201316973)
zakończone **SUCCESS**, próba 1.
[Paczka 13493833677](https://github.com/dlubom/gps-kataster-obiektow-tatr/actions/runs/42201316973/artifacts/13493833677)
ma SHA-256 `dc50ea0be9cfc01f1b26b2dd687cb358b98ff82936cb245db0c44bb260ffd020`
zgodny z GitHub. **14/14 sum**, 15 nazw oraz head/base/merge
`c858da1593a0dd1b217d162fdfeaabe0ff6ca9c3`, run i próba są poprawne;
rodzice rzeczywistego merge i zgodność jego kodu/danych z head sprawdzone w Git.

Niezależny pełny odczyt **13/13 formatów** potwierdził zgodność z lokalnym
buildem przy tych samych metadanych: CSV, GeoJSON, wszystkie GPX, XLSX
(komórki/typy/formaty/tabele/XML), Shapefile, wszystkie dane i deklaracje
GeoPackage oraz natywnie odtworzony dump ze wszystkimi tabelami i widokami
Best. Wartości źródłowe, brak/null, historia i 27 manual Best są porównane
ściśle. Dla 21982 pochodnych wartości EPSG:2180 maksymalna różnica wynosi
`1.9208528101444244e-9 m`, przy absolutnej tolerancji `1e-8 m`.

Pierwsza próba porównania z Homebrew GDAL 3.13.3 wykazała różne WKT/datum
EPSG:2180 (`ETRS89` lokalnie, `ETRF2000-PL` w CI). Deklaracje CI są identyczne
z paczką U08; jej zachowany ZIP sprawdzono ponownie względem bieżącego digestu
GitHub. Nie uznano tych CRS za równoważne. Odbiór powtórzono przez GDAL 3.12.0
z QGIS i jawnym `PROJ_DATA` jego bazy; pełne WKT/datum są wtedy zgodne.
Nie zmieniano kodu, danych ani definicji CRS w paczce.

Normalizacje dotyczą wyłącznie nagłówków ZIP, daty DBF, czasu utworzenia
GeoPackage, wariantów triggerów i fizycznych stron RTree (sprawdzonych przez
odbudowę indeksu i próby insert/update/fid/null/delete na kopiach), tokena
dumpa i komentarzy wersji klientów. Numeryczne XML XLSX sprawdzono przez
pełne wartości/typy/formaty; pozostała struktura XML jest porównana.

Bilans dokumentacji całego U09: **+183/−14** (kod i testy policzone wyżej).

Indeks zawiera zamknięcie U09 i prompt U10; U10 nie rozpoczęto. Końcowy SHA
dokumentacji, jego terminalne CI i preview są potwierdzane w opisie PR.
Bez merge, taga i wydania. Pozostawiono worktree do dalszego przeglądu.

Zakończ po U09. Następna karta: [U10](U10-artifacts-and-cli.md).
