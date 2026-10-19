# PBI-101 — odtwarzalne wartości wyliczane

Pierwsza rzeczywista paczka ujawniła różnicę PROJ/geodezyjnych obliczeń
między macOS arm64 i Linux x86_64. Diagnostyczny CI
[39311292320](https://github.com/dlubom/gps-kataster-obiektow-tatr/actions/runs/39311292320)
porównał ten sam snapshot, historyczny CSV i katalog. Dla pierwszego rekordu
otrzymał wyliczoną szerokość CSV `49.24432741630521`, zamiast zapisanej na
Macu `49.244327416305204`. Różnica wpływała na odciski lokalizacji/revizji
CSV, zbioru kandydatów i raportu. Odległości różniły się również w końcowych
cyfrach, np. `0.005245837260298067` wobec `0.005245836765731403` m.

To potwierdzona przyczyna, nie oczekiwana blokada pending ani zmiana API.
Testy diagnostyczne zachowują odmowę nawet dla zmiany surowego XY o `1e-18`.

## Jawna precyzja pochodnych

Raport zawiera `derived_precision` z wersją `tpn-derived-numerics-v1`.
Implementacja: `tpn_precision.py`. Zaokrąglenie half-even obejmuje tylko:

| Wartość wyliczana | Precyzja zapisu |
|---|---|
| WGS84 wyliczone z historycznego CSV PL-1992 | 9 miejsc po przecinku stopnia |
| Odległość wyświetlana w raporcie/history/candidate evidence | 3 miejsca po przecinku metra |
| Cache PL-1992 **nowo dodanego** pomiaru TPN | 3 miejsca po przecinku metra |

Precyzja zapisu nie jest deklaracją dokładności terenowej. Reguła promienia
kandydatów i próg bootstrapu 0,1 m nadal porównują **niezaokrąglony wynik
geodezyjny**; zaokrąglenie odległości następuje dopiero przy zapisie dowodu.
Test z `100.00001 m` nadal odrzuca kandydata przy promieniu `100 m`.

Surowe bajty API/CSV/XLSX, pełna dziesiętna geometria API, źródłowe
revision/location_hash API i wszystkie dotychczasowe pomiary pozostają
niezmienione. Normalizacja API nie używa tej precyzji. Nowy pomiar zachowuje
WGS84 API w istniejącym modelu float YAML; tylko nowy cache projekcji XY
ma zapis milimetrowy. Nie zaokrągla się historii ani nie przenosi wysokości.

## Rewizja planu, bez poluzowania kontroli

Polityka źródłowa `tpn-sync-v1`, hash kontraktu i snapshot pozostają
niezmienione. Jawna polityka pochodnych jest częścią hashowanego reportu,
więc stary report nie przechodzi przez nową regułę po cichym przeliczeniu
hasha. Został zachowany bajtowo w
[archiwum pierwszego review](verification/PBI-101-review/superseded-v1/README.md).
Nową rewizję tej samej paczki wygenerowano CLI z utrwalonego snapshotu
i tej samej bazy, z przyjętym stanem wyłącznie z origin/main.

Porównanie wszystkich 1035 rekordów potwierdza identyczne pełne dane API,
change_id i revision_hash API, klasyfikacje, cele, preimages, konflikty,
potrzebę nowego pomiaru oraz zbiory kandydatów. Zmieniły się wyłącznie
pochodne CSV/odległości i zależne od nich odciski. Jawne decyzje użytkownika
614 approve / 26 defer zachowują ten sam zakres i podstawę źródłową.

Odtworzenie reportu, decyzji, wynikowych plików i receipt nadal wymaga
ścisłej zgodności kanonicznej. Nie dodano tolerancji do porównywania hashów,
obejścia kontroli ani zmiany ogólnego selektora best. Testy symulują szum
projekcji/geodezji i sprawdzają identyczny report/cache; hosted CI weryfikuje
rzeczywisty wynik Linuksa dla końcowego SHA.
