# Issue #36 — historyczne dowiązanie i geometria systemu Pawlikowskiego

Stan sprawdzenia: 2026-10-24. Analiza tylko do odczytu. Źródła GPS: bieżący `main` 2a40b8e224ce248296e1d82742728bd9b8b6d8d1. Lokalny JKTZ sprawdzany w rewizji c39e78dca1a7fcc57a18c837e1e5c452d077130f; odtworzenie pozycji GPS z przypiętej historycznej rewizji 773c8e2e6aa910c8ba78192ae6741d107c6598e2. Lokalny Georeferencer: 7020b65b1614b6ae077079ef635ab196f7e7c353, gałąź `codex/fix-system-plan-anchors`. Te ostatnie wskazania identyfikują lokalne zbadane źródła, nie deklarują stanu zdalnego main.

## Najważniejsze rozróżnienie

Istnieją trzy różne warstwy: oryginalna lokalna geometria Filara (`_RAW`), jej historyczna kompilacja JKTZ (jedna globalna kotwica Mylna:0, ponowne wyrównanie/deklinacja), oraz dzisiejszy JKTZ z trzema osobnymi fixami pobieranymi z GPS. Nie należy traktować pozycji Obłazkowej i Raptawickiej pochodzących z tej samej sieci jako dwóch niezależnych pomiarów GNSS potwierdzających kotwicę Mylnej.

## Historia kotwicy

Najstarszy dostępny commit [70fa06abb20489136468f212d541d245e99029be, 2013-11-13](https://github.com/dlubom/Jaskiniowy-Kataster-Tatr-Zachodnich/commit/70fa06abb20489136468f212d541d245e99029be) zawiera w `Jaskinie-poligony/Dolina Kościeliska/Kominiarski Wierch/Raptawicka Turnia/Mylna/Mylna/CG.SRV` dokładnie:

```text
#prefix ML
#flag 0 /Mylna
#note 0 /Mylna
#fix 0 417179.14 5454690.67 1098
```

Plik nie podaje autora/metody pozyskania absolutnej kotwicy, datum wysokości ani dokładności. `INFO.SRV` tego commitu podaje wcześniejsze włączenie Mylnej do projektu 2012-05-14, ale nie zachowuje samodzielnego pomiaru kotwicy z tej daty.

[01ffe6a8e5b35e581f8b94372b5b0b427b4fdcdf, 2026-02-12](https://github.com/dlubom/Jaskiniowy-Kataster-Tatr-Zachodnich/commit/01ffe6a8e5b35e581f8b94372b5b0b427b4fdcdf) przenosi ten sam fix z CG do MYLNA_M. W tym konkretnym commicie metadane źródła brzmią `Polskie Towarzystwo Przyjaciol Nauk o Ziemi`, a TEAM i INSTRUMENT są `unknown`. Późniejszy plik [MYLNA_M.SRV w 773c8e2](https://github.com/dlubom/Jaskiniowy-Kataster-Tatr-Zachodnich/blob/773c8e2e6aa910c8ba78192ae6741d107c6598e2/Poligony/D_Koscieliska/Kom_Wierch/Rapt_Turnia/Syst_Pawlikowskiego/Mylna/MYLNA_M.SRV) podaje PIG i F. Filara, nadal bez metody absolutnego fixu. Sam dopisek metadanych z 2026 nie dowodzi GNSS ani pomiaru geodezyjnego w 2013/2012.

## Odtworzona kompilacja historyczna

Wydzielono oryginalne poddrzewo Systemu Pawlikowskiego z `KATASTER.wpj`, zachowano oryginalną nadrzędną `.REF`, skopiowano nienaruszone bajty 17 plików aktywnych, skompilowano Survex 1.4.24. Wynik: 705 stacji, 751 odcinków, 47 pętli, jeden punkt `FIXED` — Mylna:0. Są dwa oryginalne ostrzeżenia compass-on-plumb w WSZCZCB.SRV; ich nie poprawiano. Konwersja UTM34N EPSG:32634 → EPSG:2180 przez pyproj; datum Z pozostaje nieznane. Wynik trzech głównych stacji zgadza się z GPS do zapisanej precyzji.

| Stacja | N PL-1992 | E PL-1992 | Z |
|---|---:|---:|---:|
| Mylna:0 | 152788.47 | 562741.86 | 1098.00 |
| Mylna:39 | 152919.87 | 562808.79 | 1093.67 |
| Mylna:52 — I Okno, koniec gałęzi | 152774.88 | 562739.61 | 1097.62 |
| Mylna:53 — II Okno, koniec gałęzi | 152769.43 | 562731.63 | 1098.72 |
| Oblazkowa:0.0 | 152808.28 | 562768.93 | 1096.62 |
| Raptawicka:1.0 | 152841.98 | 562742.35 | 1141.31 |

Cały zakres węzłów: E 562653.817–562810.557; N 152755.946–152919.869; Z 1075.06–1152.21. Z wariantem PIG i 60m marginesu bezpieczny wycinek E 562545.55–562870.56, N 152694.01–152981.17.

`CG.SRV` kończy ciąg na 39; `BCWOKWYJ.SRV` opisuje okolicę 36–39 jako wyjście. Oryginalny `_RAW/SJP/Dane/Mylna/CG.SRV` ma flagi 0,333,52,53,39,0.0,1.0,5.1; plan Filara 2015-06-15 pokazuje północny otwór na poziomie −3.65 m. Łącznie jest to mocne uzasadnienie interpretacji 39 jako stacji północnego wyjścia, ale brak opisu umiejscowienia znaku pomiarowego względem fizycznego progu. Analogicznie plan oznacza południowe 0,00 trójkątem przy portalu, bez jednoznacznego opisu znaku/progu. Źródła planu analizuje osobny raport wizualny.

### Diagnostyczna translacja całej historycznej sieci

Wyniki w tabeli są odległościami poziomymi do punktów katalogowych TPN, a nie błędami względem prawdy terenowej. Wybierając m-002 przesuwamy WSZYSTKIE węzły o ΔN=−1.94, ΔE=−13.38 m; wybierając m-001 o ΔN=+1.30, ΔE=−48.27 m. Z nie jest zmieniane.

| Kotwica Mylnej | Raptawicka do TPN | północna Mylna39 do TPN | Obłazkowa do TPN |
|---|---:|---:|---:|
| m-001 PIG | 36.99 m | 37.15 m | 25.18 m |
| m-002 TPN | 2.15 m | 3.17 m | 26.34 m |
| m-003 historyczna | 11.94 m | 11.13 m | 38.46 m |

TPN opisuje punkt Raptawickiej jako `górny`, podczas gdy 1.0 oznacza główne wejście; jej kolumna nie jest więc kontrolą tego samego otworu. Zgodność północnej Mylnej wspiera test m-002 w LiDAR przy geometrii historycznej. Nie wystarcza do wyboru Best: trzy TPN mogą dzielić metodę ortofoto/NMT i nie mają dokładności; TPN Obłazkowej wymaga osobnej identyfikacji i leży blisko pozycji Mylnej.

## Oryginalna geometria lokalna nie jest tożsama z kompilacją

[RAW README w 773c8e2](https://github.com/dlubom/Jaskiniowy-Kataster-Tatr-Zachodnich/blob/773c8e2e6aa910c8ba78192ae6741d107c6598e2/Poligony/D_Koscieliska/Kom_Wierch/Rapt_Turnia/Syst_Pawlikowskiego/_RAW/README.md) przechowuje wyjaśnienie Filara: geometryczne połączenie opiera się na ciągu powierzchniowym, powtarzanym po trzy razy w obie strony; należy zachować oryginalne wzajemne położenie otworów. Jest to historycznie zapisane świadectwo autora, bez załączonej pierwotnej wiadomości/niezależnego protokołu dokładności.

[RAW CG](https://github.com/dlubom/Jaskiniowy-Kataster-Tatr-Zachodnich/blob/773c8e2e6aa910c8ba78192ae6741d107c6598e2/Poligony/D_Koscieliska/Kom_Wierch/Rapt_Turnia/Syst_Pawlikowskiego/_RAW/SJP/Dane/Mylna/CG.SRV), RAW OBLAZK i RAPTAW mają lokalne fixy względem Mylna0. Wszystkie stacje 0–39 CG są zafiksowane w RAW, a tylko Mylna0 w aktywnej kompilacji. RAW `.wpj` nie ma `.REF`, SRV nie zawierają `#date` ani `DECL`; brak udokumentowanego typu północy/deklinacji. Plany mają strzałkę N bez rozróżnienia geograficznej/magnetycznej/siatkowej. Nie przypisujemy lokalnym osiom kodu EPSG.

| Stacja | RAW local x | RAW local y | RAW local z | dystans XY RAW od0 | dystans kompilacji od0 |
|---|---:|---:|---:|---:|---:|
| Mylna39 | 58.9314407 | 133.5402718 | −3.6466171 | 145.965 m | 147.513 m |
| Obłazkowa0.0 | 24.34 | 24.09 | −2.07 | 34.246 m | 33.556 m |
| Raptawicka1.0 | −4.68 | 55.00 | 42.82 | 55.199 m | 53.534 m |

Zatem różnica obejmuje ponowne wyrównanie, nie tylko rotację. Dla przykładu hipotetyczne równoległe lokalne osie i osie PL-1992 dają przy m-003 odległość północnego39 do TPN3.64m, a przy m-00210.25m — odwracają ranking historycznej kompilacji. To jest wyłącznie test wrażliwości, NIE poprawna transformacja CRS. Bez określenia rotacji lokalnej sieci nie wolno ogłaszać tego wariantu geodezyjnie poprawnym. Rejestracja kilku rozpoznanych otworów w LiDAR może pomóc ocenić rotację/translację, lecz wymaga niezależnej identyfikacji każdego otworu.

Próbna kompilacja nienaruszonego RAW: 692 stacje, 726 odcinków, 35 pętli, 3 ostrzeżenia (dwa pionowe kompasowe, jedno przecinek−14,00 w Raptawickiej). Zachowano ją wyłącznie jako lokalną geometrię diagnostyczną; znane fixy zapisano też z pełną precyzją bezpośrednio ze źródeł. Nie należy traktować tego jako walidacji/poprawy RAW.

## Wpływ na dzisiejsze projekty

W zbadanym [szablonie JKTZ OTWORY](https://github.com/dlubom/Jaskiniowy-Kataster-Tatr-Zachodnich/blob/c39e78dca1a7fcc57a18c837e1e5c452d077130f/Poligony/OTWORY.SRV.j2) fixy są osobne: Mylna:0→KSZ-0064, Oblazkowa:0.0→KSZ-0090, Raptawicka:1.0→KSZ-0047. Aktywny WPJ nie zawiera już POW_ORM; podziemne połączenie Mylna638↔Obłazkowa pozostaje. Zmiana tylko KSZ-0064 spowoduje inne ograniczenia/wyrównanie połączonej Mylnej i Obłazkowej, nie sztywną translację całego systemu; osobno zakotwiczona Raptawicka nie podąży automatycznie. Korekta wspólnej kotwicy wymaga skoordynowania trzech eksportowanych pozycji i świadomego wyboru geometrii źródłowej. Czyścić/zmieniać repo JKTZ należy w oddzielnym, zaakceptowanym zakresie.

W zbadanym Georeferencerze mapowania: 001349 Mylna i 010935 system→KSZ-0064; 001351 Obłazkowa→KSZ-0090; 001387 Raptawicka→KSZ-0047. [Generator](https://github.com/dlubom/Georeferencer/blob/7020b65b1614b6ae077079ef635ab196f7e7c353/pipeline/02_generate_geotiff.py) przy każdym renderze oblicza pozycję obrazu z nowych lat/lon i minimalnie zmienioną zbieżność południków. Samej zmiany współrzędnych w GPS nie zobaczymy w opublikowanych obrazach do regeneracji/release Georeferencera. Istniejące zastrzeżenia jakości klików: 001349 entrance_std_px1386.36 i 0109351039.44; nie traktować tych klików jako niezależnego pomiaru terenowego.

## Odtworzenie

Skrypt `docs/asdlc/verification/PBI-116/reconstruct-network.py` wymaga lokalnego repo JKTZ z obiektem773c8e2, bieżącego katalogu GPS, Survex(cavern/dump3d), pyproj i PyYAML. Czyta Git, tworzy wyłącznie kopie w podanym output, nie przełącza gałęzi i nie zmienia źródeł.

```sh
.venv/bin/python docs/asdlc/verification/PBI-116/reconstruct-network.py \
  --jktz /Users/dariuszlubomski/proj/Jaskiniowy-Kataster-Tatr-Zachodnich \
  --catalogue /Users/dariuszlubomski/proj/gps-kataster-obiektow-tatr \
  --output build/research/mylna-network-reproduction
```

Wynik `build/research/mylna-network-reproduction/system-network.json`: wszystkie węzły/odcinki historyczne EPSG2180, wszystkie RAW wyłącznie lokalne, dokładne RAW fixy, scenariusze, manifest SHA256 źródeł, informacja o ostrzeżeniach. JSON nie zawiera bieżącego czasu, wynik można porównać bajtowo między uruchomieniami. Pliki `.3d` zawierają czas kompilacji i nie należy wymagać ich bajtowej tożsamości.

Weryfikacja skryptu: składnia PASS, dwa uruchomienia dały identyczny JSON SHA256 `4948a88986d836a50cb8f12c548d1cf0cf129c55dc5c69ff0658cb4e26de4d66` (662594B). JSON ma 705 węzłów i 749 rysowanych odcinków historycznych: raport cavern liczy751 pomiarów, w tym dwa zerowe dowiązania powierzchni `Oblazkowa:0.0→p1.0` oraz `p1.11→Raptawicka:1.0`, które nie tworzą dodatkowych LINE w dump3d. RAW ma692 węzły/726 odcinków.
