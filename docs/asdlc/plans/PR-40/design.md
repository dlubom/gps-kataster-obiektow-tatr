# Design — właściciele danych i reguł

Czytaj razem ze [spec](spec.md). To projekt kolejnych zmian, a nie opis
ich wykonania; stan znajduje się w [indeksie](README.md).

## Granice odczytu i zmian

| Granica | Obecny właściciel | Co gwarantuje |
|---|---|---|
| Odczyt plików | `data_loader.load_yaml_dataset`, `postgres._read_snapshots` | Ścisły YAML, typy źródła, znacznik i komplet katalogów U03 |
| Deklaracje legacy | `validator.validated_proposal` | Schemat i członkostwo przed ładowaniem; redundantne współrzędne na połączeniu załadowanego SQL |
| Wybrane deklaracje staging | `validate_record_schema`, `validate_staging_fields`, `_validate_proposal_membership`, `validate_coordinate_declarations` | Struktura i członkostwo przed usunięciem deklaracji; współrzędne na istniejącym połączeniu wejścia |
| Pola źródłowe zmian | `catalog_records.source_dataset`, `SourceDataset` | Jawna konwersja sprawdzonych deklaracji/projekcji; akcje nie utrzymują pól wyliczanych |
| Kanoniczna propozycja | `validator.validated_source_proposal`, `postgres.open_source_proposal` | Pola źródłowe, ścieżki i SQL bez ponownej walidacji legacy; istniejące połączenie do historii |
| Istniejący stan SQL | `validator.validate_catalog` | Kontrola już załadowanej bazy, bez ponownej serializacji/projekcji |
| Historia | `validator.history_checked_catalog`, `history.check_history` | Rzeczywisty Git baseline, istniejące połączenie; bramka build/CLI |
| Eksport | `export_data.prepare_export_data` | Jedna niezmienna historia, Best i czas dla wszystkich serializerów |

U02 rozdzieliło funkcje i cykl życia. U04 wydziela `SourceDataset` jako kontrakt
wejścia kanonicznych zmian; `open_source_proposal` odrzuca zwykłą projekcję
i sprawdza brak pól wyliczanych. Typ nie jest certyfikatem walidacji po mutacji.
Raporty staging PIG/TPN pozostają zewnętrznymi deklaracjami; review sprawdza
wybrane pola przed ich usunięciem. Historyczny adapter Git jest osobną granicą.

## Docelowy przepływ

```text
kanoniczny YAML ── kontrola źródła ── PostgreSQL ── projekcja ── ExportData
                                         │                         │
                                         │                         └─ serializery
                                         └─ kontrola Git baseline

legacy/staging ── kontrola deklaracji ── adapter źródłowy ── model zmian
                                                              │
                     decyzje operatora ────────────────────────┤
                                                              ▼
                                   SQL propozycji + historia ── writer
                                                              └─ WriteResult
```

Każdy odrębny stan jest sprawdzany raz. Nie kopiuj „certyfikatu walidacji”
przez mutację słownika: zmieniona propozycja wymaga własnej kontroli końcowej.
W review zamknij konteksty SQL przed zapisem YAML, jak w U02. Eksporty nadal
publikują staging wewnątrz kontekstu katalogu; zmiana tej kolejności nie jest
ukrytą częścią niniejszej serii.

## Decyzje projektowe

1. **Kompletność na wejściu (U03).** Wspólny opis wymaganych katalogów
   z jawnym rozróżnieniem wersji źródła. Nie przenoś sprawdzania do każdego
   eksportera i nie zmieniaj ogólnego `iter_yaml_paths` w walidator formatu.
   Stare zaakceptowane rewizje Git bez bibliografii nadal muszą być czytelne.
2. **Jedna reprezentacja zmian (U04).** Legacy `object_ids`, redundantne
   współrzędne i wyliczony auto Best są deklaracjami na granicy, nie polami
   utrzymywanymi równolegle przez każdą akcję review. Po ich sprawdzeniu
   model zmian ma `cave_id`/`membership_ordinal`, geometrię źródłową i politykę
   Best. Projekcję SQL odbierają odczyty/raporty. Adapter może użyć małego
   nazwanego typu/nośnika tylko jeśli rzeczywiście uniemożliwia pomylenie wejść;
   nie wprowadzaj pełnego ORM, zestawu DTO ani drugiej walidacji reguł SQL.
3. **Region z istniejącego SQL (U05).** `v_measurement_regions` już wylicza
   `ST_Covers` z priorytetem `boundaries.ordinal`. Przenieś wynik dla wybranego
   pomiaru do wewnętrznych danych eksportu. Nie dodawaj pola do publicznego
   CSV/Full/GeoPackage tylko dla sterowania GPX. Pythonowy resolver pozostaje
   dla importów bez katalogu i kontrastowych testów geometrii.
4. **Wynik writera (U06).** Niezmienny `WriteResult` opisuje opublikowane
   zmiany plików YAML. Writer zna stare i nowe bajty podczas przygotowania
   drzewa, więc review nie skanuje całego katalogu przed i po zapisie.
   Szczegółowy kontrakt usunięć i markerów jest w karcie U06.
5. **Testy konsumentów (U07).** Kanoniczne fixtures i osobny zaakceptowany
   commit Git są danymi testu. Zwykłe wrappery nie wywołują `validate_proposal`
   i `write_dataset`, aby „naprawić” fixture. Konwersja jest dopuszczalna
   wyłącznie w testach samej migracji; wzorce formatu pozostają niezależne.
6. **Małe wspólne mechanizmy (U08/U09).** Funkcje parsowania, renderowania
   i alokacji mają konkretne kontrakty i realnych kilku odbiorców. Nie twórz
   ogólnego `utils.py`, frameworka importerów ani globalnego mutowalnego licznika.
7. **Artefakty i CLI (U10).** Rozszerz istniejący `ReleaseArtifactsResult`
   lub wydziel mały jawny manifest. Zachowaj kolejność i dokładny zestaw,
   oddzielając 8 plików Best, 13 wydania i 2 pliki preview. CLI współdzieli
   wyłącznie identyczne argumenty/pomoc, czas i właściwe mapowanie diagnostyki;
   specyficzne komunikaty i polityka procesu pozostają jawne.
8. **CI (U11).** Wspólny setup runtime w lokalnej composite action lub małym
   skrypcie; poszczególne workflow nadal jawnie deklarują uprawnienia,
   zdarzenia, serwis PostgreSQL i baseline. Setup nie może „poświadczać”
   wcześniejszego walidowania innego SHA ani uruchamiać kodu PR z write tokenem.

## Kolejność i ryzyko

U03 usuwa rzeczywistą lukę i stabilizuje fixtures. U04 jest najbardziej
wrażliwe na historię i semantykę członkostwa; wymaga charakterystyki przed
zmianą. U06 i U07 domykają tę granicę. U05 i U08 są niezależne po U01/U02,
ale zalecana jest kolejność indeksu, aby każdy przegląd pozostał mały.
U10/U11 są ostatnie, bo porządkują już ustabilizowane wejścia i wyjścia.

Nie usuwaj `schema/*.schema.json`, `_git_baseline` ani wsparcia historycznego
YAML na podstawie tego, że obecny katalog używa formatu v2. Ich odbiorcą jest
także kontrola starych zaakceptowanych rewizji.
