# Odtworzenie badania issue #36

Wnioski i ilustracje: [PBI-116](../PBI-116.md). Dane finalnego katalogu są
niezmienione względem main `2a40b8e224ce248296e1d82742728bd9b8b6d8d1`.

## Wejścia

- LiDAR: dwa publiczne LAZ, pełne adresy i SHA w [acquisition.json](acquisition.json).
  Zachowane odpowiedzi WFS są surowe, bez poprawiania formatowania.
- JKTZ: rewizja `773c8e2e6aa910c8ba78192ae6741d107c6598e2`, źródła z
  manifestu [network-raw-comparison.json](network-raw-comparison.json).
- Cztery obiekty YAML: KSZ-0064/0090/0047/0113, sumy w [analysis.json](analysis.json).
- TPN: [surowa odpowiedź](issue36-tpn-response.json),
  [zapytanie i porównanie](issue36-tpn-comparison.json), [opis](tpn.md).
- PIG: źródłowe opisy i oryginalne lokalne grafiki, adresy i SHA w
  [entrances.md](entrances.md). Grafiki nie są reprodukowane w tym PR.

## Środowisko i polecenia

Python 3.12; biblioteki analizy w [requirements.txt](requirements.txt).
Survex 1.4.24 (`cavern`, `dump3d`) do odtworzenia sieci.
PDAL 2.9.3 / pdal_wrench 1.4.0 z QGIS 4.0.1 do niezależnego przycięcia LAZ.
Lokalnie biblioteki badania zainstalowano w osobnym katalogu tymczasowym;
nie zmieniono zależności projektu.

Uruchamiać z katalogu repo. Polecenia zapisują/nadpisują własne produkty
badania; nie kierować ich do katalogu z inną pracą. Skrypt pobierania
wykonuje nowe zapytania live, których odpowiedzi mogą różnić się od
zachowanego snapshotu; archiwalne XML pozostają tutaj jako dowody.

```sh
bash docs/asdlc/verification/PBI-116/acquire.sh
python docs/asdlc/verification/PBI-116/crop.py
python docs/asdlc/verification/PBI-116/reconstruct-network.py \
  --jktz /path/to/Jaskiniowy-Kataster-Tatr-Zachodnich \
  --catalogue . --output build/research/mylna-network-reproduction
python docs/asdlc/verification/PBI-116/analyze.py \
  build/research/mylna-2026-10-24/pawlikowskiego-2012.las \
  build/research/mylna-analysis-reproduction
python docs/asdlc/verification/PBI-116/independent-readback.py \
  build/research/mylna-analysis-reproduction \
  build/research/mylna-analysis-reproduction/independent-readback.json
```

`analyze.py` sprawdza SHA LAS względem zachowanego manifestu i korzysta
z wersjonowanych sieci. Plik odtworzony przez `reconstruct-network.py`
powinien być równy `network-raw-comparison.json`. Starszy `network.json`
zawiera tę samą część historyczną z prostszymi metadanymi; oba są kontrolowane
na zgodność węzłów i odcinków. Kompilacja zgłasza oryginalne ostrzeżenia
opisane w [network-sources.md](network-sources.md), nie poprawia źródeł.

LAS ma rekordy formatu 3, LAS 1.2, kwantyzację 0,01 m. Kolejność osi:
X=E=`y_1992`, Y=N=`x_1992`. `record_index` liczy od zera w połączonym LAS;
lokalny `pawlikowskiego-2012-source-records.npz` mapuje go na arkusz i rekord
oryginalnego LAZ. Tolerancja obliczeniowa 1e-9 m w selekcji gwarantuje
zachowanie punktów dokładnie na granicy pasa; nie jest dokładnością danych.

## Weryfikacja

[pdal-independent-check.json](pdal-independent-check.json): niezależne
przycięcie obu LAZ i porównanie wszystkich rekordów oraz 22 pól.
[independent-readback.json](independent-readback.json): dekoder `struct`
kontroluje liczby, najbliższe rekordy, wszystkie wiersze CSV i kompletność
pasów obliczoną w całkowitych centymetrach.

Wersjonowane `SHA256SUMS` obejmuje źródła pomocnicze, skrypty i wyniki
(poza samą listą sum). Dwa końcowe uruchomienia analizy porównano bajtowo.
Kontrola dokumentacji: `tests/test_release_docs.py` oraz
`tests/test_operational_docs.py`. CI PR sprawdza cały standardowy zestaw.
Nie dodano testów produkcyjnych ani nowego skilla.
