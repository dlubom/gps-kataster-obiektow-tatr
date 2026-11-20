# Bieżący kontekst projektu

[PR #40](https://github.com/dlubom/gps-kataster-obiektow-tatr/pull/40)
(PBI-119) opisuje migrację katalogu na tymczasowy PostgreSQL/PostGIS. YAML v2 w Git
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

Dwanaście historycznych pomiarów z 2026-10-17 zapisano jako zweryfikowane
przez Marka; dziesięć wyników domiarów odrzucono po rozpoznaniu błędu
poprawki magnetycznej. Ich źródłem jest poprawiony XLS z 2026-11-04; bieżący Best
wskazuje nowe rekordy z aktualizacji otrzymanej 2026-11-16 (poniżej).
Wiersz 10 wskazuje Grzędę II (MTW-0016), wiersz 11 Grzędę I (MTW-0050).
Dariusz Lubomski potwierdził Kozią 2026-11-04. Otwór I (MTW-0013) jest
zachodni, otwór II (nowy MTW-0076) wschodni. Oba należą do C-0135, a ich
wysokości z pomiarów Marka wynoszą odpowiednio 1836,99 i 1839,47 m
PL-EVRF2007-NH. Data weryfikacji Marka i dokładności punktów są nieznane.
[Pochodzenie i sumy kontrolne](../../data/sources/README.md#marek-jędrzejczak--pomiary-z-2026-10-17).

## Korekta GNSS i domiarów — 2026-11-16

W poprzednich obliczeniach odejmowano uchylenie magnetyczne; poprawne
przejście do azymutu PL-1992 je dodaje. Dopisano 20 pomiarów, zachowując
całą wcześniejszą historię. Decyzją Dariusza Lubomskiego 19 nowych rekordów
wskazano ręcznie jako Best. Miętusia MTZ-0023 zachowuje dotychczasowy m-002
i politykę auto: nowy pomiar statyczny miał słabe warunki i duże błędy
po wyrównaniu, więc służy tylko jako potwierdzenie lokalizacji.
Niebieska Studnia i Pod Wantą nie miały domiarów; ich wartości nie zmieniły się.

[Wyciąg 18 punktów](../../data/sources/marek-jedrzejczak/corrected-2026-11-16/README.md)
rozlicza daty źródłowe, mapowanie otworów, sprzęt i zespoły.
[Wysoka i Bańdzioch](../../data/sources/wysoka-bandzioch/corrected-2026-11-16/README.md)
mają zwięzły opis wyników i znanych ograniczeń. [Oryginalne XLS/PDF](../../data/sources/surveys/2026-11-16/README.md)
zachowano bajtowo w repozytorium wraz z wyciągami wartości. Nowe wpisy nie poświadczają
nowej weryfikacji terenowej, a dokładność końcowych punktów pozostaje nieznana.
Cztery pozycje KSW-0264–KSW-0267 [przeliczono z nowej kotwicy](../../data/sources/jktz/wysoka-entrances-2026-11-16/README.md)
KSW-0189/m-004, zachowując rewizję i dane sieci JKTZ. Dopisane m-002
wskazano jako ręczne Best; historyczne m-001 odrzucono z powodu błędnej kotwicy.
Łącznie aktualizacja obejmuje 24 nowe rekordy, 23 nowe wskazania Best oraz
16 odrzuconych wcześniejszych wyników: 10 domiarów z 2026-10-17, Wysoką,
Bańdziocha i cztery wyniki zależne JKTZ. Zmieniono tylko statusy i notatki
tych starszych rekordów; ich geometria, daty i kolejność są zachowane.
Punkty zależne nie mogą być dodatkowymi niezależnymi fixami JKTZ.

## Nierozstrzygnięte sprawy

- Porównanie trzech dawnych pozycji Mylnej KSZ-0064 pozostaje w otwartym
  [issue #36](https://github.com/dlubom/gps-kataster-obiektow-tatr/issues/36).
  Bieżący ręczny Best to m-004 z sieci opisanej w [PBI-117](verification/PBI-117.md).
- Rezerwacja wycofanych ID nie jest wdrożona i pozostaje poza czyszczeniem kodu;
  [issue #33](https://github.com/dlubom/gps-kataster-obiektow-tatr/issues/33).
- Potwierdzone części systemów KKTJ wskazują pozycję zbiorczą przez
  `system_cave_id`. Eksporty pokazują wymiary systemu obok wymiarów części.
  Odrębne kwestie historycznych nazw, statystyk i integracji pozostają w
  [issue #34](https://github.com/dlubom/gps-kataster-obiektow-tatr/issues/34).
  Liczba pozycji katalogowych obejmuje także systemy i ich części.
- [PBI-110: wywierzyska](plans/PBI-110-design.md) pozostaje projektem do
  akceptacji. Lokalizacja Bystrej jest nierozstrzygnięta; odbiór tabeli PIG
  dla Goryczkowego wymaga pełnych bajtów PDF i kontroli wizualnej.
- Odroczone nowe obiekty TPN, w tym Schron nad Wielką Równią i Jaskinia
  w Kozim Grzbiecie, opisują [decyzje PBI-113](verification/PBI-113.md).
- Filar („Jaskinie” 3–4 (124–125), s. 41–47) dokumentuje odrębne
  Nyże pod Zachodem Pilotów II–IV i Komorę w Kończystej Turni.
  Rekord Dziury nad Zahradziskami (TPN 6722) jest prawdopodobnym
  wcześniejszym zapisem Komory. Koleba w Zawracie Kasprowym ma jeden
  otwór na planie, a wybór reprezentacji jej dwóch rekordów TPN jest
  otwarty. Gawra w Bobrowcu ma dwa połączone otwory i wymaga przypisania
  punktu TPN do konkretnego otworu. [Porównanie źródeł](../../data/sources/jaskinie/2026-124-125/README.md).
- Tunel w Skrajnej Giewonckiej Baszcie (C-0981) grupuje otwory MLW-0044
  i MLW-0050. Filar (2026, „Jaskinie” 1–2 (122–123), s. 37) dokumentuje
  dwa połączone otwory oraz długość 10,1 m i deniwelację 2,5 m.
  Różnica wysokości punktów TPN przekracza deniwelację tunelu.
  Przypisanie odroczonego punktu TPN 6721 pozostaje nierozstrzygnięte.
- [Tunel nad Kominem Flacha (C-0976)](../../data/caves/C-0976.yml) ma dwa
  połączone otwory według Filara („Jaskinie” 3–4 (116–117), 2024, s. 49–50).
  W katalogu jest jeden punkt TPN (MLZ-0103), około 15,8 m wyżej niż
  wysokość podana w artykule. Przypisanie punktu do otworu I lub II
  oraz lokalizacja drugiego otworu pozostają do ustalenia.
- Rozbieżności i identyczne Best nie rozstrzygają błędu lokalizacji ani
  duplikatów; [ocena źródeł](reviews/data-decisions-2026-10.md).

## Pochodzenie decyzji o danych

| Zakres | Dokument źródłowy |
|---|---|
| Cztery otwory systemu Wysoka–Za7–Pośrednia: wynik istniejącej sieci JKTZ po korekcie kotwicy, bez nowych niezależnych fixów | [Bieżące dowiązanie](../../data/sources/jktz/wysoka-entrances-2026-11-16/README.md), [tożsamości i wcześniejszy wynik](../../data/sources/jktz/wysoka-entrances-2026-11-12/README.md) |
| Mnichowa Studnia Wyżnia: punkt TPN przy górnym `0`, dolny `11` z domiaru; decyzja koordynatora z 2026-11-12 | [Przypisanie, wyliczenie i warunek integracji JKTZ](../../data/sources/jktz/mnichowa-2026-11-12/README.md) |
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
