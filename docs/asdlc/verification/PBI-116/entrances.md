# Issue #36: identyfikacja otworów systemu Pawlikowskiego

Odczyt: 2026-10-24. Nie zmieniono repozytorium ani katalogu. Źródła: bieżące strony PIG oraz oryginalne, lokalnie zapisane grafiki PIG (nie wersje monochromatyczne ani upscaled).

## Rozróżnienie otworów dla LiDAR

| Obiekt | Cechy rozpoznawcze ze źródeł PIG |
|---|---|
| Mylna, południowy/główny | Ekspozycja **ENE**, mimo nazwy „południowy”. Dostępny ze ścieżki mijającej Obłazkową i prowadzącej ku SW. Znajduje się pod dużym trawiastym zachodem we wschodniej ścianie. Za nim korytarz do sali z oknami. |
| Okna Pawlikowskiego | Są osobnymi otwarciami, nie wejściem turystycznym. Pierwsze dwa wychodzą ku S i E; od zewnątrz podcięte kilkunastometrowymi progami. Opis wymienia też III Okno w dalszym bocznym ciągu. Nie należy identyfikować dowolnej widocznej dziury/wnęki jako KSZ-0064. |
| Mylna, północny | Ekspozycja NE, lesiste zbocze około 150 m NE od głównego wejścia. |

Źródło: [PIG 1349, Mylna](https://jaskiniepolski.pgi.gov.pl/Details/Information/1349), stan treści 2015; zgodne z lokalnym JSONL, wiersz 657. Tabela źródła: S i okna 1098 m, N **1084 m**. PIG wskazuje ponowne kartowanie F. Filara i M. Parczewskiego w 2009 r. z udziałem K. Zaczyńskiego i M. Rajczaka; instrumenty topofil Marbacha i Leica DistoX. To nie ustala metody bezwzględnego dowiązania XY.

**Obłazkowa**: otwór SSE, szerokość 10 m i wysokość 3 m, sklepienie łukowate; za nim komora około 15 × 5–6 m. Podawane 1096 m. Drobne połączenia z powierzchnią przy prawej części szerokiego otworu nie są oddzielnymi kotwicami systemu. Położenie przy ścieżce przed Mylną daje kontrolę kolejności otworów. Nowe pomiary F. Filar, M. Parczewski, B. Chlipała: 1.12.2013 na zlecenie TPN. [PIG 1351](https://jaskiniepolski.pgi.gov.pl/Details/Information/1351), JSONL wiersz 659.

**Raptawicka**: główne wejście jest otworem skierowanym **ku górze**, o średnicy około 3 m, w stropie korytarza; rozpoczyna studnię około 5 m z drabiną. Otwór górny wychodzi ku S; krótki korytarz za nim prowadzi do dwóch studni w stropie Prawego Korytarza. Tabela źródłowa podaje odpowiednio **1146 i 1151,9 m**. Jest to inna geometria niż poziomy portal Mylnej i potencjalnie łatwiejszy niezależny test przesunięcia sieci w ALS; możliwość identyfikacji wymaga jednak rzeczywistej chmury. [PIG 1387](https://jaskiniepolski.pgi.gov.pl/Details/Information/1387).

**System jako całość**: karta PIG 10935 nie opisuje dodatkowego otworu, a jej współrzędne odnoszą się do głównego otworu Mylnej. Dokumentuje pomiar położenia głównego otworu Raptawickiej względem południowego otworu Mylnej przez B. Chlipałę i F. Filara w czerwcu 2015; DistoX2. Plan i przekrój systemu opracował F. Filar 15.06.2015. To uzasadnia ocenę wielu otworów naraz, ale nie dostarcza niezależnej kotwicy geodezyjnej. [PIG 10935](https://jaskiniepolski.pgi.gov.pl/Details/Information/10935), JSONL wiersz 4036.

## Konflikt wysokości: plan i tabele PIG

Oglądano oryginalne grafiki PIG 11826 (plan) i 11827 (przekrój), obie podpisane aktualnością **15.06.2015**; metadata serwisu zapisują **2015-09-11**, co nie jest datą nalotu ani osobnym pomiarem.

| Otwór | Poziom względem Mylnej S na planie/przekroju | Wysokość podpisana na planie | Tabela strony PIG |
|---|---:|---:|---:|
| Mylna S | 0,00 | 1098 | 1098 |
| Mylna N | −3,65 | **1094** | **1084** |
| Obłazkowa | −2,07 | 1096 | 1096 |
| Raptawicka główna | +42,82 | **1141** | **1146** |
| Raptawicka górna | +48,81 | brak odrębnego podpisu bezwzględnego | **1151,9** |

Te wartości opisują niespójne materiały źródłowe. Nie uzasadniają samodzielnego poprawienia katalogu ani użycia Z jako bezwzględnego kryterium dopasowania do ALS. Oryginalny plan Mylna–Obłazkowa (PIG grafika 849, Filar/Parczewski 2014) również pokazuje N −3,65 / 1094 m. Oryginalny osobny plan Raptawickiej (grafika 907, 2014) ma własne 0 przy otworze głównym i +5,94 przy górnym.

Na planie 11826 główne wejście Mylnej stanowi początek siatki. Okna są na południe i południowy zachód od niego; Obłazkowa na NE; Raptawicka na N z niewielkim odsunięciem ku W; północne wyjście Mylnej znacznie dalej na NE. To orientacyjny odczyt rysunku, **nie nowe współrzędne**. Plan nie powinien być dopasowywany niezależnymi przesunięciami każdego otworu.

## Materiały do obejrzenia

Wszystkie poniższe pliki są w `/Users/dariuszlubomski/proj/Polish-Cave-Data-Scraper/caves/`:

- `010935/image_11826_zoom_10.jpg`: pełny plan systemu, 3783 × 4859; SHA-256 `4708787af1f547eb81e98bc7cf9560ebe665ec2ee36e247e44e7ae8aeb77e064`.
- `010935/image_11827_zoom_10.jpg`: przekrój S–N, 4598 × 2317; SHA-256 `a2c80952c8708aea85a60d837460dba007854037296c24e68893773330b84101`.
- `001349/image_849_zoom_10.jpg`: plan Mylna–Obłazkowa z 2014.
- `001387/image_907_zoom_10.jpg`: osobny plan Raptawickiej 2014.
- `001351/image_3576_zoom_10.jpg`: fotografia opisana w PIG jako otwór Obłazkowej, autor Jerzy Grodzicki; widoczny portal i przebieg ścieżki pod skałą.
- `001387/image_3703_zoom_10.jpg`: fotografia podejścia Raptawickiej, autor Jerzy Grodzicki; pokazuje stromy próg i dojście, nie umożliwia dokładnego odczytu obwodu studni.

Serwisowy schemat grafiki z lokalnego scraper `fetch.py:177`: `https://jaskiniepolski.pgi.gov.pl/Details/RenderImage?id=11826&zoom=10&ifGet=false`. Bieżące strony opisów odczytano przez web; pobranie samych grafik przez web było niedostępne. Oglądane lokalne grafiki mają metadane i stronę źródłową obok; nie twierdzimy, że ich bajty porównano z dzisiejszym serwerem.

Dodatkowa droga do pierwotnych fotografii Mylnej: [SKTJ, fotografie D. Bartoszewskiego](https://epimenides.sktj.pl/tatry/mylna_p.html) — podpisane wejście, Okno Pawlikowskiego, dojście i widok spod jaskini. Tekst wysokości na tej stronie nie rozstrzyga powyższego konfliktu.

## Znaczenie dla decyzji #36

Ocena każdego wariantu kotwicy powinna sprawdzać równocześnie główne wejście Mylnej, północne wyjście, portal Obłazkowej i studnię Raptawickiej. Różnicę wysokości spod okapu, dna studni, progu i gruntu należy zachować. Zgodność jednego odbicia ALS ze starym Z katalogowym nie potwierdza otworu. Najbardziej użyteczny wynik analizy to wskazanie, czy jedno wspólne przesunięcie zachowuje wiarygodne położenie wszystkich otworów, z osobnym poziomem pewności dla ich identyfikacji.
