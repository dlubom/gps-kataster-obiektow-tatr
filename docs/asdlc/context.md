# Bieżący kontekst projektu

## Migracja PostgreSQL/PostGIS — PBI-119

[Draft PR #40](https://github.com/dlubom/gps-kataster-obiektow-tatr/pull/40)
ładuje katalog z YAML w Git do tymczasowego PostgreSQL/PostGIS.
Rekordy trafiają do bazy jako parametry; kod nie parsuje składni INSERT.
Kanoniczny YAML zapisuje tylko pola źródłowe. Otwory wynikają z `cave_id`
i `membership_ordinal`; wyliczane współrzędne i ID auto Best są w modelu
odczytu. Adapter sprawdza typy i URI przed konwersjami PostgreSQL.
Zakres obejmuje program, CI/CD, dump i GeoPackage; PR #39/PBI-118 (QGIS)
pozostaje osobnym zadaniem. Merge i wydanie wymagają osobnego polecenia.
Aktualny SHA, wyniki CI i odbiór paczki wskazuje opis PR.

Poprawki review z 2026-11-06 chronią źródła i obce pliki przed podmianą
katalogu eksportu, kierują legacy w builderach przez pełny preflight oraz
sprawdzają redundantne współrzędne i cache Auto Best przed normalizacją.
[Dowody](verification/PBI-119.md#review-2026-11-06) obejmują regresje i odbiór.

U01 przygotowuje raz na build wspólny `ExportData`: niezmienne Best,
pełną historię, wybrane wiersze i czas generowania. Eksportery i statystyki
nie odbudowują tych danych. Full powstaje z metadanych obiektu/jaskini
i konkretnego pomiaru, bez uzupełniania braków wartościami Best.
Nazwy i typy wspólnych pól są niezależne od formatowania Excela.
Samodzielny eksport Best używa tego samego przygotowania.

U02 oddziela odczyt YAML, propozycje legacy, kontrolę istniejącego stanu
PostgreSQL i historię zaakceptowanej rewizji Git. Build i kanoniczne CLI
używają wspólnej bramki historii. `SourceDataset` i interfejsy propozycji
pozostają wewnętrzne do U15. Historyczne review U04 używało tych interfejsów;
[odbiór U04](plans/PR-40/tasks/U04-canonical-proposals.md#odbiór) zachowuje
dowody jego ówczesnego działania.
Grupowanie GPX korzysta z regionu SQL wybranego pomiaru, przekazanego
niezmiennymi metadanymi do `ExportData`; nie odtwarza geometrii w Pythonie.
Granice i priorytet poligonów określa `ST_Covers` / `boundaries.ordinal`.
[Odbiór U05](plans/PR-40/tasks/U05-spatial-read-model.md#odbiór) opisuje regresje
i porównanie eksportów; status i następne zlecenie są wyłącznie w indeksie.
Writer zwraca faktyczne zmiany bajtów i usunięcia przez niezmienny `WriteResult`.
Historyczne review używało `written_paths` bez pełnych skanów YAML;
[odbiór U06](plans/PR-40/tasks/U06-write-result.md#odbiór) opisuje kontrakt i pomiar IO.
Testy eksportów podają kanoniczne fixtures bezpośrednio do API/CLI, z osobnym
zaakceptowanym commitem Git sprzed mutacji; migracja legacy ma własne testy.
[Odbiór U07](plans/PR-40/tasks/U07-production-path-tests.md#odbiór) opisuje
pokrycie, diagnostykę baseline i porównanie formatów.
Historyczne U08/U09 opisywały współdzielone helpery importerów i rezerwacje
partii; U12 usuwa te zakończone ścieżki, zachowując zegar builderów oraz
przydział ID maksimum + 1 przez `assign_id`.
Builder, CLI i paczkowanie używają jednego zestawu artefaktów; lista ścieżek
z separatorem NUL przekazuje 13 ścieżek do workflow bez drugiego spisu. Wspólne argumenty
CLI zachowują politykę diagnostyki; [karta U10](plans/PR-40/tasks/U10-artifacts-and-cli.md#odbiór)
zawiera kontrakt i odbiór. Status pozostaje w indeksie.
Wspólną instalację runtime czterech workflow posiada lokalna composite action;
zdarzenia, uprawnienia, serwisy i rzeczywisty baseline pozostają u odbiorców.
[U11](plans/PR-40/tasks/U11-ci-setup.md#odbiór) opisuje zakres i dowody;
status jest wyłącznie w indeksie.

Użytkownik zaakceptował wycofanie zakończonych importów PIG/TPN, profilera
i jednorazowych napraw oraz ograniczenie programu do odczytu YAML,
walidacji i eksportów. [Plan czyszczenia](plans/PR-40/next/README.md) rozpisuje
ten zakres. Użytkownik następnie wyłączył rejestr ID i nowe zasady wycofywania
rekordów: U13/U14 nie są realizowane. Obecne błędy historii pozostają;
raport ubytków/warningi są osobnym tematem do decyzji. U12 usuwa kod importów;
dane pozostają bez zmian. [Odbiór U12](plans/PR-40/next/U12-remove-imports.md#odbiór)
opisuje dowody, a statusy są w indeksie.
API TPN/NMT, archiwalne źródła i formaty eksportów pozostają w zakresie utrzymania.

Kontynuację opisuje [pakiet zleceń PR #40](plans/PR-40/README.md): specyfikacja,
projekt, procedura wykonania i osobne karty U03–U11. Indeks jest jedynym
rejestrem ich statusów. Zachowuje numerację wdrożonych commitów: U02 to fazy,
a U03 to kontrola kompletności wejścia, w tym `publications/`. Wspólny guard
odrzuca brak/plik wymaganej ścieżki przed bazą i zapisem; odczyt legacy może
pominąć bibliografię. Układ historii pochodzi z rzeczywistych ścieżek Git.
[Wynik U03](plans/PR-40/tasks/U03-input-completeness.md#odbiór) zawiera odbiór;
statusy i następne zlecenie pozostają w indeksie serii.

Model i reguły są w [specyfikacji](../../specyfikacja_gps_kataster_obiektow_tatr_v_2.md),
[schemat SQL](../../schema/catalog.sql) jest wykonywalnym kontraktem,
[diagramy](../architecture/schema.md) pokazują relacje.
[Instrukcja operacyjna](../operations.md) opisuje edycję, runtime i walidację,
a [formaty wydania](../release_artifacts.md) — eksporty i odtworzenie dumpa.

## Pomiary Marka Jędrzejczaka — issue #43 / v1.3.3

Dwanaście pomiarów z 2026-10-17 zapisano jako zweryfikowane przez Marka
i wskazano jako ręczny Best. Źródłem jest poprawiony XLS z 2026-11-04.
Wiersz 10 wskazuje Grzędę II (MTW-0016), wiersz 11 Grzędę I (MTW-0050).
Dariusz Lubomski potwierdził Kozią 2026-11-04. Otwór I (MTW-0013) jest
zachodni, otwór II (nowy MTW-0076) wschodni. Oba należą do C-0135, a ich
wysokości z pomiarów Marka wynoszą odpowiednio 1836,99 i 1839,47 m
PL-EVRF2007-NH. Data weryfikacji Marka i dokładności punktów są nieznane.
[Pochodzenie i sumy kontrolne](../../data/sources/README.md#marek-jędrzejczak--pomiary-z-2026-10-17).


## Nierozstrzygnięte sprawy

- Mylna KSZ-0064/m-003: trzy warianty położenia wymagają porównania z LiDAR;
  [issue #36](https://github.com/dlubom/gps-kataster-obiektow-tatr/issues/36).
- Rezerwacja wycofanych ID nie jest wdrożona i pozostaje poza czyszczeniem kodu;
  [issue #33](https://github.com/dlubom/gps-kataster-obiektow-tatr/issues/33).
- Model systemów i historycznych części pozostaje otwarty;
  [issue #34](https://github.com/dlubom/gps-kataster-obiektow-tatr/issues/34).
  C-0095 i C-0295 są pozycjami katalogowymi bez własnych otworów;
  liczba pozycji katalogowych nie oznacza liczby niezależnych jaskiń.
- [PBI-110: wywierzyska](plans/PBI-110-design.md) pozostaje projektem do
  akceptacji. Lokalizacja Bystrej jest nierozstrzygnięta; odbiór tabeli PIG
  dla Goryczkowego wymaga pełnych bajtów PDF i kontroli wizualnej.
- Odroczone nowe obiekty TPN, w tym Schron nad Wielką Równią i Jaskinia
  w Kozim Grzbiecie, opisuje [projekt PBI-113](plans/PBI-113-new-tpn-objects.md).
- Rozbieżności i identyczne Best nie rozstrzygają błędu lokalizacji ani
  duplikatów; [ocena źródeł](reviews/data-decisions-2026-10.md).
  Pominięcie TPN row 476 przy uzupełnianiu notes opisuje
  [PBI-082](verification/PBI-082.md).

## Pochodzenie decyzji o danych

| Zakres | Dokument źródłowy |
|---|---|
| Raptawicka, kotwica ALS i osiem otworów systemu Pawlikowskiego | [PBI-117](verification/PBI-117.md) |
| Usunięcie punktów systemów, klasyfikacja metod | [PBI-115](verification/PBI-115.md) |
| Nowe obiekty TPN, nazwy i literatura | [PBI-113](plans/PBI-113-new-tpn-objects.md) |
| Aktualizacje TPN i metody dawnych pomiarów | [PBI-111](verification/PBI-111-provenance.md) |
| Uproszczone dane TPN i dowody wysokości | [PBI-109](verification/PBI-109.md) |
| Parametry i ograniczenia NMT TPN | [PBI-106](plans/PBI-106.md) |
| Kategorie i ocena rozbieżności | [PBI-083](verification/PBI-083.md), [ocena danych](reviews/data-decisions-2026-10.md) |

Wysokość NMT oznacza grunt, nie gwarantowaną wysokość otworu. Datum,
dokładność i najnowszość mogą pozostawać nieznane. Bibliografia jaskini
nie dowodzi położenia konkretnego otworu; źródła i niepewności są w danych.

## Praca w Git

Zmiany przechodzą przez PR i zielone `Validate code and data`. Stała polityka
jednego opiekuna wymaga 0 approving reviews; zachowaj ochronę main i pustą
listę bypass. Nowe upoważnienie do pracy nie upoważnia do merge ani wydania.
Porzuconej serii `codex/review-remediation` / PBI-034–077 nie wznawiamy.
PBI-078–086 zakończono w [v1.0.3](verification/v1.0.3.md).

Dawne dzienniki przebiegów i karty zadań są w historii Git; stan systemu
określają aktualna specyfikacja, kod i dane. Wcześniejszy pełny kontekst:
[rewizja przed migracją](https://github.com/dlubom/gps-kataster-obiektow-tatr/blob/13d734213328e5491c1a5c3171e2cb0fdcef705c/docs/asdlc/context.md).
