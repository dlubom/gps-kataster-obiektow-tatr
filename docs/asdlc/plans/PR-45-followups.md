# Propozycje po PR #45

Status: użytkownik zlecił propozycję 1 w PR #45 (2026-11-04).
Propozycje 2 i 3 pozostają do decyzji, bez zlecenia implementacji.
Stan odniesienia: PBI-120 / PR #45, 2026-11-04.

PR #45 zawiera dwie poprawki review: odtwarzanie zaakceptowanego
wydania po przesunięciu main i uczciwy opis rozbieżnego auto Best na kartach.
Uzupełnia je wyłącznie propozycja 1 z poniższej kolejności 1 → 2 → 3.
Każdy wymaga osobnego zakresu i odbioru. YAML, surowe wartości, obecność pól,
historia i publiczne formaty pozostają zgodne z bieżącą specyfikacją §9–12.

## 1. Typowanie krytycznej ścieżki i mypy w CI

**Cel:** wykrywać błędne użycie pól i typów przed uruchomieniem programu.
Obecnie `validate_loaded_dataset()` waliduje modele, ale zwraca słowniki;
`dict[str, Any]` ogranicza skuteczność statycznej kontroli dalszego kodu.

**Proponowany pierwszy zakres:** `models.py`, `best_measurement.py` i
`measurement_values.py`, konfiguracja mypy w `pyproject.toml`, zależności
deweloperskie/lock oraz krok w istniejącym `Validate code and data`.
Do typowania wejść Best użyć niewielkiego jawnego kontraktu pól odczytywanych
przez selektor; nie deklarować ponownie całego katalogu w drugim modelu.
Surowe mapy parsera pozostają wejściem wymagającym walidacji. Nie maskować
problemu przez globalne `ignore_errors` lub pozorne rzutowanie całego katalogu.

Rekomenduję stopniowe włączanie modułów zamiast jednorazowego przepisania
całego projektu. Dopiero kolejny zakres może przenosić sprawdzone modele do
budowy SQLite/eksportów. Musi wtedy zachować rozróżnienie braku pola i null,
oryginalne typy liczb oraz tekst dat/URI.

**Odbiór:** mypy blokuje CI dla wymienionych modułów; celowy błędny argument
lub odczyt nieistniejącego pola jest wykrywany; regresje Best i odczyt eksportów
przechodzą. Wyłączenia są lokalne i uzasadnione. Brak zmian YAML/schematu/Best.
**Koszt i ryzyko:** średnie; głównie doprecyzowanie istniejących słowników
i granic walidacji. Nie obiecuje to usunięcia błędów logicznych.

Podstawa: [stopniowe wdrażanie mypy](https://mypy.readthedocs.io/en/stable/existing_code.html)
oraz [integracja Pydantic](https://docs.pydantic.dev/latest/integrations/mypy/).

### Plan realizacji propozycji 1

Cel i architektura: trzy moduły sprawdzane w trybie strict, plugin Pydantic,
mały `BestMeasurementInput` (TypedDict pól czytanych przez selektor),
`Mapping[str, object]` dla surowych wejść kontroli skończoności.
Stos: Python 3.12, mypy, types-jsonschema; wersje ustala `uv.lock`.
Specyfikacja: §9–11; zakres powyżej zaakceptowany poleceniem użytkownika.
Pełna migracja słowników oraz propozycje 2/3 pozostają poza zakresem.

- [x] Dodać próby poprawnych i błędnych wywołań mypy oraz uzupełnić istniejący
  test workflow; potwierdzić brak bramki przed implementacją.
- [x] W `pyproject.toml`/`uv.lock` dodać zależności i konfigurację; w trzech
  modułach doprecyzować typy bez zmiany wartości, schematów ani reguł Best.
  Dodać `uv run --frozen mypy` do `Validate code and data`.
- [x] Potwierdzić odrzucanie złego argumentu, literówki w polu selektora i pola
  modelu; wykonać regresje, pełną bramkę, build i niezależny odczyt eksportów.
  Porównać zawartość z bazą `8a710f87`, przy identycznym czasie i source SHA.
- [x] Przejrzeć diff, uzupełnić specyfikację, komendy, backlog/kontekst i dowody
  PBI-120; commit, push do PR #45, potwierdzenie SHA i końcowych statusów CI.
  Odbiór `72fe94fd`: oba workflowy completed/success. Końcowy SHA dokumentacji
  i jego własne CI wskazuje opis PR.

Punkty przeglądu: zachowanie int/float i bool, brak/null, niepoprawne wejścia
Best, zachowanie dat/stref i remisów, rzeczywiste wykrywanie błędów przez
bramkę (bez globalnych wyłączeń). Istniejące regresje i próby mypy pokrywają
te granice; źródła i generowane schematy muszą pozostać niezmienione.

## 2. Generowane przypadki brzegowe z Hypothesis

**Cel:** sprawdzać własności danych i algorytmów dla kombinacji, których nie
pokrywają ręcznie zapisane przykłady. Zachować obecne regresje jako konkretne
świadectwa dawnych błędów.

**Proponowany zakres:** nowy `tests/test_catalog_properties.py`, jawne
strategie w `tests/`, zależność deweloperska Hypothesis w locku. Zacząć od:

- zachowania wartości i obecności pól po walidacji/model_dump na poprawnych
  rekordach, w tym int/float, brak/null, tekst dat oraz kolejność list;
- zgodności modelu i JSON Schema dla wspólnego kontraktu strukturalnego;
  osobno uwzględnić reguły Python niewyrażone w schemacie, np. zakazane XML;
- niezależności Best od kolejności pomiarów z unikalnymi ID i prawidłowego
  porównania tej samej chwili w różnych strefach;
- odrzucania zmiany chronionego pola lub prefiksu historii oraz dopuszczania
  dopisania nowego pomiaru i redakcji dozwolonych metadanych.

**Odbiór:** wygenerowane naruszenia są wykrywane; celowane mutacje tych reguł
psują testy. Nie wyliczać oczekiwań tą samą funkcją co wynik. Minimalny znaleziony
przypadek dodawać jako trwałą regresję. Proponowany profil PR: 100 przykładów
na własność, powtarzalne generowanie i budżet do 30 s dodatkowego czasu CI;
kosztowne repozytoria Git mają mniejszy jawny limit, np. 20 przykładów.
Profil 1000 przykładów uruchamiać ręcznie. Limity potwierdzić pomiarem przed
wdrożeniem; nie wyciszać testów tylko po to, by zmieścić się w czasie.
**Koszt i ryzyko:** małe/średnie; ryzykiem są wolne lub tautologiczne testy.
Można zrealizować niezależnie od propozycji 1.

Podstawa: [Hypothesis i konfiguracja przykładów](https://hypothesis.readthedocs.io/en/latest/reference/api.html).

## 3. Wersjonowane paczki i pojedyncze przełączenie aktywnej wersji

**Cel:** czytelnik otrzymuje kompletną starą albo nową paczkę; nie miesza
formatów z dwóch publikacji. Dzisiejsze `artifact_io.py` cofa obsłużone błędy,
ale podmienia pliki kolejno.

**Proponowany układ lokalnego buildu:**

```text
build/packages/<unikalny-identyfikator>/
  katalog.sqlite
  exports/...
  manifest.json   # source SHA, czas, wersja kontraktu, ścieżki i SHA-256
build/current.json  # wskazuje jedną ukończoną paczkę
```

Budować paczkę w nowym katalogu na tym samym systemie plików, sprawdzić każdy
format i sumy, a dopiero potem podmienić mały plik wskaźnika przez `os.replace`.
Paczek już wskazanych nie modyfikować. Konsument odczytuje wskaźnik raz,
zapamiętuje ścieżkę paczki i z niej bierze wszystkie formaty. Wielokrotne
rozwiązywanie wskaźnika przy każdym pliku nie zapewnia spójnego odczytu.

Publikator powinien trzymać blokadę procesu podczas przełączenia i sprawdzać,
czy od rozpoczęcia buildu nie opublikowano już nowej paczki; konflikt kończy
się bez nadpisania nowszego wyniku. Wyjście procesu zwalnia blokadę.
`fsync` plików i katalogów wymaga osobnego sprawdzenia na obsługiwanych
systemach; atomowe przełączenie samo nie dowodzi odporności na utratę zasilania.

**Zakres wdrożenia:** `release_artifacts.py`, `artifact_io.py`, CLI budowania,
preview/release jako konsumenci konkretnej ścieżki paczki oraz dokumentacja.
Zachować nazwy publicznych załączników wydania. Dotychczasowe argumenty
`--sqlite-output`/`--output-dir` pozostawić jako jawny tryb zgodności z obecną
gwarancją rollbacku; nie przypisywać mu atomowości całego zestawu.

**Odbiór:** zabicie procesu przed/po przełączeniu pozostawia jedną czytelną,
kompletną wersję; dwa publikatory nie nadpisują sobie wyników; czytelnik
nie miesza paczek; błędny manifest/suma blokują przełączenie. Testy wykonują
rzeczywiste procesy na Linux i macOS. Stare paczki pozostają do jawnego
sprzątania; na początku nie dodawać automatycznego usuwania ani GC.
**Koszt i ryzyko:** największe z trzech; zmienia umowę z lokalnymi konsumentami
i zużywa więcej miejsca. Proponuję wdrożyć, gdy współbieżność lub przerwane
publikacje będą uzasadniały ten koszt. Publikacja załączników GitHub nie staje
się przez tę zmianę transakcją; to osobna granica zewnętrznej usługi.

Podstawa: [Python: os.replace i os.fsync](https://docs.python.org/3.12/library/os.html#os.replace).
