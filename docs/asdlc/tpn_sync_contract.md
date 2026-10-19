# Kontrakt integracji TPN — PBI-095

Normatywne rozwinięcie §8.4 [specyfikacji](../../specyfikacja_gps_kataster_obiektow_tatr_v_2.md).
Wersja kontraktu: `tpn-sync-v1`, 2026-10-19. Określa wymagania przyszłej
implementacji PBI-096–103; obecne CLI CSV/XLSX ich jeszcze nie realizuje.
[Przykłady formatów](tpn_sync_examples.md), [plan](tpn_sync_plan.md),
[backlog](tpn_sync_backlog.md), [przekazanie](tpn_sync_handoff.md).

## 1. Decyzje i granice

Użytkownik przyjął kierunek planu i zlecił wyłącznie kontrakt PBI-095:
jeden PR dla paczki, osobne decyzje rekordów, zaległości przed cyklem
miesięcznym, wyłącznie ludzki merge, kontrola duplikatów, pełna historia
i ochrona geodezji/GNSS. Dodanie pomiaru i wybór best wymagają odrębnych
rozstrzygnięć. YAML katalogu pozostaje źródłem prawdy.

Doprecyzowania wykonawcze tej karty: wersjonowanie normalizacji, hashe,
lokalizacje dowodów, jawna lista aktualizowanych pól, konserwatywne progi
i formaty poniżej. Są decyzjami projektowymi wykonawcy w granicach zlecenia,
nie wcześniejszymi wypowiedziami użytkownika. Dzień/godzina miesięcznego
workflow oraz szczegóły tokena wymagają sprawdzenia w PBI-102–103.
PBI-095 nie włącza workflow, nie zmienia schematów wykonywalnych ani danych.

Uzgodnienie domenowe użytkownika w PBI-095: przy nieznanej dacie pomiaru
używamy daty modyfikacji rekordu TPN z komentarzem wyjaśniającym znaczenie
tej daty. Dokładne mapowanie i przypadek braku daty opisuje §3.1.

## 2. Źródło i tożsamość

Źródło: publiczna warstwa `Topografia___wektor_MIL1/MapServer/6`, nazwa
`Jaskinie`, geometria `esriGeometryPoint`; dokładny URL i parametry są
w przekazaniu. Tożsamość warstwy i typy pól sprawdzamy przy każdym pobraniu.
Odczyt musi mieć wszystkie atrybuty i geometrię z jawnym CRS. Przy
`outSR=4326` geometria `x=lon`, `y=lat`; cache PL-1992 zachowuje projektowe
`x_1992=northing`, `y_1992=easting`.

Klucz dopasowania: `system: TPN`, `ref_type: source_globalid` i poprawny
UUID z `external_id`. Porównujemy UUID po usunięciu otaczających białych
znaków/nawiasów i zmianie liter na małe; surową pisownię zachowujemy.
Sam system TPN, `source_row`, URL, OBJECTID, nazwa lub NR_INWENT nie są
tym kluczem. Niepoprawny/pusty UUID lub powtórzony UUID w snapshotcie
blokuje publikację snapshotu. Ten sam typed UUID w wielu obiektach jest
konfliktem katalogu; kilka różnych UUID jednego obiektu jest legalne.
Nowy UUID nie dowodzi nowego obiektu ani nowego pomiaru.

Snapshot obejmuje odpowiedzi stron, schemat, parametry i kontrole count/ID
przed oraz po pobraniu. Równe liczniki bez równego zbioru ID nie wystarczą.
Suma unikalnych OBJECTID stron musi być równa obu listom ID i licznikom.
Sprawdzamy błędy ArcGIS także przy HTTP 200, limity, każdą geometrię,
brakujące/zdublowane strony i unikalność GLOBALID. Błąd lub wykryta zmiana
źródła przerywa odczyt; ograniczone ponowienie zaczyna kompletny odczyt.
API nie gwarantuje transakcyjnej migawki: stabilne count/ID nie wykrywają
każdej zmiany atrybutu w trakcie pobrania. Manifest utrwala ten limit,
przedział czasu i dokładne bajty użyte w decyzjach.

## 3. Mapa pól i normalizacja

Schemat sprawdzony 2026-10-19: 22 deklaracje, w tym `SHAPE`; odpowiedź
query ma 21 atrybutów i osobne `geometry`. Nie zakładamy stałego licznika
rekordów ani zgodności hasha z wcześniejszym rozpoznaniem. Każde pole
i surowa geometria pozostają w snapshotcie, także gdy brak mapowania YAML.

Kolumna „rewizja” wskazuje udział w `revision_hash`; „lokalizacja” wskazuje
udział w `location_hash`. Techniczny hash surowych plików obejmuje wszystko.

| Pole API | Znaczenie / dozwolona akcja w katalogu | Rewizja | Lokalizacja |
|---|---|---|---|
| `GLOBALID` | Typed referencja obiektu; tylko `attach_source` lub utworzenie obiektu. | klucz | klucz |
| `OBJECTID` | Techniczne ID do kompletności/paginacji, bez mapowania domenowego. | nie | nie |
| `NAZWA` | Propozycja `Obiekt.name_local` lub `Jaskinia.name`; cel wskazuje człowiek. | tak | nie |
| `OTWÓR` | Nazwa konkretnego otworu / dopisany opis obiektu, z zachowaniem NAZWA. | tak | nie |
| `NR_INWENT` | Referencja `NR_INWENT/inventory_number` w Jaskini; wymaga jawnej decyzji o jaskini. | tak | nie |
| `SYSTEM` | `Jaskinia.system_name`, po rozstrzygnięciu powiązania. | tak | nie |
| `GENEZA` | Propozycja kategorii; niejednoznaczność blokuje auto-propozycję. Zmiana kategorii istniejącego obiektu wymaga dowodu. | tak | nie |
| `OPIS` | Oznaczony kontekst w notes obiektu/jaskini, wskazany cel i dopisanie. | tak | nie |
| `WER_LOK`, `UWAGI` | Kontekst rewizji; dopisanie etykiet do notes wskazanego pomiaru, bez zmiany jego wartości i statusu. | tak | nie |
| `DLUGOSC`, `GLEBOKOSC`, `PRZEWYZSZE`, `DENIWELACJ` | Morfometria w źródle/raporcie; wyłącznie jawne dopisanie do notes Jaskini, bez nowych pól domenowych. | tak | nie |
| `WERYF` | Flaga źródła w raporcie; nie nadaje lokalnego statusu zweryfikowanego. | tak | nie |
| `FIELD` | Nieinterpretowana wartość techniczna; tylko surowy snapshot/raport. | nie | nie |
| `TATER` | Semantyka nieustalona: zachować i pokazać zmianę jako wymagającą review; bez mapowania domenowego. | tak | nie |
| `CREATED_USER`, `LAST_EDITED_USER` | Audyt źródła, nie lokalny autor/weryfikator. | nie | nie |
| `CREATED_DATE`, `LAST_EDITED_DATE` | Czas utworzenia/edycji źródła; samodzielna zmiana nie tworzy pomiaru. | nie | nie |
| `SHAPE` / `geometry.x`, `geometry.y` | SHAPE jest deklaracją geometrii; rzeczywiste XY w osobnym `geometry`. Nowe ustalenie przez `append_measurement`, nigdy nadpisanie starego. | tak | tak |

API w tej wersji nie udostępnia `X1992`, `Y1992`, `Z` jako atrybutów;
pochodzą ze starego CSV. Brak wysokości w API ma znacznik `absent`, a nie
liczbową wartość 0. Nie kopiujemy wysokości starego pomiaru do nowego jako
zmierzonej z nowym XY; nowy pomiar ma `elevation_m: null`, poprzedni
zachowuje wysokość i datum. Pojawienie się Z/datum w API wymaga jawnej
wersji polityki; nie zgadujemy odniesienia wysokości.

Normalizacja `tpn-sync-v1`:

- Surowe bajty są niezmienne. Teksty do rewizji: Unicode NFC, końce linii
  LF, usunięcie zewnętrznych odstępów; pusty tekst i null są równoważne.
  Wielkość liter i wewnętrzne odstępy zachowujemy w rewizji. Osobna
  normalizacja nazw do szukania kandydatów: casefold i zwinięcie odstępów;
  zachowuje liczby, znaki diakrytyczne i oznaczenia górny/dolny/I/II/III.
- Liczby są skończone. CSV dopuszcza przecinek dziesiętny; `0`, `0.0`
  mają tę samą wartość, natomiast `null` i zero są różne. Brak oczekiwanego
  pola jest błędem schematu, nie null. Daty ArcGIS: integer milisekund UTC,
  zero oznacza epokę, nie brak. Surowe wartości zachowujemy obok konwersji.
- Zmiana XY API→API jest widoczna niezależnie od wielkości, bez zaokrąglania
  przed hashem. Dla bootstrapu CSV→API porównujemy geodezyjnie WGS84;
  odległość **≤0,1 m** oznacza wyłącznie zgodność poziomą w tolerancji
  konwersji. Zmiana >0,1 m daje propozycję review. To nie jest dokładność
  pomiaru, próg tożsamości ani zgoda na przepisanie XY. Brak Z w API nie
  czyni zgodnego poziomo starego pomiaru nową obserwacją.
- Nieznane pole, usunięte pole lub zmieniony typ jest jawnym dryfem
  schematu: diagnostyczne bajty można zachować, lecz nie publikować ich
  jako zgodnego snapshotu/nowej bazy bez aktualizacji wersji kontraktu.
  `TATER` jest już jawnie sklasyfikowane jako źródłowe, bez interpretacji.

### 3.1 Data ustalenia i data modyfikacji

Dla nowego ustalenia TPN bez dowodu daty pomiaru terenowego:

- `observed_at: null` — nie deklarujemy czasu pomiaru;
- `observed_date` i `source_date`: dzień UTC z `LAST_EDITED_DATE`;
- notes: `Data pomiaru terenowego nieznana; użyto daty modyfikacji rekordu TPN.`
  oraz etykieta `TPN LAST_EDITED_DATE:` z pełnym czasem UTC;
- rejestr źródła/raport: `date_basis: source_modified`, surowa wartość
  milisekund, czas UTC, `field_observed_at: null` i odrębne `fetched_at`.

To wykorzystuje istniejące znaczenie observed_date jako daty ustalenia
lub stanu źródła (§4.3 spec), bez nowego pola w YAML i bez zmiany schematu.
Przykład rzeczywisty: `1653480160000` → `2022-05-25T12:02:40Z` →
`observed_date: '2022-05-25'`. Sama zmiana LAST_EDITED_DATE nie tworzy
nowego pomiaru i nie zmienia daty starego. Uzasadnienie wyboru best nie
może przedstawiać tej daty jako dowodu nowszego pomiaru terenowego.

Brak/null/niepoprawna data modyfikacji blokuje `new_object` i
`append_measurement` do odroczenia lub udokumentowanego wyjaśnienia.
Nie podstawiamy daty pobrania ani CREATED_DATE. Poprawne null pozostaje
w snapshotcie; wadliwy typ/wartość daty jest błędem walidacji wejścia.
Decyzje wyłącznie o metadanych/referencjach nie wymagają daty pomiaru.
Nie korygujemy zbiorczo dat już zapisanych w historii.

## 4. Trzy rodzaje hasha i trwały stan

`raw_sha256` liczymy z dokładnych bajtów każdego zapisanego pliku po
ponownym odczycie. `snapshot_hash` to SHA-256 kanonicznego spisu
`(ścieżka względna, raw_sha256)` wszystkich stron, schematu, odpowiedzi
kontrolnych i manifestu (bez samego `snapshot_hash`, by uniknąć cyklu).

`revision_hash` obejmuje wersję polityki, canonical GLOBALID i wszystkie
pola oznaczone „tak” w tabeli, włącznie z XY. `location_hash` obejmuje
wersję polityki, GLOBALID, CRS, dokładne XY i znacznik wysokości `absent`.
Nie zawiera nazwy, uwag, daty edycji ani czasu pobrania. Jest odciskiem
ustalenia źródłowego, nie dowodem odrębnego pomiaru terenowego.

Kanoniczna serializacja: UTF-8 JSON, klucze sortowane, bez zbędnych
odstępów, tekst po normalizacji powyżej, liczby dziesiętne bez wykładnika,
zbędnych zer końcowych i ujemnego zera; kolejność list zachowana, zbiory
ID wcześniej sortowane. Wersja polityki obejmuje też reguły odległości,
ochrony i kandydatów, a jej treść ma `policy_hash`. Nie stosujemy tolerancji
odległości jako relacji równości hasha (nie jest przechodnia).

`preimage` to mapa ścieżek wszystkich czytanych/modyfikowanych celów
(obiekt, stara/nowa Jaskinia, istotne relacje) i SHA-256 ich bajtów z bazy
paczki. `catalog_hash` obejmuje posortowany spis ścieżek/hashów całego
katalogu objects/caves/relations oraz konfiguracji przestrzennej użytej
do kwalifikacji; `state_hash` wiąże poprzedni rejestr decyzji. To celowo
konserwatywna kontrola: zmiana main w tym zbiorze wymaga ponownego
porównania. Propozycje nowych ID mają warunek nieistnienia ścieżek i
rezerwację w całej partii. Wiele decyzji jednego celu używa tej samej bazy;
wynik po kolejnych akcjach jest walidowany wspólnie, nie jako nowe preimage.

Trwałe lokalizacje (tworzone dopiero przez kolejne PBI):

- `data/sources/tpn/snapshots/<snapshot-id>/`: pełne odpowiedzi użyte do
  decyzji, schemat i manifest. Niezmienne; CSV/XLSX także pozostają bez zmian.
- `data/source_state/tpn/`: ostatni snapshot przyjęty przez ludzki merge,
  powiązania GUID, rewizje, zastosowane odciski oraz kolejka odroczeń.
- `data/source_reviews/tpn/<batch-id>/`: `changes.json`, `decisions.yml`,
  czytelny raport i dowody rozstrzygnięć. Nie czyta ich loader domenowy.

Pobranie, commit na gałęzi i otwarcie PR nie przesuwają przyjętej bazy.
Kandydat stanu w PR staje się przyjęty dopiero wraz z ludzkim merge.
Po merge stan może wskazywać nowy pełny snapshot mimo odroczeń: kolejka
przenosi kompletne nierozpatrzone rewizje i ich dowody, niezależnie od
różnicy kolejnych snapshotów. `reject` dotyczy tylko rewizji i podstawy
decyzji, nie obiektu; nowa rewizja, lokalny cel lub polityka wraca do review.
`defer` pozostaje widoczny nawet przy niezmienionym źródle; sam nie tworzy
co miesiąc identycznego PR. No-op zostawia raport bez commitu/PR.

## 5. Bootstrap i porównanie

Pierwszy cykl używa zachowanego CSV, kompletnego nowego API i aktualnych
YAML. CSV jest historycznym odniesieniem źródłowym, nie przyjętą bazą API.
Bootstrap nie ogłasza wszystkich dawnych rekordów automatycznie przyjętymi.

1. Zbuduj mapę typed GLOBALID → obiekt, także wielu GUID jednego obiektu.
2. Znajdź historię przez `source: TPN`, `source_ref: TPN:{GLOBALID}`
   z normalizacją UUID oraz wartości lokalizacji. Zachowaj lokalne ID,
   statusy, wybór best, notes i historię scaleń. Niejednoznaczność jest
   konfliktem; sam numer wiersza lub zgodne XY obcego źródła nie wystarczą.
3. Potwierdzone równoważne stare ustalenie otrzymuje powiązanie w rejestrze
   źródła, bez nowego pomiaru i bez przerabiania YAML. Kilka GUID już
   scalonego obiektu nie odtwarza skasowanych wcześniej obiektów.
4. Osobno pokaż różnicę CSV/API oraz niezależną różnicę YAML wobec starego
   źródła. Rozbieżność ręcznych danych wymaga świadomego wyboru pola/celu.
   Brak mapowania GUID jest przypadkiem review, nie poleceniem tworzenia.

Każdy późniejszy cykl porównuje przyjęty snapshot, nowy snapshot i YAML,
uwzględniając rejestr decyzji. Dokładnie ten sam location_hash zastosowany
do tego celu nie tworzy kolejnego pomiaru mimo zmiany uwagi czy ID lokalnego.
Powrót do wcześniejszej lokalizacji również wskazuje istniejącą historię.
Dla różnych GUID tego samego obiektu oceniamy zgodność z jego historią:
sam nowy GUID nie uzasadnia drugiego identycznego ustalenia.

Zniknięcie z pełnego snapshotu daje `source_missing` do review. Nie usuwa
referencji, obiektu, pomiaru ani nie oznacza pomiaru jako odrzuconego.
Niepełny odczyt nie uprawnia nawet do takiej klasyfikacji.

## 6. Dozwolone decyzje i ochrona best

Status rekordu: `pending`, `approve`, `reject`, `defer`. `reject` i `defer`
wymagają uzasadnienia, bez akcji zmieniających katalog. `pending` blokuje
gotowość paczki do merge. Część approve można zastosować na gałęzi podczas
review, ale stan gotowy do merge rozlicza każdy rekord. Bot nie podszywa
się pod autora decyzji. Auto-propozycje mają osobne pochodzenie `automatic`;
ich akceptacja/odroczenie/odrzucenie jest jawne per rekord przed merge.

Akcje w approve są uporządkowane, z jawnymi wartościami przed/po:

- `update_metadata`: wyłącznie name_local/category/notes obiektu,
  name/system_name/notes Jaskini i notes wskazanego pomiaru. Notes są
  dopisywane jako oznaczone fragmenty rewizji, bez zastąpienia ręcznej
  treści; ten sam fragment nie jest dopisywany ponownie. Wyczyścić inne
  pole można wyłącznie jawnym `clear: true` z uzasadnieniem. Null źródła
  nie jest takim poleceniem. Zmiana WERYF/uwag nie zmienia statusów.
- `attach_source`: dopisanie typed TPN referencji do wskazanego obiektu;
  dopisanie NR_INWENT do wskazanej Jaskini jest osobną akcją referencji.
  Brak podmiany lub usuwania historycznych referencji.
- `new_object`: nowy obiekt i pierwszy pomiar; Jaskinia przez jawne
  `create_cave` lub `link_cave`. Przydział wszystkich ID po zaplanowaniu
  paczki. Link do istniejącej Jaskini zawsze wymaga człowieka.
  Nowy obiekt do czasu przydziału ID wskazuje `object_key`; link obejmuje
  preimage istniejącej Jaskini i kontrolę nieistnienia nowego pliku,
  bez fikcyjnej starej Jaskini (wariant opisany w przykładach §3).
- `append_measurement`: dopisanie ustalenia lokalizacji, o ile nie jest
  już w historii. `source: TPN`, `method: source_record`, status
  `nieweryfikowany`, dokładności null; stare wartości pozostają.
- `best_action: keep|select_new`: odrębne rozstrzygnięcie wymagane dla
  append do istniejącego obiektu. `keep` wskazuje dotychczasowe ID best;
  gdy auto wybrałoby inaczej, jawnie ustawia manual i reason. `select_new`
  wymaga osobnego uzasadnienia wyboru; jeśli auto go nie wybiera,
  ustawia manual z powodem. Brak best_action jest błędem, nie zgodą
  domyślną. Przed/po best i ewentualna zmiana trybu są częścią diffu.

Akcje nie obejmują nadpisywania starej lokalizacji ani masowej zmiany
statusu pomiarów. Odrzucenie starego pomiaru jest osobną zmianą danych
poza tą paczką synchronizacji, z zachowaniem wartości i uzasadnienia.

Ochrona blokuje `select_new` w ścieżce TPN, gdy obiekt ma manual albo
w historii GNSS/rozpoznaną geodezję lub własny zweryfikowany pomiar.
Obejmuje `method: gnss`, znacznik gnss, `elevation_source: gnss`, raport
GNSS/geodezyjny oraz udokumentowaną kwalifikację operatora; sam napis
`source: inne` nie znosi ochrony. Status, brak dokładności i niewybranie
pomiaru jako best także jej nie znoszą. Niejasny dowód geodezji daje
review przed zmianą best. Dotyczy to m.in. obecnego KSZ-0112/m-001.

Chroniony auto można utrwalić jako manual tylko z jawnym manifestem
konkretnych obiektów, dotychczasowym best i uzasadnieniem (PBI-099).
Brak zgody na migrację blokuje zmianę, nie wyłącza ochrony. Ewentualne
zastąpienie chronionego best odbywa się poza paczką TPN, w odrębnej
decyzji człowieka. Nie zmieniamy przy tym ogólnego algorytmu auto.

## 7. Duplikaty i nowe obiekty

Kandydaci: zgodne znormalizowane nazwy lokalne/jaskiń/źródłowe, wspólny
NR_INWENT/SYSTEM, przestrzenna bliskość do **wszystkich** pomiarów,
w tym niewybranych/odrzuconych, oraz do nowych rekordów tej samej paczki.
Promień to `max(100 m, znane dokładności poziome obu punktów)`; dokładność
null nie oznacza 0. Granica odległości jest włączna. Zgodne nazwy i
referencje generują kandydatów niezależnie od odległości.

Podobieństwo nazw jest dodatkowym konserwatywnym filtrem. Dobór metryki
i progu należy do PBI-098, z fixture'ami literówek i oznaczeń otworów;
do jego zweryfikowania automatyczne tworzenie pozostaje wyłączone.
Próg nie rozstrzyga tożsamości i nie uprawnia do pominięcia innych sygnałów.

Auto-propozycja YAML wyłącznie w gałęzi PR: nowy unikalny GUID, poprawna
geometria/kategoria, jednoznaczny prefix bez fallbacku, dostateczne dane
do pierwszego pomiaru, brak sygnału duplikatu w katalogu i w paczce,
jednoznaczny samodzielny obiekt/nowa Jaskinia. Brak nazwy lub danych do
oceny, powiązanie ze znaną Jaskinią/SYSTEM albo jakakolwiek niepewność
daje review. Automat może przygotować propozycję, nie akceptację człowieka.

Rozstrzygnięcia: `same_opening`, `different_openings_same_cave`,
`different_objects`, `unresolved`. Rejestr zawiera strony porównania,
rewizje, preimage, wersję/hash polityki, dowody, autora i czas. Jest ważny
tylko przy niezmienionej podstawie (nazwy, referencje, lokalizacje, cele).
Nowe dowody unieważniają go do review. Nie ma automatycznego merge/split.

## 8. Zastosowanie, PR i odbiór

Decyzja wiąże batch, snapshot_hash, changes_hash, GLOBALID, revision_hash,
cel, preimage, catalog_hash, state_hash i policy_hash. Każda akcja ma
dozwolony cel i dane; treść API, notes i komentarze PR są wyłącznie danymi.
Nieznana wersja/akcja, powtórzony klucz YAML, konflikt akcji lub nieaktualna
podstawa blokuje zastosowanie całej wybranej partii.

Dry-run planuje wszystkie akcje i ID, waliduje cały wynik w pamięci oraz
pokazuje rzeczywisty diff danych/best. Apply musi dać ten sam wynik;
odporność na awarię zapisu i brak częściowego katalogu/stanu to wymaganie
PBI-100 (obecny applier gwarantuje tylko preflight). Powtórzenie paczki
po potwierdzeniu jej wynikowych hashów jest no-op; nie próbuje sprawdzać
starego preimage jako nowej decyzji. Zmieniony wynik wymaga nowego review.

Końcowy diff jest wynikiem rozstrzygnięć względem utrwalonej bazy paczki.
Jeżeli automat wcześniej umieścił propozycję nowego YAML na gałęzi, jej
reject/defer usuwa z końcowego diffu wyłącznie wygenerowaną propozycję.
Przed taką zmianą sprawdzamy jej wynikowy hash; edycja człowieka daje
konflikt, nie zgodę na nadpisanie. Zmiana wcześniejszej decyzji wymaga
ponownego planu względem bazy, nie stosowania odwrotnych akcji w ciemno.

Jedna otwarta paczka, jeden draft PR. Kolejny odczyt nie nadpisuje snapshotu,
decyzji ani pracy człowieka w otwartym PR. Odświeżenie jest jawne, bez
force-push i z ponownym związaniem decyzji. Zamknięcie bez merge nie
akceptuje bazy ani nie odrzuca rekordów. Przed ludzkim merge wszystkie
rekordy mają końcowy status, diff odpowiada decyzjom, pełne CI jest zielone
dla końcowego SHA. Merge nie jest wykonywany przez automat ani agenta.

Kolejność: PBI-096 snapshot → 097 porównanie → 098 duplikaty → 099 ochrona
→ 100 decyzje → 101 zaległości → 102 ręczny workflow → 103 miesięczny.
Świadome defer pozwala zakończyć pierwszą paczkę, zachowując kolejkę.
Schedule uruchamia się dopiero po odbiorze ręcznej ścieżki; nie tworzymy
osobnego zadania aplikacji Codex. Frontend, PWA, synchronizacja PIG/Geoportal,
ogólna integracja GitHub i automatyczne wydania pozostają poza rozszerzeniem.
