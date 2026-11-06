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

- [ ] Zastąp test z wstrzykniętym resolverem prawdziwymi małymi poligonami
  i punktami PostGIS; expected regiony/kody są literalne i niezależne od SQL.
- [ ] Sprawdź granicę poligonu, otwór, nakładanie i kolejność, PL/SK,
  poza krajami, poza dolinami, outlier i rozbieżność trwałego prefixu z Best.
- [ ] Usuń alternatywny kod i jego parametry bez usunięcia resolvera potrzebnego
  przez `assign_id`. Zachowaj severity/ścieżki i znaczenie diagnostyki.
- [ ] `uv run --frozen pytest -q tests/test_postgres_catalog.py tests/test_grouped_gpx.py tests/test_prefix_resolver.py tests/test_assign_id.py`;
  pełna bramka, zgodność eksportów i niezmienione dane źródłowe.
- [ ] Commit `refactor: validate catalogue geography in PostGIS (PBI-119 U16)`;
  dostarcz, odbierz i zakończ po U16.
