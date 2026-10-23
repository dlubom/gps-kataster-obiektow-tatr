# Dwa wycinki ALS 2025: rozpoznanie geometrii przy Pod Wantą i Śnieżnej

Ocena z 2026-10-23, kontynuacja [PBI-112](../../PBI-112.md) na wyraźne
polecenie użytkownika. **W obu chmurach rozpoznano potencjalne struktury
przy pozycji TPN; nie potwierdzono otworu ani progu. Nie wyznaczono korekty
katalogowej XY lub Z.** Wynik jest niejednoznaczny, a wysokość progu pozostaje
nieobserwowalna jako jednoznacznie zidentyfikowana cecha.

## Stan i zakres

Na początku sprawdzono Git i GitHub: czysta gałąź `codex/lidar-research`,
HEAD oraz jej zdalny tip `bdb2b41fdc82cb29923a080b8b4dc576d0195863`;
`origin/main` = `caf7bae69b28eb037810215889cb87f763b2c6bd`.
[PR #29](https://github.com/dlubom/gps-kataster-obiektow-tatr/pull/29)
był otwarty, draft, `mergeCommit: null`. Kontynuowano tę gałąź, nie merge.
Końcowy SHA i terminalne CI dokładnego commitu są w opisie PR.

Zakres: Jaskinia pod Wantą / Litworowy Dzwon **MTW-0054, C-0711,
T.E-12.03** oraz Jaskinia Śnieżna **MLZ-0068, C-0648, T.E-13.01**.
Nie badano Dziury pod Wantą, Śnieżnej Studni ani całego systemu Wielkiej
Śnieżnej. Nie porównywano roczników 2012/2023 i nie wdrażano skilla.
Nie zmieniono `data/`, współrzędnych, wysokości, `best_measurement`,
statusów weryfikacji ani kodu produkcyjnego. Skrypty w tym katalogu służą
wyłącznie odtworzeniu tej analizy.

## Źródła i znaczenie współrzędnych

Odczytano ponownie aktualne YAML. Dokładne wartości, hashe YAML,
oryginalne pomiary i `best_measurement` zachowuje [analysis.json](analysis.json).
[Audyt źródeł](source-audit.md) dokumentuje identyfikatory, opisy PIG,
skorowidz, nagłówki LAS i ograniczenia datum.

| Obiekt / pomiar | Źródło | E = LAS X = `y_1992` | N = LAS Y = `x_1992` | Z zapisane w YAML |
|---|---|---:|---:|---:|
| MTW-0054 / m-001 | PIG | 566324.49 | 152969.10 | 1793.3 |
| MTW-0054 / m-002 | TPN | 566319.78 | 153075.02 | 1790.525556 |
| MLZ-0068 / m-001 | PIG | 567417.26 | 152928.35 | 1700.7 |
| MLZ-0068 / m-002 | TPN | 567414.24 | 152932.54 | 1699.800044 |

Wszystkie cztery pomiary mają `elevation_datum: unknown`, dokładności XY/Z
nieznane oraz status `nieweryfikowany`. Pozycje TPN mają źródłową informację
o weryfikacji na ortofotomapie 2020; nie są tu uznane za pomiar GNSS progu.
Odległość PIG–TPN wynosi **106.024669 m** dla Pod Wantą i **5.164930 m**
dla Śnieżnej. Pokazano obie pozycje bez wyboru zwycięzcy.

LAS deklaruje poziomy **EPSG:2180**, ale nie zawiera pionowego CRS.
**PL-EVRF2007-NH pochodzi z dopasowanego skorowidza GUGiK**, nie z nagłówka.
Nominalne błędy 0,05 m wysokości i 0,06 m XY dotyczą produktu, nie
rozpoznania progu. Nie wykonano transformacji wysokości katalogowych.
Różnic liczb Z nie interpretujemy jako błędów pomiaru ani korekt wysokości.

Znaczniki są celowo rozdzielone:

- TPN: cyan; PIG: magenta. Etykiety podają identyfikator i źródło.
- **XYZ z YAML**: zapisany punkt, z jawnym `datum unknown`. Jego położenie
  względem chmury jest ilustracją zapisanych liczb, nie porównaniem
  wysokości sprowadzonych do wspólnego układu.
- **XY@Z\*** / `XY / nearest-Z proxy`: dokładne XY z YAML i Z najbliższego
  dopuszczonego odbicia w XY. To **umowny, niezmierzony punkt wyświetlania**,
  nie rzut na ciągłą powierzchnię, grunt ani próg. Sąsiad może należeć do
  innej powierzchni. Jego rzeczywiste XYZ zachowano osobno.
- W QGIS geometria znacznika jest wyłącznie 2D XY. Z oraz datum są
  atrybutami; nie przypisano wysokości ALS geometrii warstwy.

[Ilustracja różnicy XYZ/XY](markers-xyz-vs-xy.png),
[tabela znaczników](markers.csv). W analitycznych wykresach krzyżyk oznacza
XYZ, kółko umowny XY@Z\*, a mała czarna kropka rzeczywiste najbliższe odbicie.
W CloudCompare dwa punkty mają odrębne etykiety.

| Pozycja | Indeks rzeczywistego odbicia | E, N, Z ALS [m] | dXY [m] | Klasa / PointSourceId |
|---|---:|---|---:|---|
| Pod Wantą PIG | 46137 | 566324.55, 152969.09, 1746.57 | 0.060828 | 2 / 80 |
| Pod Wantą TPN | 466740 | 566319.86, 153075.11, 1791.47 | 0.120416 | 4 / 81 |
| Śnieżna PIG | 144073 | 567417.26, 152928.29, 1700.00 | 0.060000 | 2 / 81 |
| Śnieżna TPN | 23920 | 567414.28, 152932.56, 1697.51 | 0.044721 | 12 / 80 |

Indeksy są liczone **od zera w wejściowym LAS wycinka**, nie LAZ całego
arkusza ani COPC (który zmienia kolejność rekordów). Najbliższy punkt TPN
Pod Wantą ma klasę 4, Śnieżnej klasę 12: samo sąsiedztwo XY nie wyznacza gruntu.

## Ogląd i przekroje

Obejrzano rzeczywiste odbicia w CloudCompare i QGIS oraz ich rzuty i
przekroje obliczone bez triangulacji, interpolacji i wygładzania.
Podział na PointSourceId zachowano. Są to **grupy źródłowe, nie
potwierdzone różne kierunki nalotu**. Nie wyprowadzano azymutu nalotu
z numeru grupy ani znaku kąta skanera.

Analiza i CloudCompare pomijają noise (klasa 7; analiza również 18,
nieobecną w tych wycinkach) oraz withheld. Zachowują klasę 12.
QGIS pokazuje pełny zbiór, również noise, co opisano w
[notatce QGIS](qgis-notes.md). Żaden plik źródłowy nie został przefiltrowany
ani nadpisany. Pełne wycinki mają 582 112 i 264 297 rekordów.

Ekspozycja z opisu PIG służy do ustawienia kamery: Pod Wantą SSW
(umownie 202,5°), Śnieżna E (90°). Nie jest wynikiem wyznaczenia osi otworu
z LiDAR. Widok od spodu: elewacja kamery −35°. Natywny widok od ekspozycji:
0°, analityczny: +8°. Rzut z góry ma północ siatkową u góry. Wszystkie
widoki są ortograficzne; ilustracje mają skalę i osie/orientację.
Zasłanianie odbić przez inne punkty w widoku 3D zależy od kamery i rozmiaru
symbolu. Przekroje pokazują również punkty zasłonięte w takim widoku.

| Obszar | Chmura z góry / od ekspozycji / od spodu | Przekroje i grupy źródłowe |
|---|---|---|
| Pod Wantą, obie pozycje | [QGIS](qgis-pod-wanta-overview.png), [CloudCompare](gui-pod-wanta-full-top.png) | [Rozkład XY i Z](pod-wanta-overview.png) |
| Pod Wantą przy TPN | [Góra](gui-pod-wanta-tpn-top.png), [SSW](gui-pod-wanta-tpn-exposure.png), [Spód](gui-pod-wanta-tpn-underside.png) | [Przekroje](pod-wanta-tpn-sections.png), [PointSourceId](pod-wanta-tpn-sources.png) |
| Pod Wantą przy PIG | [Góra](gui-pod-wanta-pig-top.png), [SSW](gui-pod-wanta-pig-exposure.png), [Spód](gui-pod-wanta-pig-underside.png) | [Przekroje](pod-wanta-pig-sections.png), [PointSourceId](pod-wanta-pig-sources.png) |
| Śnieżna, obie pozycje | [Góra](gui-sniezna-detail-top.png), [E](gui-sniezna-detail-exposure.png), [Spód](gui-sniezna-detail-underside.png), [QGIS](qgis-sniezna-detail.png) | [TPN](sniezna-tpn-sections.png), [PIG](sniezna-pig-sections.png), [PointSourceId](sniezna-sources.png) |

Przekroje biegną przez każde zapisane XY, wzdłuż ekspozycji i prostopadle
do niej, na długości ±12 m. Porównano pełne szerokości pasa **0,5 / 1 / 2 m**;
to tolerancja selekcji punktów, nie niepewność pomiaru. CSV `*-sections-1m.csv`
zawierają indeksy, XYZ, klasę, PointSourceId i odległości along/cross.
Wykresy `*-views.png` uzupełniają natywne obrazy trzema rzutami i podpisami.
Natywne `*-full-top.png` to widoki ogólne z obiema pozycjami, nie cały
zasięg LAS. Kadry mają stałą szerokość, a widoczny zakres pionowy zależy
od proporcji okna. Na bocznym i dolnym widoku PIG Pod Wantą zapisane XYZ
wychodzi nad kadr; jego etykieta prowadzi poza obraz, a umowny XY@Z* jest
widoczny. Pełną różnicę pokazuje osobna ilustracja XYZ/XY. Sześć próbnych
ciasnych eksportów pominięto po kontroli czytelności skali i etykiet;
interaktywne wycinki 10 m pozostają w scenie CloudCompare.

## Co widać, a czego nie potwierdzono

### Pod Wantą: PW-C1 przy pozycji TPN

**Obserwacja:** poniżej górnego pasma odbić występuje dolna gałąź. Widoczna
od spodu i w dwóch kierunkach przekrojów, a nie tylko jako ciemna plama
w rzucie z góry. Ręczne okno analizy wybiera 53 dolne odbicia:
PointSourceId 80/81 = 25/28; klasy 2/3/12 = 29/1/23.
Ich zakres to E **566319.99–566323.31**, N **153074.75–153076.85**,
Z **1786.17–1790.04** m. To zakres wybranych odbić, **nie obrys otworu**.
[Dowody PW-C1](pod-wanta-candidate.png), [punkty](pod-wanta-candidate-points.csv).

Przykład niemal wspólnego XY: dolny rekord **239962** ma
(566320.09, 153075.36, 1789.53), klasa 2 / PSID 80; górny **466382**
(566320.10, 153075.38, 1791.79), klasa 12 / PSID 81.
Odległość XY = **0,02236 m**, różnica Z = **2,26 m**, obie wysokości
w tym samym źródłowym układzie ALS. To nie jest różnica ALS–katalog.

**Hipoteza:** odbicia są zgodne z lokalną geometrią przewieszenia albo
przestrzeni pod blokiem. Nie wykazano ciągłej obwiedni wejścia, połączenia
z wnętrzem ani jednoznacznego miejsca progu. Opis PIG otworu pod wantą
jest pomocny do interpretacji, ale nie stanowi niezależnego dopasowania
chmury do fotografii. Nazwy „dolny/górny” nie oznaczają podłogi/stropu.

### Pod Wantą: okolica pozycji PIG

**Obserwacja:** w oglądanym sąsiedztwie dominują odbicia stoku; nie wskazano
porównywalnej, jednoznacznej geometrii wejścia. W promieniu 5 m odbicia
mają Z **1741,96–1752,78 m**, a zapisane PIG Z wynosi 1793,3 m z nieznanym
datum. Jest to istotna niespójność danych do wyjaśnienia, nie obliczona
korekta. XYZ PIG może wypadać poza ciasnym kadrem chmury; pełny rozdział
pokazuje ilustracja XYZ/XY.

**Wniosek:** nie rozpoznano progu przy tej pozycji. Nie dowodzi to braku
jaskini i nie upoważnia do odrzucenia PIG ani automatycznego wybrania TPN.
Niepewne XY, układ wysokości, przesłonięcie i semantyka źródłowego punktu
pozostają nierozwiązane.

### Śnieżna: SN-C1 przy pozycji TPN

**Obserwacja:** u podstawy stromego pasma występuje niższe skupisko odbić,
dobrze widoczne od spodu i w przekrojach. Ręczne okno wybiera 26 dolnych
odbić: PSID 80/81/82 = 10/9/7; klasy 2/3/4/12 = 12/1/1/12.
Zakres E **567413.60–567414.69**, N **152932.32–152934.00**,
Z **1697.02–1697.91** m. [Dowody SN-C1](sniezna-candidate.png),
[punkty](sniezna-candidate-points.csv).

Dolny rekord **88032**: (567414.15, 152932.93, 1697.31), klasa 2 / PSID 81;
górny **241271**: (567414.13, 152932.95, 1700.64), klasa 12 / PSID 82.
Odległość XY = **0,02828 m**, różnica Z = **3,33 m**.
Pozostałe pary: [candidate-near-vertical-pairs.csv](candidate-near-vertical-pairs.csv).

**Hipoteza:** dolne skupisko może należeć do wnęki lub przestrzeni pod
przewieszeniem przy wejściu. Nie potwierdzono trójkątnego otworu opisanego
w PIG, krawędzi progu ani granicy skała/śnieg. PIG leży 5,16 m od TPN;
sama bliskość nie ustala, które miejsce odpowiada progowi. Zależne od
grupy różnice najbliższego Z (około 1697,5 i 1699,83 m) nie są dowodem
błędu rejestracji pasów: mogą dotyczyć różnych powierzchni.

### Próba algorytmiczna i jej ograniczenia

Obliczono promieniowe statystyki pokrycia, rozpiętości Z w komórkach
0,25/0,5/1 m oraz przekroje o trzech szerokościach. Po ręcznym wskazaniu
okien PW-C1/SN-C1 policzono komórki 0,5 m zawierające co najmniej dwa
odbicia z dolnego i dwa z górnego zakresu. Wynik: **14** dla PW-C1 i **5**
dla SN-C1. W obrębie pojedynczych PSID: PW 80=3, 81=7; SN 80=2, 81=1,
82=1. Nie jest to więc wyłącznie skutek połączenia różnych ID.
Po ograniczeniu obu poziomów do samej klasy 2 wynik wynosi **0 w obu
oknach**. To ważne osłabienie interpretacji: górne odbicia mogą obejmować
roślinność, overlap lub powierzchnie inaczej sklasyfikowane. Klasyfikacja
również nie jest nieomylną identyfikacją materiału.

Dobór okien i progów Z był eksploracyjny, po obejrzeniu chmury. Nie jest
ślepym testem detektora ani oszacowaniem jego skuteczności. Pełne parametry
są w `analysis.py` i `analysis.json`; wyniki w
[candidate-stacked-cells-05m.csv](candidate-stacked-cells-05m.csv) oraz
[vertical-spread-diagnostic.csv](vertical-spread-diagnostic.csv).
Duża rozpiętość Z może wynikać ze stromej ściany, roślinności lub kilku
powierzchni. Nie oznacza automatycznie pustki. Najbliższy punkt danej
grupy poza lokalnym oknem nie jest wsparciem lokalnym (np. PSID 79 przy
PIG Pod Wantą jest odległy o około 131 m).

## Czy można skorygować XY i wysokość?

**Na tych dowodach nie można jeszcze wyznaczyć uzasadnionej korekty
punktu katalogowego.** Można powtarzalnie wskazać obszary dalszych oględzin
PW-C1 i SN-C1, ale ich centroid, minimum Z ani najbliższe odbicie nie są
pomiarami progu. Nie proponujemy przeniesienia punktu do tych statystyk.

Wysokości rzeczywistych odbić mają sens w źródłowym EVRF2007-NH.
Niepewność identyfikacji właściwej cechy jest tutaj dominująca i nie została
oszacowana liczbowo; nie należy przypisywać kandydatom dokładności ±0,05 m.
Zakresy XYZ powyżej są obwiedniami wybranych próbek, nie przedziałami ufności.
Nieznany datum YAML osobno uniemożliwia rzetelną korektę różnicową Z.

Do przyszłego ustalenia progu potrzebne są: jednoznaczna definicja punktu
terenowego, dopasowanie zdjęcia/obrysu otworu do wskazanych skał, kontrola
datum i ocena powtarzalności powierzchni z niezależnego pokrycia lub pomiaru.
Roczniki 2012/2023 mogą dostarczyć innej widoczności mimo większych błędów
deklarowanych; ich porównania **nie wykonano**. Śnieżna Studnia pozostaje
późniejszym niezależnym testem. Brak odbić nie dowodzi istnienia ani braku
otworu. Interpolowana powierzchnia nie byłaby pomiarem pustki/progu.

## Odtworzenie i kontrola

1. Checkout commitu z opisem PR #29. Przywrócić cztery wejściowe pliki
   do `build/research/lidar-2026-10-23/` zgodnie z wcześniejszym
   [PBI-112](../../PBI-112.md). Sumy i rozmiary są w `analysis.json`
   i wcześniejszym `inspection.json`; wejścia nie są wersjonowane.
2. W osobnym środowisku Python zainstalować `analysis-requirements.txt`.
   Z katalogu repo uruchomić:

   ```bash
   python docs/asdlc/verification/PBI-112/2025-assessment/analysis.py
   python docs/asdlc/verification/PBI-112/2025-assessment/independent-readback.py
   ```

   Analiza sprawdza źródłowe SHA i czyta YAML. Nadpisuje swoje wyniki
   w tym katalogu. Dwa uruchomienia dały 29/29 identycznych bajtowo produktów
   analitycznych; sumy w `analysis-product-SHA256SUMS`. Wersje bibliotek
   zachowano w `analysis.json` i requirements.
3. QGIS: wykonać polecenia w [qgis-notes.md](qgis-notes.md). Projekt lokalny
   `build/research/lidar-2026-10-23/qgis-2025-assessment.qgz` ma trzy warstwy,
   cztery znaczniki, pięć zakładek i pięć układów. COPC jest pochodną
   do wyświetlania. Niezależny odczyt porównał wszystkie **846 409** punktów:
   zero różnic po jawnej normalizacji klasy 12/Overlap; kąt skanera różni
   się najwyżej o 0,002° wskutek zmiany formatu LAS. Szczegóły w
   [qgis-readback.json](qgis-readback.json) i
   [qgis-project-readback.json](qgis-project-readback.json).
4. CloudCompare **2.14 beta (27 Aug 2026)**, PythonRuntime: otworzyć
   Python Editor i uruchomić zawartość [gui-cloudcompare.py](gui-cloudcompare.py).
   Na innym komputerze ustawić `REPO` lub `LIDAR_REPO`. Skrypt korzysta
   z jawnego snapshotu [gui-markers.json](gui-markers.json), zgodnego z YAML
   tej oceny, i sprawdza SHA LAS. Zachowuje istniejące obiekty aplikacji,
   wyłączając je z widoku. Generuje grupy PointSourceId, znaczniki, PNG
   oraz lokalny `cloudcompare-2025-assessment.bin`. Przesunięcie techniczne
   (−567000, −152000, 0) zachowuje globalne współrzędne i nie jest korektą
   danych. Parametry kamer i rzeczywiste sąsiednie rekordy są w
   [gui-cloudcompare-log.json](gui-cloudcompare-log.json).
   Dołączony PythonRuntime przekierowano do plików `/tmp/lidar-cc-*.log`,
   ponieważ zapis `print()` do konsoli edytora powodował lokalny crash.
   Skrypt nadpisuje własny BIN i PNG; nie zapisywać ręcznej pracy pod
   tymi nazwami. API: [CloudCompare PythonRuntime](https://tmontaigu.github.io/CloudCompare-PythonRuntime/).

Sceny CloudCompare zawierają pełne chmury i kopie lokalnych wycinków,
więc ich sumaryczny licznik nie oznacza liczby unikalnych odbić.
Pole `record_index` odsyła do oryginalnego LAS. Widoki od spodu służą
oglądowi struktury; odcięcie okna tworzy sztuczne brzegi i nie jest
powierzchnią geologiczną. Skala symbolu punktu jest parametrem rysowania.
W edytorze CloudCompare uruchomiono także [gui-readback.py](gui-readback.py):
ponownie otwiera zapisany BIN i porównuje współrzędne oraz PointSourceId
wszystkich 926 967 punktów, wliczając powtórzenia w kopiach wycinków,
22 znaczniki/etykiety i 11 zapisanych kamer. Wynik
[gui-readback.json](gui-readback.json) jest PASS. Tolerancja 0,0002 m
dotyczy wyłącznie zapisu float32 w aplikacji, nie dokładności geodezyjnej.

Niezależny dekoder rekordów LAS sprawdza indeksy, XYZ i selekcję CSV;
wynik w `independent-readback.json`: PASS, 146 332 asercje, m.in. 5468
wierszy przekrojów. Testy dokumentacji: `tests/test_release_docs.py` i
`tests/test_operational_docs.py` — 5 passed. Kontrola sum, lokalnych
linków i zakresu zmian została wykonana przed commitem. Bieżący zestaw
plików obejmuje również `SHA256SUMS` do kontroli integralności dowodów.
Obrazy i materiały w tym katalogu wystarczają do przeglądu w czystym
checkout; interaktywne projekty odtwarza się z wejść według powyższych kroków.
