---
name: tpn-elevation
description: Odczytaj wysokość gruntu dla podanego lat/lon WGS84 z publicznego NMT TPN. Używaj przy sprawdzaniu wysokości punktu w tym repozytorium.
---

# Wysokość gruntu z NMT TPN

Uruchamiaj [skrypt repozytorium](../../../scripts/tpn_elevation.py), zamiast
odtwarzać żądania HTTP lub odczytywać kolory z mapy. Komendy wykonuj
z katalogu głównego tego repozytorium. Skill jest lokalny; nie instaluj
go ani skryptu globalnie.

Podstaw dokładnie współrzędne użytkownika w stopniach dziesiętnych WGS84.
Jeśli ich brakuje lub nie wiadomo, jaki mają układ, poproś o doprecyzowanie.
Nazwane argumenty zapobiegają pomyleniu szerokości i długości:

```bash
uv run --frozen python scripts/tpn_elevation.py --lat 49.2320 --lon 19.9816 --json
```

Powyższe współrzędne są przykładem, nie domyślnym punktem. Bez `--json`
skrypt wypisuje krótki wynik tekstowy. `--timeout 20` ogranicza czas
pojedynczego żądania; skrypt wykonuje cztery odczyty HTTP.

W odpowiedzi podaj wysokość gruntu, model, źródło i ograniczenia z JSON:

- `elevation_m` jest liczbą w metrach, a `raw_elevation` zachowuje tekst API.
- `elevation_reference: sea_level`: podawaj „m n.p.m. według legendy TPN”.
  `source.elevation_reference_label`, `legend_url` i `legend_sha256`
  dokumentują oznaczenie wydawcy dla warstwy 0.
- `elevation_datum: unknown`: dokładny układ pionowy nie jest zadeklarowany.
  Nie przypisuj Kronsztadt86 ani PL-EVRF2007-NH i nie wykonuj konwersji
  pionowej. WGS84 opisuje tu lat/lon, nie datum wysokości.
- `vertical_accuracy_m: unknown`: piksel 0,5 m i liczba cyfr odpowiedzi
  nie oznaczają dokładności pionowej.
- `source.latestness: unconfirmed`: nie potwierdzono, że jest to najnowszy
  model TPN. `source.data_date: 2019-10-14/2019-10-15` jest zakresem dat
  nalotu według opisu warstwy „Wysokości” w dokumentacji TPN wskazanej przez
  `data_date_source_url`. Nie zastępuj go pojedynczą wymyśloną datą.
  `retrieved_at` jest czasem pobrania, nie datą nalotu lub pomiaru.
- NMT przedstawia grunt. Otwór w ścianie lub przewieszce może leżeć na
  innej wysokości. Interpolacja usługi pozostaje `unknown`.

Zachowaj źródłowy URL i hashe z wyniku, gdy użytkownik potrzebuje dowodu
odczytu. Brak danych lub błąd kończy skrypt niezerowym kodem i komunikatem
na stderr; nie zastępuj wysokości zerem, wartością sąsiedniego punktu ani
innym modelem. `SOURCE_CHANGED` wymaga ponownego sprawdzenia źródła;
nie omijaj kontroli tylko po to, aby otrzymać liczbę.

Odczyt nie zmienia YAML ani wyboru `best`. Zapis do katalogu to oddzielny
zakres wymagający polecenia użytkownika.

Kontrakt i źródła: [PBI-106](../../../docs/asdlc/plans/PBI-106.md).
