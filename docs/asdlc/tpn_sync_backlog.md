# Integracja TPN: PBI i stan realizacji

Stan na: 2026-10-19. [Projekt i uzasadnienie](tpn_sync_plan.md).
[Indeks całego backlogu](backlog_v1.md).

Użytkownik przyjął kontrakt PBI-095 i osobno zlecił wyłącznie **PBI-098**.
[Kontrakt](tpn_sync_contract.md) i [przykłady](tpn_sync_examples.md) są
częścią specyfikacji integracji. PBI-095: **wykonane**. PBI-096: **wykonane 2026-10-19**.
PBI-097: **wykonane 2026-10-19**; PBI-098: **wykonane 2026-10-19**.
PBI-099–103: **planowane**. Porównanie jest tylko do odczytu; bez importera i harmonogramu.
Wykonujemy po jednej gotowej karcie na osobne polecenie.
Numeracja 095–103 kontynuuje istniejący backlog, bez wznawiania starych gałęzi.

| PBI | Sprawdzalny wynik | Zależności |
|---|---|---|
| 095 | Uzgodniony kontrakt w specyfikacji | Akceptacja projektu |
| 096 | Kompletny, weryfikowalny snapshot API | 095 |
| 097 | Bootstrap i różnice źródła względem stanu katalogu | 096 |
| 098 | Kandydaci duplikatów i bramka dla nowych obiektów | 097 |
| 099 | Ochrona GNSS/geodezji i istniejącego wyboru best | 095; kolejność po 098 |
| 100 | Decyzje po rekordzie i idempotentne zastosowanie paczki | 097–099 |
| 101 | Pierwsze rozpatrzenie aktualnych danych TPN | 100 |
| 102 | Ręczne uruchomienie procesu tworzącego jeden PR | 101 |
| 103 | Comiesięczne uruchomienie sprawdzonego procesu | 102 |

## Wspólny kontrakt wykonania

- Kontekstem są aktualne spec, AGENTS, niniejszy plan i obecny main.
  Historyczne PBI-034–077 nie są dowodem dostępności funkcji.
- Każda karta zmienia tylko swój zakres. Status aktualizujemy w tym pliku
  oraz indeksie, ważne ustalenia w `context.md`, dowody w
  `docs/asdlc/verification/PBI-NNN.md`.
- Kod otrzymuje deterministyczne testy offline, fixture'y API oraz testy
  istotnych ścieżek błędów. Live API służy dodatkowej próbie, nie jest
  zależnością zwykłego CI. Testy mają sprawdzać wynik i brak utraty danych.
- Weryfikacja zgodna z [runbookiem](remediation_runbook.md): testy adekwatne
  do zmiany, pełne wymagane CI dokładnego dostarczonego SHA, odczyt wyników
  po zapisie. Zmiana danych dodatkowo wymaga odczytu eksportów i porównania
  niezmienności chronionych pomiarów.
- Commit/push/PR po zweryfikowaniu kroku. Bez automatycznego merge, tagu
  i release. Nie uruchamiamy masowego importu, zanim istnieją schematy,
  fixture'y, walidacja, ochrona oraz rejestrowanie decyzji.

## PBI-095: Uzgodnić kontrakt integracji i rozszerzyć specyfikację

Status: wykonane 2026-10-19. Kierunek [projektu](tpn_sync_plan.md) przyjęty przez
użytkownika 2026-10-19; zlecono wyłącznie tę kartę.
Dowody: [PBI-095](verification/PBI-095.md).

**Cel:** następne karty nie muszą zgadywać, co jest zmianą źródła, decyzją
operatora i dozwolonym skutkiem w katalogu.

**Zakres:** spec v2 (model źródeł/pomiarów, best, staging, §20–21), AGENTS,
context i opis decyzji. Wąski wyjątek dla TPN i GitHub Actions; pozostałe
wyłączenia V1 zachowane. Bez kodu, migracji danych i włączania workflow.

**Kryteria odbioru:**

- [x] Spec odróżnia wymagania zaakceptowane przez użytkownika od propozycji;
      ustala jeden PR z decyzjami po rekordzie i wyłącznie ludzki merge.
- [x] Kontrakt definiuje typed GLOBALID, wiele GUID jednego obiektu, stan
      źródła, hashe, preimage, bootstrap CSV/API/YAML, defer/reject i brak
      automatycznego usuwania danych po zniknięciu rekordu.
- [x] Jawna tabela mapuje pola API na dane źródłowe, dozwolone aktualizacje
      metadanych i składniki odcisku lokalizacji. Określa null/zero, tolerancję
      numeryczną, datę źródła/obserwacji/pobrania oraz zachowanie wysokości.
- [x] Spec ustala ochronę manual/GNSS/geodezji, semantykę keep/select_new,
      bramkę nowych obiektów i reguły pamiętania rozstrzygnięć duplikatów.
- [x] Schematy manifestu źródła, zmian i decyzji są opisane na przykładach
      obejmujących nowy obiekt, istniejący obiekt, konflikt i defer.
- [x] Projekt, spec i AGENTS nie zawierają sprzecznych granic tej integracji.

**Refinement PBI-095:** tabela 21 atrybutów i geometrii sprawdzona na
publicznym schemacie oraz jednej odpowiedzi query. Uzgodniono z użytkownikiem
LAST_EDITED_DATE jako datę stanu źródła z komentarzem przy nieznanej dacie
terenowej; bez tej daty pomiar odraczamy. Tolerancja bootstrapu ≤0,1 m
dotyczy wyłącznie konwersji XY; promień kandydatów minimum 100 m nie
rozstrzyga tożsamości. Wykonywalne fixture'y/schematy należą do dalszych PBI.

## PBI-096: Pobierać kompletny i odtwarzalny snapshot publicznego API

Status: wykonane 2026-10-19. Zlecone osobno 2026-10-19.
Dowody i dokładny stan dostawy: [PBI-096](verification/PBI-096.md).

**Cel:** dostarczyć wiarygodne wejście do porównań bez modyfikacji katalogu.

**Zakres:** adapter publicznej warstwy Topografia /6, CLI pobierania,
walidacja schematu i manifestu, fixture'y. Kontekst: plan §2–4, [kontrakt](tpn_sync_contract.md) §2–4,
[manifest](tpn_sync_examples.md), dotychczasowy CSV i moduł `tpn_staging.py`. Nie zapisuje Obiektów/Jaskiń ani PR.

**Kryteria odbioru:**

- [x] Pobiera wszystkie pola, w tym GLOBALID/WER_LOK/UWAGI, i geometrię
      z jawnym CRS. Manifest zawiera endpoint, parametry, czas, schemat,
      liczbę rekordów, listę ID oraz hashe rzeczywistych zapisanych plików.
- [x] Obsługuje paginację i limity usługi; sprawdza tożsamość warstwy,
      kompletność ID, unikalność GUID i zgodność licznika przed/po odczycie.
- [x] Błędy HTTP/ArcGIS, brak pola, niepoprawne GUID/geometria, zdublowane
      lub brakujące strony i zmiana źródła podczas odczytu nie publikują
      częściowego snapshotu jako poprawnego. Ponowienia są ograniczone.
- [x] Ponowny zapis nie nadpisuje wcześniejszych dowodów; odczyt po zapisie
      potwierdza hash i treść. Zwykłe testy działają bez sieci.
- [x] Jedna ręczna próba live potwierdza pełny odczyt; żaden YAML domenowy
      ani stary CSV/XLSX nie zmienia bajtów.

## PBI-097: Wyliczać zmiany TPN z uwzględnieniem katalogu i wcześniejszych decyzji

Status: wykonane 2026-10-19. Zlecone osobno 2026-10-19.
[Dowody](verification/PBI-097.md), [CLI i format rejestru](tpn_sync_comparison.md).

**Cel:** odróżnić zaległą różnicę źródła, niezależną zmianę lokalną i już
rozpatrzoną rewizję, także podczas pierwszego uruchomienia.

**Zakres:** stan źródła, normalizacja, bootstrap starego CSV i aktualnego
YAML, trzystronne porównanie, maszynowy oraz czytelny raport. Bez zapisów
do danych domenowych. Kontekst: plan §3–5 i spec z 095.

**Kryteria odbioru:**

- [x] Łączenie używa wyłącznie typu TPN/source_globalid. OBJECTID,
      NR_INWENT i nazwa nie stają się tożsamością otworu.
- [x] Raport klasyfikuje nowe GUID, zmiany metadanych/lokalizacji, braki
      powiązań, konflikty lokalne i zniknięcia; pokazuje before/after,
      kontekst WER_LOK/UWAGI oraz odległości bez deklarowania dokładności.
- [x] Bootstrap rozpoznaje kilka GUID już scalonych w jednym Obiekcie,
      stare pomiary i istniejące notatki. Nie odtwarza scalonych obiektów
      ani nie dopisuje tego samego źródłowego pomiaru pod innym ID.
- [x] Techniczne zmiany odpowiedzi nie udają nowego pomiaru; nieznane pola
      lub zmiana polityki normalizacji wymagają jawnej migracji wersji.
- [x] Testy dwóch kolejnych cykli potwierdzają: baza przyjęta dopiero po
      merge, defer zachowany, reject ważny dla rewizji, nowa rewizja wraca
      do review, zmiana celu unieważnia nieaktualną decyzję.
- [x] Ten sam snapshot i ten sam katalog dają ten sam raport semantyczny;
      no-op nie wymaga PR. Brak w niepełnym odczycie nie jest zniknięciem.

## PBI-098: Wykrywać kandydatów duplikatów i kwalifikować nowe rekordy

Status: wykonane 2026-10-19. Zależność: 097.
Osobne zlecenie użytkownika 2026-10-19. [Dowody](verification/PBI-098.md),
[CLI i parametry](tpn_sync_candidates.md).

**Cel:** automat może proponować nowy Obiekt tylko wtedy, gdy nie pomija
sygnałów, że rekord opisuje istniejący otwór lub jaskinię.

**Zakres:** raport kandydatów i klasyfikacja bez materializacji YAML.
Kontekst: plan §6, aktualne reguły dopasowania w `tpn_staging.py`; nie
przenosimy bez zmian heurystyki „jedyny kandydat” do automatycznych decyzji.

**Kryteria odbioru:**

- [x] Porównuje nazwy lokalne/jaskiń/źródłowe, NR_INWENT, SYSTEM i pozycje
      wszystkich pomiarów; sprawdza też kolizje między nowymi rekordami.
- [x] Normalizacja zachowuje oznaczenia różnych otworów; podobieństwo
      nazwy i promień przestrzenny mają jawne parametry oraz testy graniczne.
- [x] Wynik zawiera powód, kandydatów i dowody dla każdej blokady automatów;
      nie scala obiektów ani nie dołącza do istniejącej Jaskini samodzielnie.
- [x] Fixture'y obejmują nowe „Okna w Ciemniaku”, dwie „Nyże pod Zachodem
      Pilotów II”, dalekie homonimy, bliskie różne otwory, literówkę nazwy
      oraz kolizję wyłącznie z niewybranym pomiarem historycznym.
- [x] Pamiętane rozstrzygnięcie tego samego otworu/różnych otworów/różnych
      obiektów nie obowiązuje po zmianie jego istotnej podstawy.
- [x] Auto-propozycję otrzymują wyłącznie rekordy spełniające wszystkie
      warunki §6; brak danych lub niepewność daje review, nie fallback.

## PBI-099: Chronić pomiary geodezyjne i wybór best przed synchronizacją

Status: planowane. Zależność kontraktowa: 095; w kolejności po 098.

**Cel:** dodanie ustalenia TPN do historii nie zmienia samoistnie punktu
wybranego do eksportów, zwłaszcza gdy istnieje GNSS/geodezja.

**Zakres:** strażnik wyboru best w ścieżce TPN, audyt obecnych chronionych
pomiarów, minimalny manifest ewentualnej migracji zatwierdzonych best
auto → manual z uzasadnieniem. Bez importu nowego snapshotu. Kontekst:
plan §7, `best_measurement.py`, regresja KSZ-0112/m-001.

**Kryteria odbioru:**

- [ ] Ochrona obejmuje obecne manual oraz GNSS/geodezję niezależnie od
      source/status/accuracy null; nie ogranicza się do wlasne+zweryfikowany.
- [ ] keep zachowuje wskazany pomiar, a wymaganą zmianę trybu pokazuje
      jawnie; select_new nie może zastąpić chronionego best przez TPN.
- [ ] Manifest migracji wymienia konkretne obiekty, podstawę ochrony
      i uzasadnienie. Nie zmienia współrzędnych, statusu ani dokładności.
- [ ] Testy obejmują GNSS z source inne i auto, GNSS w historii, własne
      zweryfikowane, istniejący manual oraz niechroniony auto.
- [ ] Porównanie przed/po danych i eksportów dowodzi zachowania punktów
      chronionych i wszystkich wcześniejszych pomiarów. Brak zatwierdzenia
      obiektu do migracji blokuje jego automatyczną zmianę, nie znosi ochrony.

## PBI-100: Rozpatrywać i stosować decyzje po rekordzie w jednej paczce

Status: planowane. Zależności: 097, 098, 099.

**Cel:** człowiek wybiera skutek każdej zmiany, a ponowienie nie powiela
pomiarów, notatek, referencji ani obiektów.

**Zakres:** schemat changes/decisions, walidator, CLI dry-run/apply,
rozszerzenie `staging_review.py`, kontrola gotowości paczki do merge.
Kontekst: plan §4–8 i obecny format `staging_review_decisions.md`.

**Kryteria odbioru:**

- [ ] pending/approve/reject/defer i akcje metadata, append_measurement,
      attach_source, new_object/link_cave mają przykłady i walidację.
      Automatyczne nowe propozycje są odróżnione od decyzji człowieka.
- [ ] Każda decyzja wiąże snapshot, GUID, rewizję i preimage celu. Zmiana
      lokalnego celu, sprzeczne akcje lub niezatwierdzony konflikt blokują
      zastosowanie. Kilka akcji jednego obiektu jest planowane wspólnie.
- [ ] Stare wartości lokalizacji pozostają; notes są uzupełniane bez utraty
      tekstu, brak Z nie kasuje wysokości, null nie usuwa wartości milcząco.
      Zmiana opisu/daty źródła nie tworzy obserwacji lokalizacyjnej.
- [ ] Cały plan, przydział ID i pełna walidacja następują przed zapisem.
      Błąd ostatniej decyzji oraz awaria zapisu nie zostawiają częściowo
      zmodyfikowanego katalogu ani stanu źródła.
- [ ] Dwa zastosowania tej samej paczki dają identyczne pliki; nieznany
      albo niewspierany format decyzji jest błędem, nie pomijanym rekordem.
- [ ] Bramka CI odrzuca pending i niespójność decyzji z rzeczywistym diffem;
      dopuszcza świadome defer, zapisując jego kolejkę po merge.
- [ ] Dry-run pokazuje skutki w danych, best i eksportach, a apply daje
      ten sam wynik. Kontrole nie wykonują treści wejściowej jako kodu.

## PBI-101: Przeprowadzić pierwsze uzgodnienie danych TPN

Status: planowane. Zależność: 100.

**Cel:** uporządkować zaległości i pozostawić wiarygodną bazę kolejnego cyklu.

**Zakres:** jedna paczka danych z aktualnego pełnego API, trwałe wejścia,
propozycje nowych obiektów, indywidualne decyzje, ich zastosowanie w jednym
PR. Bez harmonogramu i bez wymogu zakończenia wszystkich sporów.

**Kryteria odbioru:**

- [ ] Ponowny odczyt określa rzeczywisty bieżący zakres. Znane 30 nowych
      GUID, 31 GUID bez mapowania i różnice z 2026-10-19 są punktem kontroli,
      a nie wymuszoną liczbą nowych Obiektów lub nowych pomiarów.
- [ ] Każdy przypadek ma rozstrzygnięcie albo uzasadnione defer/reject;
      duplikaty i nowe otwory znanych Jaskiń są ocenione indywidualnie.
- [ ] Snapshot, manifest i decyzje trafiają do Git z danymi. Czysty
      checkout wystarcza do odtworzenia rozpatrzonych zmian.
- [ ] Chronione best i istniejąca historia zachowują wartości; nowe
      rekordy TPN pozostają nieweryfikowane. Sprawdzony jest pełny zbiór,
      eksporty, readback i CI końcowego SHA.
- [ ] PR przedstawia liczniki i rzeczywiste diffy nowych obiektów,
      metadanych, dodanych pomiarów, best i odroczeń; ponowienie jest no-op.

**Granica:** karta dostarcza PR do człowieka. Merge wykonuje wyłącznie
człowiek po odrębnej decyzji; bez niego nie traktujemy snapshotu jako przyjętej
bazy produkcyjnego cyklu. Nie blokuje to testów narzędzi na fixture'ach.

## PBI-102: Przygotowywać pojedynczy PR przez ręczne uruchomienie workflow

Status: planowane. Zależność: 101; próba produkcyjna po ludzkim merge 101.

**Cel:** sprawdzić publikację i przegląd paczki przed jej cyklicznym użyciem.

**Zakres:** GitHub Actions `workflow_dispatch`, branch/PR, etap zastosowania
decyzji w tej samej gałęzi, uprawnienia i instrukcja operatora. Bez schedule.
Kontekst: plan §8–9, istniejące validate CI i ochrona main.

**Kryteria odbioru:**

- [ ] Pełne poprawne wejście i istotna zmiana tworzą jeden draft PR;
      no-op i błędne/niepełne API nie tworzą PR ani nie zmieniają main.
- [ ] Bot przedstawia propozycje nowych rekordów oraz pending dla
      istniejących; tylko uprawniony operator stosuje decyzje.
- [ ] Istniejący otwarty PR nie jest zastępowany nowym ani nadpisywany.
      Ponowienia/równoległe przebiegi nie tworzą dwóch paczek; zamknięcie
      bez merge nie przesuwa przyjętej bazy.
- [ ] Edycja decyzji i ponowne zastosowanie dopisują commit do tego samego
      PR, bez force-push. Zmiana main wymusza kontrolę aktualności decyzji.
- [ ] Zaufany kod pochodzi z main; wejściowy PR nie dostarcza wykonywanego
      kodu do joba z uprawnieniami zapisu. Token ma minimalny zakres.
- [ ] Zweryfikowano rzeczywisty mechanizm uruchamiania/akceptacji CI dla
      GITHUB_TOKEN, wszystkie wymagane checki dokładnego SHA oraz blokadę
      pending. Bot nie zatwierdza review ani nie włącza auto-merge.
- [ ] Instrukcja obejmuje: review danych, edycję decyzji, defer, odświeżenie
      paczki, zamknięcie bez merge i ponowienie po awarii. Dowód end-to-end
      obejmuje PR i eksporty; ludzki merge tylko na osobne polecenie.

## PBI-103: Sprawdzać źródło co miesiąc i otwierać PR do review

Status: planowane. Zależność: 102 i odbiór ręcznej ścieżki.

**Cel:** regularnie wykrywać nowe informacje, zachowując kontrolę człowieka.

**Zakres:** schedule korzystający z tego samego kodu co workflow_dispatch,
obsługa zaległego PR, diagnostyka i krótki runbook. Bez automatycznego merge.

**Kryteria odbioru:**

- [ ] Uzgodniony dzień/godzina/strefa dają jeden planowany przebieg w
      miesiącu; ręczna ścieżka nadal działa. Brak osobnego zadania Codex.
- [ ] Brak zmian nie daje commitu/PR. Zmiany tworzą draft; aktywny PR
      pozostaje nienaruszony, a wynik nowego sprawdzenia i zaległość są
      widoczne w run summary/artefakcie. Nie powstaje miesięczna kopia PR.
- [ ] Po ludzkim merge następna paczka używa przyjętej bazy i zachowuje
      odroczenia; zamknięcie bez merge nie gubi zmian.
- [ ] Testy cykli obejmują no-op, nową rewizję, błąd API i PR otwarty przez
      dwa miesiące. Konfiguracja nie zawiera merge/release/approval bota.
- [ ] Runbook opisuje best-effort harmonogramu, możliwe wyłączenie po
      60 dniach nieaktywności i ręczne wznowienie. Uruchomienie próbne
      potwierdza ten sam wynik co ścieżka ręczna.

## Kontynuacja

Bieżąca sesja kończy się po dostarczeniu PBI-098. Następna karta to
PBI-099, ochrona GNSS/geodezji i best bez importu snapshotu; wymaga nowego
polecenia. PBI-099–103 nie rozpoczęto.
Otwarty PR #12 kontynuujemy na jego gałęzi; po ludzkim merge zaczynamy od main.
