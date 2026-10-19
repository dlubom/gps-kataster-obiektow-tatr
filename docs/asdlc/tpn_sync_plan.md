# Integracja TPN: plan do uzgodnienia

Data: 2026-10-19. Baza analizy: `main` / `origin/main`
`b98fd3febb400c7ee520046682c1bb16238429ee`, po fetch i pull.

Status: **propozycja projektu i kolejności prac**. Ten dokument nie uruchamia
importu ani harmonogramu. Karty wykonawcze: [backlog TPN](tpn_sync_backlog.md).
[Start z czystego kontekstu i zapytania API](tpn_sync_handoff.md) zawiera
instrukcję pobrania bieżącego JSON; lokalna kopia nie jest częścią PR.
Obecna [specyfikacja](../../specyfikacja_gps_kataster_obiektow_tatr_v_2.md)
wyłącza cykliczną synchronizację (§20–21); jej rozszerzenie jest pierwszym PBI.
Nowy zakres dotyczy tylko TPN. YAML pozostaje źródłem prawdy katalogu.

## 1. Cel i ustalenia użytkownika

- Najpierw rozpoznać i rozpatrzyć zaległe nowe oraz zmienione rekordy TPN.
- Dla istniejącego obiektu móc osobno zdecydować o poprawieniu danych,
  dopisaniu pomiaru do historii i zmianie najlepszego pomiaru.
- Później sprawdzać źródło co miesiąc i przygotowywać PR do człowieka.
- **Jeden PR dla paczki, osobne decyzje dla rekordów** — wybór użytkownika.
- Automatyzacja nigdy nie merguje PR; nowe rekordy mogą być proponowane
  automatycznie, a zmiany istniejących wymagają rozpatrzenia.
- Wykrywać potencjalne duplikaty po nazwie i chronić dokładne pomiary
  geodezyjne przed zastąpieniem przez import TPN.

Pozostałe szczegóły poniżej są rekomendacją do uzgodnienia, a nie wcześniej
zaakceptowanymi decyzjami użytkownika.

## 2. Co wiemy z obecnych danych i kodu

Publiczne źródło: [Topografia___wektor_MIL1 / Jaskinie, warstwa 6](https://gis.tpn.pl/server/rest/services/Topografia___wektor_MIL1/MapServer/6).
Metoda `query` udostępnia anonimowo geometrię oraz `GLOBALID`, `WER_LOK`,
`UWAGI`, `SYSTEM`, `OTWÓR` i daty edycji. Nie używamy uboższej warstwy
`SIPTPN/Geologia_i_gleby/MapServer/2`.

Porównanie zrzutu z 2026-10-19 z zachowanym CSV TPN:

| Obserwacja | Wynik |
|---|---:|
| Rekordy starego CSV / nowego API | 1005 / 1035 |
| Wspólne GLOBALID / nowe / zniknięte | 1005 / 30 / 0 |
| GLOBALID API bez referencji w aktualnych YAML | 31 |
| Zmiany współrzędnych ponad 0,1 m / ponad 1 m | 31 / 30 |
| Zmiany atrybutów poza FIELD i WERYF | 183 rekordy |
| Wspólne rekordy ze zmianą tylko atrybutów FIELD/WERYF | 822 |
| Powtarzające się niepuste nazwy w API | 12 grup / 26 rekordów |

Liczby nie są liczbą nowych jaskiń ani automatycznie zatwierdzonych zmian.
31 niepowiązanych GLOBALID obejmuje również problem istniejący przed nowym
zrzutem. Trzy nowe rekordy mają nazwę „Okno w Ciemniaku”, a dwa „Nyża pod
Zachodem Pilotów II”; trzeba ustalić, czy opisują różne otwory czy duplikaty.
Zmiany `0 → null`, m.in. masowe zmiany `FIELD`, nie dowodzą nowego pomiaru.

Metoda porównania: GUID bez różnic wielkości liter/nawiasów; liczby z CSV
z przecinkiem przeliczone liczbowo; pusty tekst i null równoważne tylko
przy porównaniu tekstów. Geometria CSV przeliczona EPSG:2180 → WGS84,
odległość geodezyjna WGS84. Próg 0,1 m służy tu wyłącznie odróżnieniu
szumu konwersji; nie jest miarą dokładności pomiaru ani progiem zgodności
obiektów. Null i zero w polach liczbowych pozostają różnymi wartościami.

Podstawa odtwarzalności:

- CSV: `data/sources/tpn/tpn_otwory_jaskin.xlsx.-.Export.csv`, SHA-256
  `554beb579e04c79c4fa926910e38ae551ea684e895b9b63f8ddddca73522f581`.
- API JSON: SHA-256
  `36c9a80025ad7c253274aded89688a6151ee2bf819b62ddcb6d8754a7921d454`.
  Lokalna kopia i szczegółowy wynik porównania są w
  `build/exports/tpn-api/2026-10-19/`; pierwsze wdrożenie utrwali wejścia
  decyzji w Git, zanim zmieni katalog. Liczniki powyżej nie są stałymi testów.

Istnieją `tpn_staging.py`, `staging_review.py`, walidator i format
[decyzji operatora](staging_review_decisions.md). Wykorzystamy ich granicę
staging → decyzje → walidacja. Na tej bazie nie ma jeszcze rejestru rewizji
źródła ani ochrony przed ponownym importem tej samej obserwacji o nowym ID
pomiaru. Nie zakładamy obecności rozwiązań z porzuconych gałęzi.

Obecny `auto` daje TPN pierwszeństwo przed `source: inne`, także dla
`method: gnss`. Przykład: `KSZ-0112/m-001` (dolny otwór Bańdziocha) ma
GNSS, `source: inne`, status nieweryfikowany i `mode: auto`. Sama reguła
„własne zweryfikowane przed TPN” nie wystarcza do wymaganej ochrony.

## 3. Przepływ i trzy punkty odniesienia

1. Pobierz kompletny zrzut API i zweryfikuj jego schemat, licznik, listę ID,
   unikalność GLOBALID, geometrię oraz kompletność stron odpowiedzi.
2. Porównaj **poprzedni zrzut TPN**, **nowy zrzut TPN** i **bieżący katalog
   YAML**. Różnica TPN nie może cofnąć niezależnej poprawki operatora.
3. Przygotuj zmiany źródłowe, kandydatów dopasowania i propozycje decyzji.
4. W gałęzi PR materializuj tylko jednoznacznie nowe obiekty spełniające
   warunki §6 oraz jawnie zatwierdzone decyzje dla istniejących.
5. Waliduj cały wynik, sprawdź ochronę danych i pokaż rzeczywisty diff.
6. Człowiek przegląda paczkę, rozstrzyga poszczególne rekordy i merguje PR.

Kluczem rekordu TPN jest para `TPN/source_globalid`. `OBJECTID` jest tylko
technicznym ID danej usługi. `NR_INWENT` identyfikuje jaskinię/pozycję
katalogową i nie rozstrzyga, który otwór aktualizować.
Kilka GLOBALID może już prawidłowo wskazywać jeden obiekt po scaleniu;
import nie odtwarza dawnych obiektów ani nie rozdziela ich ponownie.

Przed pobraniem sprawdzamy tożsamość i schemat warstwy, a nie sam numer 6.
Przerwana strona, błąd API, brak kluczowego pola lub niespójność odczytu
zatrzymuje paczkę. Brak rekordu w częściowym odczycie nie jest usunięciem.
Weryfikujemy licznik/listę ID przed i po pobraniu; API nie daje nam
gwarantowanej transakcyjnej migawki. Wykryta zmienność wymaga ponowienia,
a hash utrwala dokładnie treść, którą ostatecznie rozpatrywano.

## 4. Stan źródła, historia i powtarzalność

Proponowane trwałe lokalizacje:

- `data/sources/tpn/snapshots/`: niezmienne odpowiedzi API użyte w decyzjach,
  manifesty zapytań, schemat i SHA-256; CSV/XLSX pozostają nienaruszone.
- `data/source_state/tpn/`: wersjonowany stan porównania i rozstrzygnięcia
  rewizji, osobny od danych domenowych. Loader katalogu czyta nadal wyłącznie
  `objects/`, `caves/`, `relations/`.
- `data/source_reviews/tpn/<batch-id>/`: lista zmian oraz decyzje po
  rekordzie, pozwalające wznowić review z czystego checkoutu.
- `build/`: raporty robocze i wyniki sprawdzeń, niewymagane do odtworzenia
  zatwierdzonych decyzji.

Rozdzielamy hash odpowiedzi, rewizję istotnych pól źródła i odcisk danych
lokalizacyjnych. Zmiana uwagi, nazwy lub daty edycji nie tworzy sama nowego
pomiaru. Definicje normalizacji i listy pól są wersjonowane; surowe wartości
pozostają dostępne. Numery wierszy i daty pobrania nie są tożsamością.

Stan wskazuje osobno ostatni kompletny zrzut przyjęty przez merge oraz
decyzję dla każdej rewizji `(GLOBALID, revision_hash)`. Pobranie lub utworzenie
PR nie przesuwa przyjętej bazy. `defer` pozostaje w kolejce nawet po merge
reszty paczki. `reject` dotyczy konkretnej rewizji; zmiana treści wraca do
review. Ponowne uruchomienie nie dopisuje tego samego pomiaru, obiektu,
referencji ani notatki. Decyzja o niezmienionej rewizji może wrócić do oceny,
gdy zmienił się jej lokalny cel lub polityka — kontroluje to preimage hash.

Pełny zrzut potrzebny do odtworzenia zaakceptowanej decyzji trafia do Git
w tej samej paczce. Przebieg bez istotnych zmian zostawia tylko raport
uruchomienia, bez commitu i bez PR. Nie opieramy historii zaakceptowanych
decyzji wyłącznie na wygasających artefaktach GitHub Actions.

## 5. Decyzje dla istniejącego obiektu

Raport pokazuje stary stan TPN, nowy stan TPN, obecny YAML, zmianę odległości,
WER_LOK/UWAGI, kandydatów dopasowania oraz best przed i po proponowanej akcji.

| Sytuacja | Proponowana obsługa |
|---|---|
| To samo GLOBALID i istotna treść | Brak zmiany domenowej. |
| Tylko zmiana technicznych pól/daty edycji | Informacja źródłowa, bez nowego pomiaru. |
| Zmiana nazwy, opisu, systemu lub innych atrybutów | Decyzja `update_metadata` na jawnie wskazanych polach. |
| Nowa/korygowana lokalizacja tego samego otworu | Decyzja `append_measurement`; stary pomiar pozostaje. |
| Nowy GLOBALID może dotyczyć istniejącego otworu | Decyzja `attach_source` z wybranym obiektem; opcjonalny osobny nowy pomiar. |
| Drugi otwór istniejącej jaskini | Nowy Obiekt w istniejącej Jaskini, po rozstrzygnięciu. |
| Rekord zniknął z pełnego źródła | Flaga do review; bez automatycznego usuwania/odrzucania lokalnych danych. |
| Brak wystarczających dowodów / błędna rewizja | `defer` / `reject` z uzasadnieniem. |

Zmiana współrzędnych jest propozycją nowego ustalenia lokalizacyjnego,
nie dowodem nowego pomiaru terenowego. Nie nadpisujemy współrzędnych starego
pomiaru. Osobna decyzja może oznaczyć go jako odrzucony, zachowując wartości.
`LAST_EDITED_DATE` to data edycji źródła, nie automatycznie data pomiaru.
Adapter musi zachować rozróżnienie czasu obserwacji, stanu źródła i pobrania,
zgodnie z §4.3 specyfikacji. Brak daty terenowej nie jest uzupełniany fikcją.

`update_metadata` ma listę dozwolonych pól i wartości przed/po. Ręczne nazwy,
notatki i przypisania jaskiń nie są zastępowane całą kopią rekordu TPN.
WER_LOK/UWAGI są przechowywane w rewizji źródła; zaakceptowane uzupełnienie
istniejących notes dopisuje oznaczony kontekst rewizji i zachowuje dotychczasowy
tekst. Morfometria pozostaje w danych źródłowych/raporcie, dopóki jawna decyzja
nie aktualizuje jej reprezentacji opisowej; ten projekt nie wprowadza przy
okazji nowych pól morfometrii Jaskini. Brak Z/wysokości w API nie usuwa
wcześniejszej wysokości. Null ze źródła nie kasuje niepustego pola katalogu
bez osobnej, widocznej decyzji na tym polu.

Każda decyzja wiąże batch/snapshot hash, GLOBALID, rewizję źródła, lokalny
cel i hash stanu celu. Przy wielu decyzjach do jednego obiektu walidujemy
preimage raz względem bazy paczki, a całą sekwencję atomowo w pamięci.
Zmiana celu na main wymaga ponowienia porównania, nie cichego zastosowania
starej decyzji. Nazwa czy komentarz PR nie są wykonywalną instrukcją.

## 6. Nowe rekordy i podejrzenia duplikatów

Nowy GLOBALID oznacza nowy rekord źródła; nie dowodzi nowego obiektu.
Automatyczne utworzenie YAML w PR dopuszczamy dopiero, gdy:

- GUID jest nowy, poprawny i unikalny; nie ma wcześniej przypisanego celu;
- rekord przechodzi walidację geometrii, kategorii i przypisania regionu;
- nie ma konfliktu z nazwami obiektów, jaskiń i nazwami źródłowymi,
  numerem inwentarzowym, systemem ani innymi nowymi rekordami paczki;
- nie ma pobliskiego kandydata w istniejących pomiarach, także niewybranych
  jako best; proponowany konserwatywny promień kontroli to 100 m;
- można jednoznacznie utworzyć samodzielny obiekt/jaskinię. Powiązanie
  z istniejącą jaskinią lub systemem wymaga decyzji człowieka.

Nowy pomiar TPN jest nieweryfikowany; flaga WERYF nie nadaje mu lokalnego
statusu zweryfikowanego. Automat proponuje YAML tylko w PR, nigdy na main.
Pierwsze zastosowanie podlega temu samemu review co miesięczne paczki.

Detektor duplikatów najpierw normalizuje Unicode, wielkość liter i odstępy.
Zachowuje liczby, I/II/III, „górny”, „dolny” i inne oznaczenia otworów.
Dokładna/znormalizowana zgodność nazw, wspólny NR_INWENT/SYSTEM lub bliskość
generują kandydatów do rozstrzygnięcia. Podobne nazwy są dodatkowym sygnałem,
nie dowodem tożsamości. Próg podobieństwa musi być jawnie skonfigurowany
i sprawdzony na fixture'ach przed dopuszczeniem automatycznych propozycji.

Wynik rozróżnia: ten sam otwór, różne otwory tej samej jaskini, różne obiekty
o tej samej nazwie, nierozstrzygnięte. Nie implementujemy automatycznego merge
obiektów. Zatwierdzone rozstrzygnięcie zostaje zapamiętane wraz z jego
podstawą; nowe współrzędne/referencje unieważniają niepasującą decyzję.

## 7. Ochrona geodezji i wybór best

Zachowanie historii i wybór best są osobnymi operacjami.

- Każde obecne `best_measurement.mode: manual` jest nienaruszalne dla
  automatycznego importu TPN.
- Przed pierwszą zmianą danych przeglądamy wybrane pomiary GNSS/geodezyjne
  i własne zweryfikowane. GNSS w historii oraz rozpoznana geodezja blokują
  automatyczne przestawienie best niezależnie od `source` i dokładności null.
- Dla zatwierdzonych chronionych best używamy istniejącego `mode: manual`
  z uzasadnieniem. Migracja z `auto` wymaga jawnego manifestu i review;
  nie podnosimy przy tym statusu weryfikacji ani nie wymyślamy dokładności.
- Decyzja dopisująca pomiar zawiera `best_action: keep|select_new`.
  `keep` zachowuje dotychczasowy pomiar. Jeśli `auto` wybrałoby nowy,
  propozycja jawnie zmienia best na manual z powodem; taka zmiana jest
  częścią decyzji i diffu, a nie ubocznym skutkiem importera.
- `select_new` dla chronionego obiektu jest odrzucane przez ścieżkę TPN.
  Ewentualna zmiana chronionego wyboru to odrębna, jawna decyzja o danych,
  poza automatyczną paczką synchronizacji.
- Dla `auto` bez ochrony `select_new` musi być zgodne z algorytmem lub
  jawnie ustawić manual z uzasadnieniem. Samo dodanie historii nie jest
  zgodą na zmianę eksportowanego punktu.

Na fixture'ach i rzeczywistej paczce sprawdzamy, że chronione współrzędne,
ID najlepszego pomiaru, statusy i stare pomiary zachowały wartości.
Weryfikacja samego źródła `wlasne` nie wystarcza; regresja obejmuje KSZ-0112.

## 8. Jeden PR i decyzje po rekordzie

Paczka ma `changes.json`, czytelny raport i `decisions.yml`. Decyzje
istniejących obiektów zaczynają jako `pending`; bot nie podpisuje ich
za człowieka. Nowe obiekty spełniające §6 są oznaczone jako propozycje
automatyczne z dowodami przejścia reguł. Człowiek widzi je w diffie YAML.

Operator edytuje plik decyzji w gałęzi PR i uruchamia jawny etap zastosowania
decyzji (lokalne CLI lub `workflow_dispatch` dla uprawnionego maintenera).
Ten etap dopisuje commit do tej samej gałęzi. Uruchamia się ponowna walidacja
rzeczywistego końcowego SHA. Merge wymaga braku `pending`: każdy przypadek
ma być zaakceptowany, odrzucony lub świadomie odroczony. `defer` nie blokuje
merge poprawnej części paczki i nie znika z dalszego przeglądu.

Review obejmuje trzy grupy: nowe YAML, decyzje dla istniejących, pozostające
nierozstrzygnięte/podejrzane duplikaty. Jeden przypadek może wymagać kilku
akcji, np. przypięcia referencji i dodania pomiaru; kolejność jest jawna.
Walidator odrzuca sprzeczne akcje. Nowe ID przydzielamy zbiorczo, po całym
planowaniu partii, bez kolizji przy wielu pomiarach jednego obiektu.

## 9. Uruchamianie miesięczne i obsługa otwartego PR

Rekomendacja: GitHub Actions, wspólna implementacja dla ręcznego
`workflow_dispatch` i późniejszego `schedule`. Pierwszy dzień miesiąca,
godzina poza początkiem pełnej godziny; szczegół do konfiguracji.
Nie tworzymy osobnego zadania w aplikacji Codex.

Przebieg tworzy draft PR od aktualnego main tylko dla istotnych zmian lub
nowych decyzji. Nie merguje, nie zatwierdza własnego PR i nie publikuje
release. Brak zmian kończy się bez PR. Pobieranie/walidacja poprzedza
operacje z uprawnieniami zapisu GitHub.

Jednocześnie istnieje najwyżej jeden otwarty PR synchronizacji. Gdy nadal
trwa review, miesięczny przebieg nie podmienia zrzutu ani decyzji tego PR;
zapisuje wynik sprawdzenia jako artefakt uruchomienia i sygnalizuje zaległą
paczkę. Po merge następny przebieg porówna najnowszy zrzut z przyjętą bazą,
z zachowaniem kolejki defer. Ręczne odświeżenie paczki wymaga ponownego
związania decyzji z rewizjami; bez force-push i nadpisywania pracy człowieka.
Zamknięcie PR bez merge nie przesuwa bazy i nie oznacza odrzucenia rekordów.

Pierwszy wariant uprawnień: repozytoryjny `GITHUB_TOKEN`, minimalne
`contents: write`, `pull-requests: write` tylko w etapie publikacji.
Aktualna dokumentacja GitHub przewiduje dodatkowe zatwierdzenie uruchomień
CI dla PR utworzonego tym tokenem. Wybieramy prostszy wariant z takim
zatwierdzeniem; gdy potrzebne będzie CI uruchamiane samodzielnie, osobna
konfiguracja GitHub App. Sekrety i instalację aplikacji obsługuje użytkownik.
W żadnym wariancie nie obchodzimy ochrony main. Nie wykonujemy kodu z gałęzi
PR z podwyższonymi uprawnieniami; decyzje są wejściem danych dla zaufanego
narzędzia z main.

Harmonogram GitHub jest best-effort. Plan operacyjny obejmuje ręczne
uruchomienie i sprawdzenie wyłączenia schedule po 60 dniach nieaktywności
publicznego repo. Nie obiecujemy gwarantowanego dostarczenia w danej minucie.

## 10. Kolejność i odbiór

1. Uzgodnić ten plan i rozszerzyć spec/AGENTS o wąską integrację TPN.
2. Zbudować i sprawdzić pobieranie snapshotów, bez zmian katalogu.
3. Zbudować porównanie źródła z bazą/YAML oraz wykrywanie duplikatów.
4. Wprowadzić ochronę best oraz trwałe decyzje i idempotentne zastosowanie.
5. Przeprowadzić pierwsze uzgodnienie 30 nowych GUID i zmian istniejących,
   z możliwością defer. Nie wymuszać liczby nowych Obiektów równej 30.
6. Sprawdzić cały proces ręcznie przez PR, włącznie z ponowieniem, zmianą
   main w trakcie review i merge przez człowieka.
7. Dopiero wtedy włączyć comiesięczne przygotowywanie PR.

Wspólne scenariusze odbioru: ten sam snapshot dwa razy; zmiana wyłącznie
metadanych; rzeczywista zmiana lokalizacji; null zamiast wartości; nowy GUID
znanego obiektu; różne otwory tej samej jaskini; odrzucona/deferowana rewizja;
chroniony GNSS; kilka GUID jednego obiektu po merge; niepełne API; nieaktualne
decyzje; błąd ostatniej decyzji bez częściowego zapisu; otwarty PR przez dwa
miesiące; końcowe CI dokładnego SHA oraz odczyt eksportów.

Każda karta ma własny zakres i kryteria, a wykonanie przebiega po jednej
gotowej karcie. Na tym etapie nie ma karty gotowej do implementacji.

## Źródła decyzji projektowych

- [ASDLC: PBI Authoring](https://asdlc.io/practices/pbi-authoring): zakres,
  zależności, kontekst i sprawdzalne warunki odbioru kart.
- [ASDLC: Workflow as Code](https://asdlc.io/practices/workflow-as-code):
  powtarzalne pobieranie, klasyfikacja i egzekwowanie reguł w kodzie;
  człowiek rozstrzyga tożsamość i niepewne dane.
- [GitHub: GITHUB_TOKEN](https://docs.github.com/en/actions/concepts/security/github_token)
  i [harmonogramy](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule),
  sprawdzone 2026-10-19.
