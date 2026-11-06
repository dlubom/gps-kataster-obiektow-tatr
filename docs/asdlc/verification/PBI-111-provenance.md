# Pochodzenie czterech punktów — PBI-111

Ustalenia źródłowe z 2026-10-23. Metoda `siec_pomiarowa` oznacza punkt
wynikający z sieci pomiarów jaskiniowych lub powierzchniowych; nie dowodzi
użycia GNSS ani określonej dokładności.

## Źródła i ustalenia

Import GPS `b83dede4bf36ccbf87e9e3dbf97e5c6493c2de14` błędnie opisał
wszystkie cztery m-003 jako unknown GNSS. Użytkownik zlecił korektę na
podstawie historii JKTZ, bez zmiany ręcznych wskazań ani lokalizacji.

Źródło: repozytorium `dlubom/Jaskiniowy-Kataster-Tatr-Zachodnich`,
rewizja `773c8e2e6aa910c8ba78192ae6741d107c6598e2`, rodzic
`6561bab3bdcd37f607820a4a1f0373147b63572e` wydzielającego wspólne fixy.

| Obiekt / m-003 | Stacja JKTZ | UTM 34N E / N / H [m] | Wynik |
|---|---|---|---|
| KSZ-0047 | Pawlikowskiego:Raptawicka:1.0 | 417181.04 / 5454744.17 / 1141.31 | siec_pomiarowa |
| KSZ-0090 | Pawlikowskiego:Oblazkowa:0.0 | 417206.73 / 5454709.77 / 1096.62 | siec_pomiarowa |
| LEJ-0002 | BandziochKom:136 | 415839.34 / 5455064.26 / 1675.02 | siec_pomiarowa |
| KSZ-0064 | Pawlikowskiego:Mylna:0 | 417179.14 / 5454690.67 / 1098.00 | source_record |

- `MYLNA_M.SRV`: stały fix Mylna:0, metadane PIG/F. Filar; pierwotna
  metoda wyznaczenia niepotwierdzona. Zapis istnieje już w `54fb7d7`.
- Sieć Pawlikowskiego obejmuje pomiary jaskiń oraz powierzchniowy
  `POW_ORM.SRV`, łączący Obłazkową i Raptawicką. Oba punkty są wynikowe.
- `BK-CG.SRV`: fix dolnego BandziochKom:000 opisano unknown - GNSS;
  górny BandziochKom:136 wynika z ciągu międzyotworowego RECT/NEU.
- Pełne ścieżki źródeł i linki przypięte do SHA zapisano w notes pomiarów.

Do odtworzenia: wyeksportować `git archive 773c8e2…` (KATASTER.wpj
i robocze SRV bez `_RAW`) do katalogu tymczasowego, wykonać
`cavern -o historic KATASTER.wpj`, odczytać stacje przez
`dump3d historic.3d` i przeliczyć EPSG:32634 → EPSG:4326.
Survex 1.4.24: exit 0, 69 historycznych ostrzeżeń kompilacji; dla trzech
punktów brak FIXED, dla Mylnej FIXED. Wynik po konwersji zgodny z zapisanym wtedy
lat/lon do 1e-10 stopnia, wysokości identyczne. To dowód pochodzenia
z historycznej sieci, bez deklaracji jej dokładności ani równoważności
kompilacji z natywnym Walls. Historyczne źródła i odtworzony wynik
pozostają odrębnymi klasami pochodzenia; nie dodano artefaktów do danych.

Korekta dotyczyła opisów pochodzenia m-003, bez zmiany lokalizacji,
ręcznego Best, statusów i dokładności. Zachowano `source: inne` i nieznane
datum. Daty importu nie potwierdzają dat pomiarów terenowych.
