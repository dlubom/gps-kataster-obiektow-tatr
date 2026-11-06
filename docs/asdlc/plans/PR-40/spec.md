# Spec — kontrakt uproszczeń PR #40

To specyfikacja zmian planowanych w U03–U11. Stan wdrożony określa
[specyfikacja projektu](../../../../specyfikacja_gps_kataster_obiektow_tatr_v_2.md),
w szczególności §10 (walidacja), §13 (eksporty) i §18 (historia/kompatybilność).
Statusy i następne zadanie są wyłącznie w [indeksie](README.md).

## Cel i granice

Zmniejszyć liczbę implementacji tej samej reguły, konwersji reprezentacji
i ponownych odczytów. Mierzyć osobno wielkość kodu oraz wykonaną pracę.
Przeniesienie funkcji do innego pliku nie jest redukcją. Nie zmniejszać
walidacji, jakości diagnostyki ani pokrycia zachowań tylko po to, aby usunąć linie.

Seria nie zmienia danych katalogowych, ręcznych decyzji Best, geometrii regionów,
formatów odbiorców ani zasad wyboru pomiaru. Nie obejmuje QGIS/PBI-118,
rezerwacji wycofanych ID (#33), importu nowych danych, merge ani wydania.

## Wymagania i scenariusze odbioru

| ID | Wymaganie | Dowód/odpowiedzialna karta |
|---|---|---|
| S01 | Kanoniczny katalog ma znacznik formatu oraz rzeczywiste katalogi `objects`, `caves`, `relations`, `publications`. Pusty istniejący katalog jest legalny. Brak lub plik zamiast katalogu blokuje przed bazą i zapisem. | U03: macierz brak/plik/pusty; jawny kontrakt legacy |
| S02 | Źródło, deklaracje importu, model zmian i projekcja SQL mają jawne granice. Wyliczane pola nie wracają do źródłowego YAML. Deklaracje legacy są sprawdzane przed ich usunięciem. | U02 zachowane; U04: błędne redundantne współrzędne i członkostwo nadal odrzucane |
| S03 | Relacje, automatyczny Best, współrzędne pochodne i regiony sprawdzonego katalogu mają jedno obliczenie w SQL. Importer może nadal wyznaczać kandydatów przed istnieniem katalogu. | U05: region wybranego pomiaru, granice, nakładanie, PL/SK i brak regionu |
| S04 | Historyczny wiersz eksportu pochodzi z konkretnego pomiaru; brak i null nie dziedziczą wartości Best. Pełny build dzieli jeden niezmienny `ExportData` i jeden czas. | U01 zachowane przez U04/U05/U10; odczyt rzeczywistych formatów |
| S05 | Writer jest jedynym właścicielem serializacji, atomowej podmiany i informacji o zmienionych plikach. Wynik obejmuje rzeczywiste zmiany, także wynikające z adopcji legacy. | U06: porównanie plików, dry-run, błąd przed i po podmianie |
| S06 | Zwykłe testy API/CLI wywołują produkcyjny kontrakt; pomoc testowa nie waliduje ani nie naprawia wejścia przed wywołaniem. Wzorce oczekiwanych wartości są niezależne od produkcyjnego serializera. | U07: bezpośrednie błędne wejścia, prawdziwy baseline Git, testy migracji osobno |
| S07 | Wspólne helpery zachowują semantykę wejścia: białe znaki, NBSP, przecinki, puste/null, niefinitywne wartości, daty i escaping. Różne polityki pozostają jawne przy odbiorcy. | U08: przypadki graniczne i raporty przed/po |
| S08 | Kolejne ID uwzględnia istniejące ID i rezerwacje bieżącej partii; `m-NNN` jest lokalne dla obiektu. Nie wypełniamy luk ani nie wdrażamy historii wycofanych ID. | U09: luki, kilka kandydatów, prefixy, dwa obiekty z `m-001` |
| S09 | Builder, CLI i paczkowanie korzystają z jednej jawnej listy artefaktów. Pełny zestaw liczy 13 plików; preview dodaje pochodzenie i sumy. Publikacja jest atomowa. | U10: dokładny zbiór nazw, brak/dodatkowy plik, częściowy błąd, kompatybilność CLI |
| S10 | Wspólny setup CI zachowuje wersje, wymagany check, rzeczywisty baseline historii, dump/restore, odczyt GeoPackage i smoke Dockera. Kod PR nie otrzymuje uprawnień publishera. | U11: testy workflow i terminalne uruchomienia exact SHA |

## Niezmienniki przekrojowe

- YAML i archiwalne źródła zachowują bajty przy zadaniach bez zmiany danych.
  Writer przy faktycznej edycji zachowuje kolejność pól i list, niezmienione
  pliki, sufiksy `.yml`/`.yaml`, assety, źródłowy EPSG i rozróżnienie brak/null.
- Ręczny Best oraz wszystkie pomiary i ich kolejność pozostają bez zmian.
  Kontrola historii używa rzeczywistego zaakceptowanego commitu Git.
- Niepełne/błędne wejście, niedostępna historia lub błąd przed publikacją
  nie zmieniają istniejących danych ani eksportów. Nie dodajemy wyników sukcesu
  do ścieżek, których sprzątanie bazy zakończyło się błędem.
- Zachowujemy kody, severity, ścieżki, kolejność i treść diagnostyki,
  poza jawnie wskazaną korektą U03 dla brakującego kompletu kanonicznego wejścia.
- Schemat, kolejność kolumn, precyzja, kodowanie i zawartość 13 formatów są
  kontraktem odbiorców. Binarny ZIP/dump nie musi być bajtowo identyczny;
  porównanie semantyczne ma obejmować wszystkie dane i deklaracje, nie same liczniki.

## Zakończenie serii

Każde zadanie ma zamknięte kryteria swojej karty, zmierzony bilans kodu,
usunięte zbędne ścieżki oraz udokumentowany wynik w Git/PR/CI. Kart nie uznaje
się za wykonane na podstawie samego projektu, testu mocka ani uruchomionego CI.
Jeżeli zmiana nie daje oczekiwanej redukcji, podaj rzeczywisty wynik i przyczynę;
nie dopisuj obok nowego mechanizmu i pozostawionej starej implementacji.
