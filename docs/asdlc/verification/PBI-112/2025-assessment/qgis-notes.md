# QGIS — punkty YAML na chmurach 2025

2026-10-23. Wykonano pięć map punktowych, projekt QGIS, cztery znaczniki
oraz niezależny odczyt kopii chmur. Materiał pokazuje pozycje i kontekst z góry;
sam nie identyfikuje otworu ani progu. Nie zmieniono żadnego pliku `data/`.

## Otwieranie i odtworzenie

Projekt lokalny: `build/research/lidar-2026-10-23/qgis-2025-assessment.qgz`.
Obok są `qgis-2025-markers.gpkg` i dwa `qgis-*.copc.laz`. Są to produkty
odtwarzalne z wersjonowanego skryptu i oryginalnych LAS, niewłączone do Git.
Projekt ma trzy warstwy, pięć zakładek przestrzennych i pięć układów wydruku.
Zakładki są zapisane w projekcie, nie w profilu użytkownika.

W katalogu głównym repozytorium:

```bash
export PROJ_DATA=/Applications/QGIS-final-4_0_1.app/Contents/Resources/qgis/proj
export PYTHONHOME=/Applications/QGIS-final-4_0_1.app/Contents/Frameworks
export PYTHONPATH=/Applications/QGIS-final-4_0_1.app/Contents/Resources/python3.11/site-packages
export QT_QPA_PLATFORM=offscreen
export GDAL_DATA=/Applications/QGIS-final-4_0_1.app/Contents/Resources/gdal
/Applications/QGIS-final-4_0_1.app/Contents/MacOS/python3.12 \
  docs/asdlc/verification/PBI-112/2025-assessment/qgis-build-project.py
/Applications/QGIS-final-4_0_1.app/Contents/MacOS/python3.12 \
  docs/asdlc/verification/PBI-112/2025-assessment/qgis-check-copc.py
```

Pierwszy skrypt sprawdza SHA-256 wejściowych LAS względem wcześniejszego
`inspection.json`, czyta aktualne pomiary TPN/PIG z YAML, zapisuje ich hashe
i tworzy projekt oraz PNG. Nadpisuje swoje produkty `qgis-*`; nie należy
zapisywać ręcznej pracy pod tymi samymi nazwami. Wyniki PNG i parametry
są w tym katalogu; duże pliki robocze pozostają w `build/`.
Po zmianie danych YAML mapa pokaże nowe wartości, a manifest nowe hashe:
do odtworzenia obecnego wyniku potrzebny jest odpowiadający im checkout.

Wykorzystano QGIS **4.0.1-Norrköping**, dołączony Python **3.12.11**,
PDAL wrench **1.4.0**, PDAL **2.9.3** i `untwine` z tego samego pakietu QGIS.
Test headless odczytał projekt ponownie: wszystkie trzy warstwy poprawne,
264 297 i 582 112 punktów, cztery znaczniki oraz pięć układów i zakładek.
[Zapis odczytu projektu](qgis-project-readback.json).

## Znaczenie symboli i układów

TPN: cyan `#00bcd4`; PIG: magenta `#ff00e6`. Krzyżyki mają 3 mm i biały
obrys, etykiety zawierają ID obiektu, źródło i ID pomiaru. Ich geometria jest
**wyłącznie 2D XY**, z `X=y_1992` i `Y=x_1992`. Nie przypisano im wysokości
ALS ani nie rzutowano ich na żadną powierzchnię. Zapisane `elevation_m`
i `elevation_datum` są atrybutami warstwy, nie współrzędną Z geometrii.
Wszystkie cztery pomiary YAML mają datum `unknown`; na tych mapach nie
wykonano porównania Z z chmurą. LAS ma EPSG:2180 bez pionowego CRS;
PL-EVRF2007-NH pochodzi ze skorowidza zachowanego przy raporcie PBI-112.

Wszystkie mapy mają północ siatkową w górę, obrót 0°, podziałkę metrową
i opis osi. Zasięgi: Śnieżna 110 × 110 m i szczegół 30 × 30 m; Pod Wantą
220 × 220 m z obiema pozycjami oraz osobne szczegóły 30 × 30 m przy TPN
i PIG. Dokładne granice i sumy PNG: [qgis-manifest.json](qgis-manifest.json).

- [Śnieżna — kontekst obu pozycji](qgis-sniezna-overview.png).
- [Śnieżna — szczegół TPN/PIG](qgis-sniezna-detail.png).
- [Pod Wantą — obie pozycje](qgis-pod-wanta-overview.png).
- [Pod Wantą — szczegół TPN](qgis-pod-wanta-tpn-detail.png).
- [Pod Wantą — szczegół PIG](qgis-pod-wanta-pig-detail.png).

Renderowanie używa RGB zapisanych w chmurze (stałe rozciągnięcie 0–65535),
symbolu punktu 3 px i maksymalnego błędu ekranowego 0,1 px. Punkty są
rysowane od najniższych do najwyższych Z. Jest to rzut wizualny: część odbić
może być zasłonięta przez wyższe punkty, a rozmiar symbolu jest parametrem
wyświetlania, nie rozmiarem plamki lasera ani powierzchni zmierzonej.
Nie zastosowano siatki, TIN, interpolacji, filtrów klas ani przerzedzania
plików. PNG nie zastępuje pełnej chmury do oglądu przewieszeń.

Każda chmura zachowuje alternatywny styl `PointSourceId · grupy nie azymuty`.
W QGIS: prawy przycisk warstwy → Style, wybór tego stylu; symbole legendy
pozwalają wyłączać poszczególne ID. ID 79/80/81/82 są grupami źródłowymi,
bez interpretacji ich jako potwierdzonych kierunków nalotu. Mapy PNG
przedstawiają pełny zbiór RGB, w tym punkty oznaczone jako overlap/noise.

## Kopia COPC i niezależna kontrola punktów

Automatyczne indeksowanie surowego LAS w krótkim procesie headless
pozostawiło blokadę `-indexing`; próbę przerwano. Ostateczny skrypt używa
jawnego `untwine -i wejście.las -o qgis-nazwa.copc.laz --stats --metadata`
i czytnika `copc`. Oryginalne LAS pozostają niezmienione.

COPC jest kopią w LAS 1.4, format punktu 7. Zmiana konwencji klasyfikacji
jest jawna: oryginalna klasa 12 staje się `Classification=0, Overlap=1`.
Dotyczy 8070 punktów Śnieżnej i 16 301 Pod Wantą. Nie jest to zniknięcie
ani reklasyfikacja merytoryczna odbić. Nowy `ScanChannel` ma wartość 0.
Kąt skanera przechodzi z całych stopni do jednostki 0,006°: maksymalna
różnica numeryczna wynosi 0,002° w obu kopiach. Kopia nie służy do
reinterpretacji kierunku nalotu.

[qgis-check-copc.py](qgis-check-copc.py) rozpakowuje COPC przez PDAL,
niezależnie dekoduje binarne rekordy LAS 3/7 i sortuje pełny multizbiór
punktów. Wynik: **0 różnic na 846 409 punktach** po powyższej normalizacji
klasy/overlap i osobnym porównaniu kąta. Dokładnie zachowane są XYZ wraz
ze skalą/offsetem, RGB, intensywność, GPS Time, PointSourceId, numery
odbicia, flagi kierunku/krawędzi i klasyfikacji oraz UserData.
Wynik i hashe kanonicznych multizbiorów: [qgis-readback.json](qgis-readback.json).
Nie polegano wyłącznie na licznikach lub zgodności granic.

Eksporter QGIS zgłaszał `PNG driver does not support update access` przy
próbie dopisania georeferencji obrazu. Zwrócił `Success`, PNG zostały
odczytane i obejrzane. Georeferencję zapewniają projekt i zapisane granice,
nie geotransformacja PNG. Układ strony obejmuje także tekst i podziałkę.

## Granice obserwacji

Mapy pokazują rozkład odbić i jasne/ciemne skupiska RGB przy zapisanych
pozycjach. Nie wskazano w nich piksela „progu” ani obwiedni otworu.
Ciemne tło pomiędzy punktami oznacza brak symbolu odbicia w rzucie;
nie jest pomiarem pustki. Kolor RGB również sam nie identyfikuje skały,
roślinności, cienia, śniegu ani wnętrza jaskini. Wniosek o geometrii wymaga
zestawienia widoków bocznych, od spodu i konkretnych punktów/przekrojów.
Żadna z dwóch pozycji Pod Wantą nie została wybrana jako poprawna na
podstawie tych map.
