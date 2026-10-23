# PBI-112 — audyt punktów i odniesienia wysokościowego, wycinki 2025

Data odczytu: 2026-10-23. Zakres: cztery aktualne pomiary YAML dwóch
konkretnych otworów oraz metadane dwóch wycinków 2025. To audyt wejścia do
oceny geometrii, nie rozpoznanie otworu ani propozycja zmiany katalogu.
Nie zmieniono danych, best ani statusów weryfikacji.

## Tożsamość i punkty do oznaczenia

Źródłem znaczników pozostają aktualne pliki
[MTW-0054](../../../../../data/objects/MTW/MTW-0054.yml) i
[MLZ-0068](../../../../../data/objects/MLZ/MLZ-0068.yml).
Powiązania potwierdzają [C-0711](../../../../../data/caves/C-0711.yml) oraz
[C-0648](../../../../../data/caves/C-0648.yml):

- MTW-0054 / C-0711 / T.E-12.03: Jaskinia pod Wantą, alias Litworowy Dzwon,
  PIG 1535. Nie Dziura pod Wantą.
- MLZ-0068 / C-0648 / T.E-13.01: Jaskinia Śnieżna, PIG 496. Badamy ten
  otwór, nie cały system Wielkiej Śnieżnej ani Śnieżną Studnię.

W tabeli kolejność osi odpowiada LAS/CloudCompare: **X=easting=`y_1992`,
Y=northing=`x_1992`**. Liczby Z są dokładnym odpisem YAML, bez transformacji.

| Etykieta | LAS X / easting [m] | LAS Y / northing [m] | Z zapisane [m] | Datum Z |
|---|---:|---:|---:|---|
| MTW-0054 m-001 PIG | 566324.49 | 152969.10 | 1793.3 | unknown |
| MTW-0054 m-002 TPN | 566319.78 | 153075.02 | 1790.525556 | unknown |
| MLZ-0068 m-001 PIG | 567417.26 | 152928.35 | 1700.7 | unknown |
| MLZ-0068 m-002 TPN | 567414.24 | 152932.54 | 1699.800044 | unknown |

| Etykieta | Latitude WGS84 | Longitude WGS84 | observed_date = source_date |
|---|---:|---:|---|
| MTW-0054 m-001 PIG | 49.24063334 | 19.91146104 | 2013-12-31 |
| MTW-0054 m-002 TPN | 49.24158679002186 | 19.91141386272168 | 2024-07-30 |
| MLZ-0068 m-001 PIG | 49.24014727 | 19.92646948 | 2013-12-31 |
| MLZ-0068 m-002 TPN | 49.24018529855171 | 19.926428687029865 | 2024-07-30 |

Wszystkie cztery mają `method: source_record`,
`elevation_source: source_record`, obie dokładności `null`,
`verification_status: nieweryfikowany`, urządzenie i dane weryfikatora
`null`. W obu obiektach `best_measurement` jest `auto` → `m-002`.
Wybór auto odzwierciedla regułę źródłową projektu i nie stanowi dowodu,
że pozycja TPN trafia w otwór.

Referencje TPN to odpowiednio
`TPN:{9306F8A3-B212-4456-B121-7B821EE13B60}` oraz
`TPN:{4F3D8007-20EB-412A-A46E-FE1721713639}`.
Uwagi `WER_LOK` w YAML wskazują ortofoto: dla Pod Wantą
`2020-01-11 TZK ortofoto`, dla Śnieżnej `11-02-2020 FF ortofotomapa`.
Nie są dowodem pomiaru GNSS lub wysokości progu. Daty 2013-12-31 i
2024-07-30 zachowujemy jako zapisane daty rekordów; nie utożsamiamy ich
automatycznie z dniem pomiaru w terenie.

Różnice **TPN minus PIG** obliczone z zapisanych osi PL-1992:

| Obiekt | Δeasting [m] | Δnorthing [m] | Odległość XY [m] |
|---|---:|---:|---:|
| Pod Wantą | -4.71 | +105.92 | 106.0246692992 |
| Śnieżna | -3.02 | +4.19 | 5.1649298156 |

To odległości pomiędzy rekordami, nie wyznaczone błędy lokalizacji.
Wycinek Pod Wantą musi zachować obie okolice. Nie rozstrzygamy na podstawie
priorytetu źródła, nazwy lub różnicy wysokości, która pozycja jest poprawna.

## Sprawdzenie źródeł opisowych

Pierwotne strony PIG odczytano 2026-10-23 przez przeglądarkę tekstową.
To odczyt treści udostępnionej przez narzędzie web, bez archiwizacji pełnego
HTML. Narzędzie wskazało wcześniejsze indeksowanie: około sześciu miesięcy
dla Pod Wantą i dwóch dni dla Śnieżnej; nie potwierdzono bieżącej rewizji
serwera PIG. Istotne wartości są również w lokalnym dumpie
`data/sources/pig/jaskinie_polski_pig_dump.jsonl`, wiersze 826 i 46.

**Pod Wantą:** PIG podaje ekspozycję SSW, soczewkowaty otwór około
1,2 × 5 m i płytę około 2 × 1,5 m zaklinowaną w dolnej części. Opis lokuje
go w skałkach Ratusza Miętusiego, nad kosówką. Wysokość wynosi 1793,30 m
n.p.m.; tekst wspomina pomiary sytuacyjno-wysokościowe otworu przez zespół
AGH 16.08.1981. Nie podaje nazwy datum, dokładności, punktu stabilizowanego
ani dowodu, że obecne współrzędne i wysokość pochodzą razem z tamtego pomiaru.
Metryka opisuje oczekiwaną morfologię, nie potwierdza rozpoznania jej w ALS.
[PIG 1535](https://jaskiniepolski.pgi.gov.pl/Details/Information/1535).

**Śnieżna:** PIG podaje ekspozycję E, trójkątny otwór około 2 × 2 m,
zagłębienie za dużym głazem u podstawy ściany oraz częste zaleganie śniegu.
Za wejściem korytarz schodzi stromo. Wysokość to 1700,70 m n.p.m.;
w odczytanej metryce brak nazwanego datum, dokładności i jednoznacznej
definicji punktu wysokościowego. Opis pozwala wybrać kierunki oglądu,
ale nie zamienia zagłębienia lub cienia odbić w potwierdzony otwór.
[PIG 496](https://jaskiniepolski.pgi.gov.pl/Details/Information/496).

Publiczny zapis WGS84 PIG w stopniach/minutach/sekundach ma mniejszą
precyzję prezentacji niż liczby w YAML. Znaczniki muszą używać YAML;
nie zastępować ich ponownym przeliczeniem zaokrąglonej prezentacji strony.

## Co potwierdza odniesienie Z chmur 2025

[Skorowidz JSON](../lidar-tatry-index.json) i powiązany
[surowy XML](../lidar-evrf-tatry.xml) zawierają dla obu użytych arkuszy:

| Pole | Wartość |
|---|---|
| `uklad_xy` | PL-1992 |
| `uklad_h` | PL-EVRF2007-NH |
| `akt_data` | 2025-08-13 |
| `nr_zglosz` | GK-FOTO.6201.14.2025 |
| `char_przestrz` | 12 p/m2 |
| `blad_sr_wys` | 0.05 m |
| `blad_sr_syt` | 0.06 m |

Pod Wantą jest związana adresem pobrania z arkuszem
`83768_1784517_M-34-100-B-d-1-2-1-3.laz`, Śnieżna z
`83768_1784521_M-34-100-B-d-1-2-2-3.laz`.
Źródło skorowidza: [GUGiK WFS EVRF2007](https://mapy.geoportal.gov.pl/wss/service/PZGIK/DanePomiaroweLidarEVRF2007/WFS/Skorowidze).
Parametry błędu są deklaracjami skorowidza; nie należy przenosić ich
wprost na niepewność rozpoznanego progu, pionowej ściany lub obiektu
ukrytego przez głaz, śnieg bądź roślinność.

Niezależny odczyt binarnych VLR obu lokalnych LAS potwierdził dwa VLR,
w tym GeoKeyDirectoryTag z siedmioma kluczami:
`1024, 1025, 1026, 2049, 2054, 3072, 3076`.
`3072=2180`, `3076=9001`; brak kluczy pionowych `4096–4099`.
Brak dodatkowego WKT VLR. Jest to zgodne z
[wcześniejszym odczytem PDAL](../../PBI-112.md#próba-na-rzeczywistych-plikach):
**EPSG:2180 jest w nagłówku; PL-EVRF2007-NH wynika ze skorowidza, nie
z nagłówka LAS.** Nie wykonano transformacji pionowej ani zmiany nagłówków.

Skala rekordu XYZ wynosi 0,01 m. To rozdzielczość zapisu liczb, a nie
stwierdzona dokładność powierzchni lub progu.
[inspection.json](../inspection.json) wiąże źródła i wycinki przez SHA-256.

## Reguły porównania i opisów ilustracji

1. **Zapisany XYZ:** znacznik z dokładnym Z YAML należy oznaczyć
   `XYZ YAML; datum Z unknown`. Nałożenie go w scenie ALS jest wyłącznie
   wspólnym wyświetleniem wartości liczbowych. Nie jest dopasowaniem datum.
2. **Pozycja XY na chmurze:** osobny znacznik powinien mówić
   `XY YAML; Z punktu ALS` i wskazywać regułę wyboru rzeczywistego odbicia,
   jego identyfikator w wycinku oraz odległość XY od pozycji katalogowej.
   Jeżeli punkt leży obok zadanego XY, nie nazywać go dokładnym przecięciem
   pionu z powierzchnią. Rzut na estymowaną powierzchnię trzeba jawnie
   opisać jako estymację/interpolację.
3. **Porównywalne:** geometria i różnice Z rzeczywistych odbić w tych
   chmurach 2025, przy zachowaniu źródła, klasy, grupy PointSourceId i
   kontroli lokalnej zgodności. Wspólny datum nie gwarantuje lokalnego braku
   błędu między grupami.
4. **Nieporównywalne jako korekta wysokości:** bezpośrednie
   `Z ALS − elevation_m YAML` dla wszystkich czterech pomiarów. Ich datum
   jest nieznany. Taka różnica nie dowodzi błędu katalogu, osiadania progu
   ani zmiany wysokości; nie przypisywać źródłom historycznym datum na
   podstawie samego wieku pomiaru.
5. **Teren a próg:** klasa gruntu, najniższy punkt, raster lub najbliższe
   odbicie nie definiują automatycznie progu. Nawet rzeczywiste odbicie
   może pochodzić z głazu, śniegu, ściany lub innej części otworu. Kandydat
   progu wymaga ciągłości geometrii w przekrojach, odrębnego uzasadnienia
   interpretacji i definicji punktu, którego wysokość chcemy podać.
6. **PointSourceId:** zachować grupy 79/80/81/82 Pod Wantą i 80/81/82
   Śnieżnej. Same ID nie dowodzą liczby kierunków nalotu. Interpretacja
   trajektorii wymaga dodatkowych metadanych. Nie traktować też
   ScanDirectionFlag jako azymutu samolotu.

Brak rozpoznawalnego progu jest dopuszczalnym wynikiem. Wtedy można
raportować obserwowane powierzchnie i kandydatów wraz z niepewnością
interpretacji, bez proponowania liczbowej korekty katalogu. Brak odbić
pozostaje brakiem danych, a interpolowana powierzchnia nie jest pomiarem.

## Odtworzenie audytu wejścia

Polecenie z katalogu repo, bez modyfikacji danych:

```bash
.venv/bin/python - <<'PY'
import hashlib
import math
from pathlib import Path
import yaml

for rel in ('data/objects/MTW/MTW-0054.yml',
            'data/objects/MLZ/MLZ-0068.yml'):
    path = Path(rel)
    obj = yaml.safe_load(path.read_text())
    print(rel, hashlib.sha256(path.read_bytes()).hexdigest())
    for m in obj['measurements']:
        print(obj['id'], m['id'], m['source'],
              (m['y_1992'], m['x_1992'], m['elevation_m']),
              m['elevation_datum'], m['horizontal_accuracy_m'],
              m['vertical_accuracy_m'], m['source_ref'])
    pig = next(m for m in obj['measurements'] if m['id'] == 'm-001')
    tpn = next(m for m in obj['measurements'] if m['id'] == 'm-002')
    de = tpn['y_1992'] - pig['y_1992']
    dn = tpn['x_1992'] - pig['x_1992']
    print('TPN-PIG:', de, dn, math.hypot(de, dn))
PY
```

SHA-256 wejściowych YAML podczas audytu:

```text
6a9df8f8ae9b6019a9cd3b09811bfb56bf0ba9d56f91edfdcc4f1e10ddfda1f1  data/objects/MTW/MTW-0054.yml
72418bb1ff6d7a4195ae0560006bfd8a2755e5b90621dda48e8281e66856f244  data/objects/MLZ/MLZ-0068.yml
6fd1f0faed79ff0e5d0d8b6c7b02b01cb5f2b5e79e42f1b0a8fa470e2082598a  data/caves/C-0711.yml
f418094dc85da90a507afab497d8e6542103d9882dfda41b4aa9a3ff1d18147d  data/caves/C-0648.yml
```

Nie analizowano geometrii innych roczników ani Śnieżnej Studni.
