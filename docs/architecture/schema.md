# Model bazy i przepływ publikacji

Źródłem definicji wykonywalnych jest [schema/catalog.sql](../../schema/catalog.sql).
Diagramy pokazują relacje i kluczowe pola; pola audytowe oraz opcjonalne
metadane opisuje DDL. Minimum jednego pomiaru i jednej polityki Best wymusza
łącznie schemat oraz zapytania integralności.

## Obiekt, jaskinia i historia

[Otwórz schemat jako PNG](diagrams/catalogue.png).

```mermaid
erDiagram
    caves o|--o{ caves : "jest systemem dla"
    caves o|--o{ objects : grupuje
    objects ||--|{ measurements : ma_historie
    objects ||--|| best_policy : ustala
    measurements o|--o| best_policy : manual_wskazuje
    objects ||--o{ object_external_refs : referencje_TPN
    caves ||--o{ cave_external_refs : referencje_PIG
    measurements ||--o{ measurement_tags : tagi
    objects ||--o{ attachments : zalaczniki
    measurements o|--o{ attachments : opcjonalny_pomiar
    objects ||--o{ relations : od
    objects ||--o{ relations : do
    caves {
        text id PK
        text name
        text system_cave_id FK "opcjonalny"
        float length_m
        float depth_m
        float denivelation_m
        text denivelation_qualifier
        text morphometry_source_ref
        enum bibliography_status "known lub unknown"
    }
    objects {
        text id PK
        text cave_id FK "opcjonalny"
        integer membership_ordinal "kolejnosc otworow jaskini"
        enum category
        enum bibliography_status "known lub unknown"
        text assigned_from_measurement_id FK
    }
    measurements {
        text object_id PK,FK
        text id PK "lokalne w obiekcie"
        integer history_order
        geometry input_geom "Point EPSG 4326 lub 2180"
        float elevation_m
        enum elevation_datum
        enum source
        enum verification_status
    }
    best_policy {
        text object_id PK,FK
        enum mode "auto lub manual"
        text manual_measurement_id FK "tylko manual"
        text reason "wymagany przy manual"
    }
```

FK do pomiaru zawiera zawsze ID obiektu. Jedna jaskinia może nie mieć
rozpoznanych otworów; obiekt może nie być jeszcze przypisany do jaskini.
Lista obiektów jaskini jest wyliczana z FK, bez drugiego ręcznego zapisu.
Część może wskazywać jeden system przez `caves.system_cave_id`.
System wskazany przez część sam nie może wskazywać systemu.

## Publikacje i przywołania

[Otwórz schemat jako PNG](diagrams/bibliography.png).

```mermaid
erDiagram
    publications ||--o{ cave_citations : cytowana
    publications ||--o{ object_citations : cytowana
    publications ||--o{ measurement_citations : cytowana
    caves ||--o{ cave_citations : bibliografia_jaskini
    objects ||--o{ object_citations : bibliografia_obiektu
    measurements ||--o{ measurement_citations : zrodlo_pomiaru
    publications {
        text id PK
        text citation "pelny opis bibliograficzny"
        text authors
        text title
        integer publication_year
        text url "opcjonalny"
    }
    cave_citations {
        text cave_id PK,FK
        text publication_id PK,FK
        text locator PK "strona lub fragment"
        text purpose
        text name_in_source
    }
    object_citations {
        text object_id PK,FK
        text publication_id PK,FK
        text locator PK
        text purpose
        text name_in_source
    }
    measurement_citations {
        text object_id PK,FK
        text measurement_id PK,FK
        text publication_id PK,FK
        text locator PK
    }
```

Pełne cytowanie ma pozwolić znaleźć materiał bez działającego odnośnika.
`unknown` jest dopuszczalne także dla nowego obiektu lub jaskini.
`known` wymaga odpowiedniego cytowania. Referencja TPN i literatura to różne
informacje; literatura jaskini nie przechodzi automatycznie na jej otwory.

## Baza jako etap CI/CD

[Otwórz schemat jako PNG](diagrams/pipeline.png).

```mermaid
flowchart TD
    G["Git: schemat i YAML"] --> D["Tymczasowy PostgreSQL/PostGIS"]
    D --> C["Typy, CHECK, UNIQUE, FK"]
    D --> Q["Integralność, geografia, pliki, testy"]
    B["Zaakceptowana rewizja Git"] --> H["Porównanie historii"]
    D --> H
    C --> V{"Wszystkie kontrole ukończone poprawnie?"}
    Q --> V
    H --> V
    V -->|nie| X["Błąd procesu; brak publikacji"]
    V -->|tak| E["Jeden stan: Best i pełna historia"]
    E --> A["Dump, GeoPackage i formaty wymiany"]
    A --> R["Restore i niezależny odczyt eksportów"]
    R -->|błąd| X
    R -->|poprawnie| P["Kompletna paczka do PR lub wydania"]
    P --> Z["Wyłączenie bazy"]
    X --> Z
```

Niepewność jawnie dopuszczona przez model daje ostrzeżenie. Błąd, timeout
lub brak wymaganej kontroli nie może zostać uznany za wynik poprawny.
Przejście PR nie publikuje wydania; wydanie nadal wymaga osobnego polecenia.

## Utrzymanie diagramów

Bloki Mermaid powyżej są edytowalnym źródłem diagramów; pliki PNG są
wersjami do odczytu także poza przeglądarką Markdown. Po zmianie modelu
zaktualizuj odpowiedni blok i wyrenderuj go ponownie przez Mermaid CLI
(`@mermaid-js/mermaid-cli@12.0.0`, `--size 2000 -b white -t neutral`).
