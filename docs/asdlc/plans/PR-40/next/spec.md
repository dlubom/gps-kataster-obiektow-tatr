# Kontrakt: prostszy katalog i świadome wycofania

Projekt do realizacji kartami z [indeksu](README.md), zapisany 2026-11-06.
Użytkownik zaakceptował kierunek uproszczeń i dopuścił wyjątkowe usunięcie
pojedynczego pomiaru. Szczegóły poniżej są propozycją wykonawczą; nie opisują
już wdrożonego zachowania. Bieżący kontrakt pozostaje w
[specyfikacji projektu](../../../../../specyfikacja_gps_kataster_obiektow_tatr_v_2.md).

## Cel i wybrany wariant

Program czyta ręcznie edytowany YAML, waliduje go i buduje eksporty.
Początkowy import PIG/TPN i jednorazowe naprawy zakończyły swoje zadanie.
Ich kod znika z bieżącego drzewa; źródłowe XLSX/CSV/JSONL i dowody zostają.
Narzędzia API TPN/NMT, przydział ID i eksport Excela pozostają potrzebne.

Rozważone warianty ochrony danych:

1. Porównanie wyłącznie z ostatnim wydaniem: pomija rekordy przyjęte później
   na main, dlatego nie zastępuje bramki PR.
2. Ogólne wyłączenie historii: nie ogranicza wyjątku do świadomie usuwanego
   rekordu i utrudnia review przypadkowych ubytków.
3. Wybrany projekt: porównanie z zaakceptowanym SHA oraz jawny rejestr
   wycofań. Rejestr stanowi trwałą rezerwację ID i wąskie uzasadnienie ubytku.

## Znaczenie ID

- ID identyfikuje obiekt/jaskinię/relację/publikację, a nie pozycję w pliku.
  ID pomiaru jest lokalne: jego kluczem jest `(object_id, measurement_id)`.
- Zmiana nazwy, kategorii, powiązania jaskini albo dodanie lepszego pomiaru
  tego samego obiektu zachowuje ID. Nie wymaga wycofania.
- Wycofanie usuwa rekord z bieżącego katalogu i kolejnych eksportów. Oryginał
  pozostaje w zaakceptowanym commicie i dawnych wydaniach; archiwum źródeł
  pozostaje bajtowo bez zmian. Nie jest to usunięcie treści z historii Git.
- Wycofane ID nigdy nie identyfikuje nowego obiektu. Zwykłe luki nie są
  wypełniane. Usunięcie największego numeru także nie zwalnia numeru.
- Rezerwacja zaczyna się po przyjęciu rekordu na main lub publikacji
  oficjalnego wydania. Odrzucona propozycja/dry-run i niescalona gałąź nie
  rezerwują ID na zawsze. Dane przekazywane odbiorcom mają pochodzić z main
  lub wydania; roboczy PR nie obiecuje trwałości proponowanych ID.
- Przywrócenie omyłkowo wycofanego tego samego obiektu nie jest nadaniem ID
  innemu obiektowi. Pierwsza wersja rejestru blokuje również takie przywrócenie;
  jawna procedura reaktywacji jest osobną przyszłą decyzją, nie furtką w CI.

## Rejestr

Źródło: `data/retired_ids.yml`, jedna niewielka lista. Schemat rejestru ma
własne `schema_version: 1`. Przykład jest fikcyjny, nie upoważnia do usunięcia:

```yaml
schema_version: 1
retired:
  - kind: measurement
    object_id: KSW-9000
    id: m-003
    source_commit: "0123456789abcdef0123456789abcdef01234567"
    reason: "Świadome wycofanie omyłkowo dodanego rekordu; uzasadnienie w PR."
    replacement_id: null
```

`kind` to `object`, `cave`, `relation`, `publication` lub `measurement`.
`object_id` jest wymagane wyłącznie dla pomiaru, a dla innych rodzajów jest
niedozwolone. `id` spełnia obecny format danego rodzaju. `reason` jest
niepustym tekstem, `source_commit` pełnym SHA zaakceptowanej rewizji,
która zawierała rekord. Wszystkie pola poza `replacement_id` są wymagane.
Nie dodajemy autora i daty dublujących audyt Git.

`replacement_id` jest opcjonalną informacją: ten sam rodzaj encji, a dla
pomiaru ten sam obiekt. Nowe wskazanie wymaga istniejącego aktywnego następcy
w kandydacie, innego niż wycofywany rekord. Brak następcy jest legalny, np.
dla fikcyjnego punktu systemu. Późniejsze wycofanie następcy nie unieważnia
starego wpisu. Nie wykonujemy automatycznych przekierowań, transferu pomiarów
ani rekurencyjnego rozwiązywania łańcuchów następców.

Zaakceptowane wpisy są nieusuwalne. Ich klucz, `source_commit` i zapisane
wskazanie następcy są niezmienne; doprecyzowanie `reason` jest zwykłą zmianą
tekstową w PR. Rejestr odrzuca powtórzone klucze YAML, nieznane pola,
duplikaty tożsamości, błędne typy, symlink i brak pliku kandydata.

Dodanie wymaganego rejestru zmienia znacznik katalogu na `postgresql-yaml`
`schema_version: 3`; rekordy encji nie są przepisywane. Bieżące publiczne
CLI przyjmują v3. Zaakceptowana historia nadal obsługuje legacy v1 oraz v2
bez rejestru i v3 z rejestrem. Brak rejestru w historycznym v3 jest błędem.
U13 wprowadza ten kontrakt; U15 usuwa pozostały kod starych wejść i zapisów.

## Bramka różnic i świadome usunięcie

1. Baseline pochodzi z rzeczywistego zdarzenia: baza PR, poprzedni stan main,
   a dla wydania zaakceptowany poprzednik. Brak bazy blokuje operację.
2. Anty-join porównuje wszystkie cztery rodzaje encji oraz pomiary po kluczach.
   Nie porównuje tylko Best, liczników ani nazw plików.
3. Ubytek wymaga nowego wpisu rejestru. Dla rekordu obecnego w baseline
   `source_commit` musi być jego dokładnym SHA. Przesunięcie bazy PR wymaga
   ponownego wskazania aktualnej zaakceptowanej bazy dla tego ubytku.
4. Nowy wpis historyczny, którego ID nie ma już w baseline, wymaga dowodu
   istnienia w wskazanym zaakceptowanym wcześniejszym commicie. Ten sam
   mechanizm obsługuje początkowe uzupełnienie dawnych wycofań.
5. Aktywne ID nie może być zarezerwowane w rejestrze. Ręczne wpisanie
   wycofanego ID też daje błąd, niezależnie od generatora.
6. Wycofanie obiektu obejmuje jego lokalne pomiary; nie mnożymy wpisów dla
   dzieci usuwanego obiektu. Nadal sprawdzamy przywołania, relacje, Best,
   przypisanie ID i załączniki w pozostających rekordach. Usunięcie jaskini
   nie upoważnia do usunięcia obiektów ani do ich automatycznego przeniesienia.
7. Osobne wycofanie pomiaru wymaga własnego wpisu. Pozostające stare pomiary
   zachowują względną kolejność, a nowe są dopisywane po nich. Przesunięcie
   indeksów po legalnym usunięciu środka listy nie jest zmianą kolejności.
   Utrzymanie obiektu bez pomiarów jest nadal niedozwolone.
8. Geometria źródłowa, wysokość i datum pozostających pomiarów nadal są
   niezmienne. Zwykła korekta dopisuje pomiar, błędny może zostać odrzucony.
   Notatki/status/metadane pozostają edytowalne zgodnie z obecną specyfikacją.
9. Wyjątek nie wyłącza innych błędów: usunięcie A z poprawnym wpisem nie
   legalizuje usunięcia B, zmiany pozycji C ani uszkodzenia klucza obcego.

Jedna bramka jest wywoływana przez validate, build dumpa, Best, pełny build
i preview. Wymagany check blokuje merge, a błędny build nie publikuje wyniku.
Rejestr jest przekazywany jawnie przy wejściu do bramki, bez globalnego stanu.
Loader/eksporter nie zapisuje, nie uzupełnia i nie naprawia rejestru.

## Nadawanie kolejnych ID

Istniejący `IdSequence(existing_ids=..., reserved_ids=...)` już ma potrzebny
kontrakt. Adapter przekazuje aktywne i wycofane ID w odpowiedniej przestrzeni.
Numer jest większy od obu maksimów. Generator pozostaje tylko propozycją,
bez zapisu rezerwacji; konflikt równoległych PR wykrywa ponowna walidacja
wobec aktualnej bazy przed merge. Ta seria nie wprowadza bota ani licznika.

## Dawne wycofania i odbiorcy

Zaufanym zbiorem źródłowych commitów jest główna linia zaakceptowanej bazy:
`git rev-list --first-parent <baseline_sha>`. Tę samą regułę stosuje audyt
U13 i kontrola nowego `source_commit`. Samo osiąganie commita przez bocznego
rodzica merge nie oznacza przyjęcia jego tymczasowego katalogu. Oficjalne
tagi wskazujące te commity dostarczają dodatkowej informacji o publikacji.
Historyczne oficjalne wydanie spoza tej linii wymaga osobnego rozstrzygnięcia
w audycie; dowolny tag lub branch nie rozszerza automatycznie zbioru zaufania.

U13 przegląda te drzewa i sprawdza zgodność z oficjalnymi wydaniami,
nie wszystkie porzucone branche. Dla każdej nieobecnej tożsamości zachowuje
konkretny commit źródłowy i dowód wycofania. Nie wnioskuje następcy z nazwy
lub odległości. Nieznany powód pozostaje jawnie historycznym usunięciem
o nieustalonym uzasadnieniu; wymyślone przypisanie jest niedopuszczalne.
Audyt sprawdza też ID, które zniknęły, a potem wróciły: bez dowodu tożsamości
nie kwalifikuje tego automatycznie jako tego samego obiektu lub pomyłki.
Wykryte spory wymagają decyzji o danych przed przyjęciem ich do rejestru.

[Issue #33](https://github.com/dlubom/gps-kataster-obiektow-tatr/issues/33)
wskazuje znane przykłady i ryzyko. JKTZ wyszukuje `gps_fix` po `object_id`;
Georeferencer stosuje `gps_kataster_object_id`. Brak ID może zatrzymać
odbiorcę, a nowe miejsce pod dawnym ID może zmienić dowiązanie bez ostrzeżenia.
PR wycofania podaje wpływ na odwołania. Aktualizacja odbiorców jest osobnym
zakresem, bez automatycznego przekierowania ani zmiany innych repozytoriów.

Rejestr jest publicznym YAML dostępnym w drzewie taga. Seria zachowuje 13
obecnych artefaktów, nie dodaje czternastego pliku ani nowych kolumn eksportu.
Dump pozostaje projekcją katalogu, a odtworzenie źródeł i rezerwacji wymaga
repozytorium/tagu z rejestrem. Sam dump nie staje się kompletną kopią źródeł.

## Niezmienniki upraszczania

Surowe źródła, źródłowe EPSG/wartości/null, ręczne Best, geometrie regionów,
13 artefaktów i reguły Best pozostają zachowane. Wyjątek: U13 dodaje rejestr
i zmienia znacznik formatu; nie usuwa żadnego aktywnego rekordu. U14 wdraża
możliwość wycofania, testowaną na fixtures; nie wycofuje rzeczywistych danych.
Walidacja typów, duplikatów YAML, constraints, dump/restore, odczyt GeoPackage
i ochrona ścieżek wyjścia pozostają. Porównanie wydań nie zastępuje bazy PR.
