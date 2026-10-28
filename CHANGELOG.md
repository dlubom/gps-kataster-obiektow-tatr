# Changelog

Wszystkie istotne zmiany w projekcie "GPS Kataster Obiektow Tatr" sa
udokumentowane w tym pliku.

Format jest oparty o [Keep a Changelog](https://keepachangelog.com/), a
wersjonowanie od `v1.0.0` stosuje [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Dodano

- `katalog-qgis.zip` w wydaniach i podglądach PR: Best domyślnie włączone,
  pozostałe/odrzucone pomiary, Full i linie różnic, przełączane podkłady TPN
  i OSM oraz per-model ciągi najnowszego stabilnego wydania JKTZ.
- Jawne pochodzenie i osobna atrybucja JKTZ; odbiór przeniesionej paczki
  offline w QGIS 3.44.15 i 4.0.1 przed uploadem.

## [v1.3.2] - 2026-10-25

### Dodano

- Górny otwór Raptawickiej i trzy Okna Pawlikowskiego jako odrębne obiekty.

### Zmieniono

- Wybrano osiem pozycji Best z jedną kotwicą Raptawickiej, ustaloną z ortofoto
  i ALS (H1140,8 m PL-KRON86-NH). Pozostałe otwory wyznacza sieć JKTZ
  po przywróceniu ciągu powierzchniowego Obłazkowa–Raptawicka.
- Wzorcem obliczeń jest Survex 1.4.24. Różnicę względem Walls oraz przyjętą
  deklinację powierzchni 4,83° opisano w źródłach.

Nowe Best pozostają nieweryfikowane, z nieznaną dokładnością. Dotychczasowe
pomiary zachowano. Katalog zawiera 1028 obiektów i 1934 pomiary.

## [v1.3.1] - 2026-10-24

### Poprawiono

- Usunięto dwa błędne punkty terenowe: dodatkowy wpis głównego otworu
  Mylnej oraz geometryczny środek systemu Wielkiej Śnieżnej. Obie pozycje
  katalogowe systemów pozostają w bazie.

### Zmieniono

- Statystyki wydań pokazują osobno źródło danych i sposób wyznaczenia
  pozycji, m.in. GNSS, LiDAR dowiązany GNSS i sieć pomiarową.
- Źródło „Własne pomiary” otrzymało nazwę „Opracowania własne”.

Katalog zawiera 1024 obiekty, 1019 pozycji katalogowych i 1926 pomiarów.
Pozostałe pomiary i wskazania Best pozostają bez zmian. Porównanie trzech
pozycji Mylnej z LiDAR i wybór najlepszego pomiaru odłożono do
[issue #36](https://github.com/dlubom/gps-kataster-obiektow-tatr/issues/36).

## [v1.3.0] - 2026-10-24

### Dodano

- Trzy dodatkowe pliki GPX do importu w aplikacjach z limitem punktów:
  `chocholowska-lejowa-koscieliska.gpx` (488 punktów),
  `mietusia-sucha-woda.gpx` (481 punktów) i `pozostale-pl-sk.gpx`
  (57 punktów poza regionami dolin).
- Podział według położenia wybranego pomiaru, z zachowaniem całych dolin.
  Każdy punkt trafia do jednej grupy i zachowuje wszystkie swoje dane.
- Kontrolę limitu 500 punktów w każdym dodatkowym GPX.
  Przekroczenie limitu zatrzymuje eksport bez obcinania punktów.

Pełny `best-measurements.gpx` nadal zawiera wszystkie 1026 punktów.
Dodatkowe pliki są dostępne w podglądzie PR i paczkach nowych wydań.
Dane katalogu i wybór najlepszych pomiarów pozostają bez zmian.

## [v1.2.1] - 2026-10-24

### Dodano

- 19 nowych obiektów terenowych, 18 jaskiń i 20 pomiarów z TPN,
  w tym północny otwór Smoczej Jamy przypisany do istniejącej jaskini.
- Dwa pomiary Korytarza pod Ciemniakiem przypisane do jednego obiektu,
  z zachowaniem obu rekordów źródłowych TPN.
- Wysokości gruntu z NMT TPN dla wszystkich nowych pomiarów,
  wraz z informacją o pochodzeniu odczytów.
- Opisy i bibliografię nowych jaskiń, z zaznaczeniem rozbieżności
  między TPN a literaturą oraz braku ustalonej publikacji opisowej.

Nowe pomiary pozostają nieweryfikowane. Wysokości NMT opisują grunt
i nie potwierdzają wysokości otworów.
Katalog zawiera 1026 obiektów, 1019 jaskiń i 1928 pomiarów.

## [v1.2.0] - 2026-10-23

### Dodano

- Narzędzie pobierania pełnych warstw TPN: jaskiń, lejów krasowych
  oraz sztolni i kopalń, z czytelnymi plikami JSON i opcjonalnymi
  wysokościami gruntu z NMT TPN.
- Metodę `siec_pomiarowa` dla pozycji wyznaczonych z sieci
  pomiarowej jaskini.

### Zmieniono

- Dodano 31 nowych pomiarów dla istniejących obiektów, których
  współrzędne zmieniły się w źródle TPN, zachowując poprzednie pomiary.
  Nowym punktom przypisano wysokości gruntu z NMT TPN;
  nie stanowią one potwierdzenia wysokości otworów.
- Uzupełniono informacje TPN w trzech istniejących pomiarach
  oraz dopisano aktualne długości Śnieżnej Studni, Ptasiej Studni
  i Piwnicy Miętusiej według TPN, zachowując wcześniejsze dane PIG.
- Ustawiono ręczny wybór najlepszych pomiarów Czarnej, Czarnej III
  i dolnego otworu Bańdziocha Kominiarskiego.

### Naprawiono

- Skorygowano błędne oznaczenia GNSS: pozycje Raptawickiej,
  Obłazkowej i górnego otworu Bańdziocha pochodzą z sieci pomiarowej.
  Punkt Mylnej oznaczono jako historyczny punkt dowiązania
  o niepotwierdzonej pierwotnej metodzie.
  Zachowano ich współrzędne, wysokości i ręczny wybór best.

Nowa metoda rozszerza listę dopuszczalnych wartości `method`
przy zachowaniu `schema_version: 1`. Odbiorcy korzystający
z zamkniętej listy metod muszą uwzględnić `siec_pomiarowa`.

## [v1.1.2] - 2026-10-22

### Naprawiono

- Zaktualizowano lokalizację dolnego otworu Ptasiej Studni
  (MTZ-0066): jako best wybrano współrzędne Wojciecha Rolińskiego
  z wysokością gruntu 1446,8 m z NMT TPN.
  Wysokość samego otworu pozostaje do weryfikacji.
  Zachowano pełną historię pomiarów.

## [v1.1.1] - 2026-10-19

### Dodano

- Dodatkowy, nieweryfikowany pomiar dolnego otworu Ptasiej Studni;
  dotychczasowy punkt eksportowy pozostaje bez zmian.

### Naprawiono

- Scalono zdublowane wpisy Rury nad Okapami i Szczeliny nad Okapami,
  zachowując pełną historię pomiarów i oba GLOBALID TPN każdej pary.
- Rozróżniono nazwy północnego i południowego otworu tunelu
  w Skrajnej Giewonckiej Baszcie.

## [v1.1.0] - 2026-10-16

### Dodano

- README PL/EN/SK: pobieranie GPX i Excela,
  objaśnienia jakości danych, mapy oraz kontakt e-mail i zgłoszenia z podpowiedziami.
- Automatyczne statystyki PL/EN/SK w opisie każdego nowego wydania oraz
  `statistics.md` i `statistics.json` w paczce, z wersją i commitem danych.
- Formatowany Excel `katalog.xlsx`: wybrane punkty w arkuszu Best oraz
  pełne dane z historią pomiarów w Full, filtry i zamrożone nagłówki.

### Zmieniono

- Etykiety GPX pokazują nazwy konkretnych otworów i innych obiektów;
  przy braku nazwy używają ID. Opis punktu zachowuje trwałe ID obiektu.

### Naprawiono

- Eksport Excel zachowuje daty sprzed 1900 jako tekst ISO, a daty od
  1900-01-01 jako daty, bez przesunięcia dnia.

Dane źródłowe, współrzędne i wybór najlepszych pomiarów pozostają bez zmian.

## [v1.0.4] - 2026-10-16

### Naprawiono

- Odrzucono błędne historyczne punkty PIG: Schron w Skale Kmietowicza II
  (PL-0019), Komora w Jatkach (MLZ-0045), Wojtkowa Szpara (CHZ-0011)
  i Jaskinia w Cycku (BYZ-0020), zachowując pomiary i uzasadnienia w YAML.
- Skorygowano kategorię CHZ-0011 na `sztolnia`, odpowiadającą wylotowi
  sztolni nr 7 prowadzącej do Wojtkowej Szpary.

Współrzędne best pozostają bez zmian; dokładność i położenie otworów
wymagają dalszego rozpoznania.

## [v1.0.3] - 2026-10-15

### Naprawiono

- Zablokowano budowanie SQLite i eksportów przy brakujących katalogach
  danych oraz odrzucono powtórzone klucze YAML.
- Dodano walidację całego stanu katalogu po decyzjach review przed
  rozpoczęciem zapisu, również w trybie dry-run.
- Odrzucono NaN, Infinity i powtórzone ID pomiarów w obrębie obiektu.
- Poprawiono przenoszenie obiektu między jaskiniami i kontrolę
  zgodności powiązań po obu stronach.
- Zachowano kontekst WER_LOK i UWAGI przy importowanych pomiarach TPN;
  uzupełniono go w 469 istniejących pomiarach.
- Skorygowano kategorię STR-0024 na sztolnię na podstawie źródła TPN.

### Zmieniono

- Udokumentowano niepewność CHZ-0011, rozbieżności lokalizacji
  i przypadki obiektów o identycznych współrzędnych.
- Rozbudowano dokumentację dla użytkowników w językach polskim,
  angielskim i słowackim.

## [v1.0.2] - 2026-05-21

### Zmieniono

- Usunieto dodatkowa runtime'owa bramke licencyjna z workflow release;
  licencja CC BY 4.0 pozostaje opisana w `LICENSE` i dokumentacji.
- Doprecyzowano dokumentacje AS-DLC/spec/operacyjna: release pozostaje reczny,
  semverowy i tagowany, bez automatycznego buildu po `main`.

## [v1.0.1] - 2026-05-17

Patch release z korekta wysokosci dla Jaskini Bandzioch Kominiarski.

### Naprawiono

- Uzupelniono wysokosc recznego pomiaru GNSS gornego otworu Bandziocha
  Kominiarskiego (`LEJ-0002`, `BandziochKom:136`) na `1675.02 m`.
- Dolny otwor Bandziocha (`KSZ-0112`, `BandziochKom:000`) pozostaje z
  wysokoscia `1451.06 m`; eksporty `best-measurements` zawieraja teraz
  wysokosci obu otworow.

## [v1.0.0] - 2026-05-17

Pierwsze formalne wydanie semver dla katalogu GPS/GNSS obiektow tatrzanskich.

### Dodano

- Changelog jako zrodlo notatek do GitHub Release.
- Link do najnowszego wydania w README.
- Opis recznego procesu wydania: wpis w changelogu, commit, annotated tag
  `vX.Y.Z` i push taga.

### Zmieniono

- Wersjonowanie repo przechodzi z tagow kalendarzowych `v2026.05.x` na semver
  `vX.Y.Z`, analogicznie do Jaskiniowego Katastru Tatr Zachodnich.
- GitHub Release jest publikowany wylacznie po recznym pushu taga `v*`, a
  notatki release sa wyciagane z odpowiadajacej sekcji `CHANGELOG.md`.
- Dokumentacja operacyjna opisuje recznie tagowane wydania zamiast cyklicznych
  paczek danych.

### Usunieto

- Automatyczny workflow budujacy artefakty po kazdym pushu na `main`.
