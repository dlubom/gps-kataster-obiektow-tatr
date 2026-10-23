# PBI-113: nowe obiekty z lokalnego zrzutu TPN — projekt do akceptacji

Stan: 2026-10-23. Zakres i rozstrzygnięcia uzgodniono w wywiadzie;
ten zapis projektu wymaga akceptacji przed realizacją. Katalog pozostaje
bez zmian. Baza: `caf7bae69b28eb037810215889cb87f763b2c6bd`.

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
mają status `ok`. Numery ID przydzielić przy realizacji według obecnych zasad,
bez ponownego użycia dawnych ID lub zmiany istniejących.

| OBJECTID | Obiekt | Prefix | Jaskinia |
| --- | --- | --- | --- |
| 3846 | Smocza Jama — otwór N | KSW | istniejąca C-0219 |
| 6401 | Gawra w Sarniej Skale | STR | nowa |
| 6402 | Okno przy Źródle | BIA | nowa |
| 6405 | Nyża pod Szarą Turnią I | STR | nowa |
| 6406 | Schron nad Komorą w Kończystej Turni | MTW | nowa |
| 6407 | Nyża za Jałowcem | MTW | nowa |
| 7042 | Nyża pod Szarą Turnią II | STR | nowa |
| 7044 + 6408 | Korytarz pod Ciemniakiem | MTZ | jedna nowa |
| 7045 | Szczelina przy Zbójeckiej Dziurze | CHZ | nowa |
| 7361 | Gawra w Bobrowcu | CHZ | nowa |
| 7362 | Nyża we Wysrankach | KSW | nowa |
| 7363 | Nyża pod Szarą Turnią III | STR | nowa |
| 7366 | Jaskinia Lodowa Ponorowa | MTZ | nowa |
| 7367 | Jaskinia Cynamonowa | CHZ | nowa |
| 7368 | Rura w Olejarni | CHZ | nowa |
| 7377 | Schron pod Gawrą w Bobrowcu | CHZ | nowa |
| 7378 | Okno pod Sikawką | KSW | nowa |
| 7379 | Nyża pod Szarą Turnią IV | STR | nowa |
| 7682 | Gawra w Grześkówkach | DZI | nowa |

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
  Notes wskazują model, URL i czas odczytu oraz grunt; wysokość otworu
  w ścianie nie jest tym potwierdzona.
- Zachować całe istniejące dane i ręczne Best. Jedyną modyfikacją istniejącej
  encji będzie członkostwo nowego otworu i audyt aktualizacji C-0219.
- Poza zakresem: leje, pozostała warstwa sztolni/kopalń, wywierzyska,
  nowy importer/synchronizacja, naprawy istniejących par i aktualizacja
  issue #8/#23/#24. Zrzuty i źródłowe PDF-y pozostają lokalne.
  Merge, tag i release wymagają odrębnego polecenia.

## Realizacja i odbiór po akceptacji projektu

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
