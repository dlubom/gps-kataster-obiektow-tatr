# PBI-110: wywierzyska w lokalnym zrzucie TPN — projekt do akceptacji

Stan: 2026-10-23. To projekt, nie wykonana implementacja.
Aktywny PR: [#18](https://github.com/dlubom/gps-kataster-obiektow-tatr/pull/18),
gałąź `codex/tpn-data-download`, HEAD
`27d65697d95a79b184024a9b9c258eba43d7a88e`, po fetch main
`4924415de3cd5c3bd9e1fe2c541f42e023e4a21a`.

## Uzgodniony cel

Użytkownik polecił dodać wywierzyska bez zwykłych źródeł, do istniejącego
PR #18. Następnie zatwierdził wszystkie trzy decyzje wywiadu:

1. Uwzględnić wywierzyska udokumentowane również poza turystycznym API TPN,
   pod warunkiem udokumentowania klasyfikacji i lokalizacji.
2. Uwzględnić wypływy okresowe i jawne związki z istniejącymi jaskiniami.
3. Ponory pozostawić osobnym zadaniem. Ich rozpoznanie w tej sesji nie
   upoważnia do rozszerzenia wyniku o ponory.

To nadal lokalny odczyt źródeł i widoki JSON. Bez importu do YAML,
zmiany kategorii istniejących obiektów, wyboru best, merge, taga i wydania.
Zrzuty, materiały źródłowe i wyniki NMT pozostają lokalne, poza Git.

## Rozważone podejścia

- Tylko trzy rekordy turystycznego POI: prosty filtr API, lecz pomija
  udokumentowane inne wywierzyska i wypływy okresowe.
- API oraz mały, jawny manifest udokumentowanych uzupełnień: kierunek
  wynikający z odpowiedzi użytkownika. Wymaga osobnego pochodzenia
  klasyfikacji i współrzędnych, bez pozorowania kompletnego inwentarza.
- Wszystkie 2792 źródła atlasowe lub wybór według wydajności/bliskości:
  nie spełnia polecenia „bez źródeł” i nie daje klasyfikacji wywierzysk.

## Proponowany pierwszy zestaw punktów

| Punkt | Tożsamość lokalizacji | Podstawa klasyfikacji | Stan rozpoznania |
|---|---|---|---|
| Wywierzysko Olczyskie | POI TPN GLOBALID `{BE5AEF57-6EF5-4449-A0C5-B6616C1EDFAE}` | `PUNKT=wywierzysko` | Gotowa podstawa do implementacji |
| Wywierzysko Chochołowskie | POI TPN GLOBALID `{AD3839C1-65A1-4D19-9A57-D9EB2663F252}` | `PUNKT=wywierzysko` | Gotowa podstawa do implementacji |
| Lodowe Źródło | POI TPN GLOBALID `{AB1C96C9-D0BF-42ED-B1DF-C9F17E030586}` | `PUNKT=wywierzysko`, mimo nazwy „Źródło” | Gotowa podstawa do implementacji |
| Wywierzysko Goryczkowe | PIG, arkusz 1060 PPW-WJ, tabela 1.4, punkt 29 | Nazwa w tabeli PIG i opis wywierzyska TPN | Współrzędne WGS-84 w tekście źródła; odbiór oryginalnego PDF pozostaje do wykonania |
| Kasprowa Niżnia — okresowy wypływ z otworu | TPN jaskinie GLOBALID `{87AEB6FC-4A62-4EF4-A1F2-255E6E33C54A}`, PIG 1227, T.D-16.03 | PIG opisuje wypływ otworem podczas ulew/roztopów; TPN nazywa okresowym wywierzyskiem | Udokumentowany otwór; PIG nie wymienia innych wejść. Połączenie przez numer inwentarzowy, nie bliskość |

To zestaw częściowy, nie pełna lista wywierzysk Tatr. Nie utrwalać liczby
trzech rekordów POI jako limitu przyszłych odpowiedzi API.

## Źródła i niepewności

**POI TPN:** [warstwa 1 — Atrakcje turystyczne](https://gis.tpn.pl/server/rest/services/POI/MapServer/1?f=pjson).
Dokładny filtr `PUNKT = 'wywierzysko'` zwrócił trzy rekordy. Każdy ma
`INFO=Wydajne źródło krasowe`. Wszystkie pola dat utworzenia/edycji są null;
nie zastępujemy ich datą obserwacji lub datą pomiaru.

**PIG, Tatry Zachodnie 1060, PPW-WJ, 2007:**
[tabela 1.4, strona 23 PDF, indeks 22](https://bazadata.pgi.gov.pl/data/hydro/mhp/ppw/wj/txt/mhpppwwj1060objasnienia.pdf).
Punkt 29 „wywierzysko Goryczkowe”: φ `49:15:15,5`, λ `19:58:21,0`.
Przypis potwierdza WGS-84. Zachować oryginalny zapis DMS i numer wiersza;
konwersja do stopni dziesiętnych nie podnosi dokładności. Data 11.07.2007
dotyczy analizy chemicznej, nie udokumentowanej daty pomiaru GPS.
Dokładność GPS nieznana. Odczytano tekst publikacji przez web; bezpośrednie
pobranie zwróciło HTML ochrony serwisu. Nie ma jeszcze prawidłowych bajtów
PDF, SHA-256 ani wizualnego odbioru tabeli. Nie przedstawiać hasha HTML
jako hasha publikacji. Odbiór źródła to bramka przed osadzeniem odpisu
punktu w implementacji; sam projekt jej nie spełnia.

[Barczyk i in. 2025, DOI 10.24425/agp.2024.152671, strona 4 PDF](https://journals.pan.pl/Content/136355/PDF/e49%20Barczyk%20et%20al.pdf)
niezależnie podaje nazwę i punkt Goryczkowego `49°15′15″N, 19°58′21″E`.
Publikacja jest CC BY, ale przy tych współrzędnych nie deklaruje datum ani
dokładności. Nie zastępować nią bez wyjaśnienia punktu WGS-84 z tabeli PIG.

**Kasprowa Niżnia:** [PIG 1227](https://jaskiniepolski.pgi.gov.pl/Details/Information/1227),
[opis TPN „Wody”](https://tpn.gov.pl/wody), istniejąca warstwa jaskiń TPN.
W punkcie TPN `lat=49.25413415756443`, `lon=19.978480544690157`.
Do nowego widoku przypisujemy funkcję hydrologiczną, nie zmieniamy
źródłowego `GENEZA=jaskinia`, rekordu YAML ani jego kategorii.

### Bystrej — decyzja o sposobie przedstawienia lokalizacji

PIG, ta sama tabela 1.4, punkt 28 „wywierzysko Bystrej”:
φ `49:15:27,2`, λ `19:57:59,5`, WGS-84. Nazwa nie wskazuje
jednoznacznie Bystrej Górnego albo Dolnego.

[Raport TPN, tabela 1, strona 6 PDF](https://nauka.tpn.pl/storage/images/Zasoby_wod_2012_2013.pdf)
podaje posterunek „Wywierzysko Bystrej”:
`49°15,313′N, 19°58,102′E`. Tabela dotyczy posterunków hydrologicznych,
nie identyfikacji dokładnych wypływów; nie znaleziono deklaracji datum.
Rozbieżność obu zapisów geograficznych wynosi około 300 m.
PDF TPN poprawnie pobrany i tabela obejrzana; SHA-256:
`c373374ddaf79716ffa1247b1f123fa77ef9a4c531bb7bfb592b5196fb9a87c6`.

**Propozycja:** zachować oba wskazania i tę rozbieżność w lokalnych dowodach,
ale nie publikować ich w płaskiej liście jako dwóch rozpoznanych wypływów.
Nie nadawać nazw Dolne/Górne przez bliskość ani nie wybierać „lepszego” XY.
Sposób pokazania Bystrej wymaga odpowiedzi użytkownika po tym rozpoznaniu.

Pozostają także kandydaci okresowi wymagający rozpoznania wejść:
[Jaskinia Bystrej — dolny otwór, PIG 1228](https://jaskiniepolski.pgi.gov.pl/Details/Information/1228)
oraz [Dudnica — dwa otwory, PIG 1231](https://jaskiniepolski.pgi.gov.pl/Details/Information/1231).
Nie tworzymy współrzędnych drugiego otworu przez przesunięcie punktu.

## Proponowana zmiana programu

- Zachować trzy pełne, niezależne warstwy PBI-108. Dodać filtrowany odczyt
  POI z kontrolą liczby i kompletnego zbioru ID przed/po oraz niezależnym
  sprawdzeniem `PUNKT` w pobranych rekordach. Zmiana klasyfikacji w trakcie
  pobrania ma blokować wynik.
- Mały, jawnie recenzowany manifest uzupełnień przechowuje selektory
  GLOBALID/NR_INWENT, referencje dokumentów i odpis punktu PIG po odbiorze
  źródła. To autorska konfiguracja z pochodzeniem, nie pełny zrzut usługi.
  Pobrane PDF-y, HTML/API i wyniki są wyłącznie lokalne.
- Surowy wynik zachowuje osobno dane usług i dowody klasyfikacji z
  literatury. Nie udaje jednej surowej warstwy ArcGIS dla różnych źródeł.
  Nowy format zrzutu ma osobną wersję; dotychczasowy format 1 jest nadal
  obsługiwany przez `--input`, bez dopisywania nieistniejących danych.
- Widoki `simple.json` i `simple-nmt.json` dostają listę `wywierzyska`.
  Rekord zawiera nazwę, reżim (`okresowe` lub jawny brak ustalenia),
  identyfikator i rolę punktu źródłowego, współrzędne, dane źródłowe,
  pochodzenie klasyfikacji i lokalizacji oraz związek z jaskinią, jeśli znany.
  Nie wyprowadzamy reżimu wody z turystycznego pola `CZYNNE`.
- NMT w dokładnym źródłowym XY, jako wysokość gruntu. Każdy odczyt i NO_DATA
  powiązany z jednoznacznym identyfikatorem źródła; numer OBJECTID sam nie
  identyfikuje rekordu między warstwami.
- Nie pobierać 2792 zwykłych źródeł w celu domyślnej klasyfikacji ani
  dopasowywania po odległości. Nie wyciągać ponorów z warstwy lejów.

## Weryfikacja i dalszy krok

Po akceptacji projektu powstanie właściwy plan implementacji PBI-110:
testy przed kodem, odczyt źródeł, implementacja, regresja starego zrzutu,
pełna bramka i eksporty według runbooka, celowane mutacje selekcji,
niezależny review, commit/push do tego PR, CI dokładnego SHA i odczyt paczki.
Testy mają obejmować zwykłe źródło i inny POI jako kontrprzykłady, zmianę
typu rekordu, brak oczekiwanego GLOBALID, błędną konwersję DMS/osi,
nieznane daty/dokładność, niejednoznaczny wypływ i identyfikację dowodu NMT.

Na tym etapie nie zmieniono kodu i nie wykonano jego testów ani nowego
zrzutu. Projekt wymaga akceptacji oraz rozstrzygnięcia Bystrej przed
przygotowaniem planu wykonania.

Sprawdzenie dokumentacji projektu: `git diff --check`, odczyt wszystkich
70 lokalnych odnośników w trzech zmienianych dokumentach oraz
`uv run --frozen --no-sync --offline pytest tests/test_operational_docs.py
tests/test_release_docs.py -q` — 5 istniejących testów dokumentacji przeszło.
Nie są to testy przyszłej funkcji ani dowód odbioru PDF PIG.
