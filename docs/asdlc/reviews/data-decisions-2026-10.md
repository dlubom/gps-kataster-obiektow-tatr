# Decyzje danych — PBI-083, 2026-10-15

Baza: `d86b89fa886bb0bec9f569bc6a5331384bddf0bc`. Zakres: R8 oraz historyczne ostrzeżenia odległości i wspólne best. Ocena dotyczy lokalnych, zachowanych źródeł; bez nowego pobrania i bez potwierdzenia terenowego.

Pełne ID, GLOBALID/PIG ID, wiersze, wartości źródłowe, współrzędne, statusy, best i SHA-256 znajdują się w [zapisie JSON](data-decisions-2026-10.json). [Manifest zmian](../verification/PBI-083-manifest.json) wyznacza jedyne dozwolone zmiany finalnych danych. Wiersz oznacza rekord danych od 1, bez nagłówka; dla JSONL podano fizyczną linię.

## Kategorie i decyzje

- **STR-0024 / C-0903**: TPN CSV row **273**, GLOBALID `{A5C7088E-A2FE-4898-AE2E-B0A9B420B17D}`, puste NAZWA/NR_INWENT, `GENEZA=sztolnia`; UWAGI wskazują zasypanie z widocznym belkowaniem stropu. Nazwa robocza BEZ_NAZWY_001 nie jest dowodem typu. Korygujemy `jaskinia_otwor` → **`sztolnia`**, dopisujemy uzasadnienie i audit. ID, cave_id, pomiar, best oraz status pozostają jak w bazie. Nie jest to potwierdzenie obecnego położenia ani dostępności.

- **CHZ-0011 / C-0361**: TPN row **530**, GLOBALID `{24948383-1D8D-4677-B260-CF6AB8FB68FA}`, `GENEZA=jaskinia/sztolnia`, nazwa Wojtkowa Szpara / sztolnia nr 7, UWAGI odsyłają do Jach (2002). PIG CSV row **361**, ID **1042**, ten sam numer T.C-05.06; lokalny JSONL linia **370** opisuje naturalną jaskinię zaczynającą się 6–8 m w sztolni. Oba znaczenia mają podstawę. **Zachowujemy `jaskinia_otwor`, kategoria nierozstrzygnięta**: nie ma dowodu, czy oba punkty i istniejący Obiekt oznaczają wylot sztolni, wejście do naturalnej próżni czy pozycję katalogową całego układu. Potrzebny jest plan sztolni nr 7 i jaskini, z odniesieniem obu punktów do konkretnego otworu; potem decyzja operatora, ewentualny nowy pomiar terenowy. Dopisujemy obie genezy i niepewność do notes/auditu, bez zmiany kategorii lub tworzenia drugiej encji. Różnica m-001/m-002 wynosi 735.46 m; objęta również tabelą poniżej.

Nowy staging traktuje mieszaną genezę jako jaskinia_otwor wyłącznie roboczo, zachowuje pełne GENEZA i wymóg review kategorii w notes; nazwa ze słowem sztolnia tego nie rozstrzyga. Istniejące dopasowane obiekty zachowują kategorię.

## Ponowny pomiar katalogu

Aktualnie: **1009 obiektów, 1003 jaskinie, 1875 pomiarów, 0 relacji**; **0 błędów / 2066 ostrzeżeń**, w tym **72 ostrzeżenia odległości w 72 obiektach** i **11 grup / 23 obiekty o wspólnym best**. Liczby i członkowie grup zgodni z historycznym review. Wszystkie pary odległości to PIG–TPN; każda referencja prowadzi do jednego rekordu CSV, a cache PL-1992 odpowiada źródłu (różnica <0,01 m). Nie wykryto tu błędu przepisywania współrzędnych do YAML. Nie rozstrzyga to trafności danych źródłowych.

Odległość: euklidesowa w EPSG:2180, po reprojekcji WGS84, próg **>100 m**, tak jak `_validate_measurement_distances`. Grupy: `round(lat,7), round(lon,7)` wybranego best. Wszystkie 11 grup jest też identycznych bez zaokrąglenia. Najlepszy pomiar według priorytetu źródeł nie jest równoznaczny z pomiarem zweryfikowanym.

## Dwa największe odstępstwa

### PL-0019 — Schron w Skale Kmietowicza II

PIG **1041 / T.C-05.05**, CSV row **328**, JSONL linia **369**: m-001 = 49.23512618, 19.8202703, wysokość 994 m, stan 2014. TPN row **889**, GLOBALID `{802BEAB0-6B83-45CA-B739-5547857CD0A0}`: m-002/best = 49.25731616101058, 19.815499973336546, 986.0514 m, aktualność rekordu 2022-05-25, WER_LOK 13-02-2020 FF ortofotomapa. Odległość **2490,53 m**. Oba pomiary są nieweryfikowane i bez dokładności poziomej. Surowy JSONL PIG ma również południową pozycję około 49.235125, 19.82026944; zgodność CSV z JSONL wyklucza przypisanie rozbieżności samemu importerowi. Opis PIG prowadzi od Hucisk do Niżnej Bramy Chochołowskiej, a następnie około 45 m od Schronu I w głąb doliny. WER_LOK to wskazanie pracy na ortofotomapie, bez udokumentowanej dokładności lub niezależnego pomiaru. **Nierozstrzygnięte**: potrzebna lokalizacja schronów I/II na georeferencjonowanym planie i kontrola GNSS schronu II; nazwa/numer i opis dojścia nie wystarczają do wybrania poprawnej pary współrzędnych. Zachowujemy oba punkty, best i trwały prefix PL.

### MLZ-0045 — Komora w Jatkach

PIG **1015 / T.B-12.08**, CSV row **469**, JSONL linia **352**: m-001 = 49.24851941, 19.92237225, 1190 m, stan 2010. TPN row **778**, GLOBALID `{E5496BE7-4118-4DF8-A370-BC677168CEFB}`: m-002/best = 49.26559296201374, 19.922434472506332, 1311.048764 m, aktualność rekordu 2022-05-25, WER_LOK 22-01-2020 FF ortofotomapa. Odległość **1897,61 m**, głównie północ–południe; różnica wysokości około 121 m. JSONL PIG powtarza pozycję około 49.24851944, 19.92237222, a historia dokumentacji wspomina korektę współrzędnych przez F. Filara w lipcu 2018 mimo pola stanu 2010. Daty te nie dowodzą, jaki pomiar jest poprawny ani kiedy faktycznie powstał. Opis dojścia prowadzi od Łysanek przez Jatki obok T.B-12.06 i T.B-12.07 do niskiego zasłoniętego otworu. **Nierozstrzygnięte**: potrzebny georeferencjonowany plan obejmujący te trzy otwory, identyfikacja komory i niezależny GNSS; porównać też wysokości i ich datum. Nie odrzucamy automatycznie żadnego pomiaru.

## Wszystkie ostrzeżenia odległości

Dla każdego wpisu rozstrzygnięcie **L**: zachować historię, best i status; lokalizacja nierozstrzygnięta. Brakująca informacja to niezależny GNSS wskazanego nazwą/ID otworu oraz przypisanie obu rekordów do tego samego otworu na planie/inwentarzu; bez znanej dokładności nie można wybrać poprawnego punktu z samej odległości. Każdy rekord JSON ma własny `missing_evidence`, oba pomiary z pełnymi źródłami, GLOBALID i hashem. Tabela podaje wiersze CSV i klucze źródeł; hashe całych źródeł znajdują się poniżej.

| Obiekt / nazwa | Para | m | Dowód PIG (row, ID) | Dowód TPN (row, GLOBALID) | Decyzja / brak |
|---|---|---:|---|---|---|
| PL-0019 / Schron w Skale Kmietowicza II | m-001 / m-002 | 2490.53 | 328, 1041 | 889, `{802BEAB0-6B83-45CA-B739-5547857CD0A0}` | L — GNSS i plan tego otworu |
| MLZ-0045 / Komora w Jatkach | m-001 / m-002 | 1897.61 | 469, 1015 | 778, `{E5496BE7-4118-4DF8-A370-BC677168CEFB}` | L — GNSS i plan tego otworu |
| BYW-0010 / Gawra nad Jaworzynką | m-001 / m-002 | 788.84 | 213, 4170 | 387, `{318DEE0B-B8DE-416D-8637-B93F93F7CAEE}` | L — GNSS i plan tego otworu |
| CHZ-0011 / Wojtkowa Szpara | m-001 / m-002 | 735.46 | 361, 1042 | 530, `{24948383-1D8D-4677-B260-CF6AB8FB68FA}` | L — GNSS i plan tego otworu |
| BYW-0016 / Gawra między Gawrami | m-001 / m-002 | 643.57 | 372, 4171 | 776, `{88AB16CE-FB30-4055-AD7A-CAF37AC79511}` | L — GNSS i plan tego otworu |
| PL-0010 / Głowoniowa Nyża | m-001 / m-002 | 536.92 | 150, 4436 | 126, `{8E29E068-8568-4D5A-83F4-BFEBE59FC95A}` | L — GNSS i plan tego otworu |
| BYZ-0020 / Jaskinia w Cycku | m-001 / m-002 | 325.57 | 444, 1031 | 783, `{15727EBA-3547-418B-A741-4EEF7303A0AD}` | L — GNSS i plan tego otworu |
| BYW-0020 / Jaworzyńska Nyża pod Iglicą | m-001 / m-002 | 315.58 | 452, 1271 | 591, `{ECF8FC2C-82F9-44FB-AEC9-D36EA94249E6}` | L — GNSS i plan tego otworu |
| MLZ-0053 / Kominek obok Ciasnej w Groniu | m-001 / m-002 | 302.88 | 534, 1552 | 774, `{4CFB2CA8-A771-4734-920B-C7F7AC248655}` | L — GNSS i plan tego otworu |
| KSZ-0006 / Okno Zbójnickie Wyżnie | m-001 / m-002 | 302.53 | 54, 1098 | 624, `{023B75EE-038D-4E53-8AC3-CCD673A1BD18}` | L — GNSS i plan tego otworu |
| CHW-0002 / Schron w Opalonem I | m-001 / m-002 | 282.46 | 21, 1080 | 533, `{95CB0263-87AD-4D91-A3DC-97C59AD9EB84}` | L — GNSS i plan tego otworu |
| BYZ-0021 / Szczelina w Giewoncie II | m-001 / m-002 | 257.74 | 455, 1218 | 473, `{57712B8C-BD83-47E5-ACF1-841E4A9A9A36}` | L — GNSS i plan tego otworu |
| BYZ-0014 / Szczelina w Giewoncie I | m-001 / m-002 | 255.22 | 323, 1217 | 735, `{EFB77251-48CB-43CC-B6BC-9D1D9F6B8F3F}` | L — GNSS i plan tego otworu |
| BYZ-0016 / Jaskinia Zawaliskowa w Długim Giewoncie | m-001 / m-002 | 248.40 | 360, 1215 | 932, `{0E35D5B3-4CA4-45ED-B3FA-36A966F11037}` | L — GNSS i plan tego otworu |
| CHZ-0023 / Schron w Wielkich Koryciskach | m-001 / m-002 | 242.83 | 671, 959 | 848, `{6CEBFB02-ACA8-45A8-B8C3-AA2D76FC9791}` | L — GNSS i plan tego otworu |
| MLZ-0043 / Szczelina nad Dziurą w Wantach I | m-001 / m-002 | 210.44 | 434, 1608 | 502, `{316F78E8-7D52-448F-BE57-0EB91BA51006}` | L — GNSS i plan tego otworu |
| BYW-0036 / Schron nad Przełączką | m-001 / m-002 | 207.85 | 859, 1273 | 746, `{781BAA2F-37F9-41B5-B9E8-CA37F560E463}` | L — GNSS i plan tego otworu |
| BYW-0032 / Szczelina w Zawraciku Kasprowym I | m-001 / m-002 | 201.19 | 767, 1250 | 694, `{3D779DB5-2C0A-4ACA-838F-837CB10B92C7}` | L — GNSS i plan tego otworu |
| BYW-0014 / Kasprowe Schronisko | m-001 / m-002 | 194.54 | 320, 1251 | 550, `{45FE6018-D06F-4F50-9900-5E4B63031ACD}` | L — GNSS i plan tego otworu |
| BYZ-0026 / Grota u podnóża Myślenickich Turni | m-001 / m-002 | 191.62 | 561, 1235 | 57, `{81F8A0BB-6D7F-4E11-A86C-AD579575AC13}` | L — GNSS i plan tego otworu |
| MTW-0018 / Jaskinia Barania | m-001 / m-002 | 183.55 | 170, 1497 | 942, `{1ED1AF27-2694-4ADB-8BCE-67CBC4981033}` | L — GNSS i plan tego otworu |
| BYW-0015 / Szczelina w Zawraciku Kasprowym III | m-001 / m-002 | 178.73 | 357, 1269 | 585, `{F44332A1-5638-4C3F-A285-860862AB6BC6}` | L — GNSS i plan tego otworu |
| BYW-0005 / Szczelina w Zawraciku Kasprowym II | m-001 / m-002 | 178.51 | 115, 1252 | 728, `{CC4B47CE-2FAC-48A4-845F-72491B53A27A}` | L — GNSS i plan tego otworu |
| BYW-0004 / Jaskinia Kasprowa Średnia | m-001 / m-002 | 175.26 | 108, 1247 | 655, `{D35C15CC-113C-4509-BE22-CD99939F2FAE}` | L — GNSS i plan tego otworu |
| BYW-0034 / Schronisko Jasne w Czubie Jaworzyńskiej | m-001 / m-002 | 171.31 | 797, 1261 | 536, `{6C75E22A-DCDD-44E1-819C-BDCC781AE65F}` | L — GNSS i plan tego otworu |
| BYW-0027 / Szczelina nad Jaskinią Magurską | m-001 / m-002 | 167.64 | 655, 1281 | 663, `{9A80C2BE-49EB-41A5-845A-122C52EED625}` | L — GNSS i plan tego otworu |
| BYW-0001 / Nyża pod Jaskinią Magurską III | m-001 / m-002 | 165.74 | 82, 1277 | 594, `{A69A252F-1E90-49F5-AF5D-221E62C9650C}` | L — GNSS i plan tego otworu |
| BYW-0026 / Dziura pod Nosalem | m-001 / m-002 | 165.34 | 637, 953 | 731, `{74D4DC1C-397E-4AB7-9F58-1F8AFBD78271}` | L — GNSS i plan tego otworu |
| BYZ-0017 / Myślenicka Nyża | m-001 / m-002 | 163.42 | 380, 1236 | 364, `{73B28881-E49E-41F4-BDD3-10B54D09F3F1}` | L — GNSS i plan tego otworu |
| MLZ-0070 / Jaskinia pod Progiem | m-001 / m-002 | 161.69 | 668, 1597 | 991, `{397888B8-8D89-4FE6-8539-3CC5D04C0220}` | L — GNSS i plan tego otworu |
| BYW-0011 / Szczelina nad Partyzancką | m-001 / m-002 | 159.75 | 243, 1257 | 943, `{90E56D14-17C1-4683-BBA1-7DE28EC4CC4F}` | L — GNSS i plan tego otworu |
| BYW-0009 / Nisza w Zawraciku Kasprowym | m-001 / m-002 | 159.28 | 204, 1268 | 191, `{93989CC1-336D-40D9-BBBF-AD98B9269993}` | L — GNSS i plan tego otworu |
| BYZ-0023 / Schron z Nietoperzami | m-001 / m-002 | 158.18 | 480, 1237 | 696, `{61615B89-B2AE-4F71-9945-2677002204DC}` | L — GNSS i plan tego otworu |
| BYZ-0013 / Kalacka Nyża I | m-001 / m-002 | 157.52 | 266, 1060 | 583, `{59AA9DB8-B93D-49A4-83EF-1CD0D2383C46}` | L — GNSS i plan tego otworu |
| BYW-0031 / Szczelina w Zawraciku Kasprowym IV | m-001 / m-002 | 156.30 | 757, 1270 | 665, `{D7A7582A-8BFE-456B-93A5-91F46EA22DD2}` | L — GNSS i plan tego otworu |
| BYZ-0038 / Myślenicki Korytarzyk | m-001 / m-002 | 155.75 | 831, 1238 | 686, `{1CB5F8E8-4DAE-4D86-A268-2901A67D921A}` | L — GNSS i plan tego otworu |
| BYZ-0003 / Myślenicka Dziura | m-001 / m-002 | 154.07 | 43, 1226 | 8, `{6CE25FC0-E936-4473-BF8C-374DDAD70FF8}` | L — GNSS i plan tego otworu |
| CHZ-0020 / Schron przy Szczelinie | m-001 / m-002 | 152.90 | 542, 1074 | 936, `{64AED179-2FC5-4503-9D2A-BF122CD47630}` | L — GNSS i plan tego otworu |
| BYZ-0027 / Kalacka Szczelina | m-001 / m-002 | 152.74 | 563, 1061 | 388, `{F2004E8B-B58E-44E8-BDC7-9D185AA31D19}` | L — GNSS i plan tego otworu |
| BYZ-0028 / Szczelina pod Frapującą Nyżą | m-001 / m-002 | 152.73 | 569, 1059 | 618, `{64EB9D99-D069-478B-BF1F-A9613085F1A2}` | L — GNSS i plan tego otworu |
| BYZ-0025 / Frapująca Nyża | m-001 / m-002 | 152.64 | 525, 1058 | 782, `{77B2EB4E-1963-4758-8294-4C47B7C638FD}` | L — GNSS i plan tego otworu |
| BYW-0017 / Dziura pod Kamieniem | m-001 / m-002 | 151.93 | 375, 1267 | 337, `{EDA32AD0-0DD5-4DB8-BACF-F4C127D8883A}` | L — GNSS i plan tego otworu |
| BYZ-0001 / Szczelina w Myślenickich Turniach Dolna | m-001 / m-002 | 148.99 | 11, 1240 | 412, `{351936C0-2A75-4EE7-AD6D-5031D6931D34}` | L — GNSS i plan tego otworu |
| BYZ-0009 / Szczelina w Myślenickich Turniach Górna | m-001 / m-002 | 147.85 | 215, 1241 | 360, `{EC914406-0376-4696-899F-75CC68D7BE2A}` | L — GNSS i plan tego otworu |
| BYZ-0036 / Mokra Koleba | m-001 / m-002 | 145.36 | 795, 1057 | 909, `{E39722F0-2730-4CB2-B2AB-D7130A65FDE1}` | L — GNSS i plan tego otworu |
| BYW-0006 / Jaskinia pod Limbą | m-001 / m-002 | 143.26 | 156, 1253 | 495, `{F630955B-9B96-4056-A007-8EDC623794B7}` | L — GNSS i plan tego otworu |
| BYZ-0012 / Myślenicka Szczelina | m-001 / m-002 | 138.60 | 257, 1233 | 249, `{D10D1340-938D-43B2-8E7F-19D6110CA747}` | L — GNSS i plan tego otworu |
| BYZ-0010 / Dziura w Szczerbie II | m-001 / m-002 | 134.78 | 220, 1201 | 214, `{4B115F06-4FE7-471D-8061-6145E56581FC}` | L — GNSS i plan tego otworu |
| BYZ-0022 / Dziura w Szczerbie I | m-001 / m-002 | 131.85 | 457, 1202 | 220, `{8BD895DB-7088-4012-9A28-6872C4A280C9}` | L — GNSS i plan tego otworu |
| MTW-0013 / Jaskinia Kozia | m-001 / m-002 | 129.47 | 135, 1478 | 308, `{AF271E37-C205-48CA-B546-B3F0663ED2F4}` | L — GNSS i plan tego otworu |
| BYZ-0040 / Nyża pod Myślenicką Szczeliną | m-001 / m-002 | 128.53 | 850, 1234 | 373, `{1143D549-9DE7-48EB-8D5C-DECB05CEC4DF}` | L — GNSS i plan tego otworu |
| MTZ-0018 / Jaskinia Marmurowa | m-001 / m-002 | 128.07 | 184, 1472 | 285, `{C5BCC87D-2F7E-42B5-8433-F72C556B8618}` | L — GNSS i plan tego otworu |
| BYZ-0005 / Kalacki Tunelik | m-001 / m-002 | 124.94 | 49, 1056 | 410, `{423DBA21-4484-4C50-A2DA-7028D19067ED}` | L — GNSS i plan tego otworu |
| BYZ-0039 / Kozi Korytarz | m-001 / m-002 | 123.19 | 834, 1221 | 781, `{BD2B5E3B-74AC-4D67-BEA5-1042034D9453}` | L — GNSS i plan tego otworu |
| BYZ-0018 / Studnia w Giewoncie | m-001 / m-002 | 121.70 | 410, 1220 | 769, `{FB4A2A89-B8BF-4B13-A919-9EA7275B42B0}` | L — GNSS i plan tego otworu |
| MLZ-0042 / Szczelina w Pośredniej Turni | m-001 / m-002 | 119.64 | 427, 1593 | 931, `{54C9E6C1-5224-4113-B866-B3EC8D19E0A5}` | L — GNSS i plan tego otworu |
| BYW-0019 / Jaskinia pod Szczytem | m-001 / m-002 | 119.40 | 442, 1071 | 996, `{7D9BC151-841B-4688-8811-967984B4AABD}` | L — GNSS i plan tego otworu |
| BYZ-0007 / Kalacka Nyża II | m-001 / m-002 | 117.78 | 88, 1062 | 809, `{F10D0469-BF4E-4F09-9619-17E434E6D204}` | L — GNSS i plan tego otworu |
| BYZ-0041 / Dziura za Głazami | m-001 / m-002 | 115.55 | 860, 1052 | 997, `{680A5D85-75B2-482B-9A94-D904A39945B6}` | L — GNSS i plan tego otworu |
| MTZ-0025 / Jaskinia Niedźwiedzia Niżnia | m-001 / m-002 | 113.41 | 316, 1189 | 121, `{DB1988C1-E24D-4770-9EB1-A3318C513815}` | L — GNSS i plan tego otworu |
| BYW-0024 / Dziura z Gawrą | m-001 / m-002 | 112.58 | 564, 1280 | 264, `{CA1DF9DB-A591-409B-894F-BD65C3E23B17}` | L — GNSS i plan tego otworu |
| BYZ-0006 / Ruda Nyża | m-001 / m-002 | 112.57 | 68, 1214 | 546, `{6D1EAAE4-3502-423E-87FA-7A62EF212B02}` | L — GNSS i plan tego otworu |
| CHW-0038 / Szczelina w Osmętnicy | m-001 / m-002 | 111.64 | 755, 1142 | 933, `{38B35A66-1709-47A3-9C85-1919D6D7526D}` | L — GNSS i plan tego otworu |
| BRA-0005 / Schronisko w Małym Żlebku | m-001 / m-002 | 109.39 | 703, 951 | 95, `{B0E22FDF-7578-4B2F-A4F7-3EEE8AB78A77}` | L — GNSS i plan tego otworu |
| BYZ-0035 / Szczelina w Suchym Żlebie | m-001 / m-002 | 108.41 | 789, 1054 | 303, `{6350E75C-59F9-459B-B47A-960E737C8AA9}` | L — GNSS i plan tego otworu |
| MTW-0051 / Nyża przy Schodkach | m-001 / m-002 | 107.28 | 663, 1198 | 637, `{FB5B5ECE-1FB0-4E9D-887B-BC8F30B29FB2}` | L — GNSS i plan tego otworu |
| MTZ-0044 / Komin w Kazalnicy Miętusiej | m-001 / m-002 | 107.20 | 598, 1525 | 561, `{6FC6B4BD-4E08-41BE-9237-6C2C12CCA28B}` | L — GNSS i plan tego otworu |
| BYZ-0029 / Płaska Nyża | m-001 / m-002 | 106.70 | 576, 1053 | 945, `{13BDEBA6-4CCC-46F4-A787-F34D7CA227A6}` | L — GNSS i plan tego otworu |
| MTW-0054 / Jaskinia pod Wantą | m-001 / m-002 | 106.02 | 711, 1535 | 545, `{9306F8A3-B212-4456-B121-7B821EE13B60}` | L — GNSS i plan tego otworu |
| BYZ-0037 / Szczelina pod Głazem | m-001 / m-002 | 103.01 | 809, 1219 | 845, `{1F5A419E-5C9B-4EF1-9F33-942525FB2574}` | L — GNSS i plan tego otworu |
| BYZ-0034 / Nyża z Mostem | m-001 / m-002 | 102.73 | 760, 1055 | 985, `{792E7D4A-02EC-4EE5-B409-34CF9018F530}` | L — GNSS i plan tego otworu |
| BYZ-0033 / Jaskinia w Piekle | m-001 / m-002 | 101.31 | 720, 1626 | 246, `{D48FE3ED-6A07-4BE1-82F2-2FBC84CEFFCC}` | L — GNSS i plan tego otworu |

## Dodatkowe zastrzeżenia w źródłach

- **BYW-0015**: TPN kwestionuje opis dojścia w inwentarzu. Potrzebne niezależne rozpoznanie otworu i poprawny szkic dojścia, zamiast ponownego dopasowania wyłącznie według tego opisu.
- **BYW-0031**: TPN kwestionuje opis dojścia w inwentarzu. Potrzebne niezależne rozpoznanie otworu i poprawny szkic dojścia, zamiast ponownego dopasowania wyłącznie według tego opisu.
- **BYW-0026**: TPN opisuje położenie wywiedzione z dojścia w inwentarzu, WER_LOK wskazuje NMT. Brakuje niezależnego wskazania otworu i pomiaru GNSS; interpretacja modelu terenu nie zastępuje kontroli.
- **MTZ-0025**: TPN UWAGI deklaruje wcześniejszą błędną lokalizację i poprawę po weryfikacji terenowej. To dowód treści źródła przemawiający za TPN, lecz bez daty, autora, metody i dokładności tej kontroli w rekordzie nie podnosimy statusu ani nie odrzucamy PIG. Potrzebny pierwotny protokół tej korekty.

## Wszystkie grupy wspólnych best

Dla każdej grupy rozstrzygnięcie **G**: tożsamość nierozstrzygnięta; zachować osobne ID i wszystkie pomiary. Potrzebny plan z osobnym oznaczeniem wymienionych otworów i mapowaniem ich GLOBALID/PIG oraz oddzielne pomiary GNSS. Różne nazwy/numery nie dowodzą rozdzielności, a identyczny punkt nie dowodzi duplikatu. JSON zawiera osobny `missing_evidence` i pełne dowody każdego członka.

| Grupa | WGS84 best (lat, lon) | Obiekty / nazwy | Źródła best (CSV row / klucz) | Decyzja / brak |
|---|---|---|---|
| G01 | [49.2113889, 20.0902778] | PL-0002 Wielka Żabia Szpara; PL-0027 Jaskinia Żabia Lodowa | PL-0002: TPN 268 / `{6842B5C5-69EC-4F77-810F-8A5B2368D16B}`; PL-0027: TPN 358 / `{01F20C5E-17EC-4582-BA2F-4ACF99B5C482}` | G — plan i GNSS wszystkich wymienionych otworów |
| G02 | [49.2298306, 19.9010305] | KSW-0142 Niski Schron nad Tomanową; KSW-0159 Niżni Okap nad Tomanową; KSW-0195 Wyżni Okap nad Tomanową | KSW-0142: TPN 310 / `{D29B67F7-2416-4F4E-9FF7-0D52C2ACC9A8}`; KSW-0159: TPN 435 / `{51C9495B-6D4A-4817-8247-977833B0BCB5}`; KSW-0195: TPN 810 / `{F7ED4066-4249-46A1-BD73-0532D43BC278}` | G — plan i GNSS wszystkich wymienionych otworów |
| G03 | [49.2306111, 19.89815] | KSW-0062 Szczelina przy Tomanowym Okapie; KSW-0197 Tomanowy Okap | KSW-0062: TPN 72 / `{89707F71-ADEB-45FD-BCC7-E742BA6867FF}`; KSW-0197: TPN 455 / `{7AD1ABF3-D20D-4B73-B097-54F9A33061D7}` | G — plan i GNSS wszystkich wymienionych otworów |
| G04 | [49.2311111, 19.8947222] | KSW-0063 Dziura nad Zawaliskiem; KSW-0103 Dziura pod Zawaliskiem | KSW-0063: TPN 971 / `{C7AA36ED-BD41-433F-95C9-19DE153C6BD7}`; KSW-0103: TPN 827 / `{95A15507-01C4-41CB-82DA-858B44498FE4}` | G — plan i GNSS wszystkich wymienionych otworów |
| G05 | [49.2364306, 19.8652806] | KSW-0181 Jaskinia w Zbójnickiej Turni; KSW-0215 Zbójnicka Piwnica | KSW-0181: TPN 729 / `{607C3858-E4FD-4470-982E-19DEC353648D}`; KSW-0215: TPN 494 / `{6D01AD30-46FD-45D8-8F59-2B2BF3E47D62}` | G — plan i GNSS wszystkich wymienionych otworów |
| G06 | [49.2369305, 19.8723] | KSW-0040 Szczelina na Zakręcie II; KSW-0132 Szczelina na Zakręcie I | KSW-0040: TPN 326 / `{2F06A9A5-7185-4981-B146-8DD1ACBF8176}`; KSW-0132: TPN 73 / `{B79197F0-C5A7-4141-B05A-9E2AEE44FAA3}` | G — plan i GNSS wszystkich wymienionych otworów |
| G07 | [49.2405556, 19.8994445] | MTZ-0026 Jaskinia Niespodzianka; MTZ-0035 Jaskinia Zapylna | MTZ-0026: TPN 850 / `{45251C42-3EB2-461E-9B1E-9CD0032AD20D}`; MTZ-0035: TPN 459 / `{1032BA2D-24F5-47EC-AC61-1072C1A78439}` | G — plan i GNSS wszystkich wymienionych otworów |
| G08 | [49.241151, 19.8569591] | KSZ-0080 Płaska Komórka w Żeleźniaku; KSZ-0104 Żeleźniakowa Brama | KSZ-0080: TPN 301 / `{D1578A9F-222A-404A-B528-C5021BA7F00C}`; KSZ-0104: TPN 31 / `{8700627C-CF7F-4AD8-8365-131FD3EDC9BE}` | G — plan i GNSS wszystkich wymienionych otworów |
| G09 | [49.2415706, 19.8539281] | KSZ-0013 Jaskinia nad Prożkiem w Żlebie Na Spady; KSZ-0022 Nyża nad Prożkiem w Żlebie Na Spady | KSZ-0013: TPN 507 / `{7DDC257F-1586-457A-AF54-46CDFFB7AD7B}`; KSZ-0022: TPN 429 / `{85DE85A0-28DD-4F4F-9240-C1C497A96C0A}` | G — plan i GNSS wszystkich wymienionych otworów |
| G10 | [49.2417674, 19.8556402] | KSZ-0061 Schronisko nad Bramką; KSZ-0086 Schronisko nad Bramą | KSZ-0061: TPN 525 / `{07BBCE7B-22DE-4B10-B0D4-665C443148B3}`; KSZ-0086: TPN 159 / `{3CE5E8DE-4CD1-400E-A642-D66663ECFDB2}` | G — plan i GNSS wszystkich wymienionych otworów |
| G11 | [49.2497223, 19.8513333] | LEJ-0003 Dziura nad Zabijakiem I; LEJ-0013 Dziura nad Zabijakiem II | LEJ-0003: TPN 211 / `{F0F06C12-762C-4C86-A5FC-CF3F9587D9A4}`; LEJ-0013: TPN 661 / `{283787B7-3A80-489A-BEE7-F7532B7C3EB0}` | G — plan i GNSS wszystkich wymienionych otworów |

### Porównanie historii członków grup

- **G01**: Identyczny punkt best występuje już w odrębnych źródłowych rekordach TPN, więc nie jest skutkiem spłaszczenia eksportu. W historii PIG: 2 pomiarów, 2 różnych par WGS84. Brak planu otworów wiążącego te rekordy; pozostawiamy odrębne ID.
- **G02**: Identyczny punkt best występuje już w odrębnych źródłowych rekordach TPN, więc nie jest skutkiem spłaszczenia eksportu. W historii PIG: 3 pomiarów, 1 różnych par WGS84. Brak planu otworów wiążącego te rekordy; pozostawiamy odrębne ID.
- **G03**: Identyczny punkt best występuje już w odrębnych źródłowych rekordach TPN, więc nie jest skutkiem spłaszczenia eksportu. W historii PIG: 2 pomiarów, 1 różnych par WGS84. Brak planu otworów wiążącego te rekordy; pozostawiamy odrębne ID.
- **G04**: Identyczny punkt best występuje już w odrębnych źródłowych rekordach TPN, więc nie jest skutkiem spłaszczenia eksportu. W historii PIG: 2 pomiarów, 1 różnych par WGS84. Brak planu otworów wiążącego te rekordy; pozostawiamy odrębne ID.
- **G05**: Identyczny punkt best występuje już w odrębnych źródłowych rekordach TPN, więc nie jest skutkiem spłaszczenia eksportu. W historii PIG: 2 pomiarów, 1 różnych par WGS84. Brak planu otworów wiążącego te rekordy; pozostawiamy odrębne ID.
- **G06**: Identyczny punkt best występuje już w odrębnych źródłowych rekordach TPN, więc nie jest skutkiem spłaszczenia eksportu. W historii PIG: 2 pomiarów, 1 różnych par WGS84. Brak planu otworów wiążącego te rekordy; pozostawiamy odrębne ID.
- **G07**: Identyczny punkt best występuje już w odrębnych źródłowych rekordach TPN, więc nie jest skutkiem spłaszczenia eksportu. W historii PIG: 2 pomiarów, 1 różnych par WGS84. Brak planu otworów wiążącego te rekordy; pozostawiamy odrębne ID.
- **G08**: Identyczny punkt best występuje już w odrębnych źródłowych rekordach TPN, więc nie jest skutkiem spłaszczenia eksportu. W historii PIG: 2 pomiarów, 1 różnych par WGS84. Brak planu otworów wiążącego te rekordy; pozostawiamy odrębne ID.
- **G09**: Identyczny punkt best występuje już w odrębnych źródłowych rekordach TPN, więc nie jest skutkiem spłaszczenia eksportu. W historii PIG: 2 pomiarów, 1 różnych par WGS84. Brak planu otworów wiążącego te rekordy; pozostawiamy odrębne ID.
- **G10**: Identyczny punkt best występuje już w odrębnych źródłowych rekordach TPN, więc nie jest skutkiem spłaszczenia eksportu. W historii PIG: 2 pomiarów, 1 różnych par WGS84. Brak planu otworów wiążącego te rekordy; pozostawiamy odrębne ID.
- **G11**: Identyczny punkt best występuje już w odrębnych źródłowych rekordach TPN, więc nie jest skutkiem spłaszczenia eksportu. W historii PIG: 2 pomiarów, 1 różnych par WGS84. Brak planu otworów wiążącego te rekordy; pozostawiamy odrębne ID.

## Hashe i odtworzenie

W poniższych trzech plikach znajdują się wszystkie cytowane wartości. JSON zawiera też SHA-256 pozostałych surowych CSV/XLSX i kompletu shapefile. Hashe obiektów odnoszą się do bazy PBI przed korektą notes/kategorii.

| Źródło | SHA-256 |
|---|---|
| `data/sources/pig/jaskinie_polski_pig_dump.jsonl` | `b5422cdf01a3278e27b3f184abac2fdb45fa8bd2a6a1c2169818d9524f7cbea8` |
| `data/sources/pig/pig_otwory_jaskin_.xlsx.-.Export.csv` | `54ac148504ba852d29359984fad87dac2afc9be2dd80c4b347fb447d9cc9b477` |
| `data/sources/tpn/tpn_otwory_jaskin.xlsx.-.Export.csv` | `554beb579e04c79c4fa926910e38ae551ea684e895b9b63f8ddddca73522f581` |

Odtworzenie z czystego checkoutu: `uv sync --frozen`, `uv run --frozen python scripts/validate.py`; ostrzeżenia `MEASUREMENT_DISTANCE_OUTLIER` muszą odpowiadać 72 parom JSON. Do ponownego wyliczenia użyć `load_dataset()`, kombinacji pomiarów każdego obiektu, `wgs84_to_1992` oraz `hypot(dx,dy)>100`; dla best grupować wybrane `measurement_id` według obu wartości WGS84 zaokrąglonych do 7 miejsc. Porównać z polami `pair`, `distance_m`, `rounded_wgs84` i członkami `shared_best`; weryfikować source_ref po kluczu i hashe źródeł. Nie wymaga dawnych gałęzi ani `build/`.

Pozostałe niepewności stanowią listę do weryfikacji terenowej/źródłowej. PBI-083 zamyka udokumentowaną korektę i ocenę, a nie rozstrzygnięcie 72 lokalizacji, 11 tożsamości grup i mieszanego otworu CHZ-0011. Nie przeniesiono punktów, nie scalono encji, nie odrzucono pomiarów i nie podniesiono statusów.
