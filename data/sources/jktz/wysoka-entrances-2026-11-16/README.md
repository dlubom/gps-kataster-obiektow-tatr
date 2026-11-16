# Cztery otwory sieci JKTZ po korekcie kotwicy Wysokiej

Decyzją Dariusza Lubomskiego z 2026-11-16 ponownie wyznaczono pozycje
KSW-0264–KSW-0267, używając skorygowanego pomiaru
KSW-0189/m-004 jako jedynej kotwicy Wysoka7Progow:W7-0.
Dopisane m-002 są ręcznymi Best. Historyczne m-001 oznaczono jako `odrzucony`
z powodu błędnej kotwicy; ich geometrię, daty i kolejność zachowano.
Nie są to nowe obserwacje terenowe ani niezależne fixy tej samej sieci.

## Źródła

- Sieć JKTZ: rewizja
  [77963f9ea8268556197a16e9b391cb0539b5a4ee](https://github.com/dlubom/Jaskiniowy-Kataster-Tatr-Zachodnich/tree/77963f9ea8268556197a16e9b391cb0539b5a4ee),
  ta sama co przy [poprzednich wynikach](../wysoka-entrances-2026-11-12/README.md).
  Zachowano siedem SRV, połączenia, tożsamości otworów oraz przyjętą
  rekonstrukcję Pośredniej. Sumy źródeł są w [coordinates.json](coordinates.json).
- Nowa kotwica: [KSW-0189/m-004](../../../objects/KSW/KSW-0189.yml),
  źródło `unknown:gnss:Wysoka7Progow:correction-2026-11-16`.
  E = 564379,3653697347 m, N = 152161,819801582 m (EPSG:2180),
  H = 1486,6914545149514 m (PL-EVRF2007-NH).
  [Wyciąg wartości](../../wysoka-bandzioch/corrected-2026-11-16/README.md)
  opisuje pochodzenie i ograniczenia.

## Wyznaczenie pozycji

W tymczasowej kopii źródeł zmieniono tylko aktywny `#fix` W7-0 w OTWORY.SRV.
Stara i nowa linia oraz sumy obu wersji są w coordinates.json. Konwersja
kotwicy EPSG:2180 → 4326 używa `always_xy=True`. KATASTER.wpj zachowuje
WGS 1984 / UTM 34N. Pozostałych fixów, danych sieci, deklaracji dat ani
zastępczego `DECL=0` nie zmieniano. Rzeczywista deklinacja dawnych pomiarów
podziemnych pozostaje nieznana; korekta dotyczy kotwicy, nie ich azymutów.

```sh
cavern --no-auxiliary-files -o /tmp/wysoka-new KATASTER.wpj
survexport --csv /tmp/wysoka-new.3d /tmp/wysoka-new.csv
```

Wyniki Survex 1.4.24 mają rozdzielczość 0,01 m. Przeliczenie EPSG:32634 →
4326 używa helpera JKTZ `utm34n_wgs84.py` (pyproj 3.7.2); lon/lat zapisano
do 10 miejsc po przecinku. Wysokość jest przenoszona bez transformacji.
Nowe datum wynika z kotwicy, a dokładność sieci pozostaje nieznana.
`observed_date: 2026-11-16` oznacza datę obliczenia. Status pozostaje
`nieweryfikowany`.

| Obiekt | Stacja | E UTM 34N [m] | N UTM 34N [m] | H [m] | lon | lat |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| KSW-0264 | Wysoka7Progow:W7-500 | 418784.64 | 5454046.66 | 1472.29 | 19.8843871612 | 49.2338093081 |
| KSW-0265 | Wysoka7Progow:W-300 | 418799.26 | 5454037.06 | 1498.68 | 19.8845898928 | 49.2337249092 |
| KSW-0266 | Wysoka7Progow:W7-P500 | 418796.46 | 5454023.75 | 1486.77 | 19.8845541340 | 49.2336048338 |
| KSW-0267 | Wysoka7Progow:W7-P507 | 418795.42 | 5454035.33 | 1488.18 | 19.8845375057 | 49.2337088411 |

Zmiana kotwicy w UTM wynosi około +4,11090 m E, −7,08387 m N i +0,00145 m H.
Wysokości tych czterech punktów pozostają takie same po zapisie co 0,01 m.
Do odtworzenia wyników należy użyć wskazanej rewizji sieci i dokładnej
zamiany fixa z coordinates.json, nie dowolnego nowszego JKTZ.

## Integracja

Wyniki służą jako `OBJECT_REF`, nie jako dodatkowe niezależne aktywne fixy.
Aktywna kotwica W7-0 powinna pochodzić z tego samego zatwierdzonego snapshotu
GPS co te cztery pozycje. Ta aktualizacja zapisuje wyniki w katalogu GPS;
nie modyfikuje repozytorium JKTZ ani opublikowanych wydań. Integracja JKTZ
następuje dopiero po osobno zleconym scaleniu i wydaniu GPS.
