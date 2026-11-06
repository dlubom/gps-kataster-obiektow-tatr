# Wykonywalny model katalogu

`catalog.sql` jest jedynym aktywnym schematem: PostgreSQL 18/PostGIS 3.6.
Ładowany jest przez zaufany runtime do nowej, tymczasowej bazy. Dane w
`data/**/*.yml` zawierają rekordy wczytywane jako dane i przekazywane do bazy
jako parametry przez odrębną rolę.

Stare pliki JSON Schema służą wyłącznie legacy migracji/fixture'om i formatom
staging/odczytu. Nie definiują drugiego aktywnego źródła katalogu.
`catalog.json` ma `format=postgresql-yaml`, `schema_version=2`.

[Model domeny](../specyfikacja_gps_kataster_obiektow_tatr_v_2.md) ·
[ERD i przepływ](../docs/architecture/schema.md) ·
[Runtime, edycja i walidacja](../docs/operations.md#runtime-lokalny-i-ci) ·
[Dump i GeoPackage](../docs/release_artifacts.md)
