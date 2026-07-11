🇵🇱 **Polski** | [🇸🇰 Slovenčina](README.sk.md)

# GPS Kataster Obiektów Tatr

[![Latest Release](https://img.shields.io/github/v/release/dlubom/gps-kataster-obiektow-tatr)](https://github.com/dlubom/gps-kataster-obiektow-tatr/releases/latest)

[Pobierz najnowsze dane](https://github.com/dlubom/gps-kataster-obiektow-tatr/releases/latest)

## Opis projektu

GPS Kataster Obiektów Tatr to otwarty, rozwijany zbiór współrzędnych
otworów jaskiń i innych obiektów ważnych dla speleologii i krasu po obu
stronach Tatr: sztolni, ponorów, wywierzysk oraz obiektów pokrewnych.

Projekt łączy pomiary terenowe GPS i GNSS z danymi katalogowymi oraz
instytucjonalnymi. Przy każdej lokalizacji zachowuje jej źródło, dokładność,
status weryfikacji i historię. Każdy konkretny otwór jest osobnym obiektem,
dlatego można prawidłowo opisać także jaskinie wielootworowe.

Grotołaz może pobrać punkty do odbiornika GPS lub telefonu, a kartograf i
badacz wykorzystać je w GIS oraz sprawdzić, na ile dana lokalizacja została
zweryfikowana.

## Pobierz dane

Tu możesz pobrać najnowszą wersję danych:
[GitHub Releases](https://github.com/dlubom/gps-kataster-obiektow-tatr/releases/latest).

Każde wydanie zawiera gotowe pliki do pracy w terenie i przy komputerze:

| Format | Do czego najlepiej go użyć |
|---|---|
| GPX | punkty w odbiorniku GPS lub aplikacji terenowej |
| GeoJSON i Shapefile | mapa, analiza i łączenie warstw w QGIS lub innym GIS |
| CSV | przeglądanie, filtrowanie i łączenie danych w tabeli |
| SQLite | pełniejsza analiza obiektów, jaskiń, pomiarów i ich historii |

W paczce znajduje się również `metadata.json` z wersją danych i podstawowymi
licznikami wydania.

## Dokładność i weryfikacja

Punkty pochodzą z różnych lat, urządzeń i źródeł, dlatego ich dokładność
nie jest jednakowa. Wskazanie „najlepszego dostępnego pomiaru” nie oznacza
automatycznie, że został on potwierdzony w terenie. Przed użyciem punktu sprawdź
źródło, status weryfikacji, deklarowaną dokładność i notatki.

W początkowych wydaniach większość najlepszych pomiarów może mieć
`verification_status: nieweryfikowany`. Oznacza to, że punkt pochodzi z importu
albo przepisanego źródła i nie przeszedł jeszcze projektowej weryfikacji
terenowej lub operatorskiej. Nie oznacza to automatycznie błędu ani braku
źródła; do czasu uzyskania lepszego pomiaru pozostaje najlepszą dostępną
lokalizacją.

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

## Jak możesz pomóc

Jeżeli masz dokładniejszy pomiar GPS/GNSS, znasz brakujący otwór albo widzisz
błędne przypisanie, dodaj
[zgłoszenie](https://github.com/dlubom/gps-kataster-obiektow-tatr/issues) lub
przygotuj pull request. Podaj nazwę jaskini i konkretnego otworu, współrzędne,
datę, metodę lub urządzenie, szacowaną dokładność oraz źródło danych.
Rozróżnienie otworów tej samej jaskini jest szczególnie ważne.

## Dla osób rozwijających i utrzymujących dane

Źródłem prawdy są pliki YAML w `data/`. SQLite, GeoJSON, GPX, CSV i
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
