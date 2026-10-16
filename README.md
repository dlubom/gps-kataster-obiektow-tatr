🇵🇱 **Polski** | [🇬🇧 English](README.en.md) | [🇸🇰 Slovenčina](README.sk.md)

# GPS Kataster Obiektów Tatr

[![Latest Release](https://img.shields.io/github/v/release/dlubom/gps-kataster-obiektow-tatr)](https://github.com/dlubom/gps-kataster-obiektow-tatr/releases/latest)

**[Pobierz punkty GPS — GPX](https://github.com/dlubom/gps-kataster-obiektow-tatr/releases/latest/download/best-measurements.gpx)** · [Wszystkie pliki i opis wydania](https://github.com/dlubom/gps-kataster-obiektow-tatr/releases/latest)

## Co tu znajdziesz

Współrzędne otworów jaskiń i sztolni w Tatrach, z informacją o ich
pochodzeniu i historii pomiarów. Każdy otwór jest osobnym punktem — jedna
jaskinia może więc mieć kilka punktów. Zbiór jest rozwijany i nie stanowi
pełnego spisu obiektów po polskiej ani słowackiej stronie Tatr.

Grotołaz może wgrać punkty do odbiornika GPS, a kartograf
wykorzystać je w programie do pracy z mapami, np. QGIS. Gotowe pliki pobierzesz
bez konta GitHub i bez instalowania narzędzi programistycznych.

## Pobierz dane

Tu możesz pobrać najnowszą wersję danych: [wszystkie pliki wydania](https://github.com/dlubom/gps-kataster-obiektow-tatr/releases/latest).
Na tej stronie rozwiń listę **Assets** (pliki do pobrania) i wybierz nazwę z tabeli.

| Chcę… | Plik do pobrania |
|---|---|
| Wgrać punkty do GPS | [GPX — `best-measurements.gpx`](https://github.com/dlubom/gps-kataster-obiektow-tatr/releases/latest/download/best-measurements.gpx) |
| Otworzyć czytelną tabelę w Excelu | `katalog.xlsx` — arkusze **Best** i **Full** |
| Pobrać tabelę CSV | [CSV — `best-measurements.csv`](https://github.com/dlubom/gps-kataster-obiektow-tatr/releases/latest/download/best-measurements.csv) |
| Pracować z warstwą punktów w QGIS lub innym programie mapowym | `best-measurements.geojson` lub `best-measurements.shp.zip` |
| Analizować pełną historię pomiarów | `katalog.sqlite.zip` — baza dla zaawansowanych użytkowników |

Excel będzie dostępny w wydaniach po v1.0.4. **Best** zawiera wybrane punkty,
a **Full** pełne dane i historię pomiarów, również starszych i odrzuconych.
Plik ma filtry, zamrożone nagłówki i polskie nazwy kolumn.

## Dokładność i weryfikacja

Wiele lokalizacji pochodzi z katalogów i nie zostało potwierdzonych w terenie.
„Najlepszy dostępny pomiar” to wybór spośród posiadanych danych, a nie gwarancja
trafienia dokładnie w otwór. Niepodana dokładność oznacza **dokładność nieznaną**.

W wydaniach po v1.0.4 etykiety GPX pokazują nazwy otworów i innych obiektów;
ID punktu pozostaje w opisie (przy braku nazwy również w etykiecie).
GPX zawiera źródło i uwagi, ale nie ma osobnych pól statusu weryfikacji
ani dokładności. Aby je sprawdzić, otwórz [tabelę CSV](https://github.com/dlubom/gps-kataster-obiektow-tatr/releases/latest/download/best-measurements.csv) w arkuszu
kalkulacyjnym i wyszukaj kod punktu w kolumnie `object_id`. W Excelu odpowiada
jej „ID obiektu”; status i dokładność są w Best, a pełne uwagi w Full.

| Kolumna w tabeli | Jak ją czytać |
|---|---|
| `verification_status` | `nieweryfikowany`: jeszcze niepotwierdzony w projekcie, niekoniecznie błędny. `zweryfikowany`: zaakceptowany po ocenie źródeł lub sprawdzeniu w terenie. `odrzucony`: uznany za błędny lub nieprzydatny. |
| `horizontal_accuracy_m` | Podana dokładność pozioma w metrach. Puste pole oznacza brak informacji. |
| `source`, `source_ref` | Skąd pochodzi pomiar i odniesienie do źródła; np. TPN lub PIG. |
| `measurement_notes` | Uwagi o pomiarze, rozbieżnościach i ograniczeniach lokalizacji. |

## Ile danych jest sprawdzonych

[Na stronie najnowszego wydania](https://github.com/dlubom/gps-kataster-obiektow-tatr/releases/latest) kolejne wydania po v1.0.4 będą
zawierały rozwijane **Statystyki wydania (PL)**, także po angielsku i słowacku.
Tabele powstają automatycznie z tej samej paczki danych: pokazują liczbę
obiektów, jaskiń i pomiarów, rodzaje obiektów, źródła, statusy weryfikacji oraz
liczbę punktów z podaną i nieznaną dokładnością. Punkty do pobrania i pełna
historia pomiarów są liczone osobno. Wydanie v1.0.4 i starsze nie mają tych tabel.

## Punkty na mapie

![Rozmieszczenie punktów w zbiorze na mapie Tatr](docs/images/tatry-regiony-osm.png)

**[Otwórz dużą mapę z czytelną legendą](docs/images/tatry-regiony-osm.png?raw=true)**

Kolory pokazują regiony dolin, a liczby w legendzie — obiekty w zbiorze,
nie liczbę jaskiń ani kompletność rozpoznania doliny. PL i SK oznaczają punkty
poza wyznaczonymi regionami dolin. Kolor nie określa dokładności ani weryfikacji.

<details>
<summary>Zobacz zbliżenie: Dolina Kościeliska i okolice</summary>

![Punkty w Dolinie Kościeliskiej i okolicach, z podpisanymi przykładami jaskiń](docs/images/dolina-koscieliska-osm.png)

[Otwórz zbliżenie w pełnym rozmiarze](docs/images/dolina-koscieliska-osm.png?raw=true).
Różowe punkty oznaczają po jednym wybranym pomiarze każdego obiektu w kadrze.

</details>

Obie mapy to statyczne podglądy z **2026-10-16**; nie aktualizują się wraz
z pobieranymi plikami. Podkład: © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright)
(ODbL). [Źródło i przygotowanie ilustracji](docs/images/README.md).

## Trzy powiązane projekty

Trzy repozytoria opisują ten sam teren z różnych stron:

| Projekt | Odpowiada na pytanie | Co udostępnia |
|---|---|---|
| **GPS Kataster Obiektów Tatr** (ten projekt) | Gdzie znajduje się konkretny otwór lub inny obiekt terenowy? | Najlepsze dostępne współrzędne wraz ze źródłem, historią i statusem weryfikacji. |
| [Jaskiniowy Kataster Tatr](https://github.com/dlubom/Jaskiniowy-Kataster-Tatr-Zachodnich) | Jak przebiegają pomierzone ciągi i geometria podziemi? | Dane pomiarowe Walls i Survex, wizualizacje 2D oraz [model 3D](https://dlubom.github.io/Jaskiniowy-Kataster-Tatr-Zachodnich/) dla jaskiń z dostępnymi pomiarami; gotowe pliki są w [najnowszym wydaniu](https://github.com/dlubom/Jaskiniowy-Kataster-Tatr-Zachodnich/releases/latest). |
| [Georeferencer](https://github.com/dlubom/Georeferencer) | Jak zeskanowany plan jaskini układa się na mapie? | Georeferencjonowane skany planów w formacie GeoTIFF, także dla jaskiń bez ciągów pomiarowych w Jaskiniowym Katastrze; paczka jest w [najnowszym wydaniu](https://github.com/dlubom/Georeferencer/releases/latest). |

GPS Kataster jest wspólnym źródłem współrzędnych wejść: zarówno
Jaskiniowy Kataster Tatr, jak i Georeferencer korzystają z publikowanych tutaj
najlepszych pomiarów.

## Kontakt i poprawki

Masz lepszy pomiar, znasz brakujący otwór albo widzisz błąd? Najprościej napisz
e-mail do Darka: **darek.lubomski [małpa] gmail [kropka] com**.
Zastąp `[małpa]` znakiem `@`, a `[kropka]` znakiem `.` i usuń spacje.

Możesz też [zgłosić pomiar lub błąd na GitHubie](https://github.com/dlubom/gps-kataster-obiektow-tatr/issues/new?title=Pomiar+lub+poprawka&body=Jaskinia+i+otw%C3%B3r+%2F+kod+punktu%3A%0AWsp%C3%B3%C5%82rz%C4%99dne%3A%0AData+i+urz%C4%85dzenie+%2F+metoda%3A%0ADok%C5%82adno%C5%9B%C4%87+%28je%C5%9Bli+znana%29%3A%0A%C5%B9r%C3%B3d%C5%82o+i+opis+poprawki%3A%0AZdj%C4%99cie+lub+uwagi%3A%0A) — formularz zawiera
podpowiedzi i wymaga konta GitHub. Zgłoszenia są publiczne.

Podaj nazwę jaskini i konkretnego otworu (lub kod punktu), współrzędne, datę,
urządzenie lub metodę, znaną dokładność oraz źródło danych. Zdjęcie otworu
lub opis dojścia pomoże go rozpoznać. Jeśli czegoś nie wiesz, zaznacz to;
nie musisz samodzielnie edytować plików projektu.

## Dla osób rozwijających i utrzymujących dane

Źródłem prawdy są pliki YAML w `data/`. SQLite, GeoJSON, GPX, CSV, Excel i
Shapefile są artefaktami generowanymi z tych plików.

`Obiekt` oznacza konkretny punkt w terenie, a `Jaskinia` jest rekordem
katalogowym grupującym jeden lub więcej otworów. Każdy obiekt zachowuje pełną
historię pomiarów i wskazanie najlepszego aktualnego pomiaru.

### Szybki start

```bash
uv sync
uv run pytest
uv run python scripts/validate.py
uv run python scripts/build_release_artifacts.py
```

Artefakty lokalne powstają w `build/` i nie są commitowane.

### Dokumentacja projektu

- [Specyfikacja i model domeny](specyfikacja_gps_kataster_obiektow_tatr_v_2.md)
- [Dodawanie i weryfikacja pomiarów](docs/operations.md)
- [Formaty i pola plików wydania](docs/release_artifacts.md)
- [CHANGELOG.md](CHANGELOG.md)

Publiczne wydania są wersjonowane semantycznie tagami `vX.Y.Z` i publikowane
ręcznie. Repozytorium, dokumentacja i generowane eksporty danych są
licencjonowane na warunkach Creative Commons Attribution 4.0 International,
zgodnie z plikiem [LICENSE](LICENSE).
