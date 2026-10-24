# Issue #36: bieżące cztery punkty TPN

Odczyt publicznego API TPN 2026-10-24T18:30:18Z. Zapytanie po dokładnych GLOBALID z YAML; odpowiedź 4/4 obiekty, WGS84/EPSG:4326, bez przekroczenia limitu. Współrzędne przeliczono PyProj EPSG:4326 → EPSG:2180, `always_xy=True`. Odległości liczone z pary E/N; YAML `x_1992` jest N, `y_1992` jest E.

| Obiekt | OID | Pole OTWÓR | WER_LOK | WERYF (surowy kod) | Różnica bieżące TPN–YAML XY |
|---|---:|---|---|---:|---:|
| KSZ-0064, Mylna S | 3844 | `S` | `2023-08-23 MB ortofoto` | 4 | 0,00483 m |
| KSZ-0090, Obłazkowa | 32 | spacja | `2020-01-11 TZK ortofoto` | 1 | 0,00329 m |
| KSZ-0047, Raptawicka | 178 | **`górny`** | `2020-01-11 TZK ortofoto` | 1 | 0,00152 m |
| KSZ-0113, Mylna N | 3845 | `N` | `2023-08-23 MB NMT` | 4 | 0,00283 m |

`OPIS` i `UWAGI` we wszystkich czterech rekordach zawierają tylko spację. Żadna geometria odpowiedzi nie zawiera `z`, mimo `returnZ=true`. Nie pobierano NMT i nie sprawdzano nowych wysokości.

## Wnioski

- Wszystkie cztery zapisane pozycje TPN są aktualne do centymetrowej precyzji katalogu. Nie ma podstawy do wyjaśniania rozbieżności „przestarzałym eksportem TPN”.
- **Obłazkowa** nie ma dodatkowego opisu umiejscowienia punktu w portalu. `WER_LOK` dokumentuje weryfikację na ortofotomapie, nie pomiar geodezyjny/GNSS. Jej punkt TPN leży tylko **7,54 m** od TPN Mylnej S (ΔE +7,0353 m, ΔN +2,7184 m). To obserwacja geometryczna i powód do kontroli identyfikacji, nie dowód zamiany otworów.
- **Raptawicka** ma nazwę otworu `górny`. Nie można bez dodatkowego dowodu utożsamić tego punktu z JKTZ `Raptawicka:1.0`, opisywanym jako główny otwór. Możliwą niejednoznaczność trzeba zachować w ocenie sieci.
- Metryka warstwy mówi, że pole `otwór` nazywa otwór jaskiń wielootworowych; dane morfometryczne są przechowywane tylko przy najwyższym otworze systemu. Raptawicka jako jedyna z tych czterech ma morfometrię całego systemu (2404 m, 76,1 m). Samo to nie wyznacza pozycji górnego portalu, ale wzmacnia konieczność sprawdzenia jego tożsamości.
- Warstwa opisuje `wer_lok` jako datę, inicjały autora i metodę weryfikacji. `WERYF` to tymczasowe pole oznaczające obiekty zweryfikowane przez FF, lecz metryka nie zawiera domeny kodowej; **kodów 1 i 4 nie rozwijano** i nie utożsamiano ze statusem projektowym `zweryfikowany`.

## Dowody i odtworzenie

- [Warstwa jaskiń TPN](https://gis.tpn.pl/server/rest/services/Topografia___wektor_MIL1/MapServer/6?f=pjson).
- [issue36-tpn-response.json](issue36-tpn-response.json): surowa odpowiedź HTTP, SHA-256 `f0f6f2c4acafd68f215bd393d5539c17f79ec51cb816353ef1904a1afa4b24d7`.
- [issue36-tpn-comparison.json](issue36-tpn-comparison.json): dokładny URL żądania, czas, SHA, wszystkie atrybuty, geometrie, współrzędne E/N i porównanie YAML.
- [issue36-tpn-layer.json](issue36-tpn-layer.json): surowa metryka warstwy, odczytana po odpowiedzi punktów; native extent EPSG:3857, żądanie punktów jawnie EPSG:4326.

GLOBALID kolejno: `{CECF8620-A1C8-4941-A5B1-6C2226DC1F88}`, `{3D465399-A847-4F89-932C-4EB8A276D32E}`, `{F4DE5D37-5D76-4315-8BCC-4C57A5B68F1C}`, `{01A58CFE-5670-42A3-ADE1-715CF1F1E7A4}`.
