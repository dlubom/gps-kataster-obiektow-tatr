# Kontrakt: czyszczenie kodu katalogu

Zakres zaktualizowany decyzją użytkownika 2026-11-06: realizujemy plan
czyszczenia kodu. Rejestr wycofanych ID i nowe zasady dopuszczania usunięć
zostały wyłączone z tej serii. Nie wdrażamy ich ani nie zmieniamy obecnych
błędów historii na warningi. [Indeks](README.md) posiada statusy kart.

## Cel

Program czyta ręcznie edytowany YAML, waliduje go i buduje eksporty.
Początkowy import PIG/TPN oraz jednorazowe naprawy zakończyły swoje zadanie.
Ich kod znika z bieżącego drzewa; źródłowe XLSX/CSV/JSONL i dowody zostają.
Narzędzia API TPN/NMT, przydział ID i eksport Excela pozostają w utrzymaniu.

## Kontrakt uproszczeń

- U12 usuwa zakończone importy, decyzje staging, profilowanie i naprawę TPN.
  Potrzebne zachowania wspólnych helperów oraz testy eksportów pozostają.
- U15 ogranicza bieżące publiczne wejścia do kanonicznego YAML v2
  (`postgresql-yaml`, `schema_version: 2`). Usuwa programowe przepisywanie
  źródeł oraz nieużywane ścieżki propozycji/legacy. Format danych nie zmienia się.
- Zaakceptowany baseline Git nadal może mieć historyczny format v1 albo v2.
  Czytanie starszej historii pozostaje oddzielone od bieżących wejść.
- U16 usuwa alternatywną walidację geografii katalogu przez wstrzyknięty
  resolver Pythona. PostGIS pozostaje właścicielem reguł katalogu;
  resolver Pythona nadal służy do propozycji nowego ID.
- U17 jest oceną skrócenia drogi SQL → ExportData. Wdrożenie nowego modelu
  odczytu wymaga osobnej akceptacji na podstawie wyniku i bilansu.

## Niezmienniki

- Wszystkie `data/`, archiwalne źródła, geometrie regionów oraz konfiguracja
  pozostają bajtowo bez zmian. Nie powstaje rejestr ani znacznik formatu v3.
  Wyjątek na osobne polecenie użytkownika po U12: korekta dokumentacji
  `data/sources/README.md`; dane katalogu i materiały źródłowe bez zmian.
- Reguły Best, manual Best, źródłowe EPSG/wartości/null, pomiary i ich
  kolejność oraz kontrakty 13 artefaktów pozostają zachowane.
- Obecna bramka historii i wybór rzeczywistego baseline PR/main/wydania
  pozostają. Usunięcie obiektu/pomiaru, zmiana chronionych wartości i kolejności
  nadal zgłaszają obecne błędy. Brak baseline nadal blokuje operację.
- Typy przed konwersją SQL, duplikaty YAML, constraints, dump/restore,
  niezależny odczyt GeoPackage oraz ochrona ścieżek eksportu pozostają.
- Usuwanie writerów źródeł nie usuwa atomowej publikacji artefaktów.
- Bieżący generator zachowuje maksimum aktywnych ID + 1 i brak wypełniania
  luk. Ta seria nie dodaje gwarancji rezerwacji ID wycofanych w przeszłości.

## Odrębna decyzja o przypadkowych usunięciach

[Issue #33](https://github.com/dlubom/gps-kataster-obiektow-tatr/issues/33)
pozostaje odłożone. Wariant raportu ubytków/warningów w CI jest przedmiotem
rozmowy, a nie gotową kartą wdrożenia. Sam warning nie blokuje merge.
Ewentualna zmiana polityki ma osobno określić zakres encji/pól, widoczność
raportu, świadome usunięcie i działanie buildów lokalnych oraz wydań.

Aktualne zachowanie opisuje [specyfikacja projektu](../../../../../specyfikacja_gps_kataster_obiektow_tatr_v_2.md).
Zmiany kontraktów bieżących wejść dokumentuj dopiero podczas ich wdrażania.
