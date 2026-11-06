# U16 — waliduj geografię katalogu wyłącznie w PostGIS

Czytaj [indeks](README.md), [spec](spec.md) i [odbiór](../development.md).
Zależność: U15. Zmiana dotyczy katalogu; `assign_id` nadal może używać
resolvera Pythona do propozycji przed istnieniem obiektu.

## Pliki i interfejs

Zmień `postgres.Catalog.issues`, przekazywanie `prefix_resolver` w pozostałym
walidatorze oraz `tests/test_postgres_catalog.py`. Usuń produkcyjną gałąź,
która pomija wyniki SQL i zastępuje je resolverem wstrzykniętym przez test.
Wynik: jedna implementacja reguł katalogu w `schema/catalog.sql`.

## Kroki i kryteria

- [x] Zastąp test z wstrzykniętym resolverem prawdziwymi małymi poligonami
  i punktami PostGIS; expected regiony/kody są literalne i niezależne od SQL.
- [x] Sprawdź granicę poligonu, otwór, nakładanie i kolejność, PL/SK,
  poza krajami, poza dolinami, outlier i rozbieżność trwałego prefixu z Best.
- [x] Usuń alternatywny kod i jego parametry bez usunięcia resolvera potrzebnego
  przez `assign_id`. Zachowaj severity/ścieżki i znaczenie diagnostyki.
- [x] `uv run --frozen pytest -q tests/test_postgres_catalog.py tests/test_grouped_gpx.py tests/test_prefix_resolver.py tests/test_assign_id.py`;
  pełna bramka, zgodność eksportów i niezmienione dane źródłowe.
- [x] Commit `refactor: validate catalogue geography in PostGIS (PBI-119 U16)`;
  dostarcz, odbierz i zakończ po U16.

## Odbiór

Baza refaktoru: `a9a17a21cea43510e005b622c02819bc7edd11ca`;
baseline historii: `ad5fa191a36d5a5f45f0b2de523bd39125827573` (`origin/main`).
`Catalog.issues` i trzy wejścia walidatora nie przyjmują już `prefix_resolver`;
wyniki geografii pochodzą z SQL. Resolver `assign_id`, SQL i źródła pozostają
bez zmian. Fixture małych poligonów jest wspólny dla testów katalogu i GPX.

Testy sprawdzają zewnętrzny brzeg/wierzchołek, wnętrze i brzeg/wierzchołek
otworu, nakładanie i odwróconą kolejność dolin, PL/SK i ich brzegi, brak
regionu, wybór manual/auto Best oraz 99/100/100,1 m. Expected regiony i kody
są literalne. Kontrole obejmują severity, plik źródłowy i identyfikator
pomiaru; błędny pomiar spoza Best także daje error.

Osiem przypadków przechodzi przed usunięciem alternatywnej ścieżki.
Próby mutacyjne wykazały, że testy odrzucają `ST_Contains` zamiast
`ST_Covers` (2 FAIL), odwrócony priorytet (2 FAIL) i próg `>= 100`
zamiast `> 100` (1 FAIL). Po każdej próbie przywrócono oryginalny SQL.

[Pełne dowody U16](../../../verification/PBI-119.md#u16--geografia-katalogu-w-postgis)
i opis PR zawierają wyniki bramki, bilans, porównanie eksportów oraz CI.
Merge, tag i wydanie pozostają poza tym zleceniem.
