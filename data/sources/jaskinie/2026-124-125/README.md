# „Jaskinie” 3–4 (124–125), 2026

Porównanie artykułu Filipa Filara „Uzupełnienia inwentarza jaskiń Tatr”
(s. 41–47) z warstwą „Jaskinie” Geoportalu TPN. Numery stron odpowiadają
paginacji czasopisma. Egzemplarz PDF `Jaskienie_J124-125.pdf` ma SHA-256
`c40812557dfc6841de547bbb9ab1a4a78438001818d1ee493639c74c36d6afc1`.
Artykuł opisuje 20 pozycji, w tym jedną Kolebę w Zawracie Kasprowym.
Cytowania w YAML podają stronę i zakres dowodu. Plany i fotografie wskazują
tożsamość lub liczbę otworów.

Odczyt publicznej [warstwy TPN](https://gis.tpn.pl/server/rest/services/Topografia___wektor_MIL1/MapServer/6)
z 20.11.2026 (20:04:59–20:05:08 UTC) przez `scripts/fetch_tpn_data.py`
dał 1035 rekordów jaskiń i ten sam komplet GLOBALID co
[zrzut z 19.10.2026](../../tpn/snapshots/pbi-101-live-20261019/).
SHA-256 pliku z odczytu z 20.11 to
`46e543a5f23b973039ccbd4d58cf27bc87172ea55ef17705308698b571ff017d`.
Zmieniły się dwa rekordy spoza artykułu: Jaskinia w Smreczyńskim Wierchu
(535, PL-0011, przesunięcie 3,93 m) i Jaskinia Maleńka w Smreczyńskim
Wierchu (887, PL-0021, przesunięcie 718,65 m). Oba mają teraz
`WER_LOK=FF 23102026`. Ich nowe pozycje wymagają odrębnego porównania.
Poniższe punkty TPN są identyczne w obu odczytach. Odległości są
geodezyjne na elipsoidzie WGS84.

## Rekordy odroczone w issue #30

| Jaskinia według Filara | Strona | TPN OBJECTID | NAZWA w TPN | Długość [m] | Otwór wg Filara [m n.p.m.] | Grunt NMT w XY TPN [m n.p.m.] |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| Nyża pod Zachodem Pilotów II | 46 | 6404 | Nyża pod Zachodem Pilotów II | 3 | 1513 | 1518,57 |
| Nyża pod Zachodem Pilotów III | 46 | 6403 | Nyża pod Zachodem Pilotów II | 5 | 1433 | 1435,51 |
| Nyża pod Zachodem Pilotów IV | 46 | 7041 | Nyża pod Zachodem Pilotów III | 3 | 1436 | 1437,42 |
| Komora w Kończystej Turni | 43 | 7043 | Komora w Kończystej Turni | 7 | 1168 | 1167,82 |

- **Zachód Pilotów.** Na s. 46 II leży w wyższej kopce i jest opisana obok
  wcześniej udokumentowanej, nienumerowanej Nyży (STR-0028). Długość II
  i dokumentacja z 27.05.2026 zgadzają się z TPN 6404. III i IV są w niższej
  części zachodu. Mają osobne otwory na wspólnym planie, 5 i 3 m długości,
  a punkt TPN 7041 leży 3,25 m na ESE od 6403, zgodnie z ich kolejnością na
  planie. 6404 jest oddalony od 6403 o 106,66 m. Wysokości terenu wspierają
  rozpoznanie dwóch poziomów. Nazwy źródłowe TPN zachowano przy GLOBALID.
- **Komora w Kończystej Turni.** TPN 7043 zgadza się z opisem Komory co do
  nazwy, długości i daty kartowania (6.06.2026). Leży 18,26 m na ENE od
  Okapu. Schron nad Komorą (6406) jest osobnym obiektem na planie i leży
  29,06 m dalej w poziomie. Etykieta pola przy 1168 m w druku mówi
  „nad dnem Doliny Miętusiej”, ale jednostka n.p.m. i osobna wartość
  względna 170 m wskazują wysokość bezwzględną. Dziura nad Zahradziskami
  (6722) ma 5 m długości i kod `FF 21052026` odpowiadający dacie odkrycia
  Komory. Oba punkty dzieli 0,17 m. To mocna przesłanka wcześniejszej
  nazwy lub wcześniejszego zapisu tego samego obiektu. W druku występuje
  wyłącznie Komora, więc powiązanie rekordu 6722 wymaga potwierdzenia.
- **Pozostałe odroczenia.** Artykuł nie dostarcza nowego materiału dla
  Okna w Ciemniaku, Jaskini w Kozim Grzbiecie, Tunelu w Skrajnej
  Giewonckiej Baszcie ani Schronu nad Wielką Równią. [Issue #30](https://github.com/dlubom/gps-kataster-obiektow-tatr/issues/30).

Wysokości gruntu odczytano z warstwy 0 NMT TPN `nmt_05m_mggp_2019`
(piksel 0,5 m, nalot 14–15.10.2019). Dokładność i datum pionowe są
nieznane. URL i sumy odpowiedzi są w rekordach nowych Obiektów.

## Koleba, Gawra w Bobrowcu i współrzędne w druku

- **Koleba w Zawracie Kasprowym** (s. 44). Filar dokumentuje jeden
  oznaczony otwór, 3,6 m długości i 1493 m n.p.m. Punkty TPN 5764
  (BYW-0041) i 5765 (BYW-0043) dzieli 0,61 m. Oba wprowadził `ffilar`
  16.09.2024 w odstępie 13 min 46 s. Razem wspiera to interpretację
  duplikatu. Artykuł nie wiąże żadnego XY z otworem i nie rozstrzyga
  wyboru ID. Scalenie wymaga sposobu zachowania historycznych identyfikatorów
  i pomiarów. Schron w Zawracie Kasprowym to sąsiedni, osobno
  opisany obiekt o długości 4 m. [Issue #8](https://github.com/dlubom/gps-kataster-obiektow-tatr/issues/8),
  [audyt #23](https://github.com/dlubom/gps-kataster-obiektow-tatr/issues/23),
  [historyczne ID #33](https://github.com/dlubom/gps-kataster-obiektow-tatr/issues/33).
- **Gawra w Bobrowcu** (s. 41). Plan i przekrój pokazują dwa połączone
  otwory, na 1225 i 1227 m n.p.m. Punkt do dojścia w druku ma jedną parę
  XY i leży 0,27 m od TPN 7361 (CHZ-0034). Brakuje przypisania tej pary
  do konkretnego otworu oraz współrzędnych drugiego. Do wyznaczenia
  drugiego otworu potrzebne jest dowiązanie planu albo pomiar terenowy.
- **Pozostałe wydrukowane pary XY** służą w tekście do dojścia.
  Dla Kalackiej Nyży V (s. 45) różnica od TPN 6087 wynosi 0,04 m po
  zamianie DMS na stopnie dziesiętne, dla Gawry w Sarniej Skale (s. 47)
  3,19 m od 6401, a dla Schronu pod Gawrą w Bobrowcu (s. 41) 5,25 m od
  7377. Brak podanej metody i dokładności nie pozwala traktować ich
  jako niezależnej weryfikacji TPN.
- **Wysranki** (s. 42). Autor opisuje trzy oddzielne pozycje. Bliskie
  na mapie Gawra (4801) i Nyża (7362) mają różne otwory: Gawra
  powyżej dna na 1218 m n.p.m., Nyża przy dnie na 1196 m n.p.m.
  Ich punkty TPN dzieli w poziomie 9,87 m. TPN 5767 to osobna Dziura
  we Wysrankach, której otwór Filar podaje na 1087 m n.p.m.

## Pozostała bibliografia tatrzańska

Nowak i Gawęska (s. 48–51) dokumentują 115 m Korytarza Pawełka po
kartowaniu w maju 2026 r. i podają 7445 m jako nową długość Systemu
Ptasiej. Ujęte w ich bibliografii prace Antkiewicza (1999) oraz
Pawłowskiego i Żarskiego (1982) mają w katalogu odsyłacze pośrednie
z zaznaczeniem, gdzie je przywołano. Szołtysik (s. 59–61) opisuje
akcję w Jaskini Czarnej z 1981 r.
