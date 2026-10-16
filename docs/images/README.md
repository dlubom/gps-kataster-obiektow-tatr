# Mapy do README

Statyczne ilustracje z 2026-10-16, dane z `main`
`a17e0270599d1694024a05dcbd2f872e8234cd11` (stan po v1.0.4).
Nie aktualizują się automatycznie przy wydaniu.

| Plik | Zakres |
|---|---|
| `tatry-regiony-osm.png` | Cały zbiór: 1009 obiektów, 18 polygonów dolin, osobne kolory PL/SK poza polygonami. |
| `dolina-koscieliska-osm.png` | Kościeliska i okolice: 770 obiektów w kadrze, wspólny różowy symbol. |

Każdy symbol przedstawia jeden obiekt z eksportu `best-measurements`,
nie wszystkie pomiary ani liczbę jaskiń. Symbole mogą się nakładać.
Region ustala `PrefixResolver.resolve(lat=..., lon=...)` na podstawie
bieżącego położenia best oraz `data/shapes/doliny.shp` i `config/prefixes.yml`.
Kolor regionu nie musi odpowiadać trwałemu prefixowi ID obiektu;
nie zmienia ID, best, dokładności ani statusu weryfikacji.

## Odtworzenie / aktualizacja

1. Na wybranym commicie zwaliduj YAML i wygeneruj GeoJSON:

   ```bash
   uv run python scripts/export_best_measurements.py \
     --output-dir build/readme-maps --generated-at 2026-10-16T00:00:00Z
   ```

2. Wyświetl GeoJSON na OSM w Leaflet 1.9.4. Polygony dolin przelicz
   z EPSG:2180 do WGS84, zachowując GIS X/Y = easting/northing
   (`Transformer.from_crs(2180, 4326, always_xy=True)`). Kolory punktów
   i polygonów dobierz według tego samego wyniku resolvera. Legenda ma
   obejmować wszystkie 18 regionów oraz PL/SK; sumy muszą dawać cały eksport.
3. Panorama: zrzut 1440 × 1040 px, mapa 1080 × 900 px, legenda po prawej.
   `fitBounds` obejmuje wszystkie punkty i polygony, padding 28 px,
   `zoomSnap: 0.1` (dla tego zbioru zoom 12.2, środek 49.2329943, 19.9380412).
   Punkty: promień 3.5 px, biała obwódka 0.8 px. Polygony: opacity 0.8,
   weight 1.5, fillOpacity 0.17. Etykiety regionów w środkach ich bounds.
4. Zbliżenie: zrzut 1440 × 1000 px, mapa 1440 × 860 px,
   środek 49.253, 19.866, zoom 14. Punkty: promień 4 px, kolor `#ac247e`,
   biała obwódka 1.3 px. Podpisy: KSW-0256 (Mroźna, wejście),
   KSW-0201 (Czarna), KSZ-0064 (Mylna), LEJ-0002 (Bańdzioch, otwór górny).
5. Przed zrzutem sprawdź załadowanie wszystkich kafli bez błędów,
   liczbę punktów i polygonów, czytelność legendy i atrybucji.
   Zapisz PNG, datę i commit danych; zaktualizuj podpisy PL/EN/SK.

## Podkład i prawa

Podkład: © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright),
dane OSM na [ODbL](https://opendatacommons.org/licenses/odbl/).
Kafle standardowej mapy pochodzą z `https://tile.openstreetmap.org/{z}/{x}/{y}.png`;
odczytano wyłącznie dwa widoczne kadry (24 i 16 kafli), bez skanowania obszaru.
Atrybucja jest również wewnątrz PNG. Przy ponownym przygotowaniu obowiązuje
[polityka serwera kafli](https://operations.osmfoundation.org/policies/tiles/).
Licencja repozytorium nie zastępuje praw do podkładu OSM.
