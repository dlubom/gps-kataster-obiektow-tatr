# PBI-111 — korekta pochodzenia czterech punktów

2026-10-23, kontynuacja istniejącego draft PR #19 na polecenie użytkownika.
Baza poprawki: `ea04f3aafdc41a7d37f1ea7349d2683f6c473e1a`.
[Zakres i zaakceptowana nazwa](../plans/PBI-111-provenance.md).

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
punktów brak FIXED, dla Mylnej FIXED. Wynik po konwersji zgodny z obecnym
lat/lon do 1e-10 stopnia, wysokości identyczne. To dowód pochodzenia
z historycznej sieci, bez deklaracji jej dokładności ani równoważności
kompilacji z natywnym Walls. Historyczne źródła i odtworzony wynik
pozostają odrębnymi klasami pochodzenia; nie dodano artefaktów do danych.

## Manifest i kontrakt

Tylko m-003 w czterech wymienionych obiektach: method, source_ref, tags,
elevation_source, notes; także korekta błędnych wzmiankowań GNSS w reason
best i audyt best/obiektu. `source: inne` zachowane. Trzy wysokości wynikowe
mają other, wysokość kotwicy Mylnej source_record; datum nadal unknown.
Daty importu zachowano, z wyjaśnieniem w notes, że nie potwierdzają dat
pomiarów terenowych. Nie zmieniono statusów ani nie podniesiono dokładności.

Porównanie strukturalne do bazy i dosłownych linii geometrii potwierdza:
mode manual, measurement_id m-003, wszystkie lat/lon/XY, wysokości, datum,
dokładności, daty i pozostałe pomiary pozostają bez zmian. Poza czterema
plikami żaden śledzony plik data/ nie uległ zmianie.

Dodano jedną wartość enum method w schema_version 1. Brak zmian algorytmu
auto, formatu eksportów i produkcyjnego kodu Python. Konsumenci zamkniętej
listy metod muszą przyjąć nową wartość, co opisuje changelog schematu.

## Weryfikacja

- Nowy test `test_survey_network_manual_point_survives_newer_tpn_in_database_and_exports`:
  RED — SQLite odrzucone przez SCHEMA_VALIDATION dla nowej metody;
  GREEN — manual m-001 zachowany przy automatycznym kandydacie TPN m-002,
  nowa metoda zapisana w SQLite, CSV i GeoJSON, status zachowany.
  Usunięcie nowej wartości enum odtwarza RED — kontrola 1/1 zmiany schematu.
- `.venv/bin/ruff format --check src tests scripts`: PASS, 65 plików.
- `.venv/bin/ruff check src tests scripts`: PASS.
- `.venv/bin/python -m pytest`: **951 passed**.
- `.venv/bin/python scripts/validate.py`: exit 0, **0 błędów / 2103 ostrzeżenia**.
- `scripts/build_release_artifacts.py` do
  `build/verification/PBI-111-provenance/`: 1007 obiektów, 1001 jaskiń,
  1908 pomiarów; odczyt 10/10 artefaktów, SQLite integrity/FK i identyczność
  ZIP SQLite, Best 1007 / Full 1908. Geometria i ID best całego katalogu
  zgodne z YAML (CSV/GPX z dotychczasowym formatem 12 cyfr znaczących,
  GeoJSON/SQLite z pełnymi wartościami). Cztery korekty pochodzenia potwierdzone w SQLite,
  CSV, GeoJSON, GPX, Excel; DBF poprawnie skraca długie notes na granicy UTF-8.
- Niezależny review danych, historii, schematu/spec i testu: brak uwag
  materialnych; kontrola nie obejmowała tego później spisanego dokumentu.

## Dostarczenie

Końcowy commit, zdalny HEAD i CI wskazuje opis PR #19. Pozostaje draftem;
merge, tag i wydanie nie należą do tej poprawki.
