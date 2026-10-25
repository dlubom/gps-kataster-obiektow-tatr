# Raptawicka — niezależna kontrola wysokości w NMT TPN

Odczyt: 2026-10-25. Zastosowano lokalny skill `tpn-elevation` i niezmieniony
skrypt `scripts/tpn_elevation.py`, dla dokładnej kotwicy użytkownika oraz
czterech osobnych narożników regionu wskazanego na ortofotomapie.

| Punkt | E EPSG:2180 | N EPSG:2180 | Odczyt gruntu TPN [m n.p.m.] |
|---|---:|---:|---:|
| Kotwica WGS84 49.2398375402,19.8620426566 | 562729.5 | 152838.5 | 1140.959961 |
| SW | 562729 | 152838 | 1141.030029 |
| SE | 562730 | 152838 | 1140.859985 |
| NW | 562729 | 152839 | 1178.079956 |
| NE | 562730 | 152839 | 1143.229980 |

To model **nmt_05m_mggp_2019**, dane z **14–15.10.2019**, raster0,5m.
Odniesienie to **m n.p.m. według legendy TPN**. Dokładne datum pionowe,
dokładność pionowa i sposób interpolacji pozostają **unknown**. Nie
przypisano PL-KRON86-NH ani PL-EVRF2007-NH i nie wykonywano konwersji Z.

Pełne wyniki z raw_elevation, datą pobrania, URL-ami zapytań i SHA256
odpowiedzi/metadanych/legendy: `anchor.json`, `SW.json`, `SE.json`,
`NW.json`, `NE.json`. `summary.json` zachowuje również hashe skryptu
i biblioteki. `query-points.json` zawiera osobne współrzędne WGS84 narożników,
przeliczone pyproj z EPSG:2180. Wszystkie odczyty zakończyły się poprawnie;
żadnego punktu nie zastąpiono sąsiednim.

## Interpretacja

Przyjęta kotwica znajduje się przy **wschodnim brzegu** małej studni
rozpoznanej na ortofotomapie. Plan PIG907 umieszcza poziom0,00 po tej stronie;
nie zidentyfikowano konkretnego znaku pomiarowego stacji1.0.

W regionie1×1m odczyty NMT różnią się aż o **37,219971m**. NarożnikNW
przechodzi do znacznie wyższej powierzchni, podczas gdy kotwica i dwa
południowe narożniki mają wartości około1141m. To wyraźny sygnał, że model
przecina skomplikowaną granicę skały/otworu. Nie można ustalić z tych pięciu
liczb, czy każdy piksel opisuje dolny brzeg, wyższą ścianę lub efekt
interpolacji; sam fakt etykiety „ground” nie dowodzi poziomu progu pod
przewieszką. Tego modelu nie wolno użyć jako samodzielnego pomiaru progu.

`tpn-five-points-on-ortho.png` pokazuje dokładne punkty na obrazie5cm.
Kolory obrazu NMT nie były używane do odczytu wysokości. Wynik jest
kontrolą dla niezależnej interpretacji rzeczywistych odbić ALS, nie nową
kotwicą Z ani dowodem wspólnego datum TPN i ALS2012.

Źródło daty i parametrów:
[TPN Topografia, s.4](https://geoportaltatry.pl/informacje_o_usludze/topografia.pdf).
Źródłowe URL-e modelu i zapytań znajdują się w pięciu plikach JSON.

Nie zmieniono YAML, Git, skryptu ani dokumentacji projektowej.
