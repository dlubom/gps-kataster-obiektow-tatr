# Bieżący kontekst projektu

[Draft PR #40](https://github.com/dlubom/gps-kataster-obiektow-tatr/pull/40)
(PBI-119) przenosi katalog na tymczasowy PostgreSQL/PostGIS. YAML v2 w Git
pozostaje źródłem prawdy; baza wylicza Best, współrzędne i regiony pomiarów.
Bieżące wejścia wymagają katalogów `objects`, `caves`, `relations` i
`publications`. Adapter historii odczytuje również zaakceptowany baseline v1.

Program obejmuje odczyt, walidację i eksporty. Zakończone importery,
propozycje zmian, writer YAML, profiler i jednorazowe naprawy są usunięte.
Pobieranie źródeł TPN/NMT i przydzielanie ID pozostają dostępne.
Nie wprowadzono rejestru wycofanych ID ani nowych wyjątków ochrony historii.

Eksporty korzystają ze wspólnego, niezmiennego `ExportData`; historyczny
pomiar nie dziedziczy braków z Best. Geografię katalogu sprawdza PostGIS.
Publikacja artefaktów jest atomowa. Zestaw plików i setup runtime CI mają
wspólne definicje. Przebiegi weryfikacji i bieżący SHA są w PR.
Merge i wydanie wymagają osobnego polecenia; QGIS (PR #39) jest osobnym zadaniem.

[Specyfikacja](../../specyfikacja_gps_kataster_obiektow_tatr_v_2.md),
[schemat SQL](../../schema/catalog.sql) i [diagramy](../architecture/schema.md)
opisują model. [Instrukcja operacyjna](../operations.md) opisuje pracę z katalogiem,
a [formaty wydania](../release_artifacts.md) — artefakty i odtworzenie dumpa.

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

- Porównanie trzech dawnych pozycji Mylnej KSZ-0064 pozostaje w otwartym
  [issue #36](https://github.com/dlubom/gps-kataster-obiektow-tatr/issues/36).
  Bieżący ręczny Best to m-004 z sieci opisanej w [PBI-117](verification/PBI-117.md).
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
  w Kozim Grzbiecie, opisują [decyzje PBI-113](verification/PBI-113.md).
- Rozbieżności i identyczne Best nie rozstrzygają błędu lokalizacji ani
  duplikatów; [ocena źródeł](reviews/data-decisions-2026-10.md).

## Pochodzenie decyzji o danych

| Zakres | Dokument źródłowy |
|---|---|
| Raptawicka, kotwica ALS i osiem otworów systemu Pawlikowskiego | [PBI-117](verification/PBI-117.md) |
| Usunięcie punktów reprezentujących systemy | [PBI-115](verification/PBI-115.md) |
| Nowe obiekty TPN, nazwy i literatura | [PBI-113](verification/PBI-113.md) |
| Pochodzenie czterech dawnych pomiarów | [PBI-111](verification/PBI-111-provenance.md) |
| Uproszczone dane TPN i dowody wysokości | [PBI-109](verification/PBI-109.md) |
| Parametry i ograniczenia NMT TPN | [PBI-106](verification/PBI-106.md) |
| Kategorie i ocena rozbieżności | [PBI-083](verification/PBI-083.md), [ocena danych](reviews/data-decisions-2026-10.md) |
| Pochodzenie notatek o lokalizacji TPN | [PBI-082](verification/PBI-082.md) |

Wysokość NMT oznacza grunt, nie gwarantowaną wysokość otworu. Datum,
dokładność i najnowszość mogą pozostawać nieznane. Bibliografia jaskini
nie dowodzi położenia konkretnego otworu; źródła i niepewności są w danych.
