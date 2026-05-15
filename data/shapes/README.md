# Shapefiles

Warstwy referencyjne używane do przydzielania prefixu w ID obiektu terenowego.
Wszystkie pliki w projekcji **EPSG:2180 (ETRS89 / PL-1992)**, UTF-8.

## doliny.*

18 polskich dolin tatrzańskich. Atrybut `NAME` (String, 42) — klucz
w mapowaniu `config/prefixes.yml`.

Pięć dolin jest podzielonych geometrycznie na części **Zachód** i **Wschód**
(Chochołowska, Kościeliska, Miętusia, Małej Łąki, Bystrej). Każda połówka
ma osobny polygon i osobny prefix.

## granica_polski.*

Polygon granic Rzeczypospolitej Polskiej. 1 feature. Fallback dla obiektów
poza dolinami — prefix `PL`.

## granica_slowacji.*

Polygon granic Republiki Słowackiej. 1 feature. Fallback dla obiektów poza
Polską — prefix `SK`.

## Algorytm przydzielania prefixu

Szczegóły w `SPECYFIKACJA.md` §4.3. W skrócie:

1. Reprojekcja pomiaru `(lat, lon)` WGS84 → EPSG:2180.
2. Point-in-polygon na `doliny.shp` → prefix z `config/prefixes.yml`.
3. Fallback: `granica_polski.shp` → `PL`.
4. Fallback: `granica_slowacji.shp` → `SK`.
5. Brak dopasowania → błąd, operator rozstrzyga ręcznie.

## Szybka weryfikacja

```bash
ogrinfo -al -so data/shapes/doliny.shp            # 18 features, EPSG:2180
ogrinfo -al -so data/shapes/granica_polski.shp    #  1 feature,  EPSG:2180
ogrinfo -al -so data/shapes/granica_slowacji.shp  #  1 feature,  EPSG:2180
```
