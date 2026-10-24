# PBI-113: nowe obiekty z lokalnego zrzutu TPN

Stan: 2026-10-23. Użytkownik polecił realizację projektu w PR #28.
Zakres i odroczenia z review zachowano; materializacja wykonana — do review
w draft PR #28. Baza: `caf7bae69b28eb037810215889cb87f763b2c6bd`.

## Cel i wybrane podejście

Dodać brakujące obiekty z warstwy jaskiń, zachowując obecny format
Obiekt–Jaskinia–Pomiar. Brak dopasowania GLOBALID oznacza kandydata,
nie automatycznie nowy obiekt terenowy. Przejrzano wszystkie 31 kandydatów
na tle 1007 obiektów i całej historii pomiarów, nazw/uwag 1001 jaskiń,
lokalnego PIG oraz dostępnych opisów i planów wskazanych poniżej.

Rozważono: dodanie wszystkich rekordów bez dopasowania (grozi utrwaleniem
duplikatów), wymaganie niezależnej publikacji dla każdego wpisu (odkłada
również zwykłe, jednoznaczne rekordy) i dodanie wpisów TPN po przeglądzie
konkretnych konfliktów tożsamości. Użytkownik wybrał ostatni wariant:
jednoznaczny TPN wystarcza do wpisu `nieweryfikowany`; nierozstrzygnięte
mapowanie otworu lub konflikt nazw odraczamy.

## Przypięte źródło i bilans

- Lokalny raw: `data/sources/tpn/api/tpn-20261022T162014287693Z.json`.
  Pobranie: 22.10.2026, 16:20:14–16:20:28 UTC; SHA-256
  `9c626235253c41ed992be27a177ed3f17c8491d60b02eb306c5de0814129314f`.
- Warstwa `Topografia___wektor_MIL1/MapServer/6`: 1035 rekordów,
  1004 GLOBALID dopasowane do 1002 obiektów, 31 niedopasowanych GLOBALID.
  UUID w tej warstwie i referencjach YAML są unikalne. Problemem są
  różne UUID potencjalnie opisujące ten sam obiekt.
- NMT: `data/sources/tpn/api/simple-20261022-final/nmt-evidence.json`.
  Sprawdzono hash raw, zgodność GUID/OBJECTID i dokładnego XY oraz
  niezaokrąglone wartości wysokości dla wszystkich 31 kandydatów.
  `simple-nmt.json` jest widokiem zaokrąglonym, nie źródłem dokładności.
- Do dodania: **19 Obiektów, 18 Jaskiń, 20 Pomiarów i 20 GLOBALID**.
  Jedenaście rekordów pozostaje odroczonych. Każdy z 31 rekordów ma dokładnie
  jedną dyspozycję w tabelach poniżej.
- Oczekiwany katalog względem bazy: **1026 obiektów, 1019 jaskiń,
  1928 pomiarów**. Przed wykonaniem ponownie potwierdzić bazę i liczniki.

## Lista do dodania

OBJECTID wskazuje wiersz wyłącznie przypiętego zrzutu. Trwałą referencją
jest pełny GLOBALID tego wiersza; przed zapisem potwierdzić oba identyfikatory
oraz pełne współrzędne. Prefiksy sprawdzono bieżącym resolverem, wszystkie
mają status `ok`. Numery ID przydzielono po sprawdzeniu resolvera i całej historii Git,
bez ponownego użycia dawnych ID lub zmiany istniejących. Podczas review
wykryto kolizję pierwszych propozycji z nadal istniejącymi PR #12/#13
(np. dawny MTZ-0067/C-1005 to Jaskinia w Kozim Grzbiecie). Wszystkie nowe,
jeszcze nieutrwalone ID przydzielono powyżej historycznych maksimów:
C-1030, KSW-0260, STR-0038, BIA-0009, MTW-0073, MTZ-0071, CHZ-0032, DZI-0011.
Nie zmieniono danych ani statusu tamtych PR. Tabela zawiera końcowe ID.

| OBJECTID | Obiekt | Prefix | Jaskinia | Nadane ID Obiektu / Jaskini |
| --- | --- | --- | --- | --- |
| 3846 | Smocza Jama — otwór N | KSW | istniejąca C-0219 | KSW-0261 / C-0219 |
| 6401 | Gawra w Sarniej Skale | STR | nowa | STR-0039 / C-1031 |
| 6402 | Okno przy Źródle | BIA | nowa | BIA-0010 / C-1032 |
| 6405 | Nyża pod Szarą Turnią I | STR | nowa | STR-0040 / C-1033 |
| 6406 | Schron nad Komorą w Kończystej Turni | MTW | nowa | MTW-0074 / C-1034 |
| 6407 | Nyża za Jałowcem | MTW | nowa | MTW-0075 / C-1035 |
| 7042 | Nyża pod Szarą Turnią II | STR | nowa | STR-0041 / C-1036 |
| 7044 + 6408 | Korytarz pod Ciemniakiem | MTZ | jedna nowa | MTZ-0072 / C-1037 |
| 7045 | Szczelina przy Zbójeckiej Dziurze | CHZ | nowa | CHZ-0033 / C-1038 |
| 7361 | Gawra w Bobrowcu | CHZ | nowa | CHZ-0034 / C-1039 |
| 7362 | Nyża we Wysrankach | KSW | nowa | KSW-0262 / C-1040 |
| 7363 | Nyża pod Szarą Turnią III | STR | nowa | STR-0042 / C-1041 |
| 7366 | Jaskinia Lodowa Ponorowa | MTZ | nowa | MTZ-0073 / C-1042 |
| 7367 | Jaskinia Cynamonowa | CHZ | nowa | CHZ-0035 / C-1043 |
| 7368 | Rura w Olejarni | CHZ | nowa | CHZ-0036 / C-1044 |
| 7377 | Schron pod Gawrą w Bobrowcu | CHZ | nowa | CHZ-0037 / C-1045 |
| 7378 | Okno pod Sikawką | KSW | nowa | KSW-0263 / C-1046 |
| 7379 | Nyża pod Szarą Turnią IV | STR | nowa | STR-0043 / C-1047 |
| 7682 | Gawra w Grześkówkach | DZI | nowa | DZI-0012 / C-1048 |

### Smocza Jama

TPN 410 ma `OTWÓR=S`, T.E-08.07 i GLOBALID
`{B8C9F363-3509-48DB-9ABC-90E665EF74C3}` powiązany z KSW-0065/C-0219.
Nowy 3846 ma jawne `OTWÓR=N` i GLOBALID
`{273B92B8-201B-443E-AD19-73DE844B9F5B}`.
[PIG 760](https://jaskiniepolski.pgi.gov.pl/Details/Information/760)
opisuje dwa połączone otwory. Dodać nowy obiekt do C-0219 i uzupełnić jej
`object_ids` oraz audyt aktualizacji. Nie tworzyć drugiej Jaskini,
nie przenosić historycznego PIG i nie zmieniać KSW-0065 ani jego Best.

### Korytarz pod Ciemniakiem — zaakceptowana interpretacja

Użytkownik zaakceptował jeden obiekt, dwa GLOBALID, dwa pomiary i Best 7044:

- 7044: `{8E246480-F366-4D0F-BA7E-A601E865FD03}` — `m-001`, Best.
- 6408: `{0BFC7731-A83A-40E6-B773-766798366ADD}` — `m-002`, zachowana
  źródłowa nazwa „Korytarz w Ciemniaku” w pochodzeniu/uwagach.

[Nowak 2014, Jaskinie 77, s. 29](http://jaskinie.org.pl/files/Jaskinie__77_2014.pdf#page=29)
przedstawia jeden otwór ślepego schroniska 8 m/+1,3 m. Rekord 7044 odpowiada
nazwie i metrykom publikacji. Nieuzupełniony 6408 utworzył ten sam autor
12 sekund wcześniej; różnica XY wynosi około 0,097 m. To łączna podstawa
interpretacji, nie sama bliskość. Pełniejszy zapis nie dowodzi większej
dokładności XY; punktów nie uśredniać. Oba mają tę samą datę stanu źródła;
`auto` wybiera `m-001` przy remisie dat i nieznanej dokładności. Zapisać
uzasadnienie wyboru i nie odrzucać drugiego pomiaru.

### Pozostałe rozpoznane sąsiedztwa

- [Nowak 2018, Jaskinie 93, s. 32–33](http://jaskinie.org.pl/files/Jaskinie__93_2018.pdf#page=32)
  dokumentuje Szczelinę przy Zbójeckiej Dziurze i Rurę w Olejarni jako
  osobne jaskinie, odróżnione od Zbójeckiej. Rozbieżności metryk/dojścia
  zachować jako informacje źródłowe, bez korekty XY.
- [Solarczyk 2020, Jaskinie 101, s. 33–34](http://jaskinie.org.pl/files/Jaskinie__101_2020.pdf#page=33)
  ma osobny plan i współrzędne Cynamonowej zgodne z punktem TPN;
  nie łączyć jej z pobliską Kokonową.
- [Nowak 2013, Jaskinie 73, s. 27–28](http://jaskinie.org.pl/files/Jaskinie__73_2013.pdf#page=27)
  rozdziela Okno pod Sikawką od Jaskini przy Sikawce.
- Cztery Nyże pod Szarą Turnią zachowują numerację TPN i osobne wpisy.
  Nyża za Jałowcem, Nyża we Wysrankach oraz Gawra/Schron w Bobrowcu
  nie mają konkretnego dowodu utożsamienia z sąsiadami. Sama bliskość,
  wspólny toponim lub nazwa „pod/nad” nie oznacza wspólnego `cave_id`.

## Jedenaście odroczonych rekordów

| OBJECTID | Grupa | Powód odroczenia |
| --- | --- | --- |
| 6409, 7364, 7380 | Okno w Ciemniaku | plan ma portal i komin do powierzchni; brak mapowania GUID na otwory/powtórzenia |
| 6410 | Jaskinia w Kozim Grzbiecie | opis i przekrój rozróżniają wejście główne oraz okno nad nim; TPN nie określa otworu |
| 6722, 7043 | Dziura nad Zahradziskami / Komora w Kończystej Turni | 0,169 m, różne nazwy i długości 5/7 m; nieustalona zmiana nazwy lub odrębność |
| 6403, 6404, 7041 | Nyże pod Zachodem Pilotów | dwa różne II, III i istniejąca nienumerowana STR-0028; nieustalona tożsamość i numeracja |
| 6721 | Tunel w Skrajnej Giewonckiej Baszcie | nowy punkt nie wskazuje otworu S/N; nie tworzyć trzeciego obiektu z samego nowego GUID |
| 7681 | Schron nad Wielką Równią | użytkownik wybrał odroczenie relacji do istniejącej Gawry/Jaskini; nie jest to stwierdzenie duplikatu |

Po review 23.10.2026 użytkownik zdecydował odroczyć Jaskinię w Kozim
Grzbiecie, OBJECTID 6410, GLOBALID `{4D57492D-D68A-471E-B00E-770A594A2C7B}`.
[Nowak 2016, Jaskinie 85, s. 28](http://jaskinie.org.pl/files/Jaskinie__85_2016.pdf#page=28)
opisuje wejście do głównego ciągu pod okapem oraz przewieszone okno nad nim,
prowadzące do ciągu bocznego. TPN ma `OTWÓR=null`; nie ustalono, któremu
otwarciu odpowiada punkt. Rekord pozostaje odroczony do rozstrzygnięcia
tej tożsamości; nie przesądza to błędnego XY ani potrzeby drugiego Obiektu.

[Nowak 2016, Jaskinie 82, s. 27](http://jaskinie.org.pl/files/Jaskinie__82_2016.pdf#page=27)
potwierdza wielootworowość Okna, lecz nie przypisuje trzech GUID.
[KKTJ, Dolinki Reglowe, lipiec 2026](https://kktj.pl/DesktopModules/EasyDNNNews/DocumentDownload.ashx?portalid=0&moduleid=387&articleid=283&documentid=395)
wymienia Tunel oraz Gawrę i Jaskinię nad Wielką Równią. Pełnego artykułu
Filara w Jaskinie 122–123, s. 36–39 nie uzyskano; jego treści nie zakładać.
Nie poprawiać numeracji Pilotów. Istniejące encje Tunelu C-0947/C-0981
pozostają poza zakresem naprawy.

## Zapis danych i granice

- Bez zmian kodu, schematu, algorytmu Best i formatu YAML. Kategoria nowych
  obiektów: `jaskinia_otwor`; zwykły pomiar `m-001`, `source: TPN`,
  `method: source_record`, tag `tpn`, `verification_status: nieweryfikowany`.
- GLOBALID na Obiekcie, dokładne `source_ref: TPN:{GLOBALID}` przy pomiarze;
  wszystkie nowe rekordy nie mają NR_INWENT, więc nie dopisywać numerów
  ani PIG według sąsiedztwa. Publikacje mogą być źródłem opisu w notes.
- `observed_date` i `source_date` z daty `LAST_EDITED_DATE`, analogicznie
  do PBI-111, z jawnym opisem daty stanu źródła, nie pomiaru terenowego.
  Zachować WER_LOK/UWAGI, kod WERYF i jego odrębność od statusu projektu.
  Obiektowe i jaskiniowe informacje trafiają do właściwego poziomu notes.
- Zachować pełne lat/lon; PL-1992 obliczyć obecnymi narzędziami. Wysokość
  z niezaokrąglonego dowodu NMT w dokładnym XY każdego pomiaru:
  `elevation_source: dem`, datum `unknown`, dokładności `null`.
  Po zaakceptowanej korekcie opisów z 2026-10-24 referencja NMT wskazuje
  ID i source_ref pomiaru, model, dokładny URL, czas odczytu i hash odpowiedzi.
  Notes pomiaru zachowują zastrzeżenie: grunt, wysokość otworu niepotwierdzona.
- Zachować całe istniejące dane i ręczne Best. Jedyną modyfikacją istniejącej
  encji będzie członkostwo nowego otworu i audyt aktualizacji C-0219.
- Poza zakresem: leje, pozostała warstwa sztolni/kopalń, wywierzyska,
  nowy importer/synchronizacja, naprawy istniejących par i aktualizacja
  issue #8/#23/#24. Zrzuty i źródłowe PDF-y pozostają lokalne.
  Merge, tag i release wymagają odrębnego polecenia.

## Realizacja i odbiór

1. Potwierdzić bieżący Git, hash raw i NMT, wszystkie 31 GUID i podział
   20 dodanych / 11 odroczonych. Przy zmianie bazy przeliczyć kolizje i ID.
2. Nadać ID zgodnie z resolverem i obecnym rejestrem, utworzyć 19 Obiektów
   i 18 Jaskiń, dopisać otwór do C-0219. Każdy pomiar zachowuje własny GUID,
   punkt i NMT; Korytarz ma oba źródła oraz Best z 7044.
3. Walidacja YAML, symetria członkostwa, unikalność ID/GLOBALID i zgodność
   WGS84/PL-1992; pełna bramka projektu według runbooka.
4. Porównać katalog z bazą: wszystkie dawne Obiekty i ich pomiary/Best
   bez zmian; dawne Jaskinie poza członkostwem/audytem C-0219 bez zmian.
   Potwierdzić liczniki i brak jedenastu odroczonych GUID w nowych danych.
5. Niezależnie odczytać SQLite i wszystkie formaty eksportów, w tym pełne
   wiersze Best/Full, oba pomiary Korytarza i jeden Best na nowy Obiekt.
   Potwierdzić tagi, referencje, NMT i notatki pochodzenia w artefaktach.
6. Commit/push, odczyt zdalnego SHA, terminalne CI dla tego SHA i odczyt
   pobranej paczki PR. Uzasadnienia zmian danych w YAML i opisie PR;
   nie rozbudowywać osobnego raportu dla samej materializacji.

## Odbiór materializacji — 2026-10-23

- 19 nowych Obiektów i 18 Jaskiń według tabeli; 20 pomiarów i GUID.
  Katalog: 1026/1019/1928. Wszystkie 11 odroczonych GUID pozostaje poza katalogiem.
- Dokładne XY, niezaokrąglone NMT, daty LAST_EDITED_DATE i pochodzenie
  wszystkich nowych pomiarów zgodne z przypiętym raw i dowodem NMT.
  SHA-256 dowodu NMT: `d9fa6e4169e18ef26603fa215db7bab0efe604a536617c2a96a919109a95ec14`.
- 1007 dawnych Obiektów i 1000 Jaskiń identyczne bajtowo; w C-0219 zmieniono
  wyłącznie `object_ids`, `updated_at` i `updated_by`.
- 951 testów, Ruff format/lint, walidacja i build PASS; 2123 ostrzeżenia
  walidacji obejmują jawnie nieznane dokładności, bez błędów. Użyto istniejącego
  środowiska przez `uv run --frozen --no-sync --offline`.
- Niezależny odczyt SQLite, CSV, GeoJSON, GPX, Shapefile, Excel Best/Full,
  metadata, statystyk i ZIP SQLite: 136727 porównań, 0 błędów.
- Końcowy SHA, wynik CI oraz odbiór pobranej paczki są podawane w opisie PR #28.
  Po korekcie ID powtórzono
  pełną bramkę i odczyt eksportów z tym samym wynikiem. Niezależny review:
  jedyny finding dotyczący ID naprawiono; pozostałe kontrole bez ustaleń. Bez merge, taga i wydania.

Commit danych `40bf339d60ca281477cb28f94dd43c1d8ffee17b` potwierdzono zdalnie.
[Validate](https://github.com/dlubom/gps-kataster-obiektow-tatr/actions/runs/40001826303)
i [preview](https://github.com/dlubom/gps-kataster-obiektow-tatr/actions/runs/40001826305)
zakończone `completed/success`, wszystkie joby i kroki również. Pobrana
paczka 12521389970: digest ZIP i CRC, 10/10 sum kontrolnych, zgodne
HEAD/base/merge/run; 136753 porównania wszystkich formatów, 0 błędów.
Zdalny blob MTZ-0072 zgodny z lokalnym. Końcowy SHA dokumentacji, jego CI
i odbiór jego paczki wskazuje opis PR; PBI-113 wykonane, zakończyć po nim.

## Korekta opisów i bibliografii — 2026-10-23

Na polecenie użytkownika usunięto odniesienia do PBI/PR i procesu pracy
z opisów 18 nowych Jaskiń i 19 Obiektów. Siedem nazw ma potwierdzenie
w wykazach Jakuba Nowaka/KKTJ 2026.07: Okno przy Źródle, Korytarz pod
Ciemniakiem, Szczelina przy Zbójeckiej Dziurze, Jaskinia Lodowa Ponorowa,
Cynamonowa, Rura w Olejarni i Okno pod Sikawką. Pięć z nich ma również
odczytane oryginalne artykuły. Bibliografia w YAML zawiera 12 referencji,
konkretne strony i pozycje; nie przypisuje listom autorstwa pomiarów.
Dla pozostałych 11 nazw nie ustalono niezależnego źródła mimo rozszerzenia
poszukiwań na dawne wykazy, materiały klubowe, inne publikacje i PIG.
Zachowano nazwy TPN i jawną niepewność, bez dopasowań przez samo sąsiedztwo.
Rozdzielono 5,3 m literatury od 5,5 m TPN dla Szczeliny; deniwelację 2 m
od przewyższenia TPN dla Rury; 11,3 m listy KKTJ od 11,9 m artykułu i TPN
dla Cynamonowej. Nie zmieniono pomiarów, współrzędnych, wysokości ani Best.
Dowody merytoryczne są w opisach/referencjach YAML; końcowy SHA, CI oraz
odczyt paczki korekty wskazuje opis PR #28. Bez merge, taga i wydania.

2026-10-24 użytkownik zaakceptował dalsze uporządkowanie: krótkie opisy
z jednym blokiem Literatura (autor, tytuł, rok, numer i strony), bez URL-i,
GUID i opisu przebiegu sprawdzania. Zachowujemy morfometrię i rozbieżności;
11 wpisów TPN jawnie ma nieustaloną publikację opisową. Techniczne pochodzenie
przenosimy do external_refs Obiektu: istniejąca referencja GLOBALID zachowuje
źródło XY, datę edycji, hash zrzutu i kod WERYF; osobna referencja NMT z ID
pomiaru i jego source_ref zachowuje model, nalot, dokładny odczyt, czas, URL
i hash odpowiedzi. WER_LOK/UWAGI pozostają przy Pomiarze. Odbiór obejmuje
niezmienność wszystkich pozostałych pól pomiarów i pełnego Best oraz pełne
uwagi nowych pomiarów w limicie 254 bajtów DBF. Kod i schema bez zmian.
Lokalny odbiór korekty: 951 testów, Ruff, walidacja (0 błędów) i build PASS;
136918 porównań wszystkich eksportów bez błędów. Notes mają do 159 bajtów
UTF-8; wszystkie 19 nowych uwag Best odczytano z DBF w całości. Zachowane
pozostałe pola 1928 pomiarów, całe Best i 12 referencji bibliograficznych;
1007 starych Obiektów i 1001 Jaskiń identyczne bajtowo z `a709238`.
Końcowy SHA, jego CI i odbiór pobranej paczki wskazuje opis PR #28.
