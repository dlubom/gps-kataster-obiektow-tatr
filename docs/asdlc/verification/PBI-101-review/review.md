# PBI-101 — konkretne propozycje do decyzji

**Status: oczekuje na decyzje użytkownika.** Po przedstawieniu tych konkretnych propozycji użytkownik odpowiedział: „Na razie pozostaw wszystko pending”. Wszystkie zalecane poniżej statusy są więc nadal wyłącznie propozycjami. Żaden approve/reject/defer nie został zastosowany do produkcji. Autor i czas wszystkich 640 decyzji pending są null. Zalecenia poniżej pochodzą od Codex i nie są akceptacją człowieka.

Paczka `pbi-101-20261019`, baza `60afeca2d17bbc4b5aa690abc83da1d25d89a506`, przyjęty stan wyłącznie z origin/main `b98fd3febb400c7ee520046682c1bb16238429ee` (bootstrap CSV; brak rejestru na main). Snapshot `481e83a1a113a0596947d40e30d7a186de0f0f51154957c5f48713c4ae3324d8` pochodzi z nowego odczytu 2026-10-19T16:39:29.750178Z–16:39:32.954639Z. Utrwalony przed przygotowaniem paczki w commicie bazy.

Źródło jest rekordem punktowym TPN; kandydat i dystans nie dowodzą tożsamości otworu. API nie ma wysokości ani dokładności. Data poniżej jest dniem LAST_EDITED_DATE, z komentarzem o nieznanej dacie terenowej.

## Zakres i odpowiedź

| Grupa | Konkretne wpisy | Propozycja |
|---|---:|---|
| A | A001–A578 | approve z actions=[]: przyjąć rewizję źródła, zachować katalog |
| B | B001–B031 | approve: dopisać ustalenie TPN; osobno keep dotychczasowego best i jawny tryb podany w tabeli |
| C | C001–C005 | approve: nowa Jaskinia i nowy Obiekt, pierwszy pomiar best |
| D | D001–D026 | defer: indywidualne powody i konkretni kandydaci poniżej |

Możesz zaakceptować wskazane ID lub całe jawnie wyliczone zakresy, podając wyjątki. Przykład odpowiedzi: „A001–A578 approve bez zmian YAML; B001–B031 approve append i keep z trybami z tabeli; C001–C005 approve; D001–D026 defer z podanymi powodami”. To jest format możliwej odpowiedzi, a nie dokonana decyzja. Możesz wybrać inne rozstrzygnięcia dla dowolnego ID. Zmiana akcji/celu wymaga odświeżenia wykonawczej propozycji i pokazania nowego diffu.

Manifest PBI-099 pozostaje pending, 9/9 preimages zgodne. Brak migracji chronionych auto→manual i brak select_new. Wszystkie obecne 1876 pomiarów zachowują pełne wartości i kolejność.

## Warunkowy efekt zweryfikowany w izolowanej symulacji

Symulacja używa wyłącznie autora `simulation:codex` i czasu testowego; nie reprezentuje decyzji użytkownika. [Diff danych](simulated-domain.patch) pokazuje skutek proponowanych grup B/C. Stan źródła i kolejka defer powstaną dopiero po rzeczywistych decyzjach.

Przewidywane dodatki: 5 Obiektów, 5 Jaskiń i 36 pomiarów (31 historii + 5 pierwszych). 1007 → 1012 Obiektów, 1001 → 1006 Jaskiń, 1876 → 1912 pomiarów; 26 defer; 0 reject; istniejące punkty best bez przesunięcia. Tryb auto→manual: 31 niechronionych Obiektów z grupy B, jawnie wskazanych niżej.

395 pozostałych rekordów technical_only nie wymaga decyzji; pełne 1035 wejść i wszystkie 273 strony kandydatów znajdują się w [changes.json](../../../../data/source_reviews/tpn/pbi-101-20261019/changes.json). [decisions.yml](../../../../data/source_reviews/tpn/pbi-101-20261019/decisions.yml) to aktywna paczka pending do review. [recommendations.json](recommendations.json) mapuje ID A/B/C/D na pełny change_id i reason. Użytkownik jawnie polecił pozostawić wszystkie decyzje pending. Bramka CI aktywnej paczki ma odmówić gotowości do merge. PBI-101 pozostaje w toku do decyzji końcowych, apply i check.

## Grupa B — Nowa lokalizacja istniejącego obiektu

### B001 — Dziura w Kończystej Niżnia

GLOBALID `0257a120-426e-4b7d-b47f-1d9f853c6c85`; change_id `0257a120-426e-4b7d-b47f-1d9f853c6c85:797229725c7ef9c2f73f16b9364a7c0f0711ec95ec5cf93dff4ce2fa6e834696`.

Źródło teraz: lat=49.264073726826076, lon=19.878120085354027; data stanu=2026-05-04; GENEZA=jaskinia; WER_LOK="FF NMT 04052026"; UWAGI=null.

Cel: `MTW-0031` / `C-0395`. CSV przed: `{"crs":"EPSG:4326","elevation":"absent","lat":49.26411135898811,"lon":19.878480842128265}`; źródło przesunięte o **26.589 m**. Dopisać `m-003`; istniejące pomiary `m-001, m-002` bez zmiany któregokolwiek pola. Nowy pomiar: TPN/source_record/nieweryfikowany, elevation=null, obie accuracy=null.

**Oddzielna propozycja best:** keep `m-002`; tryb `auto → manual`. Pozycja i wysokość eksportu dotychczasowego obiektu bez zmian. Powód: `Zachować dotychczasowy punkt eksportu; nowa lokalizacja TPN trafia wyłącznie do historii. Data edycji źródła nie dowodzi nowszego pomiaru terenowego.`.

Różnice metadanych źródła: `{"WERYF":{"before":0,"after":1},"WER_LOK":{"before":null,"after":"FF NMT 04052026"}}`. Proponowane akcje: append_measurement + jawny best_action; bez nadpisania notes starego pomiaru.

### B002 — Studnia za Murem

GLOBALID `062430d3-83c1-49ed-8004-044b1dd8fb80`; change_id `062430d3-83c1-49ed-8004-044b1dd8fb80:52a69fba15eeef32abc37d8930a879667a0e95bce55281c2ab86969723697a62`.

Źródło teraz: lat=49.240124697203726, lon=19.901338718659066; data stanu=2026-02-11; GENEZA=jaskinia; WER_LOK="29-05-2020 FF ortofotomapa"; UWAGI=null.

Cel: `MTZ-0031` / `C-0407`. CSV przed: `{"crs":"EPSG:4326","elevation":"absent","lat":49.24010960588787,"lon":19.90134051763272}`; źródło przesunięte o **1.683 m**. Dopisać `m-003`; istniejące pomiary `m-001, m-002` bez zmiany któregokolwiek pola. Nowy pomiar: TPN/source_record/nieweryfikowany, elevation=null, obie accuracy=null.

**Oddzielna propozycja best:** keep `m-002`; tryb `auto → manual`. Pozycja i wysokość eksportu dotychczasowego obiektu bez zmian. Powód: `Zachować dotychczasowy punkt eksportu; nowa lokalizacja TPN trafia wyłącznie do historii. Data edycji źródła nie dowodzi nowszego pomiaru terenowego.`.

Różnice metadanych źródła: `{}`. Proponowane akcje: append_measurement + jawny best_action; bez nadpisania notes starego pomiaru.

### B003 — Schron pod Kończystą

GLOBALID `0c34f113-d6d5-4e57-9db1-b240ed3533b5`; change_id `0c34f113-d6d5-4e57-9db1-b240ed3533b5:17f9f84f15e9ee2a39ab447d88bf2ae6a85d42741ca338ba6f2a1eb0a3c7810e`.

Źródło teraz: lat=49.26341546673104, lon=19.878307635700317; data stanu=2026-05-04; GENEZA=jaskinia; WER_LOK="FF NMT 04052026"; UWAGI=null.

Cel: `MTW-0043` / `C-0566`. CSV przed: `{"crs":"EPSG:4326","elevation":"absent","lat":49.263347202723814,"lon":19.87849807358909}`; źródło przesunięte o **15.804 m**. Dopisać `m-003`; istniejące pomiary `m-001, m-002` bez zmiany któregokolwiek pola. Nowy pomiar: TPN/source_record/nieweryfikowany, elevation=null, obie accuracy=null.

**Oddzielna propozycja best:** keep `m-002`; tryb `auto → manual`. Pozycja i wysokość eksportu dotychczasowego obiektu bez zmian. Powód: `Zachować dotychczasowy punkt eksportu; nowa lokalizacja TPN trafia wyłącznie do historii. Data edycji źródła nie dowodzi nowszego pomiaru terenowego.`.

Różnice metadanych źródła: `{"WERYF":{"before":0,"after":1},"WER_LOK":{"before":null,"after":"FF NMT 04052026"}}`. Proponowane akcje: append_measurement + jawny best_action; bez nadpisania notes starego pomiaru.

### B004 — Ciasna Norka

GLOBALID `1f9eaae2-f97d-4205-bf67-7a43e6ddb5e7`; change_id `1f9eaae2-f97d-4205-bf67-7a43e6ddb5e7:3d525e9749a661b5bb5d1ae8b924495ba490952d62c9f1ae75b36bf712bd9903`.

Źródło teraz: lat=49.263149449546525, lon=19.878710729456344; data stanu=2026-05-04; GENEZA=jaskinia; WER_LOK="FF NMT 04052026"; UWAGI=null.

Cel: `MTW-0024` / `C-0280`. CSV przed: `{"crs":"EPSG:4326","elevation":"absent","lat":49.263036550758336,"lon":19.878917259715838}`; źródło przesunięte o **19.586 m**. Dopisać `m-003`; istniejące pomiary `m-001, m-002` bez zmiany któregokolwiek pola. Nowy pomiar: TPN/source_record/nieweryfikowany, elevation=null, obie accuracy=null.

**Oddzielna propozycja best:** keep `m-002`; tryb `auto → manual`. Pozycja i wysokość eksportu dotychczasowego obiektu bez zmian. Powód: `Zachować dotychczasowy punkt eksportu; nowa lokalizacja TPN trafia wyłącznie do historii. Data edycji źródła nie dowodzi nowszego pomiaru terenowego.`.

Różnice metadanych źródła: `{"WERYF":{"before":0,"after":1},"WER_LOK":{"before":null,"after":"FF NMT 04052026"}}`. Proponowane akcje: append_measurement + jawny best_action; bez nadpisania notes starego pomiaru.

### B005 — Jaskinia Mała w Mułowej

GLOBALID `23287a45-d91f-46d7-a9b2-2c6ebfda9764`; change_id `23287a45-d91f-46d7-a9b2-2c6ebfda9764:6ceb8e92ec4cc1750fe735928ce73f363a3419581853c9b4ad31a14bb34286ab`.

Źródło teraz: lat=49.2382402987435, lon=19.902221547034937; data stanu=2026-02-11; GENEZA=jaskinia; WER_LOK="11-03-2020 FF"; UWAGI=null.

Cel: `MTZ-0027` / `C-0341`. CSV przed: `{"crs":"EPSG:4326","elevation":"absent","lat":49.238258172590285,"lon":19.902225885303192}`; źródło przesunięte o **2.013 m**. Dopisać `m-003`; istniejące pomiary `m-001, m-002` bez zmiany któregokolwiek pola. Nowy pomiar: TPN/source_record/nieweryfikowany, elevation=null, obie accuracy=null.

**Oddzielna propozycja best:** keep `m-002`; tryb `auto → manual`. Pozycja i wysokość eksportu dotychczasowego obiektu bez zmian. Powód: `Zachować dotychczasowy punkt eksportu; nowa lokalizacja TPN trafia wyłącznie do historii. Data edycji źródła nie dowodzi nowszego pomiaru terenowego.`.

Różnice metadanych źródła: `{}`. Proponowane akcje: append_measurement + jawny best_action; bez nadpisania notes starego pomiaru.

### B006 — Średni Lej

GLOBALID `34b1e400-eed4-4773-8416-8d48d04038b4`; change_id `34b1e400-eed4-4773-8416-8d48d04038b4:660ec148c1d93f22c9f07aeb9d9e93b84c9d6f0a7555d2071d6a89a43b3222ad`.

Źródło teraz: lat=49.239847644511535, lon=19.92063056805087; data stanu=2026-02-11; GENEZA=jaskinia; WER_LOK="11-02-2020 FF ortofotomapa"; UWAGI=null.

Cel: `MLZ-0079` / `C-0794`. CSV przed: `{"crs":"EPSG:4326","elevation":"absent","lat":49.23981391112247,"lon":19.920591663951324}`; źródło przesunięte o **4.701 m**. Dopisać `m-003`; istniejące pomiary `m-001, m-002` bez zmiany któregokolwiek pola. Nowy pomiar: TPN/source_record/nieweryfikowany, elevation=null, obie accuracy=null.

**Oddzielna propozycja best:** keep `m-002`; tryb `auto → manual`. Pozycja i wysokość eksportu dotychczasowego obiektu bez zmian. Powód: `Zachować dotychczasowy punkt eksportu; nowa lokalizacja TPN trafia wyłącznie do historii. Data edycji źródła nie dowodzi nowszego pomiaru terenowego.`.

Różnice metadanych źródła: `{}`. Proponowane akcje: append_measurement + jawny best_action; bez nadpisania notes starego pomiaru.

### B007 — Koleba za Kończystą

GLOBALID `4509213c-4194-4179-90e8-cffa30639191`; change_id `4509213c-4194-4179-90e8-cffa30639191:7425befd9fec8864005e6614e8ca22d881f788be7be9a34f19405faedf9360e0`.

Źródło teraz: lat=49.264608453745275, lon=19.878429806915516; data stanu=2026-05-04; GENEZA=jaskinia; WER_LOK="FF NMT 04052026"; UWAGI=null.

Cel: `MTW-0021` / `C-0241`. CSV przed: `{"crs":"EPSG:4326","elevation":"absent","lat":49.264338903915906,"lon":19.877630507465454}`; źródło przesunięte o **65.445 m**. Dopisać `m-003`; istniejące pomiary `m-001, m-002` bez zmiany któregokolwiek pola. Nowy pomiar: TPN/source_record/nieweryfikowany, elevation=null, obie accuracy=null.

**Oddzielna propozycja best:** keep `m-002`; tryb `auto → manual`. Pozycja i wysokość eksportu dotychczasowego obiektu bez zmian. Powód: `Zachować dotychczasowy punkt eksportu; nowa lokalizacja TPN trafia wyłącznie do historii. Data edycji źródła nie dowodzi nowszego pomiaru terenowego.`.

Różnice metadanych źródła: `{"WERYF":{"before":0,"after":1},"WER_LOK":{"before":null,"after":"FF NMT 04052026"}}`. Proponowane akcje: append_measurement + jawny best_action; bez nadpisania notes starego pomiaru.

### B008 — Gawra we Wysrankach

GLOBALID `4c30384d-7d8d-48d8-8d57-aea8cc59687c`; change_id `4c30384d-7d8d-48d8-8d57-aea8cc59687c:c775cce963990e4475e63d8a5dc3659fa8d39a25bcdf2c0b3d8aa1da05d1d18b`.

Źródło teraz: lat=49.24968194423332, lon=19.87713595606838; data stanu=2026-06-02; GENEZA=jaskinia; WER_LOK="21-03-2024 TZK"; UWAGI="Dane morfometr. orientacyjnie".

Cel: `KSW-0241` / `C-0879`. CSV przed: `{"crs":"EPSG:4326","elevation":"absent","lat":49.24975075016535,"lon":19.876947696655524}`; źródło przesunięte o **15.698 m**. Dopisać `m-002`; istniejące pomiary `m-001` bez zmiany któregokolwiek pola. Nowy pomiar: TPN/source_record/nieweryfikowany, elevation=null, obie accuracy=null.

**Oddzielna propozycja best:** keep `m-001`; tryb `auto → manual`. Pozycja i wysokość eksportu dotychczasowego obiektu bez zmian. Powód: `Zachować dotychczasowy punkt eksportu; nowa lokalizacja TPN trafia wyłącznie do historii. Data edycji źródła nie dowodzi nowszego pomiaru terenowego.`.

Różnice metadanych źródła: `{}`. Proponowane akcje: append_measurement + jawny best_action; bez nadpisania notes starego pomiaru.

### B009 — Szara Studnia

GLOBALID `518fe961-d9da-4997-804e-cfc2e389a5ab`; change_id `518fe961-d9da-4997-804e-cfc2e389a5ab:d28168a04ea4d8b076cb92bece0145734428fc47e51fbf6fda8e282ebebd33fe`.

Źródło teraz: lat=49.24414031693521, lon=19.912367100700102; data stanu=2026-02-11; GENEZA=jaskinia; WER_LOK=null; UWAGI=null.

Cel: `MTW-0020` / `C-0201`. CSV przed: `{"crs":"EPSG:4326","elevation":"absent","lat":49.24413612558762,"lon":19.912372260113106}`; źródło przesunięte o **0.599 m**. Dopisać `m-003`; istniejące pomiary `m-001, m-002` bez zmiany któregokolwiek pola. Nowy pomiar: TPN/source_record/nieweryfikowany, elevation=null, obie accuracy=null.

**Oddzielna propozycja best:** keep `m-002`; tryb `auto → manual`. Pozycja i wysokość eksportu dotychczasowego obiektu bez zmian. Powód: `Zachować dotychczasowy punkt eksportu; nowa lokalizacja TPN trafia wyłącznie do historii. Data edycji źródła nie dowodzi nowszego pomiaru terenowego.`.

Różnice metadanych źródła: `{}`. Proponowane akcje: append_measurement + jawny best_action; bez nadpisania notes starego pomiaru.

### B010 — Szpara pod Rysami

GLOBALID `527aee0b-533c-4cb4-bc8b-443de48eb624`; change_id `527aee0b-533c-4cb4-bc8b-443de48eb624:0e86b9070af2403a342fdb6a80c2ca892530af42ad9203aa4f5d713007eca06a`.

Źródło teraz: lat=49.18200944871954, lon=20.08133060093272; data stanu=2026-06-02; GENEZA=jaskinia; WER_LOK=null; UWAGI=null.

Cel: `PL-0022` / `C-0382`. CSV przed: `{"crs":"EPSG:4326","elevation":"absent","lat":49.181601734619925,"lon":20.08095270814154}`; źródło przesunięte o **53.057 m**. Dopisać `m-003`; istniejące pomiary `m-001, m-002` bez zmiany któregokolwiek pola. Nowy pomiar: TPN/source_record/nieweryfikowany, elevation=null, obie accuracy=null.

**Oddzielna propozycja best:** keep `m-002`; tryb `auto → manual`. Pozycja i wysokość eksportu dotychczasowego obiektu bez zmian. Powód: `Zachować dotychczasowy punkt eksportu; nowa lokalizacja TPN trafia wyłącznie do historii. Data edycji źródła nie dowodzi nowszego pomiaru terenowego.`.

Różnice metadanych źródła: `{"WERYF":{"before":0,"after":1}}`. Proponowane akcje: append_measurement + jawny best_action; bez nadpisania notes starego pomiaru.

### B011 — Bliźniaczy Komin

GLOBALID `61f5cfc1-a9eb-4193-a3b3-e4fd8dd9c60d`; change_id `61f5cfc1-a9eb-4193-a3b3-e4fd8dd9c60d:41e19cc0f90b51e064a63b18240b0d4590641eb9d1063513c649b1f34013d107`.

Źródło teraz: lat=49.242521869375864, lon=19.905487761479854; data stanu=2026-05-09; GENEZA=jaskinia; WER_LOK="FF 09052026"; UWAGI=null.

Cel: `MTW-0046` / `C-0580`. CSV przed: `{"crs":"EPSG:4326","elevation":"absent","lat":49.242166394295865,"lon":19.906101986463444}`; źródło przesunięte o **59.693 m**. Dopisać `m-003`; istniejące pomiary `m-001, m-002` bez zmiany któregokolwiek pola. Nowy pomiar: TPN/source_record/nieweryfikowany, elevation=null, obie accuracy=null.

**Oddzielna propozycja best:** keep `m-002`; tryb `auto → manual`. Pozycja i wysokość eksportu dotychczasowego obiektu bez zmian. Powód: `Zachować dotychczasowy punkt eksportu; nowa lokalizacja TPN trafia wyłącznie do historii. Data edycji źródła nie dowodzi nowszego pomiaru terenowego.`.

Różnice metadanych źródła: `{"WERYF":{"before":0,"after":1},"WER_LOK":{"before":null,"after":"FF 09052026"}}`. Proponowane akcje: append_measurement + jawny best_action; bez nadpisania notes starego pomiaru.

### B012 — Schron z Balkonem

GLOBALID `65d4a109-b1aa-4741-b694-b1a65ef93752`; change_id `65d4a109-b1aa-4741-b694-b1a65ef93752:d2dcbddf171ece91a95ac68cbf47f5024c0b501fe8ca0bcdb13033e50fb6cc26`.

Źródło teraz: lat=49.237925581626655, lon=19.90220458612156; data stanu=2026-02-11; GENEZA=jaskinia; WER_LOK="16-09-2021 FF, NMT"; UWAGI=null.

Cel: `MTZ-0001` / `C-0016`. CSV przed: `{"crs":"EPSG:4326","elevation":"absent","lat":49.23795263854196,"lon":19.902197508027328}`; źródło przesunięte o **3.053 m**. Dopisać `m-003`; istniejące pomiary `m-001, m-002` bez zmiany któregokolwiek pola. Nowy pomiar: TPN/source_record/nieweryfikowany, elevation=null, obie accuracy=null.

**Oddzielna propozycja best:** keep `m-002`; tryb `auto → manual`. Pozycja i wysokość eksportu dotychczasowego obiektu bez zmian. Powód: `Zachować dotychczasowy punkt eksportu; nowa lokalizacja TPN trafia wyłącznie do historii. Data edycji źródła nie dowodzi nowszego pomiaru terenowego.`.

Różnice metadanych źródła: `{}`. Proponowane akcje: append_measurement + jawny best_action; bez nadpisania notes starego pomiaru.

### B013 — Bliźniacza Studnia

GLOBALID `7006936a-289f-4f87-8614-3c6253d13228`; change_id `7006936a-289f-4f87-8614-3c6253d13228:33de506eff0f54aab5a8bb738f341ffc275b5d9c762026920e1378e463b2dade`.

Źródło teraz: lat=49.23987014050215, lon=19.92527898654571; data stanu=2026-02-11; GENEZA=jaskinia; WER_LOK=null; UWAGI=null.

Cel: `MLZ-0012` / `C-0111`. CSV przed: `{"crs":"EPSG:4326","elevation":"absent","lat":49.239888895619956,"lon":19.925205563763825}`; źródło przesunięte o **5.739 m**. Dopisać `m-003`; istniejące pomiary `m-001, m-002` bez zmiany któregokolwiek pola. Nowy pomiar: TPN/source_record/nieweryfikowany, elevation=null, obie accuracy=null.

**Oddzielna propozycja best:** keep `m-002`; tryb `auto → manual`. Pozycja i wysokość eksportu dotychczasowego obiektu bez zmian. Powód: `Zachować dotychczasowy punkt eksportu; nowa lokalizacja TPN trafia wyłącznie do historii. Data edycji źródła nie dowodzi nowszego pomiaru terenowego.`.

Różnice metadanych źródła: `{}`. Proponowane akcje: append_measurement + jawny best_action; bez nadpisania notes starego pomiaru.

### B014 — Dziura w Kończystej Turni

GLOBALID `7033eb52-9352-4f35-9adf-89490fbb5f1f`; change_id `7033eb52-9352-4f35-9adf-89490fbb5f1f:4d7843860ad5405c55645d9c51cc6783caee8d876716869f2bcbf5c62e0e22c4`.

Źródło teraz: lat=49.26420814848368, lon=19.878301642090463; data stanu=2026-05-04; GENEZA=jaskinia; WER_LOK="FF NMT 04052026"; UWAGI=null.

Cel: `MTW-0059` / `C-0753`. CSV przed: `{"crs":"EPSG:4326","elevation":"absent","lat":49.26397710347857,"lon":19.878552428721427}`; źródło przesunięte o **31.519 m**. Dopisać `m-003`; istniejące pomiary `m-001, m-002` bez zmiany któregokolwiek pola. Nowy pomiar: TPN/source_record/nieweryfikowany, elevation=null, obie accuracy=null.

**Oddzielna propozycja best:** keep `m-002`; tryb `auto → manual`. Pozycja i wysokość eksportu dotychczasowego obiektu bez zmian. Powód: `Zachować dotychczasowy punkt eksportu; nowa lokalizacja TPN trafia wyłącznie do historii. Data edycji źródła nie dowodzi nowszego pomiaru terenowego.`.

Różnice metadanych źródła: `{"WERYF":{"before":0,"after":1},"WER_LOK":{"before":null,"after":"FF NMT 04052026"}}`. Proponowane akcje: append_measurement + jawny best_action; bez nadpisania notes starego pomiaru.

### B015 — Jaskinia przy Sikawce

GLOBALID `71dd8dce-2bc1-42f7-a5e9-174902ca7aed`; change_id `71dd8dce-2bc1-42f7-a5e9-174902ca7aed:8640a7f554d1d0cd7650505530d87bf12b81eb85ec5f7b0bc4bf9c6f09140ce1`.

Źródło teraz: lat=49.24787225375916, lon=19.88195744765718; data stanu=2026-06-02; GENEZA=jaskinia; WER_LOK=null; UWAGI=null.

Cel: `KSW-0147` / `C-0476`. CSV przed: `{"crs":"EPSG:4326","elevation":"absent","lat":49.24811663952398,"lon":19.880999960095412}`; źródło przesunięte o **74.823 m**. Dopisać `m-003`; istniejące pomiary `m-001, m-002` bez zmiany któregokolwiek pola. Nowy pomiar: TPN/source_record/nieweryfikowany, elevation=null, obie accuracy=null.

**Oddzielna propozycja best:** keep `m-002`; tryb `auto → manual`. Pozycja i wysokość eksportu dotychczasowego obiektu bez zmian. Powód: `Zachować dotychczasowy punkt eksportu; nowa lokalizacja TPN trafia wyłącznie do historii. Data edycji źródła nie dowodzi nowszego pomiaru terenowego.`.

Różnice metadanych źródła: `{"WERYF":{"before":0,"after":1}}`. Proponowane akcje: append_measurement + jawny best_action; bez nadpisania notes starego pomiaru.

### B016 — Szczelina na Drodze Steckiego

GLOBALID `766d6d08-d9fd-492c-95de-6cc01a2efd24`; change_id `766d6d08-d9fd-492c-95de-6cc01a2efd24:18eaf6801b17633b4b4ea05262f40c297599af018619795bacf4579a3eea8809`.

Źródło teraz: lat=49.24121577065699, lon=19.90536621884487; data stanu=2026-05-09; GENEZA=jaskinia; WER_LOK="FF 09052026"; UWAGI=null.

Cel: `MTW-0033` / `C-0409`. CSV przed: `{"crs":"EPSG:4326","elevation":"absent","lat":49.24208433394799,"lon":19.906927265078853}`; źródło przesunięte o **149.171 m**. Dopisać `m-003`; istniejące pomiary `m-001, m-002` bez zmiany któregokolwiek pola. Nowy pomiar: TPN/source_record/nieweryfikowany, elevation=null, obie accuracy=null.

**Oddzielna propozycja best:** keep `m-002`; tryb `auto → manual`. Pozycja i wysokość eksportu dotychczasowego obiektu bez zmian. Powód: `Zachować dotychczasowy punkt eksportu; nowa lokalizacja TPN trafia wyłącznie do historii. Data edycji źródła nie dowodzi nowszego pomiaru terenowego.`.

Różnice metadanych źródła: `{"WERYF":{"before":0,"after":1},"WER_LOK":{"before":null,"after":"FF 09052026"}}`. Proponowane akcje: append_measurement + jawny best_action; bez nadpisania notes starego pomiaru.

### B017 — Dziura w Żlebku

GLOBALID `83869a78-6375-4f82-bc45-cbed0f9b7236`; change_id `83869a78-6375-4f82-bc45-cbed0f9b7236:59d3b3312d7ddb4ea49a5fcc66c237d49ef9bbd0346eae9750c75a642bc461c9`.

Źródło teraz: lat=49.262707573633136, lon=19.881245493231482; data stanu=2026-05-21; GENEZA=jaskinia; WER_LOK="FF 21052026"; UWAGI=null.

Cel: `MTW-0035` / `C-0420`. CSV przed: `{"crs":"EPSG:4326","elevation":"absent","lat":49.26285556469619,"lon":19.881461143097734}`; źródło przesunięte o **22.743 m**. Dopisać `m-003`; istniejące pomiary `m-001, m-002` bez zmiany któregokolwiek pola. Nowy pomiar: TPN/source_record/nieweryfikowany, elevation=null, obie accuracy=null.

**Oddzielna propozycja best:** keep `m-002`; tryb `auto → manual`. Pozycja i wysokość eksportu dotychczasowego obiektu bez zmian. Powód: `Zachować dotychczasowy punkt eksportu; nowa lokalizacja TPN trafia wyłącznie do historii. Data edycji źródła nie dowodzi nowszego pomiaru terenowego.`.

Różnice metadanych źródła: `{"WERYF":{"before":0,"after":1},"WER_LOK":{"before":null,"after":"FF 21052026"}}`. Proponowane akcje: append_measurement + jawny best_action; bez nadpisania notes starego pomiaru.

### B018 — Nyża pod Progiem w Kończystej

GLOBALID `9ba8f361-d7aa-413f-bc86-ac235940f603`; change_id `9ba8f361-d7aa-413f-bc86-ac235940f603:6a14de86be2d7feb1b912202546fc2f88891196a4b32b5885aa46dd2a91be446`.

Źródło teraz: lat=49.26330019605871, lon=19.87941770037199; data stanu=2026-05-21; GENEZA=jaskinia; WER_LOK="FF 21052026"; UWAGI=null.

Cel: `MTW-0039` / `C-0536`. CSV przed: `{"crs":"EPSG:4326","elevation":"absent","lat":49.26372345142175,"lon":19.88020701888239}`; źródło przesunięte o **74.272 m**. Dopisać `m-003`; istniejące pomiary `m-001, m-002` bez zmiany któregokolwiek pola. Nowy pomiar: TPN/source_record/nieweryfikowany, elevation=null, obie accuracy=null.

**Oddzielna propozycja best:** keep `m-002`; tryb `auto → manual`. Pozycja i wysokość eksportu dotychczasowego obiektu bez zmian. Powód: `Zachować dotychczasowy punkt eksportu; nowa lokalizacja TPN trafia wyłącznie do historii. Data edycji źródła nie dowodzi nowszego pomiaru terenowego.`.

Różnice metadanych źródła: `{"WERYF":{"before":0,"after":1},"WER_LOK":{"before":null,"after":"FF 21052026"}}`. Proponowane akcje: append_measurement + jawny best_action; bez nadpisania notes starego pomiaru.

### B019 — Okap w Kończystej Turni

GLOBALID `b2a16ea5-23c8-4e73-bbe7-b4ce1cdf5440`; change_id `b2a16ea5-23c8-4e73-bbe7-b4ce1cdf5440:6142c1d9210149d8a443958df42e169bc6535f64df59f282266b592213436996`.

Źródło teraz: lat=49.263577417975604, lon=19.878911640356993; data stanu=2026-05-04; GENEZA=jaskinia; WER_LOK="FF NMT 04052026"; UWAGI=null.

Cel: `MTW-0052` / `C-0672`. CSV przed: `{"crs":"EPSG:4326","elevation":"absent","lat":49.26362292664921,"lon":19.87911012389721}`; źródło przesunięte o **15.308 m**. Dopisać `m-003`; istniejące pomiary `m-001, m-002` bez zmiany któregokolwiek pola. Nowy pomiar: TPN/source_record/nieweryfikowany, elevation=null, obie accuracy=null.

**Oddzielna propozycja best:** keep `m-002`; tryb `auto → manual`. Pozycja i wysokość eksportu dotychczasowego obiektu bez zmian. Powód: `Zachować dotychczasowy punkt eksportu; nowa lokalizacja TPN trafia wyłącznie do historii. Data edycji źródła nie dowodzi nowszego pomiaru terenowego.`.

Różnice metadanych źródła: `{"WERYF":{"before":0,"after":1},"WER_LOK":{"before":null,"after":"FF NMT 04052026"}}`. Proponowane akcje: append_measurement + jawny best_action; bez nadpisania notes starego pomiaru.

### B020 — Koprowa Studnia

GLOBALID `b605e5ea-f1a5-43a2-803c-030b412b7415`; change_id `b605e5ea-f1a5-43a2-803c-030b412b7415:4f6c10b4f9d019c1e909da758dbe31e1dcd0b9c13a022f6a2cf015b45380999b`.

Źródło teraz: lat=49.23935809141422, lon=19.930249838155245; data stanu=2026-02-11; GENEZA=jaskinia; WER_LOK="11-02-2020 FF ortofotomapa"; UWAGI=null.

Cel: `MLW-0020` / `C-0508`. CSV przed: `{"crs":"EPSG:4326","elevation":"absent","lat":49.239347293489594,"lon":19.930248067221417}`; źródło przesunięte o **1.208 m**. Dopisać `m-003`; istniejące pomiary `m-001, m-002` bez zmiany któregokolwiek pola. Nowy pomiar: TPN/source_record/nieweryfikowany, elevation=null, obie accuracy=null.

**Oddzielna propozycja best:** keep `m-002`; tryb `auto → manual`. Pozycja i wysokość eksportu dotychczasowego obiektu bez zmian. Powód: `Zachować dotychczasowy punkt eksportu; nowa lokalizacja TPN trafia wyłącznie do historii. Data edycji źródła nie dowodzi nowszego pomiaru terenowego.`.

Różnice metadanych źródła: `{}`. Proponowane akcje: append_measurement + jawny best_action; bez nadpisania notes starego pomiaru.

### B021 — Mała Dziura w Kończystej Turni

GLOBALID `c4a17714-5976-4b41-a6a6-9eacae7e9421`; change_id `c4a17714-5976-4b41-a6a6-9eacae7e9421:b1d84e68c2e0bee43393ff092fd6941b777558d11c17d789a22e9ee230740274`.

Źródło teraz: lat=49.26426450542717, lon=19.87816642861684; data stanu=2026-05-04; GENEZA=jaskinia; WER_LOK="FF NMT 04052026"; UWAGI=null.

Cel: `MTW-0065` / `C-0847`. CSV przed: `{"crs":"EPSG:4326","elevation":"absent","lat":49.264154234831665,"lon":19.8782737164101}`; źródło przesunięte o **14.539 m**. Dopisać `m-003`; istniejące pomiary `m-001, m-002` bez zmiany któregokolwiek pola. Nowy pomiar: TPN/source_record/nieweryfikowany, elevation=null, obie accuracy=null.

**Oddzielna propozycja best:** keep `m-002`; tryb `auto → manual`. Pozycja i wysokość eksportu dotychczasowego obiektu bez zmian. Powód: `Zachować dotychczasowy punkt eksportu; nowa lokalizacja TPN trafia wyłącznie do historii. Data edycji źródła nie dowodzi nowszego pomiaru terenowego.`.

Różnice metadanych źródła: `{"WERYF":{"before":0,"after":1},"WER_LOK":{"before":null,"after":"FF NMT 04052026"}}`. Proponowane akcje: append_measurement + jawny best_action; bez nadpisania notes starego pomiaru.

### B022 — Jaskinia Marmurowa

GLOBALID `c5bcc87d-2f7e-42b5-8433-f72c556b8618`; change_id `c5bcc87d-2f7e-42b5-8433-f72c556b8618:18c64f5ccbd098e674be7c8d7c54bdd54c75260615c61ac7f18460ceba7c9162`.

Źródło teraz: lat=49.23937312351105, lon=19.900823468627657; data stanu=2026-02-11; GENEZA=jaskinia; WER_LOK="ortofoto FF 12-05-2020"; UWAGI=null.

Cel: `MTZ-0018` / `C-0184`. CSV przed: `{"crs":"EPSG:4326","elevation":"absent","lat":49.2393721034716,"lon":19.900800629206767}`; źródło przesunięte o **1.667 m**. Dopisać `m-003`; istniejące pomiary `m-001, m-002` bez zmiany któregokolwiek pola. Nowy pomiar: TPN/source_record/nieweryfikowany, elevation=null, obie accuracy=null.

**Oddzielna propozycja best:** keep `m-002`; tryb `auto → manual`. Pozycja i wysokość eksportu dotychczasowego obiektu bez zmian. Powód: `Zachować dotychczasowy punkt eksportu; nowa lokalizacja TPN trafia wyłącznie do historii. Data edycji źródła nie dowodzi nowszego pomiaru terenowego.`.

Różnice metadanych źródła: `{}`. Proponowane akcje: append_measurement + jawny best_action; bez nadpisania notes starego pomiaru.

### B023 — Zaspałkowa Szczelina

GLOBALID `ca9ef295-4fb4-43d5-9d7e-005dac6ff8b4`; change_id `ca9ef295-4fb4-43d5-9d7e-005dac6ff8b4:7301437eb1f6a50080da782f7ddfd3f34f24333b3aa663da1ce5a5448e85c2ba`.

Źródło teraz: lat=49.238599709660214, lon=19.927715368320143; data stanu=2026-02-11; GENEZA=jaskinia; WER_LOK=null; UWAGI=null.

Cel: `MLW-0014` / `C-0416`. CSV przed: `{"crs":"EPSG:4326","elevation":"absent","lat":49.238619412750445,"lon":19.92771107633848}`; źródło przesunięte o **2.213 m**. Dopisać `m-003`; istniejące pomiary `m-001, m-002` bez zmiany któregokolwiek pola. Nowy pomiar: TPN/source_record/nieweryfikowany, elevation=null, obie accuracy=null.

**Oddzielna propozycja best:** keep `m-002`; tryb `auto → manual`. Pozycja i wysokość eksportu dotychczasowego obiektu bez zmian. Powód: `Zachować dotychczasowy punkt eksportu; nowa lokalizacja TPN trafia wyłącznie do historii. Data edycji źródła nie dowodzi nowszego pomiaru terenowego.`.

Różnice metadanych źródła: `{}`. Proponowane akcje: append_measurement + jawny best_action; bez nadpisania notes starego pomiaru.

### B024 — Jaskinia Niska

GLOBALID `cde95846-f436-4079-8594-4268e6048a6d`; change_id `cde95846-f436-4079-8594-4268e6048a6d:a48c9eb59eaec034afef8ae325d213c5649ac1f65df387aae31f15e9e35a133a`.

Źródło teraz: lat=49.26426237097673, lon=19.87770642143427; data stanu=2026-05-04; GENEZA=jaskinia; WER_LOK="FF NMT 04052026"; UWAGI=null.

Cel: `MTW-0063` / `C-0824`. CSV przed: `{"crs":"EPSG:4326","elevation":"absent","lat":49.2641039651145,"lon":19.87772519670315}`; źródło przesunięte o **17.670 m**. Dopisać `m-003`; istniejące pomiary `m-001, m-002` bez zmiany któregokolwiek pola. Nowy pomiar: TPN/source_record/nieweryfikowany, elevation=null, obie accuracy=null.

**Oddzielna propozycja best:** keep `m-002`; tryb `auto → manual`. Pozycja i wysokość eksportu dotychczasowego obiektu bez zmian. Powód: `Zachować dotychczasowy punkt eksportu; nowa lokalizacja TPN trafia wyłącznie do historii. Data edycji źródła nie dowodzi nowszego pomiaru terenowego.`.

Różnice metadanych źródła: `{"WERYF":{"before":0,"after":1},"WER_LOK":{"before":null,"after":"FF NMT 04052026"}}`. Proponowane akcje: append_measurement + jawny best_action; bez nadpisania notes starego pomiaru.

### B025 — Schronik w Kończystej Turni

GLOBALID `d532520a-cc0f-4f01-9089-01c883cc553b`; change_id `d532520a-cc0f-4f01-9089-01c883cc553b:2b21c2931a2f7576806aedb54b6de181fd65fc109658d53362738e6e58a5f49a`.

Źródło teraz: lat=49.26373292586074, lon=19.877677490491408; data stanu=2026-05-04; GENEZA=jaskinia; WER_LOK="FF NMT 04052026"; UWAGI=null.

Cel: `MTW-0017` / `C-0165`. CSV przed: `{"crs":"EPSG:4326","elevation":"absent","lat":49.263609525873136,"lon":19.87773649990552}`; źródło przesunięte o **14.380 m**. Dopisać `m-003`; istniejące pomiary `m-001, m-002` bez zmiany któregokolwiek pola. Nowy pomiar: TPN/source_record/nieweryfikowany, elevation=null, obie accuracy=null.

**Oddzielna propozycja best:** keep `m-002`; tryb `auto → manual`. Pozycja i wysokość eksportu dotychczasowego obiektu bez zmian. Powód: `Zachować dotychczasowy punkt eksportu; nowa lokalizacja TPN trafia wyłącznie do historii. Data edycji źródła nie dowodzi nowszego pomiaru terenowego.`.

Różnice metadanych źródła: `{"WERYF":{"before":0,"after":1},"WER_LOK":{"before":null,"after":"FF NMT 04052026"}}`. Proponowane akcje: append_measurement + jawny best_action; bez nadpisania notes starego pomiaru.

### B026 — Dziura Niżnia w Kończystej Turni

GLOBALID `dca8221f-d3c2-4eb2-98ea-77957bb07a1a`; change_id `dca8221f-d3c2-4eb2-98ea-77957bb07a1a:7ab7aedd7b9cb7ea5782adbc723fbb3f52ce7b2ae33729200e0f4048a79fbd66`.

Źródło teraz: lat=49.26384966106653, lon=19.87802359643874; data stanu=2026-05-04; GENEZA=jaskinia; WER_LOK="FF NMT 04052026"; UWAGI=null.

Cel: `MTW-0060` / `C-0778`. CSV przed: `{"crs":"EPSG:4326","elevation":"absent","lat":49.263614239606895,"lon":19.87821738549228}`; źródło przesunięte o **29.740 m**. Dopisać `m-003`; istniejące pomiary `m-001, m-002` bez zmiany któregokolwiek pola. Nowy pomiar: TPN/source_record/nieweryfikowany, elevation=null, obie accuracy=null.

**Oddzielna propozycja best:** keep `m-002`; tryb `auto → manual`. Pozycja i wysokość eksportu dotychczasowego obiektu bez zmian. Powód: `Zachować dotychczasowy punkt eksportu; nowa lokalizacja TPN trafia wyłącznie do historii. Data edycji źródła nie dowodzi nowszego pomiaru terenowego.`.

Różnice metadanych źródła: `{"WERYF":{"before":0,"after":1},"WER_LOK":{"before":null,"after":"FF NMT 04052026"}}`. Proponowane akcje: append_measurement + jawny best_action; bez nadpisania notes starego pomiaru.

### B027 — Jaskinia Świstacza

GLOBALID `de04bc2c-8e52-43a7-8881-0677c9a98590`; change_id `de04bc2c-8e52-43a7-8881-0677c9a98590:46a91bb5220100c07a632a1a892f95070bd76990a1b76f08eefc93e85c703d17`.

Źródło teraz: lat=49.23930995267978, lon=19.930685823312448; data stanu=2026-02-11; GENEZA=jaskinia; WER_LOK="11-02-2020 FF ortofotomapa"; UWAGI=null.

Cel: `MLW-0028` / `C-0657`. CSV przed: `{"crs":"EPSG:4326","elevation":"absent","lat":49.239314307520935,"lon":19.93066796095015}`; źródło przesunięte o **1.388 m**. Dopisać `m-003`; istniejące pomiary `m-001, m-002` bez zmiany któregokolwiek pola. Nowy pomiar: TPN/source_record/nieweryfikowany, elevation=null, obie accuracy=null.

**Oddzielna propozycja best:** keep `m-002`; tryb `auto → manual`. Pozycja i wysokość eksportu dotychczasowego obiektu bez zmian. Powód: `Zachować dotychczasowy punkt eksportu; nowa lokalizacja TPN trafia wyłącznie do historii. Data edycji źródła nie dowodzi nowszego pomiaru terenowego.`.

Różnice metadanych źródła: `{}`. Proponowane akcje: append_measurement + jawny best_action; bez nadpisania notes starego pomiaru.

### B028 — Dziura pod Ratuszem

GLOBALID `e0642496-f87c-4eee-a7a0-a60365191209`; change_id `e0642496-f87c-4eee-a7a0-a60365191209:b08c96f057b7583409161f745f5e661c8561f4d330753ac0dc5f6040c4fe4667`.

Źródło teraz: lat=49.24253336771759, lon=19.905484187953224; data stanu=2026-05-09; GENEZA=jaskinia; WER_LOK="FF 09052026"; UWAGI=null.

Cel: `MTW-0057` / `C-0744`. CSV przed: `{"crs":"EPSG:4326","elevation":"absent","lat":49.24220941234638,"lon":19.905894566305243}`; źródło przesunięte o **46.808 m**. Dopisać `m-003`; istniejące pomiary `m-001, m-002` bez zmiany któregokolwiek pola. Nowy pomiar: TPN/source_record/nieweryfikowany, elevation=null, obie accuracy=null.

**Oddzielna propozycja best:** keep `m-002`; tryb `auto → manual`. Pozycja i wysokość eksportu dotychczasowego obiektu bez zmian. Powód: `Zachować dotychczasowy punkt eksportu; nowa lokalizacja TPN trafia wyłącznie do historii. Data edycji źródła nie dowodzi nowszego pomiaru terenowego.`.

Różnice metadanych źródła: `{"WERYF":{"before":0,"after":1},"WER_LOK":{"before":null,"after":"FF 09052026"}}`. Proponowane akcje: append_measurement + jawny best_action; bez nadpisania notes starego pomiaru.

### B029 — Nyża pod Zachodem Pilotów

GLOBALID `e6ba5010-45f5-4769-9026-229423ddf3cb`; change_id `e6ba5010-45f5-4769-9026-229423ddf3cb:9ee52a0b3dddd95a389f2da08166a2addb17cb420cb7b22c21ef6659e552a0ce`.

Źródło teraz: lat=49.25277039955315, lon=19.92907822473404; data stanu=2026-05-27; GENEZA=jaskinia; WER_LOK="17-05-2025 FF NMT"; UWAGI=null.

Cel: `STR-0028` / `C-0984`. CSV przed: `{"crs":"EPSG:4326","elevation":"absent","lat":49.2526949682589,"lon":19.929166613270816}`; źródło przesunięte o **10.573 m**. Dopisać `m-002`; istniejące pomiary `m-001` bez zmiany któregokolwiek pola. Nowy pomiar: TPN/source_record/nieweryfikowany, elevation=null, obie accuracy=null.

**Oddzielna propozycja best:** keep `m-001`; tryb `auto → manual`. Pozycja i wysokość eksportu dotychczasowego obiektu bez zmian. Powód: `Zachować dotychczasowy punkt eksportu; nowa lokalizacja TPN trafia wyłącznie do historii. Data edycji źródła nie dowodzi nowszego pomiaru terenowego.`.

Różnice metadanych źródła: `{"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}}`. Proponowane akcje: append_measurement + jawny best_action; bez nadpisania notes starego pomiaru.

### B030 — Nyża w Kończystej

GLOBALID `f3ae1e5e-ba6a-4c62-86fe-a4f42892808c`; change_id `f3ae1e5e-ba6a-4c62-86fe-a4f42892808c:81b8b53700e122624330e9a4714d858d5dca686412def381ef7cc7f497539166`.

Źródło teraz: lat=49.26369744590149, lon=19.878434328324417; data stanu=2026-05-04; GENEZA=jaskinia; WER_LOK="FF NMT 04052026"; UWAGI=null.

Cel: `MTW-0005` / `C-0091`. CSV przed: `{"crs":"EPSG:4326","elevation":"absent","lat":49.263711448091684,"lon":19.878970769188165}`; źródło przesunięte o **39.076 m**. Dopisać `m-003`; istniejące pomiary `m-001, m-002` bez zmiany któregokolwiek pola. Nowy pomiar: TPN/source_record/nieweryfikowany, elevation=null, obie accuracy=null.

**Oddzielna propozycja best:** keep `m-002`; tryb `auto → manual`. Pozycja i wysokość eksportu dotychczasowego obiektu bez zmian. Powód: `Zachować dotychczasowy punkt eksportu; nowa lokalizacja TPN trafia wyłącznie do historii. Data edycji źródła nie dowodzi nowszego pomiaru terenowego.`.

Różnice metadanych źródła: `{"WERYF":{"before":0,"after":1},"WER_LOK":{"before":null,"after":"FF NMT 04052026"}}`. Proponowane akcje: append_measurement + jawny best_action; bez nadpisania notes starego pomiaru.

### B031 — Schronisko Wschodnie w Kończystej

GLOBALID `f64fab23-53f9-45fa-a1c2-748d15a67568`; change_id `f64fab23-53f9-45fa-a1c2-748d15a67568:2410c06804369c428ce01c4e252a3e0643d2876bb65aecbb3fad0645da07fc7c`.

Źródło teraz: lat=49.26364386529371, lon=19.87959767840208; data stanu=2026-05-21; GENEZA=jaskinia; WER_LOK="FF 21052026"; UWAGI=null.

Cel: `MTW-0062` / `C-0803`. CSV przed: `{"crs":"EPSG:4326","elevation":"absent","lat":49.263362534731066,"lon":19.880077683634262}`; źródło przesunięte o **46.899 m**. Dopisać `m-003`; istniejące pomiary `m-001, m-002` bez zmiany któregokolwiek pola. Nowy pomiar: TPN/source_record/nieweryfikowany, elevation=null, obie accuracy=null.

**Oddzielna propozycja best:** keep `m-002`; tryb `auto → manual`. Pozycja i wysokość eksportu dotychczasowego obiektu bez zmian. Powód: `Zachować dotychczasowy punkt eksportu; nowa lokalizacja TPN trafia wyłącznie do historii. Data edycji źródła nie dowodzi nowszego pomiaru terenowego.`.

Różnice metadanych źródła: `{"WERYF":{"before":0,"after":1},"WER_LOK":{"before":null,"after":"FF 21052026"}}`. Proponowane akcje: append_measurement + jawny best_action; bez nadpisania notes starego pomiaru.

## Grupa C — Nowe samodzielne obiekty

### C001 — Jaskinia w Kozim Grzbiecie

GLOBALID `4d57492d-d68a-471e-b00e-770a594a2c7b`; change_id `4d57492d-d68a-471e-b00e-770a594a2c7b:f6cf40c6ee81bd84bec7f8c4b1e0eb5ff19c1a5bfaff7bd16389de30ee0f1337`.

Źródło teraz: lat=49.234858453380134, lon=19.907862585693493; data stanu=2026-06-16; GENEZA=jaskinia; WER_LOK="FF16062026"; UWAGI=null.

Proponowane ID: `MTZ-0067` / `C-1005`, `category=jaskinia_otwor`, pierwszy pomiar `m-001` jako best auto. Dokładne wartości YAML: [warunkowy diff](simulated-domain.patch). 0 kandydatów po pełnym indeksie nazw TPN/PIG i wszystkich pomiarów oraz konkurentów partii. WER_LOK jest jedyną blokadą automatic_proposal; nie stanowi zgody człowieka. Proponowane rozstrzygnięcie ręczne: approve create_cave + new_object. Bez przyłączenia do istniejącej Jaskini.

### C002 — Gawra w Sarniej Skale

GLOBALID `551df3ad-f3e1-4920-bd23-d741ac938ba8`; change_id `551df3ad-f3e1-4920-bd23-d741ac938ba8:98097d7078619264ff5a264b978c3fc097731271dc2dfd45ef49d9753331e7ee`.

Źródło teraz: lat=49.26586630293456, lon=19.936818198902632; data stanu=2026-05-04; GENEZA=jaskinia; WER_LOK="FF NMT 04052026"; UWAGI=null.

Proponowane ID: `STR-0030` / `C-1006`, `category=jaskinia_otwor`, pierwszy pomiar `m-001` jako best auto. Dokładne wartości YAML: [warunkowy diff](simulated-domain.patch). 0 kandydatów po pełnym indeksie nazw TPN/PIG i wszystkich pomiarów oraz konkurentów partii. WER_LOK jest jedyną blokadą automatic_proposal; nie stanowi zgody człowieka. Proponowane rozstrzygnięcie ręczne: approve create_cave + new_object. Bez przyłączenia do istniejącej Jaskini.

### C003 — Okno przy Źródle

GLOBALID `6ebd9c00-d272-4909-85ec-00ae2bb6632d`; change_id `6ebd9c00-d272-4909-85ec-00ae2bb6632d:6064efb0ca1761b8a62171e586f39c2ac7496173b0793400a52b8b92821e69a4`.

Źródło teraz: lat=49.25953732835311, lon=19.953589664455603; data stanu=2026-05-09; GENEZA=jaskinia; WER_LOK="FF 09052026"; UWAGI=null.

Proponowane ID: `BIA-0009` / `C-1007`, `category=jaskinia_otwor`, pierwszy pomiar `m-001` jako best auto. Dokładne wartości YAML: [warunkowy diff](simulated-domain.patch). 0 kandydatów po pełnym indeksie nazw TPN/PIG i wszystkich pomiarów oraz konkurentów partii. WER_LOK jest jedyną blokadą automatic_proposal; nie stanowi zgody człowieka. Proponowane rozstrzygnięcie ręczne: approve create_cave + new_object. Bez przyłączenia do istniejącej Jaskini.

### C004 — Gawra w Grześkówkach

GLOBALID `c9dc792d-fdd9-4ad9-b024-26b8c795cdaf`; change_id `c9dc792d-fdd9-4ad9-b024-26b8c795cdaf:7e95dddc0427505ccb17e4324874690d9a04a23a5e8fa6e415dc9eb2a3c1381c`.

Źródło teraz: lat=49.268889145683346, lon=19.936981261083442; data stanu=2026-10-04; GENEZA=jaskinia; WER_LOK="04102026"; UWAGI=null.

Proponowane ID: `DZI-0011` / `C-1008`, `category=jaskinia_otwor`, pierwszy pomiar `m-001` jako best auto. Dokładne wartości YAML: [warunkowy diff](simulated-domain.patch). 0 kandydatów po pełnym indeksie nazw TPN/PIG i wszystkich pomiarów oraz konkurentów partii. WER_LOK jest jedyną blokadą automatic_proposal; nie stanowi zgody człowieka. Proponowane rozstrzygnięcie ręczne: approve create_cave + new_object. Bez przyłączenia do istniejącej Jaskini.

### C005 — Jaskinia Lodowa Ponorowa

GLOBALID `f27fa875-821f-45f6-8f02-c5a9ffc579e4`; change_id `f27fa875-821f-45f6-8f02-c5a9ffc579e4:45b941debabd15a3fc6c0b3fbf98e0d90141221e0a049a3d82dd7a6a473cbb09`.

Źródło teraz: lat=49.234277473653904, lon=19.9063092182706; data stanu=2026-06-16; GENEZA=jaskinia; WER_LOK="FF16062026"; UWAGI=null.

Proponowane ID: `MTZ-0068` / `C-1009`, `category=jaskinia_otwor`, pierwszy pomiar `m-001` jako best auto. Dokładne wartości YAML: [warunkowy diff](simulated-domain.patch). 0 kandydatów po pełnym indeksie nazw TPN/PIG i wszystkich pomiarów oraz konkurentów partii. WER_LOK jest jedyną blokadą automatic_proposal; nie stanowi zgody człowieka. Proponowane rozstrzygnięcie ręczne: approve create_cave + new_object. Bez przyłączenia do istniejącej Jaskini.

## Grupa D — Odroczenia wymagające potwierdzenia tożsamości

### D001 — Szczelina przy Zbójeckiej Dziurze

GLOBALID `00a63f59-3d03-4703-a18e-27a0a75a7da1`; change_id `00a63f59-3d03-4703-a18e-27a0a75a7da1:267536eb2e2f292ec181cc6b7f18ce5e46f8921d6f3f8a0a2a3fd855b80e0b3c`.

Źródło teraz: lat=49.247641014687375, lon=19.811788641224744; data stanu=2026-06-16; GENEZA=jaskinia; WER_LOK="FF16062026"; UWAGI=null.

**Proponowane defer:** Odroczyć: brak dowodu tożsamości/odrębności wobec konkretnych kandydatów z raportu; nie tworzyć ani nie scalać obiektów, nie przypinać źródła.

| Kandydat | Nazwy / cel | Sygnały i dystanse |
|---|---|---|
| object:CHZ-0012 | Zbójecka Dziura / {"cave_id":"C-0370","object_id":"CHZ-0012"} | 14.893 m; pomiar m-001; best=False; status=nieweryfikowany; 8.484 m; pomiar m-002; best=True; status=nieweryfikowany |
| source:current:d96cd642-e9d3-4eb8-b9dc-d7df3f449705 | Rura w Olejarni / {"globalid":"d96cd642-e9d3-4eb8-b9dc-d7df3f449705","origin":"current"} | 28.597 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:e70f5d13-0917-470d-abb0-5d7853d98016 | Zbójecka Dziura / {"globalid":"e70f5d13-0917-470d-abb0-5d7853d98016","origin":"current"} | 8.481 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:e70f5d13-0917-470d-abb0-5d7853d98016 | Zbójecka Dziura / {"globalid":"e70f5d13-0917-470d-abb0-5d7853d98016","origin":"baseline"} | 8.484 m; pomiar źródłowy; best=n/d; status=n/d |

Do rozstrzygnięcia potrzebne oznaczenia otworów/plan lub inny dowód wskazujący, czy to ten sam otwór, inne otwory jednej jaskini, czy różne obiekty. Współrzędne i podobna nazwa są tylko sygnałem. Defer zachowa rewizję i snapshot w trwałej kolejce po zatwierdzeniu tej propozycji.

### D002 — Okno w Ciemniaku

GLOBALID `041adf4d-119c-4a51-93b9-982b2127d2a4`; change_id `041adf4d-119c-4a51-93b9-982b2127d2a4:d68904fc2927f6e55655097e430115da4bb459203bc1d65ee692423c543a7891`.

Źródło teraz: lat=49.23205854949837, lon=19.904428134768768; data stanu=2026-06-16; GENEZA=jaskinia; WER_LOK="FF16062026"; UWAGI=null.

**Proponowane defer:** Odroczyć: brak dowodu tożsamości/odrębności wobec konkretnych kandydatów z raportu; nie tworzyć ani nie scalać obiektów, nie przypinać źródła.

| Kandydat | Nazwy / cel | Sygnały i dystanse |
|---|---|---|
| source:current:0bfc7731-a83a-40e6-b773-766798366add | Korytarz w Ciemniaku / {"globalid":"0bfc7731-a83a-40e6-b773-766798366add","origin":"current"} | 94.682 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:2cb1b34b-9aa8-440b-96e7-729bd2cdf7b6 | Okno w Ciemniaku / {"globalid":"2cb1b34b-9aa8-440b-96e7-729bd2cdf7b6","origin":"current"} | {"code":"exact_name","left":{"field":"current.NAZWA","value":"Okno w Ciemniaku"},"normalized":"okno w ciemniaku","right":{"field":"current.NAZWA","value":"Okno w Ciemniaku"}}; 3.352 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:4bbef00c-a6c1-4706-9590-9dbc61b70ddd | Okno w Ciemniaku / {"globalid":"4bbef00c-a6c1-4706-9590-9dbc61b70ddd","origin":"current"} | {"code":"exact_name","left":{"field":"current.NAZWA","value":"Okno w Ciemniaku"},"normalized":"okno w ciemniaku","right":{"field":"current.NAZWA","value":"Okno w Ciemniaku"}}; 1.719 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:8e246480-f366-4d0f-ba7e-a601e865fd03 | Korytarz pod Ciemniakiem / {"globalid":"8e246480-f366-4d0f-ba7e-a601e865fd03","origin":"current"} | 94.688 m; pomiar źródłowy; best=n/d; status=n/d |

Do rozstrzygnięcia potrzebne oznaczenia otworów/plan lub inny dowód wskazujący, czy to ten sam otwór, inne otwory jednej jaskini, czy różne obiekty. Współrzędne i podobna nazwa są tylko sygnałem. Defer zachowa rewizję i snapshot w trwałej kolejce po zatwierdzeniu tej propozycji.

### D003 — Korytarz w Ciemniaku

GLOBALID `0bfc7731-a83a-40e6-b773-766798366add`; change_id `0bfc7731-a83a-40e6-b773-766798366add:0c0261924a0f921891f1cacae7e9bbb61fedcf6b0408b8eee15ac477efbcdcb1`.

Źródło teraz: lat=49.2321110675022, lon=19.90313059173134; data stanu=2026-06-16; GENEZA=None; WER_LOK=null; UWAGI=null.

**Proponowane defer:** Odroczyć: brak dowodu tożsamości/odrębności wobec konkretnych kandydatów z raportu; nie tworzyć ani nie scalać obiektów, nie przypinać źródła. Źródło nie określa jednoznacznej kategorii.

| Kandydat | Nazwy / cel | Sygnały i dystanse |
|---|---|---|
| source:current:041adf4d-119c-4a51-93b9-982b2127d2a4 | Okno w Ciemniaku / {"globalid":"041adf4d-119c-4a51-93b9-982b2127d2a4","origin":"current"} | 94.682 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:2cb1b34b-9aa8-440b-96e7-729bd2cdf7b6 | Okno w Ciemniaku / {"globalid":"2cb1b34b-9aa8-440b-96e7-729bd2cdf7b6","origin":"current"} | 95.071 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:4bbef00c-a6c1-4706-9590-9dbc61b70ddd | Okno w Ciemniaku / {"globalid":"4bbef00c-a6c1-4706-9590-9dbc61b70ddd","origin":"current"} | 95.329 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:8e246480-f366-4d0f-ba7e-a601e865fd03 | Korytarz pod Ciemniakiem / {"globalid":"8e246480-f366-4d0f-ba7e-a601e865fd03","origin":"current"} | 0.097 m; pomiar źródłowy; best=n/d; status=n/d |

Do rozstrzygnięcia potrzebne oznaczenia otworów/plan lub inny dowód wskazujący, czy to ten sam otwór, inne otwory jednej jaskini, czy różne obiekty. Współrzędne i podobna nazwa są tylko sygnałem. Defer zachowa rewizję i snapshot w trwałej kolejce po zatwierdzeniu tej propozycji.

### D004 — Nyża pod Szarą Turnią III

GLOBALID `1792c71c-54b5-46ce-8e24-454f4a31e73f`; change_id `1792c71c-54b5-46ce-8e24-454f4a31e73f:59598f523bb151478b0da84bc47ff3c3fd5f294a526a700fca23599a88af9aff`.

Źródło teraz: lat=49.253266838681846, lon=19.927308030992126; data stanu=2026-06-14; GENEZA=jaskinia; WER_LOK="FF 14062026"; UWAGI=null.

**Proponowane defer:** Odroczyć: brak dowodu tożsamości/odrębności wobec konkretnych kandydatów z raportu; nie tworzyć ani nie scalać obiektów, nie przypinać źródła.

| Kandydat | Nazwy / cel | Sygnały i dystanse |
|---|---|---|
| source:current:55ed69a3-9228-452b-87ce-8133710292b1 | Nyża pod Szarą Turnią I / {"globalid":"55ed69a3-9228-452b-87ce-8133710292b1","origin":"current"} | {"code":"similar_name","left":{"field":"current.NAZWA","value":"Nyża pod Szarą Turnią III"},"right":{"field":"current.NAZWA","value":"Nyża pod Szarą Turnią I"},"similarity":0.92,"threshold":0.9}; 58.392 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:70fc9cd8-57de-4c66-a50f-674b3c6f5d55 | Nyża pod Szarą Turnią IV / {"globalid":"70fc9cd8-57de-4c66-a50f-674b3c6f5d55","origin":"current"} | {"code":"similar_name","left":{"field":"current.NAZWA","value":"Nyża pod Szarą Turnią III"},"right":{"field":"current.NAZWA","value":"Nyża pod Szarą Turnią IV"},"similarity":0.92,"threshold":0.9}; 45.026 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:b51c01e8-271e-4aef-802d-c87025a09845 | Nyża pod Szarą Turnią II / {"globalid":"b51c01e8-271e-4aef-802d-c87025a09845","origin":"current"} | {"code":"similar_name","left":{"field":"current.NAZWA","value":"Nyża pod Szarą Turnią III"},"right":{"field":"current.NAZWA","value":"Nyża pod Szarą Turnią II"},"similarity":0.96,"threshold":0.9}; 28.363 m; pomiar źródłowy; best=n/d; status=n/d |

Do rozstrzygnięcia potrzebne oznaczenia otworów/plan lub inny dowód wskazujący, czy to ten sam otwór, inne otwory jednej jaskini, czy różne obiekty. Współrzędne i podobna nazwa są tylko sygnałem. Defer zachowa rewizję i snapshot w trwałej kolejce po zatwierdzeniu tej propozycji.

### D005 — Schron nad Komorą w Kończystej Turni

GLOBALID `2549106f-2ea9-477a-a5d3-77e6b920c8e5`; change_id `2549106f-2ea9-477a-a5d3-77e6b920c8e5:bc178859ce6b645aa23444b1289021490b207a67d05154be86567bf7f1967be5`.

Źródło teraz: lat=49.26385313676503, lon=19.87900934046395; data stanu=2026-06-14; GENEZA=jaskinia; WER_LOK="FF 06062026"; UWAGI=null.

**Proponowane defer:** Odroczyć: brak dowodu tożsamości/odrębności wobec konkretnych kandydatów z raportu; nie tworzyć ani nie scalać obiektów, nie przypinać źródła.

| Kandydat | Nazwy / cel | Sygnały i dystanse |
|---|---|---|
| object:MTW-0005 | Nyża w Kończystej / {"cave_id":"C-0091","object_id":"MTW-0005"} | 16.006 m; pomiar m-001; best=False; status=nieweryfikowany; 16.006 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:MTW-0017 | Schronik w Kończystej Turni / {"cave_id":"C-0165","object_id":"MTW-0017"} | 96.524 m; pomiar m-001; best=False; status=nieweryfikowany; 96.524 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:MTW-0024 | Ciasna Norka / {"cave_id":"C-0280","object_id":"MTW-0024"} | 91.064 m; pomiar m-001; best=False; status=nieweryfikowany; 91.063 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:MTW-0031 | Dziura w Kończystej Niżnia / {"cave_id":"C-0395","object_id":"MTW-0031"} | 48.004 m; pomiar m-001; best=False; status=nieweryfikowany; 48.004 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:MTW-0039 | Nyża pod Progiem w Kończystej / {"cave_id":"C-0536","object_id":"MTW-0039"} | 88.358 m; pomiar m-001; best=False; status=nieweryfikowany; 88.358 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:MTW-0043 | Schron pod Kończystą / {"cave_id":"C-0566","object_id":"MTW-0043"} | 67.460 m; pomiar m-001; best=False; status=nieweryfikowany; 67.460 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:MTW-0052 | Okap w Kończystej Turni / {"cave_id":"C-0672","object_id":"MTW-0052"} | 26.632 m; pomiar m-001; best=False; status=nieweryfikowany; 26.633 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:MTW-0059 | Dziura w Kończystej Turni / {"cave_id":"C-0753","object_id":"MTW-0059"} | 36.000 m; pomiar m-001; best=False; status=nieweryfikowany; 36.001 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:MTW-0060 | Dziura Niżnia w Kończystej Turni / {"cave_id":"C-0778","object_id":"MTW-0060"} | 63.470 m; pomiar m-001; best=False; status=nieweryfikowany; 63.471 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:MTW-0062 | Schronisko Wschodnie w Kończystej / {"cave_id":"C-0803","object_id":"MTW-0062"} | 94.992 m; pomiar m-001; best=False; status=nieweryfikowany; 94.992 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:MTW-0063 | Jaskinia Niska / {"cave_id":"C-0824","object_id":"MTW-0063"} | 97.540 m; pomiar m-001; best=False; status=nieweryfikowany; 97.540 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:MTW-0065 | Mała Dziura w Kończystej Turni / {"cave_id":"C-0847","object_id":"MTW-0065"} | 63.151 m; pomiar m-001; best=False; status=nieweryfikowany; 63.151 m; pomiar m-002; best=True; status=nieweryfikowany |
| source:current:0257a120-426e-4b7d-b47f-1d9f853c6c85 | Dziura w Kończystej Niżnia / {"globalid":"0257a120-426e-4b7d-b47f-1d9f853c6c85","origin":"current"} | 69.217 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:0c34f113-d6d5-4e57-9db1-b240ed3533b5 | Schron pod Kończystą / {"globalid":"0c34f113-d6d5-4e57-9db1-b240ed3533b5","origin":"current"} | 70.553 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:1f9eaae2-f97d-4205-bf67-7a43e6ddb5e7 | Ciasna Norka / {"globalid":"1f9eaae2-f97d-4205-bf67-7a43e6ddb5e7","origin":"current"} | 81.222 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:37ef7fe5-6e87-47d4-97c8-cb0ebd9ddeee | Dziura nad Zahradziskami / {"globalid":"37ef7fe5-6e87-47d4-97c8-cb0ebd9ddeee","origin":"current"} | 29.068 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:4509213c-4194-4179-90e8-cffa30639191 | Koleba za Kończystą / {"globalid":"4509213c-4194-4179-90e8-cffa30639191","origin":"current"} | 93.998 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:7033eb52-9352-4f35-9adf-89490fbb5f1f | Dziura w Kończystej Turni / {"globalid":"7033eb52-9352-4f35-9adf-89490fbb5f1f","origin":"current"} | 64.901 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:9ba8f361-d7aa-413f-bc86-ac235940f603 | Nyża pod Progiem w Kończystej / {"globalid":"9ba8f361-d7aa-413f-bc86-ac235940f603","origin":"current"} | 68.301 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:9beb2e85-ecb8-432a-90d4-623df217c6da | Nyża za Jałowcem / {"globalid":"9beb2e85-ecb8-432a-90d4-623df217c6da","origin":"current"} | 41.381 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:b2a16ea5-23c8-4e73-bbe7-b4ce1cdf5440 | Okap w Kończystej Turni / {"globalid":"b2a16ea5-23c8-4e73-bbe7-b4ce1cdf5440","origin":"current"} | 31.478 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:c24021bb-73c2-4bc2-83f1-aabefc26492e | Komora w Kończystej Turni / {"globalid":"c24021bb-73c2-4bc2-83f1-aabefc26492e","origin":"current"} | 29.063 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:c4a17714-5976-4b41-a6a6-9eacae7e9421 | Mała Dziura w Kończystej Turni / {"globalid":"c4a17714-5976-4b41-a6a6-9eacae7e9421","origin":"current"} | 76.531 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:d532520a-cc0f-4f01-9089-01c883cc553b | Schronik w Kończystej Turni / {"globalid":"d532520a-cc0f-4f01-9089-01c883cc553b","origin":"current"} | 97.856 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:dca8221f-d3c2-4eb2-98ea-77957bb07a1a | Dziura Niżnia w Kończystej Turni / {"globalid":"dca8221f-d3c2-4eb2-98ea-77957bb07a1a","origin":"current"} | 71.748 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:f3ae1e5e-ba6a-4c62-86fe-a4f42892808c | Nyża w Kończystej / {"globalid":"f3ae1e5e-ba6a-4c62-86fe-a4f42892808c","origin":"current"} | 45.292 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:f64fab23-53f9-45fa-a1c2-748d15a67568 | Schronisko Wschodnie w Kończystej / {"globalid":"f64fab23-53f9-45fa-a1c2-748d15a67568","origin":"current"} | 48.738 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:0257a120-426e-4b7d-b47f-1d9f853c6c85 | Dziura w Kończystej Niżnia / {"globalid":"0257a120-426e-4b7d-b47f-1d9f853c6c85","origin":"baseline"} | 48.004 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:0c34f113-d6d5-4e57-9db1-b240ed3533b5 | Schron pod Kończystą / {"globalid":"0c34f113-d6d5-4e57-9db1-b240ed3533b5","origin":"baseline"} | 67.460 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:1f9eaae2-f97d-4205-bf67-7a43e6ddb5e7 | Ciasna Norka / {"globalid":"1f9eaae2-f97d-4205-bf67-7a43e6ddb5e7","origin":"baseline"} | 91.063 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:7033eb52-9352-4f35-9adf-89490fbb5f1f | Dziura w Kończystej Turni / {"globalid":"7033eb52-9352-4f35-9adf-89490fbb5f1f","origin":"baseline"} | 36.001 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:9ba8f361-d7aa-413f-bc86-ac235940f603 | Nyża pod Progiem w Kończystej / {"globalid":"9ba8f361-d7aa-413f-bc86-ac235940f603","origin":"baseline"} | 88.358 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:b2a16ea5-23c8-4e73-bbe7-b4ce1cdf5440 | Okap w Kończystej Turni / {"globalid":"b2a16ea5-23c8-4e73-bbe7-b4ce1cdf5440","origin":"baseline"} | 26.633 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:c4a17714-5976-4b41-a6a6-9eacae7e9421 | Mała Dziura w Kończystej Turni / {"globalid":"c4a17714-5976-4b41-a6a6-9eacae7e9421","origin":"baseline"} | 63.151 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:cde95846-f436-4079-8594-4268e6048a6d | Jaskinia Niska / {"globalid":"cde95846-f436-4079-8594-4268e6048a6d","origin":"baseline"} | 97.540 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:d532520a-cc0f-4f01-9089-01c883cc553b | Schronik w Kończystej Turni / {"globalid":"d532520a-cc0f-4f01-9089-01c883cc553b","origin":"baseline"} | 96.524 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:dca8221f-d3c2-4eb2-98ea-77957bb07a1a | Dziura Niżnia w Kończystej Turni / {"globalid":"dca8221f-d3c2-4eb2-98ea-77957bb07a1a","origin":"baseline"} | 63.471 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:f3ae1e5e-ba6a-4c62-86fe-a4f42892808c | Nyża w Kończystej / {"globalid":"f3ae1e5e-ba6a-4c62-86fe-a4f42892808c","origin":"baseline"} | 16.006 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:f64fab23-53f9-45fa-a1c2-748d15a67568 | Schronisko Wschodnie w Kończystej / {"globalid":"f64fab23-53f9-45fa-a1c2-748d15a67568","origin":"baseline"} | 94.992 m; pomiar źródłowy; best=n/d; status=n/d |

Do rozstrzygnięcia potrzebne oznaczenia otworów/plan lub inny dowód wskazujący, czy to ten sam otwór, inne otwory jednej jaskini, czy różne obiekty. Współrzędne i podobna nazwa są tylko sygnałem. Defer zachowa rewizję i snapshot w trwałej kolejce po zatwierdzeniu tej propozycji.

### D006 — Smocza Jama

GLOBALID `273b92b8-201b-443e-ad19-73de844b9f5b`; change_id `273b92b8-201b-443e-ad19-73de844b9f5b:7b80547a2199238dc2b383d4e530f21fe6fa3b87709e92d09b9f90ec0684581e`.

Źródło teraz: lat=49.237987023120034, lon=19.867534682198418; data stanu=2023-08-28; GENEZA=jaskinia; WER_LOK="28-08-2023 MB NMT"; UWAGI=null.

**Proponowane defer:** Odroczyć: brak dowodu tożsamości/odrębności wobec konkretnych kandydatów z raportu; nie tworzyć ani nie scalać obiektów, nie przypinać źródła. Smocza Jama/otwór N: potrzebne potwierdzenie odrębnego otworu i powiązania z C-0219; ten GUID istnieje w historycznym CSV.

| Kandydat | Nazwy / cel | Sygnały i dystanse |
|---|---|---|
| cave:C-0219 | Smocza Jama / {"cave_id":"C-0219","object_id":null} | {"code":"exact_name","left":{"field":"current.NAZWA","value":"Smocza Jama"},"normalized":"smocza jama","right":{"field":"C-0219.name","value":"Smocza Jama"}} |
| object:KSW-0065 | Smocza Jama / {"cave_id":"C-0219","object_id":"KSW-0065"} | {"code":"exact_name","left":{"field":"current.NAZWA","value":"Smocza Jama"},"normalized":"smocza jama","right":{"field":"KSW-0065.name_local","value":"Smocza Jama"}}; {"code":"exact_name","left":{"field":"current.NAZWA","value":"Smocza Jama"},"normalized":"smocza jama","right":{"field":"C-0219.name","value":"Smocza Jama"}}; 21.827 m; pomiar m-001; best=False; status=nieweryfikowany; 20.393 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:KSW-0082 | Dziura pod Smoczą Jamą / {"cave_id":"C-0268","object_id":"KSW-0082"} | 20.759 m; pomiar m-001; best=False; status=nieweryfikowany; 22.273 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:KSW-0143 | Schron pod Zbójnicką Turnią / {"cave_id":"C-0466","object_id":"KSW-0143"} | 13.083 m; pomiar m-001; best=False; status=nieweryfikowany; 13.082 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:KSW-0191 | Korytarzyk w Szczelinie / {"cave_id":"C-0675","object_id":"KSW-0191"} | 69.473 m; pomiar m-001; best=False; status=nieweryfikowany; 69.474 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:KSW-0203 | Schron za Smoczą Jamą / {"cave_id":"C-0721","object_id":"KSW-0203"} | 8.471 m; pomiar m-001; best=False; status=nieweryfikowany; 8.471 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:KSW-0219 | Szczelina pod Smoczą Jamą / {"cave_id":"C-0790","object_id":"KSW-0219"} | 54.053 m; pomiar m-001; best=False; status=nieweryfikowany; 54.053 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:KSW-0223 | Schron przy Smoczej Jamie / {"cave_id":"C-0821","object_id":"KSW-0223"} | 23.850 m; pomiar m-001; best=False; status=nieweryfikowany; 23.850 m; pomiar m-002; best=True; status=nieweryfikowany |
| pig:219:760 | Smocza Jama / {"pig_catalog_id":"760","source_row":219} | {"code":"exact_name","left":{"field":"current.NAZWA","value":"Smocza Jama"},"normalized":"smocza jama","right":{"field":"PIG.Nazwa","value":"Smocza Jama"}} |
| source:current:01a58cfe-5670-42a3-ade1-715cf1f1e7a4 | Jaskinia Mylna; N / {"globalid":"01a58cfe-5670-42a3-ade1-715cf1f1e7a4","origin":"current"} | {"code":"exact_name","left":{"field":"current.OTWÓR","value":"N"},"normalized":"n","right":{"field":"current.OTWÓR","value":"N"}} |
| source:current:0c942f35-3c72-4dd9-a0d1-511893b1a6ee | Schron pod Zbójnicką Turnią / {"globalid":"0c942f35-3c72-4dd9-a0d1-511893b1a6ee","origin":"current"} | 13.082 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:4bc59950-3b6f-4c61-b865-a44d6a3849c7 | Dziura pod Smoczą Jamą / {"globalid":"4bc59950-3b6f-4c61-b865-a44d6a3849c7","origin":"current"} | 22.271 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:78811f4c-ad7f-4979-998e-9e6f998f446c | Schron przy Smoczej Jamie / {"globalid":"78811f4c-ad7f-4979-998e-9e6f998f446c","origin":"current"} | 23.850 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:8cd9cafe-ed57-456a-95da-79be5518d09a | Szczelina pod Smoczą Jamą / {"globalid":"8cd9cafe-ed57-456a-95da-79be5518d09a","origin":"current"} | 54.053 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:b33edd51-a246-4a3a-a8fa-8ce95eec525d | Korytarzyk w Szczelinie / {"globalid":"b33edd51-a246-4a3a-a8fa-8ce95eec525d","origin":"current"} | 69.473 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:b8c9f363-3509-48db-9abc-90e665ef74c3 | Smocza Jama; S / {"globalid":"b8c9f363-3509-48db-9abc-90e665ef74c3","origin":"current"} | {"code":"exact_name","left":{"field":"current.NAZWA","value":"Smocza Jama"},"normalized":"smocza jama","right":{"field":"current.NAZWA","value":"Smocza Jama"}}; 20.396 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:b918424f-9161-4841-8bc8-0051445a4d29 | Jaskinia Czarna; N / {"globalid":"b918424f-9161-4841-8bc8-0051445a4d29","origin":"current"} | {"code":"exact_name","left":{"field":"current.OTWÓR","value":"N"},"normalized":"n","right":{"field":"current.OTWÓR","value":"N"}} |
| source:current:f22edcd0-acfd-4797-b2a0-cfd5b325bc8e | tunel w Skrajnej Giewonckiej Baszcie; N / {"globalid":"f22edcd0-acfd-4797-b2a0-cfd5b325bc8e","origin":"current"} | {"code":"exact_name","left":{"field":"current.OTWÓR","value":"N"},"normalized":"n","right":{"field":"current.OTWÓR","value":"N"}} |
| source:current:fcc7a4d6-7779-45d7-b594-af18f1ebb840 | Schron za Smoczą Jamą / {"globalid":"fcc7a4d6-7779-45d7-b594-af18f1ebb840","origin":"current"} | 8.471 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:01a58cfe-5670-42a3-ade1-715cf1f1e7a4 | Jaskinia Mylna; N / {"globalid":"01a58cfe-5670-42a3-ade1-715cf1f1e7a4","origin":"baseline"} | {"code":"exact_name","left":{"field":"current.OTWÓR","value":"N"},"normalized":"n","right":{"field":"baseline.OTWÓR","value":"N"}} |
| source:baseline:0c942f35-3c72-4dd9-a0d1-511893b1a6ee | Schron pod Zbójnicką Turnią / {"globalid":"0c942f35-3c72-4dd9-a0d1-511893b1a6ee","origin":"baseline"} | 13.082 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:4bc59950-3b6f-4c61-b865-a44d6a3849c7 | Dziura pod Smoczą Jamą / {"globalid":"4bc59950-3b6f-4c61-b865-a44d6a3849c7","origin":"baseline"} | 22.273 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:78811f4c-ad7f-4979-998e-9e6f998f446c | Schron przy Smoczej Jamie / {"globalid":"78811f4c-ad7f-4979-998e-9e6f998f446c","origin":"baseline"} | 23.850 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:8cd9cafe-ed57-456a-95da-79be5518d09a | Szczelina pod Smoczą Jamą / {"globalid":"8cd9cafe-ed57-456a-95da-79be5518d09a","origin":"baseline"} | 54.053 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:b33edd51-a246-4a3a-a8fa-8ce95eec525d | Korytarzyk w Szczelinie / {"globalid":"b33edd51-a246-4a3a-a8fa-8ce95eec525d","origin":"baseline"} | 69.474 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:b8c9f363-3509-48db-9abc-90e665ef74c3 | Smocza Jama; S / {"globalid":"b8c9f363-3509-48db-9abc-90e665ef74c3","origin":"baseline"} | {"code":"exact_name","left":{"field":"current.NAZWA","value":"Smocza Jama"},"normalized":"smocza jama","right":{"field":"baseline.NAZWA","value":"Smocza Jama"}}; 20.393 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:b918424f-9161-4841-8bc8-0051445a4d29 | Jaskinia Czarna; N / {"globalid":"b918424f-9161-4841-8bc8-0051445a4d29","origin":"baseline"} | {"code":"exact_name","left":{"field":"current.OTWÓR","value":"N"},"normalized":"n","right":{"field":"baseline.OTWÓR","value":"N"}} |
| source:baseline:f22edcd0-acfd-4797-b2a0-cfd5b325bc8e | tunel w Skrajnej Giewonckiej Baszcie; N / {"globalid":"f22edcd0-acfd-4797-b2a0-cfd5b325bc8e","origin":"baseline"} | {"code":"exact_name","left":{"field":"current.OTWÓR","value":"N"},"normalized":"n","right":{"field":"baseline.OTWÓR","value":"N"}} |
| source:baseline:fcc7a4d6-7779-45d7-b594-af18f1ebb840 | Schron za Smoczą Jamą / {"globalid":"fcc7a4d6-7779-45d7-b594-af18f1ebb840","origin":"baseline"} | 8.471 m; pomiar źródłowy; best=n/d; status=n/d |

Do rozstrzygnięcia potrzebne oznaczenia otworów/plan lub inny dowód wskazujący, czy to ten sam otwór, inne otwory jednej jaskini, czy różne obiekty. Współrzędne i podobna nazwa są tylko sygnałem. Defer zachowa rewizję i snapshot w trwałej kolejce po zatwierdzeniu tej propozycji.

### D007 — Schron pod Gawrą w Bobrowcu

GLOBALID `28bd775c-1b67-4aea-9ffb-49c32eef6bed`; change_id `28bd775c-1b67-4aea-9ffb-49c32eef6bed:52767533c8616e62a11fafb131b4ac61e520e48367600a9339ca4e133fc3ff63`.

Źródło teraz: lat=49.24042794387105, lon=19.800939863529027; data stanu=2026-06-17; GENEZA=jaskinia; WER_LOK="FF 27052026"; UWAGI=null.

**Proponowane defer:** Odroczyć: brak dowodu tożsamości/odrębności wobec konkretnych kandydatów z raportu; nie tworzyć ani nie scalać obiektów, nie przypinać źródła.

| Kandydat | Nazwy / cel | Sygnały i dystanse |
|---|---|---|
| source:current:a32f96eb-2092-4974-9256-b1d26b3f35a3 | Gawra w Bobrowcu / {"globalid":"a32f96eb-2092-4974-9256-b1d26b3f35a3","origin":"current"} | 49.359 m; pomiar źródłowy; best=n/d; status=n/d |

Do rozstrzygnięcia potrzebne oznaczenia otworów/plan lub inny dowód wskazujący, czy to ten sam otwór, inne otwory jednej jaskini, czy różne obiekty. Współrzędne i podobna nazwa są tylko sygnałem. Defer zachowa rewizję i snapshot w trwałej kolejce po zatwierdzeniu tej propozycji.

### D008 — Okno w Ciemniaku

GLOBALID `2cb1b34b-9aa8-440b-96e7-729bd2cdf7b6`; change_id `2cb1b34b-9aa8-440b-96e7-729bd2cdf7b6:1f98fb62e5670d57371309d1ff86eb16b751a92b7663d93601df7b2002742de2`.

Źródło teraz: lat=49.23208829805866, lon=19.90443548643466; data stanu=2026-06-16; GENEZA=None; WER_LOK=null; UWAGI=null.

**Proponowane defer:** Odroczyć: brak dowodu tożsamości/odrębności wobec konkretnych kandydatów z raportu; nie tworzyć ani nie scalać obiektów, nie przypinać źródła. Źródło nie określa jednoznacznej kategorii.

| Kandydat | Nazwy / cel | Sygnały i dystanse |
|---|---|---|
| source:current:041adf4d-119c-4a51-93b9-982b2127d2a4 | Okno w Ciemniaku / {"globalid":"041adf4d-119c-4a51-93b9-982b2127d2a4","origin":"current"} | {"code":"exact_name","left":{"field":"current.NAZWA","value":"Okno w Ciemniaku"},"normalized":"okno w ciemniaku","right":{"field":"current.NAZWA","value":"Okno w Ciemniaku"}}; 3.352 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:0bfc7731-a83a-40e6-b773-766798366add | Korytarz w Ciemniaku / {"globalid":"0bfc7731-a83a-40e6-b773-766798366add","origin":"current"} | 95.071 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:4bbef00c-a6c1-4706-9590-9dbc61b70ddd | Okno w Ciemniaku / {"globalid":"4bbef00c-a6c1-4706-9590-9dbc61b70ddd","origin":"current"} | {"code":"exact_name","left":{"field":"current.NAZWA","value":"Okno w Ciemniaku"},"normalized":"okno w ciemniaku","right":{"field":"current.NAZWA","value":"Okno w Ciemniaku"}}; 1.764 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:8e246480-f366-4d0f-ba7e-a601e865fd03 | Korytarz pod Ciemniakiem / {"globalid":"8e246480-f366-4d0f-ba7e-a601e865fd03","origin":"current"} | 95.073 m; pomiar źródłowy; best=n/d; status=n/d |

Do rozstrzygnięcia potrzebne oznaczenia otworów/plan lub inny dowód wskazujący, czy to ten sam otwór, inne otwory jednej jaskini, czy różne obiekty. Współrzędne i podobna nazwa są tylko sygnałem. Defer zachowa rewizję i snapshot w trwałej kolejce po zatwierdzeniu tej propozycji.

### D009 — Dziura nad Zahradziskami

GLOBALID `37ef7fe5-6e87-47d4-97c8-cb0ebd9ddeee`; change_id `37ef7fe5-6e87-47d4-97c8-cb0ebd9ddeee:1983bf1f06f31313e26424dc612cbab07fd0e628ebee86cccaa712a44a1d02e7`.

Źródło teraz: lat=49.263609834607415, lon=19.879155242621014; data stanu=2026-05-21; GENEZA=Jaskinia; WER_LOK="FF 21052026"; UWAGI=null.

**Proponowane defer:** Odroczyć: brak dowodu tożsamości/odrębności wobec konkretnych kandydatów z raportu; nie tworzyć ani nie scalać obiektów, nie przypinać źródła.

| Kandydat | Nazwy / cel | Sygnały i dystanse |
|---|---|---|
| object:MTW-0005 | Nyża w Kończystej / {"cave_id":"C-0091","object_id":"MTW-0005"} | 17.550 m; pomiar m-001; best=False; status=nieweryfikowany; 17.550 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:MTW-0024 | Ciasna Norka / {"cave_id":"C-0280","object_id":"MTW-0024"} | 66.069 m; pomiar m-001; best=False; status=nieweryfikowany; 66.069 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:MTW-0031 | Dziura w Kończystej Niżnia / {"cave_id":"C-0395","object_id":"MTW-0031"} | 74.300 m; pomiar m-001; best=False; status=nieweryfikowany; 74.300 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:MTW-0039 | Nyża pod Progiem w Kończystej / {"cave_id":"C-0536","object_id":"MTW-0039"} | 77.589 m; pomiar m-001; best=False; status=nieweryfikowany; 77.589 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:MTW-0043 | Schron pod Kończystą / {"cave_id":"C-0566","object_id":"MTW-0043"} | 56.045 m; pomiar m-001; best=False; status=nieweryfikowany; 56.045 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:MTW-0052 | Okap w Kończystej Turni / {"cave_id":"C-0672","object_id":"MTW-0052"} | 3.593 m; pomiar m-001; best=False; status=nieweryfikowany; 3.592 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:MTW-0059 | Dziura w Kończystej Turni / {"cave_id":"C-0753","object_id":"MTW-0059"} | 59.945 m; pomiar m-001; best=False; status=nieweryfikowany; 59.945 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:MTW-0060 | Dziura Niżnia w Kończystej Turni / {"cave_id":"C-0778","object_id":"MTW-0060"} | 68.263 m; pomiar m-001; best=False; status=nieweryfikowany; 68.264 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:MTW-0062 | Schronisko Wschodnie w Kończystej / {"cave_id":"C-0803","object_id":"MTW-0062"} | 72.555 m; pomiar m-001; best=False; status=nieweryfikowany; 72.555 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:MTW-0065 | Mała Dziura w Kończystej Turni / {"cave_id":"C-0847","object_id":"MTW-0065"} | 88.218 m; pomiar m-001; best=False; status=nieweryfikowany; 88.218 m; pomiar m-002; best=True; status=nieweryfikowany |
| source:current:0257a120-426e-4b7d-b47f-1d9f853c6c85 | Dziura w Kończystej Niżnia / {"globalid":"0257a120-426e-4b7d-b47f-1d9f853c6c85","origin":"current"} | 91.314 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:0c34f113-d6d5-4e57-9db1-b240ed3533b5 | Schron pod Kończystą / {"globalid":"0c34f113-d6d5-4e57-9db1-b240ed3533b5","origin":"current"} | 65.371 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:1f9eaae2-f97d-4205-bf67-7a43e6ddb5e7 | Ciasna Norka / {"globalid":"1f9eaae2-f97d-4205-bf67-7a43e6ddb5e7","origin":"current"} | 60.567 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:2549106f-2ea9-477a-a5d3-77e6b920c8e5 | Schron nad Komorą w Kończystej Turni / {"globalid":"2549106f-2ea9-477a-a5d3-77e6b920c8e5","origin":"current"} | 29.068 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:7033eb52-9352-4f35-9adf-89490fbb5f1f | Dziura w Kończystej Turni / {"globalid":"7033eb52-9352-4f35-9adf-89490fbb5f1f","origin":"current"} | 91.037 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:9ba8f361-d7aa-413f-bc86-ac235940f603 | Nyża pod Progiem w Kończystej / {"globalid":"9ba8f361-d7aa-413f-bc86-ac235940f603","origin":"current"} | 39.380 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:9beb2e85-ecb8-432a-90d4-623df217c6da | Nyża za Jałowcem / {"globalid":"9beb2e85-ecb8-432a-90d4-623df217c6da","origin":"current"} | 32.256 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:b2a16ea5-23c8-4e73-bbe7-b4ce1cdf5440 | Okap w Kończystej Turni / {"globalid":"b2a16ea5-23c8-4e73-bbe7-b4ce1cdf5440","origin":"current"} | 18.093 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:c24021bb-73c2-4bc2-83f1-aabefc26492e | Komora w Kończystej Turni / {"globalid":"c24021bb-73c2-4bc2-83f1-aabefc26492e","origin":"current"} | 0.169 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:dca8221f-d3c2-4eb2-98ea-77957bb07a1a | Dziura Niżnia w Kończystej Turni / {"globalid":"dca8221f-d3c2-4eb2-98ea-77957bb07a1a","origin":"current"} | 86.577 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:f3ae1e5e-ba6a-4c62-86fe-a4f42892808c | Nyża w Kończystej / {"globalid":"f3ae1e5e-ba6a-4c62-86fe-a4f42892808c","origin":"current"} | 53.369 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:f64fab23-53f9-45fa-a1c2-748d15a67568 | Schronisko Wschodnie w Kończystej / {"globalid":"f64fab23-53f9-45fa-a1c2-748d15a67568","origin":"current"} | 32.424 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:0257a120-426e-4b7d-b47f-1d9f853c6c85 | Dziura w Kończystej Niżnia / {"globalid":"0257a120-426e-4b7d-b47f-1d9f853c6c85","origin":"baseline"} | 74.300 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:0c34f113-d6d5-4e57-9db1-b240ed3533b5 | Schron pod Kończystą / {"globalid":"0c34f113-d6d5-4e57-9db1-b240ed3533b5","origin":"baseline"} | 56.045 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:1f9eaae2-f97d-4205-bf67-7a43e6ddb5e7 | Ciasna Norka / {"globalid":"1f9eaae2-f97d-4205-bf67-7a43e6ddb5e7","origin":"baseline"} | 66.069 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:7033eb52-9352-4f35-9adf-89490fbb5f1f | Dziura w Kończystej Turni / {"globalid":"7033eb52-9352-4f35-9adf-89490fbb5f1f","origin":"baseline"} | 59.945 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:9ba8f361-d7aa-413f-bc86-ac235940f603 | Nyża pod Progiem w Kończystej / {"globalid":"9ba8f361-d7aa-413f-bc86-ac235940f603","origin":"baseline"} | 77.589 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:b2a16ea5-23c8-4e73-bbe7-b4ce1cdf5440 | Okap w Kończystej Turni / {"globalid":"b2a16ea5-23c8-4e73-bbe7-b4ce1cdf5440","origin":"baseline"} | 3.592 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:c4a17714-5976-4b41-a6a6-9eacae7e9421 | Mała Dziura w Kończystej Turni / {"globalid":"c4a17714-5976-4b41-a6a6-9eacae7e9421","origin":"baseline"} | 88.218 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:dca8221f-d3c2-4eb2-98ea-77957bb07a1a | Dziura Niżnia w Kończystej Turni / {"globalid":"dca8221f-d3c2-4eb2-98ea-77957bb07a1a","origin":"baseline"} | 68.264 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:f3ae1e5e-ba6a-4c62-86fe-a4f42892808c | Nyża w Kończystej / {"globalid":"f3ae1e5e-ba6a-4c62-86fe-a4f42892808c","origin":"baseline"} | 17.550 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:f64fab23-53f9-45fa-a1c2-748d15a67568 | Schronisko Wschodnie w Kończystej / {"globalid":"f64fab23-53f9-45fa-a1c2-748d15a67568","origin":"baseline"} | 72.555 m; pomiar źródłowy; best=n/d; status=n/d |

Do rozstrzygnięcia potrzebne oznaczenia otworów/plan lub inny dowód wskazujący, czy to ten sam otwór, inne otwory jednej jaskini, czy różne obiekty. Współrzędne i podobna nazwa są tylko sygnałem. Defer zachowa rewizję i snapshot w trwałej kolejce po zatwierdzeniu tej propozycji.

### D010 — Okno w Ciemniaku

GLOBALID `4bbef00c-a6c1-4706-9590-9dbc61b70ddd`; change_id `4bbef00c-a6c1-4706-9590-9dbc61b70ddd:702fbea0035612937a3db5ce2c81e9b63b75d7f92d8fa66c4c1dde7e90c8e89c`.

Źródło teraz: lat=49.23207253551044, lon=19.904438168831337; data stanu=2026-06-16; GENEZA=None; WER_LOK="FF16062026"; UWAGI=null.

**Proponowane defer:** Odroczyć: brak dowodu tożsamości/odrębności wobec konkretnych kandydatów z raportu; nie tworzyć ani nie scalać obiektów, nie przypinać źródła. Źródło nie określa jednoznacznej kategorii.

| Kandydat | Nazwy / cel | Sygnały i dystanse |
|---|---|---|
| source:current:041adf4d-119c-4a51-93b9-982b2127d2a4 | Okno w Ciemniaku / {"globalid":"041adf4d-119c-4a51-93b9-982b2127d2a4","origin":"current"} | {"code":"exact_name","left":{"field":"current.NAZWA","value":"Okno w Ciemniaku"},"normalized":"okno w ciemniaku","right":{"field":"current.NAZWA","value":"Okno w Ciemniaku"}}; 1.719 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:0bfc7731-a83a-40e6-b773-766798366add | Korytarz w Ciemniaku / {"globalid":"0bfc7731-a83a-40e6-b773-766798366add","origin":"current"} | 95.329 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:2cb1b34b-9aa8-440b-96e7-729bd2cdf7b6 | Okno w Ciemniaku / {"globalid":"2cb1b34b-9aa8-440b-96e7-729bd2cdf7b6","origin":"current"} | {"code":"exact_name","left":{"field":"current.NAZWA","value":"Okno w Ciemniaku"},"normalized":"okno w ciemniaku","right":{"field":"current.NAZWA","value":"Okno w Ciemniaku"}}; 1.764 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:8e246480-f366-4d0f-ba7e-a601e865fd03 | Korytarz pod Ciemniakiem / {"globalid":"8e246480-f366-4d0f-ba7e-a601e865fd03","origin":"current"} | 95.333 m; pomiar źródłowy; best=n/d; status=n/d |

Do rozstrzygnięcia potrzebne oznaczenia otworów/plan lub inny dowód wskazujący, czy to ten sam otwór, inne otwory jednej jaskini, czy różne obiekty. Współrzędne i podobna nazwa są tylko sygnałem. Defer zachowa rewizję i snapshot w trwałej kolejce po zatwierdzeniu tej propozycji.

### D011 — Nyża pod Szarą Turnią I

GLOBALID `55ed69a3-9228-452b-87ce-8133710292b1`; change_id `55ed69a3-9228-452b-87ce-8133710292b1:7c4915d207fd4ddae2329699ccc37b0e110a0c64510acb6127a757d2e13a7aa3`.

Źródło teraz: lat=49.25319985046087, lon=19.928103567508114; data stanu=2026-06-14; GENEZA=jaskinia; WER_LOK="FF 27052026"; UWAGI=null.

**Proponowane defer:** Odroczyć: brak dowodu tożsamości/odrębności wobec konkretnych kandydatów z raportu; nie tworzyć ani nie scalać obiektów, nie przypinać źródła.

| Kandydat | Nazwy / cel | Sygnały i dystanse |
|---|---|---|
| object:STR-0028 | Nyża pod Zachodem Pilotów / {"cave_id":"C-0984","object_id":"STR-0028"} | 95.614 m; pomiar m-001; best=True; status=nieweryfikowany |
| source:current:1792c71c-54b5-46ce-8e24-454f4a31e73f | Nyża pod Szarą Turnią III / {"globalid":"1792c71c-54b5-46ce-8e24-454f4a31e73f","origin":"current"} | {"code":"similar_name","left":{"field":"current.NAZWA","value":"Nyża pod Szarą Turnią I"},"right":{"field":"current.NAZWA","value":"Nyża pod Szarą Turnią III"},"similarity":0.92,"threshold":0.9}; 58.392 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:643487f7-79ea-45a5-9427-dcde64334e71 | Nyża pod Zachodem Pilotów II / {"globalid":"643487f7-79ea-45a5-9427-dcde64334e71","origin":"current"} | 92.764 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:70fc9cd8-57de-4c66-a50f-674b3c6f5d55 | Nyża pod Szarą Turnią IV / {"globalid":"70fc9cd8-57de-4c66-a50f-674b3c6f5d55","origin":"current"} | {"code":"similar_name","left":{"field":"current.NAZWA","value":"Nyża pod Szarą Turnią I"},"right":{"field":"current.NAZWA","value":"Nyża pod Szarą Turnią IV"},"similarity":0.9583333333333334,"threshold":0.9}; 26.202 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:adbf9ca1-deff-402f-a223-04ba9c1d0d35 | Nyża pod Zachodem Pilotów III / {"globalid":"adbf9ca1-deff-402f-a223-04ba9c1d0d35","origin":"current"} | 92.006 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:b51c01e8-271e-4aef-802d-c87025a09845 | Nyża pod Szarą Turnią II / {"globalid":"b51c01e8-271e-4aef-802d-c87025a09845","origin":"current"} | {"code":"similar_name","left":{"field":"current.NAZWA","value":"Nyża pod Szarą Turnią I"},"right":{"field":"current.NAZWA","value":"Nyża pod Szarą Turnią II"},"similarity":0.9583333333333334,"threshold":0.9}; 50.758 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:dec416bc-64f2-49e0-abf9-cb2c5a040004 | Nyża pod Zachodem Pilotów II / {"globalid":"dec416bc-64f2-49e0-abf9-cb2c5a040004","origin":"current"} | 89.957 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:e6ba5010-45f5-4769-9026-229423ddf3cb | Nyża pod Zachodem Pilotów / {"globalid":"e6ba5010-45f5-4769-9026-229423ddf3cb","origin":"current"} | 85.533 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:e6ba5010-45f5-4769-9026-229423ddf3cb | Nyża pod Zachodem Pilotów / {"globalid":"e6ba5010-45f5-4769-9026-229423ddf3cb","origin":"baseline"} | 95.614 m; pomiar źródłowy; best=n/d; status=n/d |

Do rozstrzygnięcia potrzebne oznaczenia otworów/plan lub inny dowód wskazujący, czy to ten sam otwór, inne otwory jednej jaskini, czy różne obiekty. Współrzędne i podobna nazwa są tylko sygnałem. Defer zachowa rewizję i snapshot w trwałej kolejce po zatwierdzeniu tej propozycji.

### D012 — Nyża pod Zachodem Pilotów II

GLOBALID `643487f7-79ea-45a5-9427-dcde64334e71`; change_id `643487f7-79ea-45a5-9427-dcde64334e71:c2566bd0ea5535c7fbfa170fb936d84ba969accb715a0652537dfb3017620bba`.

Źródło teraz: lat=49.25262948132323, lon=19.929033300384997; data stanu=2026-06-14; GENEZA=jaskinia; WER_LOK="FF 27052026"; UWAGI=null.

**Proponowane defer:** Odroczyć: brak dowodu tożsamości/odrębności wobec konkretnych kandydatów z raportu; nie tworzyć ani nie scalać obiektów, nie przypinać źródła.

| Kandydat | Nazwy / cel | Sygnały i dystanse |
|---|---|---|
| object:STR-0002 | Nyża pod Brzózką / {"cave_id":"C-0018","object_id":"STR-0002"} | 92.565 m; pomiar m-001; best=False; status=nieweryfikowany |
| object:STR-0028 | Nyża pod Zachodem Pilotów / {"cave_id":"C-0984","object_id":"STR-0028"} | 12.134 m; pomiar m-001; best=True; status=nieweryfikowany |
| source:current:55ed69a3-9228-452b-87ce-8133710292b1 | Nyża pod Szarą Turnią I / {"globalid":"55ed69a3-9228-452b-87ce-8133710292b1","origin":"current"} | 92.764 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:70fc9cd8-57de-4c66-a50f-674b3c6f5d55 | Nyża pod Szarą Turnią IV / {"globalid":"70fc9cd8-57de-4c66-a50f-674b3c6f5d55","origin":"current"} | 99.303 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:adbf9ca1-deff-402f-a223-04ba9c1d0d35 | Nyża pod Zachodem Pilotów III / {"globalid":"adbf9ca1-deff-402f-a223-04ba9c1d0d35","origin":"current"} | {"code":"similar_name","left":{"field":"current.NAZWA","value":"Nyża pod Zachodem Pilotów II"},"right":{"field":"current.NAZWA","value":"Nyża pod Zachodem Pilotów III"},"similarity":0.9655172413793104,"threshold":0.9} |
| source:current:dec416bc-64f2-49e0-abf9-cb2c5a040004 | Nyża pod Zachodem Pilotów II / {"globalid":"dec416bc-64f2-49e0-abf9-cb2c5a040004","origin":"current"} | {"code":"exact_name","left":{"field":"current.NAZWA","value":"Nyża pod Zachodem Pilotów II"},"normalized":"nyża pod zachodem pilotów ii","right":{"field":"current.NAZWA","value":"Nyża pod Zachodem Pilotów II"}} |
| source:current:e6ba5010-45f5-4769-9026-229423ddf3cb | Nyża pod Zachodem Pilotów / {"globalid":"e6ba5010-45f5-4769-9026-229423ddf3cb","origin":"current"} | 16.010 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:e6ba5010-45f5-4769-9026-229423ddf3cb | Nyża pod Zachodem Pilotów / {"globalid":"e6ba5010-45f5-4769-9026-229423ddf3cb","origin":"baseline"} | 12.134 m; pomiar źródłowy; best=n/d; status=n/d |

Do rozstrzygnięcia potrzebne oznaczenia otworów/plan lub inny dowód wskazujący, czy to ten sam otwór, inne otwory jednej jaskini, czy różne obiekty. Współrzędne i podobna nazwa są tylko sygnałem. Defer zachowa rewizję i snapshot w trwałej kolejce po zatwierdzeniu tej propozycji.

### D013 — Nyża pod Szarą Turnią IV

GLOBALID `70fc9cd8-57de-4c66-a50f-674b3c6f5d55`; change_id `70fc9cd8-57de-4c66-a50f-674b3c6f5d55:dd3a2d3afa44efa7b6e40b41d4dc143ec9319b016589d8c0e24c8e5e512cb948`.

Źródło teraz: lat=49.25304799740581, lon=19.927828378885028; data stanu=2026-06-14; GENEZA=jaskinia; WER_LOK="FF 14062026"; UWAGI=null.

**Proponowane defer:** Odroczyć: brak dowodu tożsamości/odrębności wobec konkretnych kandydatów z raportu; nie tworzyć ani nie scalać obiektów, nie przypinać źródła.

| Kandydat | Nazwy / cel | Sygnały i dystanse |
|---|---|---|
| source:current:1792c71c-54b5-46ce-8e24-454f4a31e73f | Nyża pod Szarą Turnią III / {"globalid":"1792c71c-54b5-46ce-8e24-454f4a31e73f","origin":"current"} | {"code":"similar_name","left":{"field":"current.NAZWA","value":"Nyża pod Szarą Turnią IV"},"right":{"field":"current.NAZWA","value":"Nyża pod Szarą Turnią III"},"similarity":0.92,"threshold":0.9}; 45.026 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:55ed69a3-9228-452b-87ce-8133710292b1 | Nyża pod Szarą Turnią I / {"globalid":"55ed69a3-9228-452b-87ce-8133710292b1","origin":"current"} | {"code":"similar_name","left":{"field":"current.NAZWA","value":"Nyża pod Szarą Turnią IV"},"right":{"field":"current.NAZWA","value":"Nyża pod Szarą Turnią I"},"similarity":0.9583333333333334,"threshold":0.9}; 26.202 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:643487f7-79ea-45a5-9427-dcde64334e71 | Nyża pod Zachodem Pilotów II / {"globalid":"643487f7-79ea-45a5-9427-dcde64334e71","origin":"current"} | 99.303 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:b51c01e8-271e-4aef-802d-c87025a09845 | Nyża pod Szarą Turnią II / {"globalid":"b51c01e8-271e-4aef-802d-c87025a09845","origin":"current"} | {"code":"similar_name","left":{"field":"current.NAZWA","value":"Nyża pod Szarą Turnią IV"},"right":{"field":"current.NAZWA","value":"Nyża pod Szarą Turnią II"},"similarity":0.9583333333333334,"threshold":0.9}; 51.409 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:e6ba5010-45f5-4769-9026-229423ddf3cb | Nyża pod Zachodem Pilotów / {"globalid":"e6ba5010-45f5-4769-9026-229423ddf3cb","origin":"current"} | 96.085 m; pomiar źródłowy; best=n/d; status=n/d |

Do rozstrzygnięcia potrzebne oznaczenia otworów/plan lub inny dowód wskazujący, czy to ten sam otwór, inne otwory jednej jaskini, czy różne obiekty. Współrzędne i podobna nazwa są tylko sygnałem. Defer zachowa rewizję i snapshot w trwałej kolejce po zatwierdzeniu tej propozycji.

### D014 — Korytarz pod Ciemniakiem

GLOBALID `8e246480-f366-4d0f-ba7e-a601e865fd03`; change_id `8e246480-f366-4d0f-ba7e-a601e865fd03:01216c884dc22035e965378ca344f245e413aac414d8cf0812e238e15d89cc43`.

Źródło teraz: lat=49.232111943661685, lon=19.903130591561503; data stanu=2026-06-16; GENEZA=jaskinia; WER_LOK="FF 16062026"; UWAGI=null.

**Proponowane defer:** Odroczyć: brak dowodu tożsamości/odrębności wobec konkretnych kandydatów z raportu; nie tworzyć ani nie scalać obiektów, nie przypinać źródła.

| Kandydat | Nazwy / cel | Sygnały i dystanse |
|---|---|---|
| source:current:041adf4d-119c-4a51-93b9-982b2127d2a4 | Okno w Ciemniaku / {"globalid":"041adf4d-119c-4a51-93b9-982b2127d2a4","origin":"current"} | 94.688 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:0bfc7731-a83a-40e6-b773-766798366add | Korytarz w Ciemniaku / {"globalid":"0bfc7731-a83a-40e6-b773-766798366add","origin":"current"} | 0.097 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:2cb1b34b-9aa8-440b-96e7-729bd2cdf7b6 | Okno w Ciemniaku / {"globalid":"2cb1b34b-9aa8-440b-96e7-729bd2cdf7b6","origin":"current"} | 95.073 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:4bbef00c-a6c1-4706-9590-9dbc61b70ddd | Okno w Ciemniaku / {"globalid":"4bbef00c-a6c1-4706-9590-9dbc61b70ddd","origin":"current"} | 95.333 m; pomiar źródłowy; best=n/d; status=n/d |

Do rozstrzygnięcia potrzebne oznaczenia otworów/plan lub inny dowód wskazujący, czy to ten sam otwór, inne otwory jednej jaskini, czy różne obiekty. Współrzędne i podobna nazwa są tylko sygnałem. Defer zachowa rewizję i snapshot w trwałej kolejce po zatwierdzeniu tej propozycji.

### D015 — Nyża za Jałowcem

GLOBALID `9beb2e85-ecb8-432a-90d4-623df217c6da`; change_id `9beb2e85-ecb8-432a-90d4-623df217c6da:5cbf572c663a2c9afcfe9fbe7461a23a2527552ea9085eaac58fdca0be0f0d0a`.

Źródło teraz: lat=49.26374024770888, lon=19.879551085758283; data stanu=2026-06-14; GENEZA=jaskinia; WER_LOK="FF 06062026"; UWAGI=null.

**Proponowane defer:** Odroczyć: brak dowodu tożsamości/odrębności wobec konkretnych kandydatów z raportu; nie tworzyć ani nie scalać obiektów, nie przypinać źródła.

| Kandydat | Nazwy / cel | Sygnały i dystanse |
|---|---|---|
| object:MTW-0005 | Nyża w Kończystej / {"cave_id":"C-0091","object_id":"MTW-0005"} | 42.359 m; pomiar m-001; best=False; status=nieweryfikowany; 42.359 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:MTW-0024 | Ciasna Norka / {"cave_id":"C-0280","object_id":"MTW-0024"} | 90.847 m; pomiar m-001; best=False; status=nieweryfikowany; 90.847 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:MTW-0031 | Dziura w Kończystej Niżnia / {"cave_id":"C-0395","object_id":"MTW-0031"} | 88.156 m; pomiar m-001; best=False; status=nieweryfikowany; 88.156 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:MTW-0039 | Nyża pod Progiem w Kończystej / {"cave_id":"C-0536","object_id":"MTW-0039"} | 47.779 m; pomiar m-001; best=False; status=nieweryfikowany; 47.778 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:MTW-0043 | Schron pod Kończystą / {"cave_id":"C-0566","object_id":"MTW-0043"} | 88.233 m; pomiar m-001; best=False; status=nieweryfikowany; 88.233 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:MTW-0052 | Okap w Kończystej Turni / {"cave_id":"C-0672","object_id":"MTW-0052"} | 34.646 m; pomiar m-001; best=False; status=nieweryfikowany; 34.646 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:MTW-0059 | Dziura w Kończystej Turni / {"cave_id":"C-0753","object_id":"MTW-0059"} | 77.313 m; pomiar m-001; best=False; status=nieweryfikowany; 77.313 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:MTW-0060 | Dziura Niżnia w Kończystej Turni / {"cave_id":"C-0778","object_id":"MTW-0060"} | 98.079 m; pomiar m-001; best=False; status=nieweryfikowany; 98.079 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:MTW-0062 | Schronisko Wschodnie w Kończystej / {"cave_id":"C-0803","object_id":"MTW-0062"} | 56.866 m; pomiar m-001; best=False; status=nieweryfikowany; 56.865 m; pomiar m-002; best=True; status=nieweryfikowany |
| source:current:0c34f113-d6d5-4e57-9db1-b240ed3533b5 | Schron pod Kończystą / {"globalid":"0c34f113-d6d5-4e57-9db1-b240ed3533b5","origin":"current"} | 97.446 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:1f9eaae2-f97d-4205-bf67-7a43e6ddb5e7 | Ciasna Norka / {"globalid":"1f9eaae2-f97d-4205-bf67-7a43e6ddb5e7","origin":"current"} | 89.769 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:2549106f-2ea9-477a-a5d3-77e6b920c8e5 | Schron nad Komorą w Kończystej Turni / {"globalid":"2549106f-2ea9-477a-a5d3-77e6b920c8e5","origin":"current"} | 41.381 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:37ef7fe5-6e87-47d4-97c8-cb0ebd9ddeee | Dziura nad Zahradziskami / {"globalid":"37ef7fe5-6e87-47d4-97c8-cb0ebd9ddeee","origin":"current"} | 32.256 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:9ba8f361-d7aa-413f-bc86-ac235940f603 | Nyża pod Progiem w Kończystej / {"globalid":"9ba8f361-d7aa-413f-bc86-ac235940f603","origin":"current"} | 49.894 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:b2a16ea5-23c8-4e73-bbe7-b4ce1cdf5440 | Okap w Kończystej Turni / {"globalid":"b2a16ea5-23c8-4e73-bbe7-b4ce1cdf5440","origin":"current"} | 49.941 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:c24021bb-73c2-4bc2-83f1-aabefc26492e | Komora w Kończystej Turni / {"globalid":"c24021bb-73c2-4bc2-83f1-aabefc26492e","origin":"current"} | 32.087 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:f3ae1e5e-ba6a-4c62-86fe-a4f42892808c | Nyża w Kończystej / {"globalid":"f3ae1e5e-ba6a-4c62-86fe-a4f42892808c","origin":"current"} | 81.422 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:f64fab23-53f9-45fa-a1c2-748d15a67568 | Schronisko Wschodnie w Kończystej / {"globalid":"f64fab23-53f9-45fa-a1c2-748d15a67568","origin":"current"} | 11.243 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:0257a120-426e-4b7d-b47f-1d9f853c6c85 | Dziura w Kończystej Niżnia / {"globalid":"0257a120-426e-4b7d-b47f-1d9f853c6c85","origin":"baseline"} | 88.156 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:0c34f113-d6d5-4e57-9db1-b240ed3533b5 | Schron pod Kończystą / {"globalid":"0c34f113-d6d5-4e57-9db1-b240ed3533b5","origin":"baseline"} | 88.233 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:1f9eaae2-f97d-4205-bf67-7a43e6ddb5e7 | Ciasna Norka / {"globalid":"1f9eaae2-f97d-4205-bf67-7a43e6ddb5e7","origin":"baseline"} | 90.847 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:7033eb52-9352-4f35-9adf-89490fbb5f1f | Dziura w Kończystej Turni / {"globalid":"7033eb52-9352-4f35-9adf-89490fbb5f1f","origin":"baseline"} | 77.313 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:9ba8f361-d7aa-413f-bc86-ac235940f603 | Nyża pod Progiem w Kończystej / {"globalid":"9ba8f361-d7aa-413f-bc86-ac235940f603","origin":"baseline"} | 47.778 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:b2a16ea5-23c8-4e73-bbe7-b4ce1cdf5440 | Okap w Kończystej Turni / {"globalid":"b2a16ea5-23c8-4e73-bbe7-b4ce1cdf5440","origin":"baseline"} | 34.646 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:dca8221f-d3c2-4eb2-98ea-77957bb07a1a | Dziura Niżnia w Kończystej Turni / {"globalid":"dca8221f-d3c2-4eb2-98ea-77957bb07a1a","origin":"baseline"} | 98.079 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:f3ae1e5e-ba6a-4c62-86fe-a4f42892808c | Nyża w Kończystej / {"globalid":"f3ae1e5e-ba6a-4c62-86fe-a4f42892808c","origin":"baseline"} | 42.359 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:f64fab23-53f9-45fa-a1c2-748d15a67568 | Schronisko Wschodnie w Kończystej / {"globalid":"f64fab23-53f9-45fa-a1c2-748d15a67568","origin":"baseline"} | 56.865 m; pomiar źródłowy; best=n/d; status=n/d |

Do rozstrzygnięcia potrzebne oznaczenia otworów/plan lub inny dowód wskazujący, czy to ten sam otwór, inne otwory jednej jaskini, czy różne obiekty. Współrzędne i podobna nazwa są tylko sygnałem. Defer zachowa rewizję i snapshot w trwałej kolejce po zatwierdzeniu tej propozycji.

### D016 — Gawra w Bobrowcu

GLOBALID `a32f96eb-2092-4974-9256-b1d26b3f35a3`; change_id `a32f96eb-2092-4974-9256-b1d26b3f35a3:52b298ee38523e41f50a88e8783149671448fedd226bd7f95a3e17548e593b84`.

Źródło teraz: lat=49.24085926092091, lon=19.801099619438673; data stanu=2026-06-17; GENEZA=jaskinia; WER_LOK="FF 27052026"; UWAGI=null.

**Proponowane defer:** Odroczyć: brak dowodu tożsamości/odrębności wobec konkretnych kandydatów z raportu; nie tworzyć ani nie scalać obiektów, nie przypinać źródła.

| Kandydat | Nazwy / cel | Sygnały i dystanse |
|---|---|---|
| source:current:28bd775c-1b67-4aea-9ffb-49c32eef6bed | Schron pod Gawrą w Bobrowcu / {"globalid":"28bd775c-1b67-4aea-9ffb-49c32eef6bed","origin":"current"} | 49.359 m; pomiar źródłowy; best=n/d; status=n/d |

Do rozstrzygnięcia potrzebne oznaczenia otworów/plan lub inny dowód wskazujący, czy to ten sam otwór, inne otwory jednej jaskini, czy różne obiekty. Współrzędne i podobna nazwa są tylko sygnałem. Defer zachowa rewizję i snapshot w trwałej kolejce po zatwierdzeniu tej propozycji.

### D017 — Schron nad Wielką Równią

GLOBALID `a61dc23d-4158-4eee-8bf0-885e41f79740`; change_id `a61dc23d-4158-4eee-8bf0-885e41f79740:8140aaa217623ec2e2f4e559d00e02debdd8b6dd4f11de09dee6cd5ba577ed6f`.

Źródło teraz: lat=49.25512416543047, lon=19.936354637159493; data stanu=2026-10-03; GENEZA=jaskinia; WER_LOK="03102026"; UWAGI=null.

**Proponowane defer:** Odroczyć: brak dowodu tożsamości/odrębności wobec konkretnych kandydatów z raportu; nie tworzyć ani nie scalać obiektów, nie przypinać źródła.

| Kandydat | Nazwy / cel | Sygnały i dystanse |
|---|---|---|
| object:STR-0009 | Kominek Giewontowy / {"cave_id":"C-0349","object_id":"STR-0009"} | 77.149 m; pomiar m-001; best=False; status=nieweryfikowany |
| object:STR-0015 | Nyża Giewontowa / {"cave_id":"C-0600","object_id":"STR-0015"} | 86.167 m; pomiar m-001; best=False; status=nieweryfikowany |
| object:STR-0024 | BEZ_NAZWY_001 / {"cave_id":"C-0903","object_id":"STR-0024"} | 51.120 m; pomiar m-001; best=True; status=nieweryfikowany |
| object:STR-0025 | Gawra nad Wielką Równią / {"cave_id":"C-0906","object_id":"STR-0025"} | 16.743 m; pomiar m-001; best=True; status=nieweryfikowany |
| object:STR-0029 | Jaskinia nad Wielką Równią / {"cave_id":"C-0986","object_id":"STR-0029"} | 18.675 m; pomiar m-001; best=True; status=nieweryfikowany |
| source:current:98377d8a-8e3d-41e9-bd6d-da78e5e56745 | Gawra nad Wielką Równią / {"globalid":"98377d8a-8e3d-41e9-bd6d-da78e5e56745","origin":"current"} | 16.749 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:a5c7088e-a2fe-4898-ae2e-b0a9b420b17d |  / {"globalid":"a5c7088e-a2fe-4898-ae2e-b0a9b420b17d","origin":"current"} | 51.125 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:b3202807-f363-428a-b8f0-0e22a2fa66da | Jaskinia nad Wielką Równią / {"globalid":"b3202807-f363-428a-b8f0-0e22a2fa66da","origin":"current"} | 18.679 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:98377d8a-8e3d-41e9-bd6d-da78e5e56745 | Gawra nad Wielką Równią / {"globalid":"98377d8a-8e3d-41e9-bd6d-da78e5e56745","origin":"baseline"} | 16.743 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:a5c7088e-a2fe-4898-ae2e-b0a9b420b17d |  / {"globalid":"a5c7088e-a2fe-4898-ae2e-b0a9b420b17d","origin":"baseline"} | 51.120 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:b3202807-f363-428a-b8f0-0e22a2fa66da | Jaskinia nad Wielką Równią / {"globalid":"b3202807-f363-428a-b8f0-0e22a2fa66da","origin":"baseline"} | 18.675 m; pomiar źródłowy; best=n/d; status=n/d |

Do rozstrzygnięcia potrzebne oznaczenia otworów/plan lub inny dowód wskazujący, czy to ten sam otwór, inne otwory jednej jaskini, czy różne obiekty. Współrzędne i podobna nazwa są tylko sygnałem. Defer zachowa rewizję i snapshot w trwałej kolejce po zatwierdzeniu tej propozycji.

### D018 — Jaskinia Cynamonowa

GLOBALID `a876a547-7912-4033-bb3f-8ed2f589c5f0`; change_id `a876a547-7912-4033-bb3f-8ed2f589c5f0:6141712b74e44bcce4b78290ee01ad0a40d3b7e3761f7b0fa1d8cd3973b93a18`.

Źródło teraz: lat=49.24315800000112, lon=19.803833000273805; data stanu=2026-06-16; GENEZA=jaskinia; WER_LOK="FF16062026"; UWAGI=null.

**Proponowane defer:** Odroczyć: brak dowodu tożsamości/odrębności wobec konkretnych kandydatów z raportu; nie tworzyć ani nie scalać obiektów, nie przypinać źródła.

| Kandydat | Nazwy / cel | Sygnały i dystanse |
|---|---|---|
| object:CHZ-0009 | Jaskinia Kokonowa / {"cave_id":"C-0292","object_id":"CHZ-0009"} | 17.400 m; pomiar m-001; best=False; status=nieweryfikowany; 17.399 m; pomiar m-002; best=True; status=nieweryfikowany |
| source:current:a00678a9-e909-4776-b57b-fe446d4fd3e0 | Jaskinia Kokonowa / {"globalid":"a00678a9-e909-4776-b57b-fe446d4fd3e0","origin":"current"} | 17.399 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:a00678a9-e909-4776-b57b-fe446d4fd3e0 | Jaskinia Kokonowa / {"globalid":"a00678a9-e909-4776-b57b-fe446d4fd3e0","origin":"baseline"} | 17.399 m; pomiar źródłowy; best=n/d; status=n/d |

Do rozstrzygnięcia potrzebne oznaczenia otworów/plan lub inny dowód wskazujący, czy to ten sam otwór, inne otwory jednej jaskini, czy różne obiekty. Współrzędne i podobna nazwa są tylko sygnałem. Defer zachowa rewizję i snapshot w trwałej kolejce po zatwierdzeniu tej propozycji.

### D019 — Nyża pod Zachodem Pilotów III

GLOBALID `adbf9ca1-deff-402f-a223-04ba9c1d0d35`; change_id `adbf9ca1-deff-402f-a223-04ba9c1d0d35:73457ca247fbab308bcf676430638fefb6f21c1be92c38178a68341c4bfbe9ce`.

Źródło teraz: lat=49.25357122743566, lon=19.92923288628315; data stanu=2026-05-24; GENEZA=jaskinia; WER_LOK="FF 24052026"; UWAGI=null.

**Proponowane defer:** Odroczyć: brak dowodu tożsamości/odrębności wobec konkretnych kandydatów z raportu; nie tworzyć ani nie scalać obiektów, nie przypinać źródła.

| Kandydat | Nazwy / cel | Sygnały i dystanse |
|---|---|---|
| object:STR-0001 | Szczelina w Żlebie Kirkora / {"cave_id":"C-0015","object_id":"STR-0001"} | 78.285 m; pomiar m-001; best=False; status=nieweryfikowany; 78.286 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:STR-0002 | Nyża pod Brzózką / {"cave_id":"C-0018","object_id":"STR-0002"} | 87.743 m; pomiar m-001; best=False; status=nieweryfikowany; 79.757 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:STR-0028 | Nyża pod Zachodem Pilotów / {"cave_id":"C-0984","object_id":"STR-0028"} | 97.572 m; pomiar m-001; best=True; status=nieweryfikowany |
| source:current:2091f15d-54bf-40c7-9cf8-04b2fde247fe | Szczelina w Żlebie Kirkora / {"globalid":"2091f15d-54bf-40c7-9cf8-04b2fde247fe","origin":"current"} | 78.286 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:38626571-caa6-4317-8900-d61a995020e9 | Nyża pod Brzózką / {"globalid":"38626571-caa6-4317-8900-d61a995020e9","origin":"current"} | 79.760 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:55ed69a3-9228-452b-87ce-8133710292b1 | Nyża pod Szarą Turnią I / {"globalid":"55ed69a3-9228-452b-87ce-8133710292b1","origin":"current"} | 92.006 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:643487f7-79ea-45a5-9427-dcde64334e71 | Nyża pod Zachodem Pilotów II / {"globalid":"643487f7-79ea-45a5-9427-dcde64334e71","origin":"current"} | {"code":"similar_name","left":{"field":"current.NAZWA","value":"Nyża pod Zachodem Pilotów III"},"right":{"field":"current.NAZWA","value":"Nyża pod Zachodem Pilotów II"},"similarity":0.9655172413793104,"threshold":0.9} |
| source:current:dec416bc-64f2-49e0-abf9-cb2c5a040004 | Nyża pod Zachodem Pilotów II / {"globalid":"dec416bc-64f2-49e0-abf9-cb2c5a040004","origin":"current"} | {"code":"similar_name","left":{"field":"current.NAZWA","value":"Nyża pod Zachodem Pilotów III"},"right":{"field":"current.NAZWA","value":"Nyża pod Zachodem Pilotów II"},"similarity":0.9655172413793104,"threshold":0.9}; 3.254 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:e6ba5010-45f5-4769-9026-229423ddf3cb | Nyża pod Zachodem Pilotów / {"globalid":"e6ba5010-45f5-4769-9026-229423ddf3cb","origin":"current"} | 89.773 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:2091f15d-54bf-40c7-9cf8-04b2fde247fe | Szczelina w Żlebie Kirkora / {"globalid":"2091f15d-54bf-40c7-9cf8-04b2fde247fe","origin":"baseline"} | 78.286 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:38626571-caa6-4317-8900-d61a995020e9 | Nyża pod Brzózką / {"globalid":"38626571-caa6-4317-8900-d61a995020e9","origin":"baseline"} | 79.757 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:e6ba5010-45f5-4769-9026-229423ddf3cb | Nyża pod Zachodem Pilotów / {"globalid":"e6ba5010-45f5-4769-9026-229423ddf3cb","origin":"baseline"} | 97.572 m; pomiar źródłowy; best=n/d; status=n/d |

Do rozstrzygnięcia potrzebne oznaczenia otworów/plan lub inny dowód wskazujący, czy to ten sam otwór, inne otwory jednej jaskini, czy różne obiekty. Współrzędne i podobna nazwa są tylko sygnałem. Defer zachowa rewizję i snapshot w trwałej kolejce po zatwierdzeniu tej propozycji.

### D020 — Nyża pod Szarą Turnią II

GLOBALID `b51c01e8-271e-4aef-802d-c87025a09845`; change_id `b51c01e8-271e-4aef-802d-c87025a09845:f114364a59ad37cd44ed3d8486328caa3d21cd4993139c233ce2dc00eb092acb`.

Źródło teraz: lat=49.253470614329444, lon=19.927542287402037; data stanu=2026-06-14; GENEZA=jaskinia; WER_LOK="FF 27052026"; UWAGI=null.

**Proponowane defer:** Odroczyć: brak dowodu tożsamości/odrębności wobec konkretnych kandydatów z raportu; nie tworzyć ani nie scalać obiektów, nie przypinać źródła.

| Kandydat | Nazwy / cel | Sygnały i dystanse |
|---|---|---|
| source:current:1792c71c-54b5-46ce-8e24-454f4a31e73f | Nyża pod Szarą Turnią III / {"globalid":"1792c71c-54b5-46ce-8e24-454f4a31e73f","origin":"current"} | {"code":"similar_name","left":{"field":"current.NAZWA","value":"Nyża pod Szarą Turnią II"},"right":{"field":"current.NAZWA","value":"Nyża pod Szarą Turnią III"},"similarity":0.96,"threshold":0.9}; 28.363 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:55ed69a3-9228-452b-87ce-8133710292b1 | Nyża pod Szarą Turnią I / {"globalid":"55ed69a3-9228-452b-87ce-8133710292b1","origin":"current"} | {"code":"similar_name","left":{"field":"current.NAZWA","value":"Nyża pod Szarą Turnią II"},"right":{"field":"current.NAZWA","value":"Nyża pod Szarą Turnią I"},"similarity":0.9583333333333334,"threshold":0.9}; 50.758 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:70fc9cd8-57de-4c66-a50f-674b3c6f5d55 | Nyża pod Szarą Turnią IV / {"globalid":"70fc9cd8-57de-4c66-a50f-674b3c6f5d55","origin":"current"} | {"code":"similar_name","left":{"field":"current.NAZWA","value":"Nyża pod Szarą Turnią II"},"right":{"field":"current.NAZWA","value":"Nyża pod Szarą Turnią IV"},"similarity":0.9583333333333334,"threshold":0.9}; 51.409 m; pomiar źródłowy; best=n/d; status=n/d |

Do rozstrzygnięcia potrzebne oznaczenia otworów/plan lub inny dowód wskazujący, czy to ten sam otwór, inne otwory jednej jaskini, czy różne obiekty. Współrzędne i podobna nazwa są tylko sygnałem. Defer zachowa rewizję i snapshot w trwałej kolejce po zatwierdzeniu tej propozycji.

### D021 — Komora w Kończystej Turni

GLOBALID `c24021bb-73c2-4bc2-83f1-aabefc26492e`; change_id `c24021bb-73c2-4bc2-83f1-aabefc26492e:07f0b342b06f752496b7656f9536b23a64da9efe289b8d67c3eb2640207fea67`.

Źródło teraz: lat=49.26361043909647, lon=19.879157374523544; data stanu=2026-06-14; GENEZA=jaskinia; WER_LOK="FF 06062026"; UWAGI=null.

**Proponowane defer:** Odroczyć: brak dowodu tożsamości/odrębności wobec konkretnych kandydatów z raportu; nie tworzyć ani nie scalać obiektów, nie przypinać źródła.

| Kandydat | Nazwy / cel | Sygnały i dystanse |
|---|---|---|
| object:MTW-0005 | Nyża w Kończystej / {"cave_id":"C-0091","object_id":"MTW-0005"} | 17.626 m; pomiar m-001; best=False; status=nieweryfikowany; 17.626 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:MTW-0024 | Ciasna Norka / {"cave_id":"C-0280","object_id":"MTW-0024"} | 66.175 m; pomiar m-001; best=False; status=nieweryfikowany; 66.174 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:MTW-0031 | Dziura w Kończystej Niżnia / {"cave_id":"C-0395","object_id":"MTW-0031"} | 74.352 m; pomiar m-001; best=False; status=nieweryfikowany; 74.352 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:MTW-0039 | Nyża pod Progiem w Kończystej / {"cave_id":"C-0536","object_id":"MTW-0039"} | 77.425 m; pomiar m-001; best=False; status=nieweryfikowany; 77.425 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:MTW-0043 | Schron pod Kończystą / {"cave_id":"C-0566","object_id":"MTW-0043"} | 56.213 m; pomiar m-001; best=False; status=nieweryfikowany; 56.213 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:MTW-0052 | Okap w Kończystej Turni / {"cave_id":"C-0672","object_id":"MTW-0052"} | 3.709 m; pomiar m-001; best=False; status=nieweryfikowany; 3.709 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:MTW-0059 | Dziura w Kończystej Turni / {"cave_id":"C-0753","object_id":"MTW-0059"} | 60.013 m; pomiar m-001; best=False; status=nieweryfikowany; 60.013 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:MTW-0060 | Dziura Niżnia w Kończystej Turni / {"cave_id":"C-0778","object_id":"MTW-0060"} | 68.418 m; pomiar m-001; best=False; status=nieweryfikowany; 68.418 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:MTW-0062 | Schronisko Wschodnie w Kończystej / {"cave_id":"C-0803","object_id":"MTW-0062"} | 72.437 m; pomiar m-001; best=False; status=nieweryfikowany; 72.437 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:MTW-0065 | Mała Dziura w Kończystej Turni / {"cave_id":"C-0847","object_id":"MTW-0065"} | 88.284 m; pomiar m-001; best=False; status=nieweryfikowany; 88.285 m; pomiar m-002; best=True; status=nieweryfikowany |
| source:current:0257a120-426e-4b7d-b47f-1d9f853c6c85 | Dziura w Kończystej Niżnia / {"globalid":"0257a120-426e-4b7d-b47f-1d9f853c6c85","origin":"current"} | 91.405 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:0c34f113-d6d5-4e57-9db1-b240ed3533b5 | Schron pod Kończystą / {"globalid":"0c34f113-d6d5-4e57-9db1-b240ed3533b5","origin":"current"} | 65.539 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:1f9eaae2-f97d-4205-bf67-7a43e6ddb5e7 | Ciasna Norka / {"globalid":"1f9eaae2-f97d-4205-bf67-7a43e6ddb5e7","origin":"current"} | 60.707 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:2549106f-2ea9-477a-a5d3-77e6b920c8e5 | Schron nad Komorą w Kończystej Turni / {"globalid":"2549106f-2ea9-477a-a5d3-77e6b920c8e5","origin":"current"} | 29.063 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:37ef7fe5-6e87-47d4-97c8-cb0ebd9ddeee | Dziura nad Zahradziskami / {"globalid":"37ef7fe5-6e87-47d4-97c8-cb0ebd9ddeee","origin":"current"} | 0.169 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:7033eb52-9352-4f35-9adf-89490fbb5f1f | Dziura w Kończystej Turni / {"globalid":"7033eb52-9352-4f35-9adf-89490fbb5f1f","origin":"current"} | 91.094 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:9ba8f361-d7aa-413f-bc86-ac235940f603 | Nyża pod Progiem w Kończystej / {"globalid":"9ba8f361-d7aa-413f-bc86-ac235940f603","origin":"current"} | 39.364 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:9beb2e85-ecb8-432a-90d4-623df217c6da | Nyża za Jałowcem / {"globalid":"9beb2e85-ecb8-432a-90d4-623df217c6da","origin":"current"} | 32.087 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:b2a16ea5-23c8-4e73-bbe7-b4ce1cdf5440 | Okap w Kończystej Turni / {"globalid":"b2a16ea5-23c8-4e73-bbe7-b4ce1cdf5440","origin":"current"} | 18.259 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:dca8221f-d3c2-4eb2-98ea-77957bb07a1a | Dziura Niżnia w Kończystej Turni / {"globalid":"dca8221f-d3c2-4eb2-98ea-77957bb07a1a","origin":"current"} | 86.704 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:f3ae1e5e-ba6a-4c62-86fe-a4f42892808c | Nyża w Kończystej / {"globalid":"f3ae1e5e-ba6a-4c62-86fe-a4f42892808c","origin":"current"} | 53.509 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:f64fab23-53f9-45fa-a1c2-748d15a67568 | Schronisko Wschodnie w Kończystej / {"globalid":"f64fab23-53f9-45fa-a1c2-748d15a67568","origin":"current"} | 32.262 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:0257a120-426e-4b7d-b47f-1d9f853c6c85 | Dziura w Kończystej Niżnia / {"globalid":"0257a120-426e-4b7d-b47f-1d9f853c6c85","origin":"baseline"} | 74.352 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:0c34f113-d6d5-4e57-9db1-b240ed3533b5 | Schron pod Kończystą / {"globalid":"0c34f113-d6d5-4e57-9db1-b240ed3533b5","origin":"baseline"} | 56.213 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:1f9eaae2-f97d-4205-bf67-7a43e6ddb5e7 | Ciasna Norka / {"globalid":"1f9eaae2-f97d-4205-bf67-7a43e6ddb5e7","origin":"baseline"} | 66.174 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:7033eb52-9352-4f35-9adf-89490fbb5f1f | Dziura w Kończystej Turni / {"globalid":"7033eb52-9352-4f35-9adf-89490fbb5f1f","origin":"baseline"} | 60.013 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:9ba8f361-d7aa-413f-bc86-ac235940f603 | Nyża pod Progiem w Kończystej / {"globalid":"9ba8f361-d7aa-413f-bc86-ac235940f603","origin":"baseline"} | 77.425 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:b2a16ea5-23c8-4e73-bbe7-b4ce1cdf5440 | Okap w Kończystej Turni / {"globalid":"b2a16ea5-23c8-4e73-bbe7-b4ce1cdf5440","origin":"baseline"} | 3.709 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:c4a17714-5976-4b41-a6a6-9eacae7e9421 | Mała Dziura w Kończystej Turni / {"globalid":"c4a17714-5976-4b41-a6a6-9eacae7e9421","origin":"baseline"} | 88.285 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:dca8221f-d3c2-4eb2-98ea-77957bb07a1a | Dziura Niżnia w Kończystej Turni / {"globalid":"dca8221f-d3c2-4eb2-98ea-77957bb07a1a","origin":"baseline"} | 68.418 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:f3ae1e5e-ba6a-4c62-86fe-a4f42892808c | Nyża w Kończystej / {"globalid":"f3ae1e5e-ba6a-4c62-86fe-a4f42892808c","origin":"baseline"} | 17.626 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:f64fab23-53f9-45fa-a1c2-748d15a67568 | Schronisko Wschodnie w Kończystej / {"globalid":"f64fab23-53f9-45fa-a1c2-748d15a67568","origin":"baseline"} | 72.437 m; pomiar źródłowy; best=n/d; status=n/d |

Do rozstrzygnięcia potrzebne oznaczenia otworów/plan lub inny dowód wskazujący, czy to ten sam otwór, inne otwory jednej jaskini, czy różne obiekty. Współrzędne i podobna nazwa są tylko sygnałem. Defer zachowa rewizję i snapshot w trwałej kolejce po zatwierdzeniu tej propozycji.

### D022 — Tunel w Skrajnej Giewonckiej Baszcie

GLOBALID `ce72fc5c-f14b-4c6e-bd3e-b411934a8c30`; change_id `ce72fc5c-f14b-4c6e-bd3e-b411934a8c30:cd99b786dd5a8352ea183981d3854b9627912fd7077278c6dcb1e274a6ff7af4`.

Źródło teraz: lat=49.25130687175565, lon=19.928466013383918; data stanu=2026-05-09; GENEZA=jaskinia; WER_LOK="FF 09052026"; UWAGI=null.

**Proponowane defer:** Odroczyć: brak dowodu tożsamości/odrębności wobec konkretnych kandydatów z raportu; nie tworzyć ani nie scalać obiektów, nie przypinać źródła.

| Kandydat | Nazwy / cel | Sygnały i dystanse |
|---|---|---|
| cave:C-0947 | tunel w Skrajnej Giewonckiej Baszcie / {"cave_id":"C-0947","object_id":null} | {"code":"exact_name","left":{"field":"current.NAZWA","value":"Tunel w Skrajnej Giewonckiej Baszcie"},"normalized":"tunel w skrajnej giewonckiej baszcie","right":{"field":"C-0947.name","value":"tunel w Skrajnej Giewonckiej Baszcie"}} |
| cave:C-0981 | tunel w Skrajnej Giewonckiej Baszcie / {"cave_id":"C-0981","object_id":null} | {"code":"exact_name","left":{"field":"current.NAZWA","value":"Tunel w Skrajnej Giewonckiej Baszcie"},"normalized":"tunel w skrajnej giewonckiej baszcie","right":{"field":"C-0981.name","value":"tunel w Skrajnej Giewonckiej Baszcie"}} |
| object:MLW-0044 | tunel w Skrajnej Giewonckiej Baszcie - otwór N; tunel w Skrajnej Giewonckiej Baszcie / {"cave_id":"C-0947","object_id":"MLW-0044"} | {"code":"exact_name","left":{"field":"current.NAZWA","value":"Tunel w Skrajnej Giewonckiej Baszcie"},"normalized":"tunel w skrajnej giewonckiej baszcie","right":{"field":"C-0947.name","value":"tunel w Skrajnej Giewonckiej Baszcie"}}; 8.311 m; pomiar m-001; best=True; status=nieweryfikowany |
| object:MLW-0047 | Schron w Skrajnej Giewonckiej Baszcie / {"cave_id":"C-0959","object_id":"MLW-0047"} | 70.741 m; pomiar m-001; best=True; status=nieweryfikowany |
| object:MLW-0048 | Dziura w Małym Giewoncie / {"cave_id":"C-0969","object_id":"MLW-0048"} | 45.826 m; pomiar m-001; best=True; status=nieweryfikowany |
| object:MLW-0050 | tunel w Skrajnej Giewonckiej Baszcie - otwór S; tunel w Skrajnej Giewonckiej Baszcie / {"cave_id":"C-0981","object_id":"MLW-0050"} | {"code":"exact_name","left":{"field":"current.NAZWA","value":"Tunel w Skrajnej Giewonckiej Baszcie"},"normalized":"tunel w skrajnej giewonckiej baszcie","right":{"field":"C-0981.name","value":"tunel w Skrajnej Giewonckiej Baszcie"}}; 2.202 m; pomiar m-001; best=True; status=nieweryfikowany |
| source:current:5bd9e6e5-330d-45c1-bb5b-27f0a57d8cf0 | Dziura w Małym Giewoncie / {"globalid":"5bd9e6e5-330d-45c1-bb5b-27f0a57d8cf0","origin":"current"} | 45.827 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:65764152-f017-43e3-83ad-3a672092d0be | Schron w Skrajnej Giewonckiej Baszcie / {"globalid":"65764152-f017-43e3-83ad-3a672092d0be","origin":"current"} | 70.739 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:9b566416-3888-4900-b351-cf81fc2a387e | tunel w Skrajnej Giewonckiej Baszcie; S / {"globalid":"9b566416-3888-4900-b351-cf81fc2a387e","origin":"current"} | {"code":"exact_name","left":{"field":"current.NAZWA","value":"Tunel w Skrajnej Giewonckiej Baszcie"},"normalized":"tunel w skrajnej giewonckiej baszcie","right":{"field":"current.NAZWA","value":"tunel w Skrajnej Giewonckiej Baszcie"}}; 2.206 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:f22edcd0-acfd-4797-b2a0-cfd5b325bc8e | tunel w Skrajnej Giewonckiej Baszcie; N / {"globalid":"f22edcd0-acfd-4797-b2a0-cfd5b325bc8e","origin":"current"} | {"code":"exact_name","left":{"field":"current.NAZWA","value":"Tunel w Skrajnej Giewonckiej Baszcie"},"normalized":"tunel w skrajnej giewonckiej baszcie","right":{"field":"current.NAZWA","value":"tunel w Skrajnej Giewonckiej Baszcie"}}; 8.312 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:5bd9e6e5-330d-45c1-bb5b-27f0a57d8cf0 | Dziura w Małym Giewoncie / {"globalid":"5bd9e6e5-330d-45c1-bb5b-27f0a57d8cf0","origin":"baseline"} | 45.826 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:65764152-f017-43e3-83ad-3a672092d0be | Schron w Skrajnej Giewonckiej Baszcie / {"globalid":"65764152-f017-43e3-83ad-3a672092d0be","origin":"baseline"} | 70.741 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:9b566416-3888-4900-b351-cf81fc2a387e | tunel w Skrajnej Giewonckiej Baszcie; S / {"globalid":"9b566416-3888-4900-b351-cf81fc2a387e","origin":"baseline"} | {"code":"exact_name","left":{"field":"current.NAZWA","value":"Tunel w Skrajnej Giewonckiej Baszcie"},"normalized":"tunel w skrajnej giewonckiej baszcie","right":{"field":"baseline.NAZWA","value":"tunel w Skrajnej Giewonckiej Baszcie"}}; 2.202 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:f22edcd0-acfd-4797-b2a0-cfd5b325bc8e | tunel w Skrajnej Giewonckiej Baszcie; N / {"globalid":"f22edcd0-acfd-4797-b2a0-cfd5b325bc8e","origin":"baseline"} | {"code":"exact_name","left":{"field":"current.NAZWA","value":"Tunel w Skrajnej Giewonckiej Baszcie"},"normalized":"tunel w skrajnej giewonckiej baszcie","right":{"field":"baseline.NAZWA","value":"tunel w Skrajnej Giewonckiej Baszcie"}}; 8.311 m; pomiar źródłowy; best=n/d; status=n/d |

Do rozstrzygnięcia potrzebne oznaczenia otworów/plan lub inny dowód wskazujący, czy to ten sam otwór, inne otwory jednej jaskini, czy różne obiekty. Współrzędne i podobna nazwa są tylko sygnałem. Defer zachowa rewizję i snapshot w trwałej kolejce po zatwierdzeniu tej propozycji.

### D023 — Rura w Olejarni

GLOBALID `d96cd642-e9d3-4eb8-b9dc-d7df3f449705`; change_id `d96cd642-e9d3-4eb8-b9dc-d7df3f449705:987668cf9a5776893249eb4151030ab0b92a31bcff676f711296bdd05c887546`.

Źródło teraz: lat=49.247898045743995, lon=19.811777669961646; data stanu=2026-06-16; GENEZA=jaskinia; WER_LOK="FF16062026"; UWAGI=null.

**Proponowane defer:** Odroczyć: brak dowodu tożsamości/odrębności wobec konkretnych kandydatów z raportu; nie tworzyć ani nie scalać obiektów, nie przypinać źródła.

| Kandydat | Nazwy / cel | Sygnały i dystanse |
|---|---|---|
| object:CHZ-0012 | Zbójecka Dziura / {"cave_id":"C-0370","object_id":"CHZ-0012"} | 14.712 m; pomiar m-001; best=False; status=nieweryfikowany; 32.831 m; pomiar m-002; best=True; status=nieweryfikowany |
| source:current:00a63f59-3d03-4703-a18e-27a0a75a7da1 | Szczelina przy Zbójeckiej Dziurze / {"globalid":"00a63f59-3d03-4703-a18e-27a0a75a7da1","origin":"current"} | 28.597 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:e70f5d13-0917-470d-abb0-5d7853d98016 | Zbójecka Dziura / {"globalid":"e70f5d13-0917-470d-abb0-5d7853d98016","origin":"current"} | 32.829 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:e70f5d13-0917-470d-abb0-5d7853d98016 | Zbójecka Dziura / {"globalid":"e70f5d13-0917-470d-abb0-5d7853d98016","origin":"baseline"} | 32.831 m; pomiar źródłowy; best=n/d; status=n/d |

Do rozstrzygnięcia potrzebne oznaczenia otworów/plan lub inny dowód wskazujący, czy to ten sam otwór, inne otwory jednej jaskini, czy różne obiekty. Współrzędne i podobna nazwa są tylko sygnałem. Defer zachowa rewizję i snapshot w trwałej kolejce po zatwierdzeniu tej propozycji.

### D024 — Nyża pod Zachodem Pilotów II

GLOBALID `dec416bc-64f2-49e0-abf9-cb2c5a040004`; change_id `dec416bc-64f2-49e0-abf9-cb2c5a040004:a4e6104b19377df1e03f38b8ed311f19cd4ddbd230bb17801fc7e17fda448bdd`.

Źródło teraz: lat=49.25358290318176, lon=19.929191894997533; data stanu=2026-05-24; GENEZA=jaskinia; WER_LOK="FF  24052026"; UWAGI=null.

**Proponowane defer:** Odroczyć: brak dowodu tożsamości/odrębności wobec konkretnych kandydatów z raportu; nie tworzyć ani nie scalać obiektów, nie przypinać źródła.

| Kandydat | Nazwy / cel | Sygnały i dystanse |
|---|---|---|
| object:STR-0001 | Szczelina w Żlebie Kirkora / {"cave_id":"C-0015","object_id":"STR-0001"} | 80.526 m; pomiar m-001; best=False; status=nieweryfikowany; 80.527 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:STR-0002 | Nyża pod Brzózką / {"cave_id":"C-0018","object_id":"STR-0002"} | 90.841 m; pomiar m-001; best=False; status=nieweryfikowany; 82.852 m; pomiar m-002; best=True; status=nieweryfikowany |
| object:STR-0028 | Nyża pod Zachodem Pilotów / {"cave_id":"C-0984","object_id":"STR-0028"} | 98.769 m; pomiar m-001; best=True; status=nieweryfikowany |
| source:current:2091f15d-54bf-40c7-9cf8-04b2fde247fe | Szczelina w Żlebie Kirkora / {"globalid":"2091f15d-54bf-40c7-9cf8-04b2fde247fe","origin":"current"} | 80.527 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:38626571-caa6-4317-8900-d61a995020e9 | Nyża pod Brzózką / {"globalid":"38626571-caa6-4317-8900-d61a995020e9","origin":"current"} | 82.855 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:55ed69a3-9228-452b-87ce-8133710292b1 | Nyża pod Szarą Turnią I / {"globalid":"55ed69a3-9228-452b-87ce-8133710292b1","origin":"current"} | 89.957 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:643487f7-79ea-45a5-9427-dcde64334e71 | Nyża pod Zachodem Pilotów II / {"globalid":"643487f7-79ea-45a5-9427-dcde64334e71","origin":"current"} | {"code":"exact_name","left":{"field":"current.NAZWA","value":"Nyża pod Zachodem Pilotów II"},"normalized":"nyża pod zachodem pilotów ii","right":{"field":"current.NAZWA","value":"Nyża pod Zachodem Pilotów II"}} |
| source:current:adbf9ca1-deff-402f-a223-04ba9c1d0d35 | Nyża pod Zachodem Pilotów III / {"globalid":"adbf9ca1-deff-402f-a223-04ba9c1d0d35","origin":"current"} | {"code":"similar_name","left":{"field":"current.NAZWA","value":"Nyża pod Zachodem Pilotów II"},"right":{"field":"current.NAZWA","value":"Nyża pod Zachodem Pilotów III"},"similarity":0.9655172413793104,"threshold":0.9}; 3.254 m; pomiar źródłowy; best=n/d; status=n/d |
| source:current:e6ba5010-45f5-4769-9026-229423ddf3cb | Nyża pod Zachodem Pilotów / {"globalid":"e6ba5010-45f5-4769-9026-229423ddf3cb","origin":"current"} | 90.740 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:2091f15d-54bf-40c7-9cf8-04b2fde247fe | Szczelina w Żlebie Kirkora / {"globalid":"2091f15d-54bf-40c7-9cf8-04b2fde247fe","origin":"baseline"} | 80.527 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:38626571-caa6-4317-8900-d61a995020e9 | Nyża pod Brzózką / {"globalid":"38626571-caa6-4317-8900-d61a995020e9","origin":"baseline"} | 82.852 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:e6ba5010-45f5-4769-9026-229423ddf3cb | Nyża pod Zachodem Pilotów / {"globalid":"e6ba5010-45f5-4769-9026-229423ddf3cb","origin":"baseline"} | 98.769 m; pomiar źródłowy; best=n/d; status=n/d |

Do rozstrzygnięcia potrzebne oznaczenia otworów/plan lub inny dowód wskazujący, czy to ten sam otwór, inne otwory jednej jaskini, czy różne obiekty. Współrzędne i podobna nazwa są tylko sygnałem. Defer zachowa rewizję i snapshot w trwałej kolejce po zatwierdzeniu tej propozycji.

### D025 — Okno pod Sikawką

GLOBALID `ef966744-eb95-48b3-b2ba-7a031f8df91a`; change_id `ef966744-eb95-48b3-b2ba-7a031f8df91a:38267f647f1d889bfccde7780705a838bb149d68edc6614946c631bacd460778`.

Źródło teraz: lat=49.2479509176144, lon=19.883164220891572; data stanu=2026-06-02; GENEZA=jaskinia; WER_LOK=null; UWAGI=null.

**Proponowane defer:** Odroczyć: brak dowodu tożsamości/odrębności wobec konkretnych kandydatów z raportu; nie tworzyć ani nie scalać obiektów, nie przypinać źródła.

| Kandydat | Nazwy / cel | Sygnały i dystanse |
|---|---|---|
| source:current:71dd8dce-2bc1-42f7-a5e9-174902ca7aed | Jaskinia przy Sikawce / {"globalid":"71dd8dce-2bc1-42f7-a5e9-174902ca7aed","origin":"current"} | 88.297 m; pomiar źródłowy; best=n/d; status=n/d |

Do rozstrzygnięcia potrzebne oznaczenia otworów/plan lub inny dowód wskazujący, czy to ten sam otwór, inne otwory jednej jaskini, czy różne obiekty. Współrzędne i podobna nazwa są tylko sygnałem. Defer zachowa rewizję i snapshot w trwałej kolejce po zatwierdzeniu tej propozycji.

### D026 — Nyża we Wysrankach

GLOBALID `fdd25a5f-1d27-4bab-9bf7-ebb1c062746c`; change_id `fdd25a5f-1d27-4bab-9bf7-ebb1c062746c:dedaed4d550d837dd184cd6b9402bb9a1d04804ebcb07e44d50cbb7d8d9801f7`.

Źródło teraz: lat=49.24966207787314, lon=19.877003828090277; data stanu=2026-06-02; GENEZA=jaskinia; WER_LOK="FF 02062026"; UWAGI=null.

**Proponowane defer:** Odroczyć: brak dowodu tożsamości/odrębności wobec konkretnych kandydatów z raportu; nie tworzyć ani nie scalać obiektów, nie przypinać źródła.

| Kandydat | Nazwy / cel | Sygnały i dystanse |
|---|---|---|
| object:KSW-0241 | Gawra we Wysrankach / {"cave_id":"C-0879","object_id":"KSW-0241"} | 10.675 m; pomiar m-001; best=True; status=nieweryfikowany |
| source:current:4c30384d-7d8d-48d8-8d57-aea8cc59687c | Gawra we Wysrankach / {"globalid":"4c30384d-7d8d-48d8-8d57-aea8cc59687c","origin":"current"} | 9.870 m; pomiar źródłowy; best=n/d; status=n/d |
| source:baseline:4c30384d-7d8d-48d8-8d57-aea8cc59687c | Gawra we Wysrankach / {"globalid":"4c30384d-7d8d-48d8-8d57-aea8cc59687c","origin":"baseline"} | 10.675 m; pomiar źródłowy; best=n/d; status=n/d |

Do rozstrzygnięcia potrzebne oznaczenia otworów/plan lub inny dowód wskazujący, czy to ten sam otwór, inne otwory jednej jaskini, czy różne obiekty. Współrzędne i podobna nazwa są tylko sygnałem. Defer zachowa rewizję i snapshot w trwałej kolejce po zatwierdzeniu tej propozycji.

## Grupa A — Przyjęcie rewizji źródła bez zmiany katalogu

Każdy approve tej tabeli ma actions=[]: **0 zmian YAML domenowego, pomiarów i best**. Różnice morfometrii (także 0→null), WERYF i WER_LOK są zachowane w snapshotcie/rejestrze źródła. Nie usuwają istniejących opisów. Lokalne nazwy i systemy zachowujemy świadomie. Sama zmiana flagi/daty nie tworzy pomiaru.

| ID | GLOBALID | Nazwa / cel | Dokładne zmiany metadanych źródła | Rozbieżności lokalne — zachować obecne |
|---|---|---|---|---|
| A001 | 0021b205-658a-4117-bff5-e29a95612527 | Szczelina w Ratuszu / {"cave_id":"C-0293","object_id":"KSW-0089"} | {"WERYF":{"before":0,"after":null}} | [] |
| A002 | 00230389-7441-47af-a7ac-8773c7a7b018 | Lustrzana Szczelina / {"cave_id":"C-0163","object_id":"KSW-0047"} | {"WERYF":{"before":0,"after":null}} | [] |
| A003 | 0139978c-1ed6-4717-bd6c-c444aa7f0683 | Schron z Płytą / {"cave_id":"C-0533","object_id":"CHW-0026"} | {"WERYF":{"before":0,"after":null}} | [] |
| A004 | 0146e7be-ebae-4187-833d-200a4f960987 | Sztolnia - Kopalnia w Wantulach II / {"cave_id":"C-0932","object_id":"MTW-0067"} | {"PRZEWYZSZE":{"before":0,"after":null},"WERYF":{"before":0,"after":null}} | [] |
| A005 | 0152572f-b1bc-42fd-a435-fb38f6c3015e | Schron przy Suchym Biwaku / {"cave_id":"C-0610","object_id":"LEJ-0019"} | {"WERYF":{"before":0,"after":null}} | [] |
| A006 | 01a13fe3-0d09-4d00-b525-835760ff4303 | Dziura nad Zachodem / {"cave_id":"C-0074","object_id":"KSW-0023"} | {"WERYF":{"before":0,"after":null}} | [] |
| A007 | 01a58cfe-5670-42a3-ade1-715cf1f1e7a4 | Jaskinia Mylna / {"cave_id":"C-0573","object_id":"KSZ-0113"} | {} | [{"catalog_current":"Jaskinia Mylna - otwór północny","field":"object.name_local","source_after":"N","source_before":"N","source_field":"OTWÓR"}] |
| A008 | 01f20c5e-17ec-4582-ba2f-4acf99b5c482 | Jaskinia Żabia Lodowa / {"cave_id":"C-0482","object_id":"PL-0027"} | {"WERYF":{"before":0,"after":null}} | [] |
| A009 | 02346839-21f2-4d2c-bd00-1c9ad8615175 | Jaskinia nad Lodową Basztą / {"cave_id":"C-0973","object_id":"KSW-0252"} | {"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A010 | 02bc3513-59cd-4dea-b46c-ddb0d0fe8665 | Schronisko pod Dziobem III / {"cave_id":"C-0687","object_id":"CHW-0033"} | {"WERYF":{"before":0,"after":null}} | [] |
| A011 | 0439d7c5-6300-4945-8025-2a86c81e20db | Jasiowa Dziura / {"cave_id":"C-0518","object_id":"MTZ-0037"} | {"WERYF":{"before":0,"after":null}} | [] |
| A012 | 049a3b16-f077-4887-970d-15055b5310dd | Jaskinia Goryckiego / {"cave_id":"C-0300","object_id":"KSW-0093"} | {"WERYF":{"before":0,"after":null}} | [] |
| A013 | 04afa3c6-ef98-4598-bb0b-c5a1172dc2ea | Jaskinia pod Zamkiem / {"cave_id":"C-0526","object_id":"KSW-0158"} | {"WERYF":{"before":0,"after":null}} | [] |
| A014 | 04ba7e19-68aa-4cb7-8486-e946d162c525 | Jaskinia Owcza / {"cave_id":"C-0392","object_id":"KSW-0120"} | {"WERYF":{"before":0,"after":null}} | [] |
| A015 | 0597c8dd-69b6-4ed0-b8ae-0848045006ed | Mała Komora / {"cave_id":"C-0102","object_id":"MTZ-0010"} | {"WERYF":{"before":0,"after":null}} | [] |
| A016 | 05da5368-a9b8-435f-9204-6c7b7e63b816 | Studnia w Progu Mułowym / {"cave_id":"C-0418","object_id":"MTZ-0032"} | {"WERYF":{"before":0,"after":null}} | [] |
| A017 | 05f4e7b0-cb85-4581-9801-3f728ebb1ee6 | Schron nad Kominami / {"cave_id":"C-0097","object_id":"MTZ-0009"} | {"WERYF":{"before":0,"after":null}} | [] |
| A018 | 0606a079-d986-44f9-bc11-22be576a107e | Sztolnia w Dolinie Białego nr 1 / {"cave_id":"C-0881","object_id":"BIA-0005"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null},"WERYF":{"before":0,"after":null}} | [] |
| A019 | 063836dd-fceb-4b79-a7c0-9b7257ac3078 | Dzwonnica / {"cave_id":"C-0364","object_id":"KSW-0109"} | {"WERYF":{"before":0,"after":null}} | [] |
| A020 | 0642cc8d-3c79-4801-a619-542161381fcb | Okap z Rurką / {"cave_id":"C-0979","object_id":"KSW-0253"} | {"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null},"WERYF":{"before":0,"after":null}} | [] |
| A021 | 069e157b-f7b8-47a9-84d7-be52ece92ecf | Nyża pod Bańdziochem / {"cave_id":"C-0274","object_id":"KSZ-0028"} | {"WERYF":{"before":0,"after":null}} | [] |
| A022 | 06b61b57-90eb-48ca-8ff2-dc177585f725 | Mała Szczelina / {"cave_id":"C-0373","object_id":"KSW-0113"} | {"WERYF":{"before":0,"after":null}} | [] |
| A023 | 07247104-afdf-41de-82f4-3c841dc0ca24 | Szczelina w Nosalu / {"cave_id":"C-0890","object_id":"BYW-0039"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null}} | [] |
| A024 | 0729f655-7478-4270-a08e-ffc931a7215f | Jaskinia Zawaliskowa Tomanowa / {"cave_id":"C-0281","object_id":"KSW-0085"} | {"WERYF":{"before":0,"after":null}} | [] |
| A025 | 07bbce7b-22de-4b10-b0d4-665c443148b3 | Schronisko nad Bramką / {"cave_id":"C-0519","object_id":"KSZ-0061"} | {"WERYF":{"before":0,"after":null}} | [] |
| A026 | 08743e0e-f81b-45e6-9c91-f1216680287b | Szczelina w Dudzińcu / {"cave_id":"C-0159","object_id":"CHW-0008"} | {"WERYF":{"before":0,"after":null}} | [] |
| A027 | 088c1f4a-7c5b-4f1b-bcad-527d58944742 | Dziura pod Lodową Małołącką II / {"cave_id":"C-0332","object_id":"MLW-0011"} | {} | [{"catalog_current":null,"field":"cave.system_name","source_after":"SYSTEM Dziurawe","source_before":"SYSTEM Dziurawe","source_field":"SYSTEM"}] |
| A028 | 08b81c36-6909-4560-b876-9c7a04390725 | Sztolnia na Klinowej Czubie nr 5 / {"cave_id":"C-0974","object_id":"CHW-0055"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null},"WERYF":{"before":0,"after":null}} | [] |
| A029 | 08dbe3c9-16d9-498a-879e-11bb66d285b0 | Ciasna Szczelina / {"cave_id":"C-0497","object_id":"MTZ-0036"} | {"WERYF":{"before":0,"after":null}} | [] |
| A030 | 0913d064-7520-486f-9224-225f22c2654a | Schron przy Studni Kuturniańskiej / {"cave_id":"C-0368","object_id":"KSW-0112"} | {"WERYF":{"before":0,"after":null}} | [] |
| A031 | 096c8187-fa3e-4fb9-b077-7205cff221f6 | Studnia w Małej Świstówce / {"cave_id":"C-0718","object_id":"MTZ-0053"} | {"WERYF":{"before":0,"after":null}} | [] |
| A032 | 0a918778-2ba0-4ae8-8dbd-1b8b7c319066 | Koleba w Zawracie Kasprowym / {"cave_id":"C-0911","object_id":"BYW-0041"} | {"DENIWELACJ":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A033 | 0ad65dec-21fd-49ed-9416-5cdfaeb34d29 | Nyża w Białym Grzbiecie / {"cave_id":"C-0991","object_id":"BIA-0008"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A034 | 0ae8810a-0b9d-4603-afaa-4b699daf628b | Koszowa Dziura / {"cave_id":"C-0738","object_id":"PL-0042"} | {"WERYF":{"before":0,"after":null}} | [] |
| A035 | 0afbfc7d-0bd3-4fe7-a7f2-1774398d7dd9 | Schron w Nosalu / {"cave_id":"C-0941","object_id":"BYW-0042"} | {"GLEBOKOSC":{"before":0,"after":null}} | [] |
| A036 | 0c92d771-b5dd-4d1a-a061-8c639277bccb | Okap w Kondratowych Basztach / {"cave_id":"C-0918","object_id":"BYZ-0048"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A037 | 0c942f35-3c72-4dd9-a0d1-511893b1a6ee | Schron pod Zbójnicką Turnią / {"cave_id":"C-0466","object_id":"KSW-0143"} | {"WERYF":{"before":0,"after":null}} | [] |
| A038 | 0e88fdce-b981-49db-96d8-85b1e010921c | Jaskinia pod Niżnią Zbójnicką Turnią / {"cave_id":"C-0623","object_id":"KSW-0177"} | {"WERYF":{"before":0,"after":null}} | [{"catalog_current":null,"field":"cave.system_name","source_after":"SYSTEM Ziobrowa","source_before":"SYSTEM Ziobrowa","source_field":"SYSTEM"}] |
| A039 | 0f0a4f22-d9a3-4f22-8099-259457b49cde | Schron w Żlebie Goryckiego / {"cave_id":"C-0644","object_id":"KSW-0184"} | {"WERYF":{"before":0,"after":null}} | [] |
| A040 | 1032ba2d-24f5-47ec-ac61-1072c1a78439 | Jaskinia Zapylna / {"cave_id":"C-0493","object_id":"MTZ-0035"} | {"WERYF":{"before":0,"after":null}} | [] |
| A041 | 1162df92-39ab-448c-96e0-ecd4a9d131fa | Jaskinia Ciepła / {"cave_id":"C-0377","object_id":"KSW-0114"} | {"WERYF":{"before":0,"after":null}} | [] |
| A042 | 125ab922-4eed-48fe-ae4a-e12d5453bd26 | Studzienka za Ratuszem / {"cave_id":"C-0415","object_id":"MTW-0034"} | {"WERYF":{"before":0,"after":null}} | [] |
| A043 | 137d8706-5bb5-4e9e-bbb8-7dc60b3e75eb | Zbójnicka Nyża / {"cave_id":"C-0698","object_id":"KSW-0200"} | {"WERYF":{"before":0,"after":null}} | [] |
| A044 | 14faf5e2-6113-40e2-b03f-bb5451bf2919 | Dziura nad Studnią / {"cave_id":"C-0627","object_id":"MTZ-0045"} | {"WERYF":{"before":0,"after":null}} | [] |
| A045 | 1519106b-efae-4ffd-89fb-66ecf9b97c30 | Szczelina przed Kufą / {"cave_id":"C-0345","object_id":"CHW-0016"} | {"WERYF":{"before":0,"after":null}} | [] |
| A046 | 161042a4-b8c9-4297-aa43-96c370011bb2 | Schron pod Gniazdem / {"cave_id":"C-0925","object_id":"OLC-0008"} | {"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A047 | 169e7850-6009-4b5f-ae5c-16cc56890b97 | Dziura nad Wapiennikiem / {"cave_id":"C-0835","object_id":"KSZ-0103"} | {"WERYF":{"before":0,"after":null}} | [] |
| A048 | 16cb2c1b-d59f-4c30-b9eb-218bd6d437fa | Dziura w Organach V / {"cave_id":"C-0104","object_id":"KSW-0032"} | {"WERYF":{"before":0,"after":null}} | [] |
| A049 | 173f7ff9-4243-4a98-994f-090ac19b2905 | Jaskinia Mroźna / {"cave_id":"C-0267","object_id":"KSW-0081"} | {} | [{"catalog_current":"Jaskinia Mroźna - wyjście z trasy turystycznej","field":"object.name_local","source_after":"wyjscie z trasy turystycznej","source_before":"wyjscie z trasy turystycznej","source_field":"OTWÓR"},{"catalog_current":null,"field":"cave.system_name","source_after":"Mroźna","source_before":"Mroźna","source_field":"SYSTEM"}] |
| A050 | 186cd6b6-1879-4d04-a806-3ccb64555ba0 | Jaskinia przy Studni w Mnichu / {"cave_id":"C-0652","object_id":"PL-0034"} | {"WERYF":{"before":0,"after":null}} | [] |
| A051 | 192ff205-aacf-4a53-a1bf-c5b44b89846e | Żółta Dziura / {"cave_id":"C-0183","object_id":"KSW-0051"} | {"WERYF":{"before":0,"after":null}} | [] |
| A052 | 19484418-ef5d-48ea-92e9-f424a9f7d3a5 | Schron ze Świeczką / {"cave_id":"C-0660","object_id":"KSW-0188"} | {"WERYF":{"before":0,"after":null}} | [] |
| A053 | 1af0d677-c56c-4ec1-a632-01e0251bbf63 | Jaskinia pod Murem / {"cave_id":"C-0136","object_id":"KSZ-0014"} | {"WERYF":{"before":0,"after":null}} | [] |
| A054 | 1b063c24-a127-41e2-87e8-9c3f271ff79b | Nisza przy Szemrzącym Schronie I / {"cave_id":"C-0307","object_id":"LEJ-0011"} | {"WERYF":{"before":0,"after":null}} | [] |
| A055 | 1b274ba2-8a70-4fba-bce5-50a642876eaa | Jaskinia nad Kasprową Niżnią / {"cave_id":"C-0895","object_id":"BYW-0040"} | {"DENIWELACJ":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A056 | 1b3c3a21-95df-4879-83c6-fea85c95e7aa | Mała Szczelina w Tomanowym Grzbiecie / {"cave_id":"C-0856","object_id":"KSW-0236"} | {"WERYF":{"before":0,"after":null}} | [] |
| A057 | 1c03ab0c-0df5-4c20-95d8-07fb3b2f19c6 | Szczelina w Żlebie Między Mnichy / {"cave_id":"C-0958","object_id":"MLW-0046"} | {"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A058 | 1d079841-ba86-4f16-a9cd-dc89a215567e | Dziura w Organach I / {"cave_id":"C-0149","object_id":"KSW-0042"} | {"WERYF":{"before":0,"after":null}} | [] |
| A059 | 1d6bf396-1f46-47f1-9cc9-953f0a88ec15 | Nyża ze Znakami / {"cave_id":"C-0808","object_id":"KSZ-0098"} | {"WERYF":{"before":0,"after":null}} | [] |
| A060 | 1ea40e28-3959-4489-be4d-320bb3821154 | Studnia w Dziurawej Czubie / {"cave_id":"C-0390","object_id":"PL-0023"} | {"WERYF":{"before":0,"after":null}} | [] |
| A061 | 1ec639a6-0c1c-4522-b7a4-6423e7fa3ac0 | Gawra w Żabim / {"cave_id":"C-1001","object_id":"PL-0056"} | {"GLEBOKOSC":{"before":0,"after":null}} | [] |
| A062 | 1ee240ca-4b40-4ed9-b76a-ef432184b618 | Szczelina w Iglicy / {"cave_id":"C-0686","object_id":"MLZ-0071"} | {} | [{"catalog_current":"Szczelina w Iglicy","field":"object.name_local","source_after":"<Null>","source_before":"<Null>","source_field":"OTWÓR"}] |
| A063 | 1f042473-2e44-4835-ab00-af1c900a30cc | Jaskinia Ślimacza / {"cave_id":"C-0805","object_id":"KSZ-0096"} | {"WERYF":{"before":0,"after":null}} | [] |
| A064 | 1f4770bc-5ce0-4c5f-bb7f-0d120c193b62 | Dziura w Kominie / {"cave_id":"C-0814","object_id":"MTZ-0063"} | {"WERYF":{"before":0,"after":null}} | [] |
| A065 | 1f704d07-e20f-45a0-9d42-cbc0a19163fe | Jaskinia Koszowa / {"cave_id":"C-0063","object_id":"PL-0005"} | {"WERYF":{"before":0,"after":1},"WER_LOK":{"before":null,"after":"FF 08092026"}} | [] |
| A066 | 2004e2cd-6cb8-496d-9a1f-854933b17924 | Dziura w Wysokim Grzbiecie / {"cave_id":"C-0626","object_id":"KSW-0178"} | {"WERYF":{"before":0,"after":null}} | [] |
| A067 | 204a0610-40f4-4d2d-aa17-a138a1237b13 | Gawra w Pronobisie / {"cave_id":"C-0904","object_id":"MLZ-0094"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A068 | 20567815-1502-4120-a2ed-f49884e668b4 | Jaskinia nad Korytem / {"cave_id":"C-0713","object_id":"MLZ-0108"} | {"DENIWELACJ":{"before":0,"after":null},"DLUGOSC":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [{"catalog_current":"Jaskinia nad Korytem - otwór wschodni","field":"object.name_local","source_after":"SE","source_before":"SE","source_field":"OTWÓR"},{"catalog_current":null,"field":"cave.system_name","source_after":"Jaskinia nad Korytem","source_before":"Jaskinia nad Korytem","source_field":"SYSTEM"}] |
| A069 | 206fb217-1cd7-4d83-8fa3-47d9c1a97af2 | Schron pod Przeziorową / {"cave_id":"C-0780","object_id":"KSW-0217"} | {"WERYF":{"before":0,"after":null}} | [] |
| A070 | 20e92310-e70d-4be2-97b8-0bdb690376cb | Jaskinia z Konkrecjami Niżnia / {"cave_id":"C-0052","object_id":"KSW-0013"} | {"WERYF":{"before":0,"after":null}} | [] |
| A071 | 20f45b20-d1ed-4ca6-bd79-7ee08043c244 | Dziura w Stole / {"cave_id":"C-0291","object_id":"KSW-0088"} | {"WERYF":{"before":0,"after":null}} | [] |
| A072 | 222b5960-dc2d-45da-a3cb-ecff4b6b0f3d | Dziurka w Organach / {"cave_id":"C-0630","object_id":"KSW-0180"} | {"WERYF":{"before":0,"after":null}} | [] |
| A073 | 23bc2c1a-02d6-41f2-87fa-e87e50a9f69c | Studnia Kuturniańska / {"cave_id":"C-0582","object_id":"KSW-0170"} | {"WERYF":{"before":0,"after":null}} | [] |
| A074 | 2421d669-e136-4ed2-ae27-9bcfe57bc6d7 | Sztolnia w Ornaczańskim Żlebie nr 1 / {"cave_id":"C-0961","object_id":"PL-0054"} | {"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null},"WERYF":{"before":0,"after":null}} | [] |
| A075 | 245d9ce7-7ea0-430e-8bd7-cb5bcb2a365b | Komora nad Kobylarzem / {"cave_id":"C-1000","object_id":"MTW-0069"} | {"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A076 | 2485b351-01d1-48a7-a37d-209be0407f2c | Jaskinia Balkonowa / {"cave_id":"C-0311","object_id":"KSW-0096"} | {"WERYF":{"before":0,"after":null}} | [] |
| A077 | 24948383-1d8d-4677-b260-cf6ab8fb68fa | Wojtkowa Szpara / sztolnia nr 7 / {"cave_id":"C-0361","object_id":"CHZ-0011"} | {} | [{"catalog_current":"Wojtkowa Szpara","field":"object.name_local","source_after":"Wojtkowa Szpara / sztolnia nr 7","source_before":"Wojtkowa Szpara / sztolnia nr 7","source_field":"NAZWA"},{"catalog_current":"Wojtkowa Szpara","field":"cave.name","source_after":"Wojtkowa Szpara / sztolnia nr 7","source_before":"Wojtkowa Szpara / sztolnia nr 7","source_field":"NAZWA"}] |
| A078 | 24fdd81c-79c9-45cf-8d50-e24df8ca3d17 | Schronisko nad Trawersem w Żeleźniaku I / {"cave_id":"C-0614","object_id":"KSZ-0068"} | {"WERYF":{"before":0,"after":null}} | [] |
| A079 | 255f6ebd-01ab-4dc0-b4c5-363dc5a6805d | Okap z Kurtyną / {"cave_id":"C-0155","object_id":"KSW-0044"} | {"WERYF":{"before":0,"after":null}} | [] |
| A080 | 25604785-57c9-44e3-a432-b94c85d4551b | Szczelina przy Piórze / {"cave_id":"C-0892","object_id":"OLC-0005"} | {"GLEBOKOSC":{"before":0,"after":null}} | [] |
| A081 | 26544190-6761-48e5-a785-82c9f8770f08 | Szczelina w Wołowym Żlebie / {"cave_id":"C-0851","object_id":"MTZ-0065"} | {"WERYF":{"before":0,"after":null}} | [] |
| A082 | 26cc4ba6-2813-4889-9312-d65b431db780 | Jaskinia pod Głazem / {"cave_id":"C-0103","object_id":"KSZ-0010"} | {"WERYF":{"before":0,"after":null}} | [] |
| A083 | 273c4ee6-2362-47ea-a8a1-fcaf3658c6e5 | Jaskinia pod Dachem / {"cave_id":"C-0404","object_id":"MTW-0032"} | {} | [{"catalog_current":"Jaskinia pod Dachem","field":"object.name_local","source_after":"górny","source_before":"górny","source_field":"OTWÓR"}] |
| A084 | 27b1bb14-3ca0-40d1-8d61-487b47998ebc | Świnicka Koleba Niżnia / {"cave_id":"C-0398","object_id":"SUW-0004"} | {"WERYF":{"before":0,"after":null}} | [] |
| A085 | 27d9fb42-f6b9-495d-b6b8-d0f0b6943a5a | Nisza nad Jelenią Percią / {"cave_id":"C-0710","object_id":"KSZ-0084"} | {"WERYF":{"before":0,"after":null}} | [] |
| A086 | 27e2eb89-a22f-443a-934f-ee4f6fbc9636 | Jaskinia za Smrekiem / {"cave_id":"C-0224","object_id":"KSW-0067"} | {"WERYF":{"before":0,"after":null}} | [] |
| A087 | 283787b7-3a80-489a-bee7-f7532b7c3eb0 | Dziura nad Zabijakiem II / {"cave_id":"C-0359","object_id":"LEJ-0013"} | {"WERYF":{"before":0,"after":null}} | [] |
| A088 | 28dea51d-b6ae-478e-b52a-834c3eb460fc | Sztolnia w Przedniej Kopce nr 1 / {"cave_id":"C-0910","object_id":"KSZ-0109"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null},"WERYF":{"before":0,"after":null}} | [] |
| A089 | 2921c035-4b83-4092-8734-a131dc108def | Schronisko pod Dziobem I / {"cave_id":"C-0619","object_id":"CHW-0029"} | {"WERYF":{"before":0,"after":null}} | [] |
| A090 | 295326d3-b141-4d6d-8368-5ad199538330 | Jaskinia Dwuotworowa Krakowska / {"cave_id":"C-0071","object_id":"KSW-0022"} | {"WERYF":{"before":0,"after":null}} | [] |
| A091 | 29ebb2cb-8aab-4ef1-a8dc-7728ae2cc368 | Piwnica Miętusia / {"cave_id":"C-0172","object_id":"MTZ-0017"} | {"DLUGOSC":{"before":2300,"after":3700}} | [] |
| A092 | 2a1db3f5-3264-4c30-97f2-96525aa7ae9a | Nisza przy Szemrzącym Schronie II / {"cave_id":"C-0285","object_id":"LEJ-0009"} | {"WERYF":{"before":0,"after":null}} | [] |
| A093 | 2b10b023-5f25-4cc3-b9f8-3ba313d9c527 | Samkowy Schron / {"cave_id":"C-0891","object_id":"STR-0022"} | {"DENIWELACJ":{"before":0,"after":null},"DLUGOSC":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A094 | 2b423ce5-4084-4093-a935-7648032d30e1 | Wielka Szczelina / {"cave_id":"C-0739","object_id":"KSZ-0088"} | {"WERYF":{"before":0,"after":null}} | [] |
| A095 | 2c536a0d-8e71-488d-9204-6bbc400c4bcc | Jaskinia Zimna / {"cave_id":"C-0297","object_id":"KSW-0257"} | {"DENIWELACJ":{"before":0,"after":null},"DLUGOSC":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [{"catalog_current":"Jaskinia Biała - górny otwór Jaskini Zimnej","field":"object.name_local","source_after":"Jaskinia Biała","source_before":"Jaskinia Biała","source_field":"OTWÓR"},{"catalog_current":null,"field":"cave.system_name","source_after":"Zimna","source_before":"Zimna","source_field":"SYSTEM"}] |
| A096 | 2ce6e27e-96a4-47e3-a020-31264f010d2e | Dziura ze Znakami / {"cave_id":"C-0697","object_id":"KSW-0199"} | {"WERYF":{"before":0,"after":null}} | [] |
| A097 | 2d06db10-ad59-4e25-abd6-25ba344bdc07 | Gawra / {"cave_id":"C-0127","object_id":"KSW-0036"} | {"WERYF":{"before":0,"after":null}} | [] |
| A098 | 2d358179-7fc1-4894-af4d-ea740e5cd480 | Jaskinia za Ratuszem Owalna / {"cave_id":"C-0714","object_id":"MTW-0055"} | {"WERYF":{"before":0,"after":null}} | [] |
| A099 | 2d720753-31d1-4190-99be-a5c2c9709b92 | Szczelina w Żlebie z Bramką II / {"cave_id":"C-0841","object_id":"KSZ-0105"} | {"WERYF":{"before":0,"after":null}} | [] |
| A100 | 2e4c8a2f-d6d3-4073-8747-da85e8f3ba3e | Studnia w Dziurawem / {"cave_id":"C-0137","object_id":"MTZ-0012"} | {"WERYF":{"before":0,"after":null}} | [] |
| A101 | 2e726c9c-0112-404e-8f23-ebdd592eab6f | Świnicka Koleba / {"cave_id":"C-0187","object_id":"SUW-0001"} | {"WERYF":{"before":0,"after":null}} | [] |
| A102 | 2f06a9a5-7185-4981-b146-8dd1acbf8176 | Szczelina na Zakręcie II / {"cave_id":"C-0141","object_id":"KSW-0040"} | {"WERYF":{"before":0,"after":null}} | [] |
| A103 | 2f864f67-8447-4a52-8693-906136daa126 | Okap nad Kościołem / {"cave_id":"C-0116","object_id":"CHW-0007"} | {"WERYF":{"before":0,"after":null}} | [] |
| A104 | 2f87ed72-7153-46ca-aa09-bda5c60a968a | Upłazkowa Szczelina / {"cave_id":"C-0385","object_id":"KSW-0117"} | {"WERYF":{"before":0,"after":null}} | [] |
| A105 | 30f0a3b7-a808-4c9a-a066-0a758d526192 | Mnichowy Komin / {"cave_id":"C-0818","object_id":"PL-0045"} | {"WERYF":{"before":0,"after":null}} | [] |
| A106 | 31379085-223b-4255-804d-b8fe31e0865a | Schron przy Źródle / {"cave_id":"C-0706","object_id":"SUW-0005"} | {"WERYF":{"before":0,"after":null}} | [] |
| A107 | 315d798d-e0b0-4952-ac05-93bc41fd6f72 | Dziura nad Trawiastym Progiem / {"cave_id":"C-0099","object_id":"KSW-0030"} | {"WERYF":{"before":0,"after":null}} | [] |
| A108 | 32002bf4-19e5-4bdc-8ef1-93d2e7b54909 | Szczelina nad Okapami / {"cave_id":"C-0866","object_id":"MLZ-0087"} | {"PRZEWYZSZE":{"before":0,"after":null},"WERYF":{"before":0,"after":null}} | [] |
| A109 | 3312298e-caf0-4380-ac6c-35f11d4db105 | Jaskinia Smytnia / {"cave_id":"C-0659","object_id":"KSZ-0076"} | {"WERYF":{"before":0,"after":null}} | [] |
| A110 | 331a7e2e-439b-4e79-a5a8-f4b6cce19662 | Mała Żabia Szpara / {"cave_id":"C-0773","object_id":"PL-0044"} | {"WERYF":{"before":0,"after":null}} | [] |
| A111 | 33966ee8-29e8-438d-a2fa-d2fe604d5dd0 | Korytarz nad Kominem Flacha / {"cave_id":"C-0933","object_id":"MLZ-0096"} | {"DENIWELACJ":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A112 | 34002888-690d-42b3-bcaf-7b6a2243bf3b | Szczelina w Żlebie z Bramką I / {"cave_id":"C-0701","object_id":"KSZ-0081"} | {"WERYF":{"before":0,"after":null}} | [] |
| A113 | 347e9678-1439-45d4-b7a1-f3f8f7d66921 | Szczelina z Mostkiem / {"cave_id":"C-0222","object_id":"KSW-0066"} | {"WERYF":{"before":0,"after":null}} | [] |
| A114 | 3490dd50-6a7f-43c3-9e6e-942edd72a091 | Żółty Schron / {"cave_id":"C-0134","object_id":"KSW-0039"} | {"WERYF":{"before":0,"after":null}} | [] |
| A115 | 34e08e1e-9ab5-42bb-8640-3c73b10d978a | Szczelina pod Siodłową Turnią / {"cave_id":"C-0957","object_id":"MLW-0045"} | {"DENIWELACJ":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A116 | 351f2f77-2551-4ae3-b265-f5f16650e8de | Groby / {"cave_id":"C-0745","object_id":"KSW-0210"} | {"WERYF":{"before":0,"after":null}} | [] |
| A117 | 35c7e917-a53f-4a9b-ab4a-7d44b6b7915e | Jaskinia w Kondratowych Basztach / {"cave_id":"C-0965","object_id":"BYZ-0055"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null}} | [] |
| A118 | 364e48c0-8408-4732-bea1-06ee039f7126 | Zawaliskowy Korytarz / {"cave_id":"C-0719","object_id":"MTZ-0054"} | {"WERYF":{"before":0,"after":null}} | [] |
| A119 | 36599465-f9ff-48d7-81c4-a6441ecf652b | Zimna Szczelina I / {"cave_id":"C-0750","object_id":"KSZ-0089"} | {"WERYF":{"before":0,"after":null}} | [] |
| A120 | 366db31c-d355-4e7a-ae28-9cee64b0fc4e | Trzyotworowy Kominek przy Bańdziochu / {"cave_id":"C-0653","object_id":"KSZ-0073"} | {"WERYF":{"before":0,"after":null}} | [] |
| A121 | 368f5025-3b22-4381-ac16-3fcaa21035dd | Zimna Szczelina III / {"cave_id":"C-0555","object_id":"KSZ-0063"} | {"WERYF":{"before":0,"after":null}} | [] |
| A122 | 3a508711-f9f0-40a0-9dd5-7c13c3f68e52 | Szczelina za Siedmiu Progami / {"cave_id":"C-0217","object_id":"KSW-0064"} | {"WERYF":{"before":0,"after":null}} | [] |
| A123 | 3c126795-babc-4d81-b482-270c24629384 | Podwójna Szczelina / {"cave_id":"C-0584","object_id":"MTZ-0042"} | {"WERYF":{"before":0,"after":null}} | [] |
| A124 | 3c6678c5-9b82-4db8-8de9-ab31b1f31a5d | Szczelina w Tomanowym Grzbiecie VI / {"cave_id":"C-0399","object_id":"KSW-0122"} | {"WERYF":{"before":0,"after":null}} | [] |
| A125 | 3ce5e8de-4cd1-400e-a642-d66663ecfdb2 | Schronisko nad Bramą / {"cave_id":"C-0730","object_id":"KSZ-0086"} | {"WERYF":{"before":0,"after":null}} | [] |
| A126 | 3ce9af97-b67a-47f3-9309-60a8442f46e7 | Szczelina w Grani II / {"cave_id":"C-0240","object_id":"LEJ-0007"} | {"WERYF":{"before":0,"after":null}} | [] |
| A127 | 3e46acc8-6c9f-4340-b525-8c64c859caa2 | Jaskinia Poszukiwaczy Skarbów / {"cave_id":"C-0196","object_id":"KSW-0057"} | {"WERYF":{"before":0,"after":null}} | [] |
| A128 | 3e61d26b-9233-4844-ba9e-ad834e0fb23f | Krakowska Piwnica / {"cave_id":"C-0522","object_id":"KSW-0157"} | {"WERYF":{"before":0,"after":null}} | [] |
| A129 | 3edd58b4-5f56-44fd-ad00-33cc9e44a795 | Nyża w Depresji Strzebońskiego / {"cave_id":"C-0943","object_id":"MLZ-0100"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A130 | 3f1326dd-25e3-4a65-b5e2-f9b6e93ad13e | Dziura nad Wantulami II / {"cave_id":"C-0309","object_id":"MTZ-0024"} | {"WERYF":{"before":0,"after":null}} | [] |
| A131 | 3f7018b7-6bb7-4181-9f09-607add6ec315 | Szczelina w Niżniej Świstówce I / {"cave_id":"C-0898","object_id":"MLW-0038"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A132 | 4033c400-e3f6-4a80-a3a5-5f9b34fc8386 | Raptawicki Tunelik / {"cave_id":"C-0180","object_id":"KSZ-0019"} | {"WERYF":{"before":0,"after":null}} | [] |
| A133 | 40babaca-2961-4151-b400-51d2dd77ef40 | Schron pod Owczą II / {"cave_id":"C-0836","object_id":"KSW-0229"} | {"WERYF":{"before":0,"after":null}} | [] |
| A134 | 41bc4040-43bc-4b5b-9254-f22882835c7e | Kozi Schron / {"cave_id":"C-0828","object_id":"KSW-0226"} | {"WERYF":{"before":0,"after":null}} | [] |
| A135 | 4228b47b-8852-4afb-8d2f-d2a49b7d3ed5 | Szczelina przy Dziurawcu / {"cave_id":"C-0035","object_id":"KSW-0009"} | {"WERYF":{"before":0,"after":null}} | [] |
| A136 | 42d3f366-f55c-48cf-a5bc-1eaabe01cc7f | Szczelina nad Okapami / {"cave_id":"C-0866","object_id":"MLZ-0087"} | {"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A137 | 42df76de-54b3-49cb-a115-a20a09f4f0fe | Grota nad Małą Przełączką / {"cave_id":"C-0194","object_id":"KSW-0055"} | {"WERYF":{"before":0,"after":null}} | [] |
| A138 | 437ebc4e-4e38-439b-b926-3048ca7fc33f | Wciągająca Szczelina / {"cave_id":"C-0715","object_id":"MTW-0056"} | {"WERYF":{"before":0,"after":null}} | [] |
| A139 | 43cc32a1-2758-44d8-89cc-4f537f35bda9 | Schron pod Tunelem / {"cave_id":"C-0329","object_id":"KSZ-0040"} | {"WERYF":{"before":0,"after":null}} | [] |
| A140 | 43e5925d-1348-42e6-abbc-115d0f255f5a | Schron przy Wymytem / {"cave_id":"C-0897","object_id":"DZI-0006"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A141 | 445cd659-54b4-4c12-b5dd-3d75678bd427 | Nyża przy Perci / {"cave_id":"C-0810","object_id":"KSZ-0099"} | {"WERYF":{"before":0,"after":null}} | [] |
| A142 | 448a3fe4-168f-47cb-a7e0-5e32ed04dab7 | Jaskinia w Żarze / {"cave_id":"C-0846","object_id":"KSW-0233"} | {"WERYF":{"before":0,"after":null}} | [] |
| A143 | 44cea0b5-66bc-45ce-9f0a-8c35e4999cb2 | Okno w Zamczysku / {"cave_id":"C-0646","object_id":"KSW-0185"} | {"WERYF":{"before":0,"after":null}} | [] |
| A144 | 45251c42-3eb2-461e-9b1e-9cd0032ad20d | Jaskinia Niespodzianka / {"cave_id":"C-0326","object_id":"MTZ-0026"} | {"WERYF":{"before":0,"after":null}} | [] |
| A145 | 455d8919-51f3-4745-b0ae-c8455f437a5e | Schron za Smrekiem / {"cave_id":"C-0596","object_id":"CHW-0028"} | {"WERYF":{"before":0,"after":null}} | [] |
| A146 | 45db9dc6-2ca9-448a-a2a1-d0a3bb4c1f16 | Piwniczka / {"cave_id":"C-0039","object_id":"MTZ-0005"} | {"WERYF":{"before":0,"after":null}} | [] |
| A147 | 474fb43c-d2ec-45a9-a5f3-5c9d92bcc1d2 | Mały Krakowski Schron / {"cave_id":"C-0502","object_id":"KSW-0154"} | {"WERYF":{"before":0,"after":null}} | [] |
| A148 | 480831fa-5194-4224-a4a9-05e713efccbe | Sztolnia w Ornaczańskim Żlebie nr 2 / {"cave_id":"C-0931","object_id":"PL-0053"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null},"WERYF":{"before":0,"after":null}} | [] |
| A149 | 48419e6f-c8b9-4cda-b034-923f57c688b7 | Krasowa Nisza / {"cave_id":"C-0009","object_id":"KSW-0004"} | {"WERYF":{"before":0,"after":null}} | [] |
| A150 | 48c7400b-eadc-459e-a231-e3889a364e3b | Śnieżna Szczelina / {"cave_id":"C-0628","object_id":"KSW-0179"} | {"WERYF":{"before":0,"after":null}} | [] |
| A151 | 4993d9a0-1e73-4b09-b796-a1b227ed8583 | Schron nad Lejową / {"cave_id":"C-0736","object_id":"LEJ-0024"} | {"WERYF":{"before":0,"after":null}} | [] |
| A152 | 49c610d9-1f24-4303-82a8-9e077342683e | Świstowa Studnia / {"cave_id":"C-0487","object_id":"MLZ-0046"} | {} | [{"catalog_current":"Świstowa Studnia","field":"object.name_local","source_after":"<pusta wartość>","source_before":"<pusta wartość>","source_field":"OTWÓR"},{"catalog_current":null,"field":"cave.system_name","source_after":"<pusta wartość>","source_before":"<pusta wartość>","source_field":"SYSTEM"}] |
| A153 | 49ca1c93-b861-42c0-b6e6-bf67746e362f | Szczelina w Tomanowym Grzbiecie I / {"cave_id":"C-0453","object_id":"KSW-0140"} | {"WERYF":{"before":0,"after":null}} | [] |
| A154 | 49ce04d4-881e-4d94-ba4a-02ca600fae88 | Studnia przy Mnichowym Kominie / {"cave_id":"C-0734","object_id":"PL-0041"} | {"WERYF":{"before":0,"after":null}} | [] |
| A155 | 4a2e89dd-c0bf-4e5d-bfa8-9e7d8adcaa3d | Jaskinia Skoruszowa / {"cave_id":"C-0365","object_id":"KSW-0110"} | {"WERYF":{"before":0,"after":null}} | [] |
| A156 | 4a5f7d4e-8063-41af-bf87-8ed372d14d56 | Jaskinia Piarżysta / {"cave_id":"C-0077","object_id":"KSW-0026"} | {"WERYF":{"before":0,"after":null}} | [] |
| A157 | 4b93fea3-bf1a-4b34-bd98-0e41e9535be9 | Szczelina w Łomiku / {"cave_id":"C-0862","object_id":"BIA-0003"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A158 | 4dcf9f3c-2719-44f3-b6d8-c208e02edd74 | Korytarzyk pod Jagnięcą / {"cave_id":"C-0481","object_id":"KSW-0149"} | {"WERYF":{"before":0,"after":null}} | [] |
| A159 | 4e07a949-607f-4a3a-ad34-2921f3660890 | Nyża nad Ziobrową / {"cave_id":"C-0333","object_id":"KSW-0102"} | {"WERYF":{"before":0,"after":null}} | [] |
| A160 | 4e200262-7a42-4923-acaa-cac2ea924bcf | Nyża pod Jaskinią w Kosówkach / {"cave_id":"C-0255","object_id":"LEJ-0008"} | {"WERYF":{"before":0,"after":null}} | [] |
| A161 | 4e7cbe59-8470-4963-8247-3c2daa9ea66d | Jaskinia w Kosówkach / {"cave_id":"C-0813","object_id":"KSZ-0100"} | {"WERYF":{"before":0,"after":null}} | [] |
| A162 | 4f3d8007-20eb-412a-a46e-fe1721713639 | Jaskinia Śnieżna / {"cave_id":"C-0648","object_id":"MLZ-0068"} | {} | [{"catalog_current":null,"field":"cave.system_name","source_after":"Jaskinia Wielka Śnieżna","source_before":"Jaskinia Wielka Śnieżna","source_field":"SYSTEM"}] |
| A163 | 4fc50beb-f256-44c8-9f80-0f1f82000086 | Tomanowa Szczelina I / {"cave_id":"C-0833","object_id":"KSW-0228"} | {"WERYF":{"before":0,"after":null}} | [] |
| A164 | 50026e60-aae0-43b5-914d-445812703942 | Lustrzany Korytarz / {"cave_id":"C-0306","object_id":"KSW-0095"} | {"WERYF":{"before":0,"after":null}} | [] |
| A165 | 506807b1-ed3b-4230-a608-17ecb40a8d8b | Szczelina w Ścianie / {"cave_id":"C-0678","object_id":"KSW-0193"} | {"WERYF":{"before":0,"after":null}} | [] |
| A166 | 5085400e-9c55-4bde-89c7-740a8f6190b6 | Zielona Szczelina / {"cave_id":"C-0996","object_id":"KSW-0255"} | {"GLEBOKOSC":{"before":0,"after":null}} | [] |
| A167 | 513f5fb1-96ac-4b73-a9e3-4dacbf64fe4f | Zasłonięta Szczelina / {"cave_id":"C-0324","object_id":"KSZ-0039"} | {"WERYF":{"before":0,"after":null}} | [] |
| A168 | 51ab7014-9feb-4e1a-97fa-902abe7cc018 | Szczelina pod Tunelem Pawlikowskiego / {"cave_id":"C-0053","object_id":"KSW-0014"} | {"WERYF":{"before":0,"after":null}} | [] |
| A169 | 51b5c393-762b-4f82-ae55-2b3aecd95035 | Jaskinia Czarna / {"cave_id":"C-0699","object_id":"KSW-0201"} | {} | [{"catalog_current":null,"field":"cave.system_name","source_after":"Czarna","source_before":"Czarna","source_field":"SYSTEM"}] |
| A170 | 51c9495b-6d4a-4817-8247-977833b0bcb5 | Niżni Okap nad Tomanową / {"cave_id":"C-0529","object_id":"KSW-0159"} | {"WERYF":{"before":0,"after":null}} | [] |
| A171 | 521ea98b-14d4-4581-9388-e9c79e0a46cf | Nisza z Jaworem / {"cave_id":"C-0680","object_id":"KSW-0194"} | {"WERYF":{"before":0,"after":null}} | [] |
| A172 | 524ded86-ff47-4a92-ad52-1d79d1bb0ce0 | Koliby / {"cave_id":"C-0414","object_id":"KSW-0125"} | {"WERYF":{"before":0,"after":null}} | [] |
| A173 | 52a6d4d9-779e-44ba-9c4f-0ae35c796ee7 | Szczelina za Płytą / {"cave_id":"C-0571","object_id":"MTW-0044"} | {"WERYF":{"before":0,"after":null}} | [] |
| A174 | 52ac1d8a-24f3-40aa-84c7-7ca9dc07b0d4 | Dziura w Organach VII / {"cave_id":"C-0691","object_id":"KSW-0198"} | {"WERYF":{"before":0,"after":null}} | [] |
| A175 | 52b4ee08-00c8-46f7-bd53-948290edfae4 | Jaskinia Troista / {"cave_id":"C-0792","object_id":"CHW-0039"} | {"WERYF":{"before":0,"after":null}} | [] |
| A176 | 5420590a-d973-41bf-87ae-820ea966d43a | Nyża przed Bramą / {"cave_id":"C-0259","object_id":"KSZ-0025"} | {"WERYF":{"before":0,"after":null}} | [] |
| A177 | 5473f2d1-ac72-40e9-a7e7-b09e7867e9fa | Jaskinia Lejbusiowa / {"cave_id":"C-0160","object_id":"MTZ-0013"} | {"WERYF":{"before":0,"after":null}} | [] |
| A178 | 55347a38-104a-43f0-b682-1126c79c55ca | Szczelina w Panienkach Smytniańskich / {"cave_id":"C-0174","object_id":"KSZ-0018"} | {"WERYF":{"before":0,"after":null}} | [] |
| A179 | 55c5b8f5-ffdc-4856-aa93-507f74b532d1 | Schron pod Owczą I / {"cave_id":"C-0203","object_id":"KSW-0059"} | {"WERYF":{"before":0,"after":null}} | [] |
| A180 | 56768c10-58d4-4635-9ba6-35f9c835ff1a | Dziura pod Smrekiem / {"cave_id":"C-0441","object_id":"KSW-0136"} | {"WERYF":{"before":0,"after":null}} | [] |
| A181 | 568d3748-9abd-4ccc-ad15-50a7e8efbfa1 | Sowia Jama II / {"cave_id":"C-0282","object_id":"KSZ-0031"} | {"WERYF":{"before":0,"after":null}} | [] |
| A182 | 5703f7a0-5171-4cdc-bbd0-ac730bd6fb56 | Nyża pod Schronem w Dolinie Litworowej / {"cave_id":"C-0443","object_id":"MTW-0037"} | {"WERYF":{"before":0,"after":null}} | [] |
| A183 | 5760c06d-8e78-4d2c-a4df-2a3fcb0bf8b2 | Szczelina w Zameczkach / {"cave_id":"C-0864","object_id":"BIA-0004"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null}} | [] |
| A184 | 5764bf98-913e-45f9-9fce-50c498610fa3 | Komora w Okręcie / {"cave_id":"C-0716","object_id":"KSW-0202"} | {"WERYF":{"before":0,"after":null}} | [] |
| A185 | 57d7d3f9-32bd-430d-826d-d5a67d07a4f7 | Omszała Szczelina w Żeleźniaku / {"cave_id":"C-0779","object_id":"KSZ-0091"} | {"WERYF":{"before":0,"after":null}} | [] |
| A186 | 5811b4f0-9466-491f-a4a5-28ed700d1a5d | Sztolnia na Klinowej Czubie nr 8 / {"cave_id":"C-0867","object_id":"CHW-0043"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null},"WERYF":{"before":0,"after":null}} | [] |
| A187 | 589ee1aa-2cb9-4ae9-bda4-edff136826d9 | Korytarz nad Dziurawem / {"cave_id":"C-0431","object_id":"MTZ-0033"} | {"WERYF":{"before":0,"after":null}} | [] |
| A188 | 58dd6281-41bf-4a91-980e-3dbc769549c2 | Suchy Biwak / {"cave_id":"C-0568","object_id":"LEJ-0018"} | {"WERYF":{"before":0,"after":null}} | [] |
| A189 | 59093de6-709c-4a98-ad99-2c2dd899b772 | Szczelina w Mechach / {"cave_id":"C-0955","object_id":"KSW-0248"} | {"DENIWELACJ":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A190 | 5a18cee0-da04-4700-a785-133eeed3e146 | Szczelina przy Zawieszonej Skale II / {"cave_id":"C-0151","object_id":"KSZ-0016"} | {"WERYF":{"before":0,"after":null}} | [] |
| A191 | 5aab57a3-cc95-4ae0-adf1-c335f1db7601 | Kominki w Panienkach Smytniańskich / {"cave_id":"C-0038","object_id":"KSZ-0003"} | {"WERYF":{"before":0,"after":null}} | [] |
| A192 | 5ab5c041-c89d-4653-b05b-31ea2e8eb461 | Schron w Wysokim Grzbiecie / {"cave_id":"C-0962","object_id":"KSW-0250"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A193 | 5abd931b-40ac-4081-b817-f92a01231bff | Dziura w Krzesanicy II / {"cave_id":"C-0164","object_id":"MTZ-0014"} | {"WERYF":{"before":0,"after":null}} | [] |
| A194 | 5bd9e6e5-330d-45c1-bb5b-27f0a57d8cf0 | Dziura w Małym Giewoncie / {"cave_id":"C-0969","object_id":"MLW-0048"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A195 | 5cdc0722-1a08-4178-8618-f6351261a155 | Schronisko pod Dziobem II / {"cave_id":"C-0579","object_id":"CHW-0027"} | {"WERYF":{"before":0,"after":null}} | [] |
| A196 | 5d102bca-7697-444f-b98a-af5027b41b3f | Tunel pod Upłazkowym Przechodem / {"cave_id":"C-0558","object_id":"KSW-0165"} | {"WERYF":{"before":0,"after":null}} | [] |
| A197 | 5ddcec2f-0fb7-4366-8a30-363a20e70f16 | Nisza Zachodnia / {"cave_id":"C-0645","object_id":"KSZ-0072"} | {"WERYF":{"before":0,"after":null}} | [] |
| A198 | 5deecef0-d133-4954-9235-6229fc686b9f | Sztolnia w Żlebie Piekło / {"cave_id":"C-0878","object_id":"PL-0048"} | {"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null},"WERYF":{"before":0,"after":null}} | [] |
| A199 | 5e109aad-ec27-43c8-af97-e9492b597f11 | Żwirowa Dziura Niżnia / {"cave_id":"C-0175","object_id":"KSW-0048"} | {"WERYF":{"before":0,"after":null}} | [] |
| A200 | 5f35683c-23c0-4cc9-bbc8-ba8febbe9400 | Dziura w Ścianie / {"cave_id":"C-0092","object_id":"KSW-0029"} | {"WERYF":{"before":0,"after":null}} | [] |
| A201 | 5fd3f337-9f29-49ac-9183-3d97af490c9d | Rzędowa Szczelina / {"cave_id":"C-0585","object_id":"KSW-0171"} | {"WERYF":{"before":0,"after":null}} | [] |
| A202 | 6028a57d-ef11-4296-bdba-5dc639d14f39 | Dziura nad Żlebem / {"cave_id":"C-0131","object_id":"KSW-0038"} | {"WERYF":{"before":0,"after":null}} | [] |
| A203 | 607c3858-e4fd-4470-982e-19dec353648d | Jaskinia w Zbójnickiej Turni / {"cave_id":"C-0632","object_id":"KSW-0181"} | {"WERYF":{"before":0,"after":null}} | [] |
| A204 | 618bb524-677e-40bc-83ed-ea213385fa49 | Szczelina za Ptakową Turnią / {"cave_id":"C-0262","object_id":"KSW-0080"} | {"WERYF":{"before":0,"after":null}} | [] |
| A205 | 61a58610-c3ae-4d2d-9c78-3e5741214d77 | Schron w Zdziarchach / {"cave_id":"C-0893","object_id":"BYZ-0047"} | {"GLEBOKOSC":{"before":0,"after":null}} | [] |
| A206 | 61a88b7e-f4d7-448e-89c5-22f89ba5baef | Schron w Kondratowych Basztach / {"cave_id":"C-0863","object_id":"BYZ-0042"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null}} | [] |
| A207 | 61c8f926-ccaa-4aaf-a5d3-6d212ccfa8b8 | Szczelina w Tomanowym Grzbiecie III / {"cave_id":"C-0840","object_id":"KSW-0231"} | {"WERYF":{"before":0,"after":null}} | [] |
| A208 | 63ce8b66-47f2-4b2b-bac3-bd01b2127446 | Schron w Piecach / {"cave_id":"C-0438","object_id":"CHW-0020"} | {"WERYF":{"before":0,"after":null}} | [] |
| A209 | 64959601-03de-4d5f-97b7-0d7b3ad605a1 | Szczelina w Iwanówce / {"cave_id":"C-0047","object_id":"CHW-0005"} | {"WERYF":{"before":0,"after":null}} | [] |
| A210 | 64a27a6a-c25b-4f35-b18e-95c389fee794 | Dziura na Półce / {"cave_id":"C-0704","object_id":"MTZ-0051"} | {"WERYF":{"before":0,"after":null}} | [] |
| A211 | 64d75a4b-054c-4861-b3c3-a13eaa3605d6 | Nisza w Organach / {"cave_id":"C-0490","object_id":"KSW-0150"} | {"WERYF":{"before":0,"after":null}} | [] |
| A212 | 65764152-f017-43e3-83ad-3a672092d0be | Schron w Skrajnej Giewonckiej Baszcie / {"cave_id":"C-0959","object_id":"MLW-0047"} | {"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A213 | 65b7b865-77d5-43a4-94f1-0a31eba041db | Dziura w Organach III / {"cave_id":"C-0607","object_id":"KSW-0176"} | {"WERYF":{"before":0,"after":null}} | [] |
| A214 | 660052dc-2294-4683-a02c-c80e4fbafffe | Jaskinia za Ratuszem Szeroka / {"cave_id":"C-0340","object_id":"MTW-0029"} | {"WERYF":{"before":0,"after":null}} | [] |
| A215 | 66b3cf2a-364b-4a5a-bce4-53ea7f74f4ca | Schron w Depresji Strzebońskiego / {"cave_id":"C-0968","object_id":"MLZ-0102"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A216 | 66ff6cc1-710b-4226-b424-08a8b1ee4c7b | Dziura nad Zachodem Wyżnia / {"cave_id":"C-0389","object_id":"KSW-0119"} | {"WERYF":{"before":0,"after":null}} | [] |
| A217 | 674815a2-6117-4345-ae0c-96b55454081d | Dziura nad Piórem / {"cave_id":"C-0917","object_id":"OLC-0007"} | {"GLEBOKOSC":{"before":0,"after":null}} | [] |
| A218 | 6842b5c5-69ec-4f77-810f-8a5b2368d16b | Wielka Żabia Szpara / {"cave_id":"C-0007","object_id":"PL-0002"} | {"WERYF":{"before":0,"after":null}} | [] |
| A219 | 685f7459-2f5d-4ac5-a5e8-b305d8bb865b | Korytarzyk w Czarnych Turniach / {"cave_id":"C-0848","object_id":"KSZ-0106"} | {"WERYF":{"before":0,"after":null}} | [] |
| A220 | 68642d6b-f4c0-4c24-a3ca-ed50c8ee96ba | Kalacka Nyża IV / {"cave_id":"C-0919","object_id":"BYZ-0049"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A221 | 690fc059-791f-46ee-969d-cdd1f0ba3460 | Szczelina w Baranich Schodach / {"cave_id":"C-0987","object_id":"MLZ-0105"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A222 | 69aafa05-b645-40cc-9904-7240ad30f03f | Dziura pod Oknem / {"cave_id":"C-0742","object_id":"KSW-0208"} | {"WERYF":{"before":0,"after":null}} | [] |
| A223 | 6bc083e5-ef96-4b9f-85bd-e6ed886486b0 | Szczelina za Okrętem II / {"cave_id":"C-0446","object_id":"KSW-0137"} | {"WERYF":{"before":0,"after":null}} | [] |
| A224 | 6c6683bc-de94-4daa-8716-64c86939974b | Myślenicki Meanderek / {"cave_id":"C-0990","object_id":"BYZ-0059"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A225 | 6ca87105-875d-4773-98b8-2235192b32f7 | Dziura w Organach VI / {"cave_id":"C-0032","object_id":"KSW-0007"} | {"WERYF":{"before":0,"after":null}} | [] |
| A226 | 6ce94674-5ac1-47ca-be15-f216270a5e9a | Schron przy Troistej II / {"cave_id":"C-0696","object_id":"CHW-0034"} | {"WERYF":{"before":0,"after":null}} | [] |
| A227 | 6d01ad30-46fd-45d8-8f59-2b2bf3e47d62 | Zbójnicka Piwnica / {"cave_id":"C-0765","object_id":"KSW-0215"} | {"WERYF":{"before":0,"after":null}} | [] |
| A228 | 6d0adc15-4701-4bc5-ad88-7b442046e34e | Szczelina pod Gankową III / {"cave_id":"C-0478","object_id":"KSW-0148"} | {"WERYF":{"before":0,"after":null}} | [] |
| A229 | 6d429c71-ad9e-4bc9-8637-446925f87ee9 | Szczelina przed Bańdziochem / {"cave_id":"C-0483","object_id":"KSZ-0054"} | {"WERYF":{"before":0,"after":null}} | [] |
| A230 | 6e0ebc33-4eac-46f5-9bab-fbfc1b2466c1 | Szczelina nad Mechami / {"cave_id":"C-0915","object_id":"KSW-0245"} | {"DENIWELACJ":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A231 | 6eb691b5-23db-4f59-b479-d408a585e062 | Krakowski Okap / {"cave_id":"C-0065","object_id":"KSW-0018"} | {"WERYF":{"before":0,"after":null}} | [] |
| A232 | 6ec33aec-4b9e-4e47-82fa-3c49a2d401ee | Schron z Kołem / {"cave_id":"C-0729","object_id":"KSZ-0085"} | {"WERYF":{"before":0,"after":null}} | [] |
| A233 | 6f686c88-d161-433b-b965-9575e18e0de8 | Jaskinia Lodowa Małołącka / {"cave_id":"C-0588","object_id":"MLW-0024"} | {} | [{"catalog_current":null,"field":"cave.system_name","source_after":"SYSTEM Dziurawe","source_before":"SYSTEM Dziurawe","source_field":"SYSTEM"}] |
| A234 | 708fd55b-662e-46dc-b8bc-f94c84cefa87 | Dziura za Modrzewiami / {"cave_id":"C-0284","object_id":"KSW-0086"} | {"WERYF":{"before":0,"after":null}} | [] |
| A235 | 709473b2-1483-4a63-862e-7cb0517a3901 | Dziura w Koprowym Żlebie / {"cave_id":"C-0930","object_id":"MLW-0042"} | {"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A236 | 70a167a1-5f4f-4d61-bab5-331259d29f0e | Gruzowa Dziura / {"cave_id":"C-0067","object_id":"KSW-0020"} | {"WERYF":{"before":0,"after":null}} | [] |
| A237 | 70ac2223-b049-4359-afb7-7069d04fe4f1 | Szczelina w Litworowej / {"cave_id":"C-0139","object_id":"MTW-0014"} | {"WERYF":{"before":0,"after":null}} | [] |
| A238 | 70e23a03-450d-43c9-9578-0cd5e598b65c | Dziura w Ździarach / {"cave_id":"C-0605","object_id":"KSW-0175"} | {"WERYF":{"before":0,"after":null}} | [] |
| A239 | 70f662b2-3d79-4bca-9c24-971dd57d8dbf | Jaskinia Lodowa Litworowa / {"cave_id":"C-0273","object_id":"MTW-0023"} | {} | [{"catalog_current":null,"field":"cave.system_name","source_after":"SYSTEM Ptasia Studnia","source_before":"SYSTEM Ptasia Studnia","source_field":"SYSTEM"}] |
| A240 | 71432220-ca17-4420-acc8-394596edf79f | Jaskinia Mroźna / {"cave_id":"C-0267","object_id":"KSW-0256"} | {"DENIWELACJ":{"before":0,"after":null},"DLUGOSC":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [{"catalog_current":"Jaskinia Mroźna - wejście na trasę turystyczną","field":"object.name_local","source_after":"wejście na trasę turystyczną","source_before":"wejście na trasę turystyczną","source_field":"OTWÓR"},{"catalog_current":null,"field":"cave.system_name","source_after":"Mroźna","source_before":"Mroźna","source_field":"SYSTEM"}] |
| A241 | 714e4515-70ee-451d-bdc1-a6783f50d6a3 | Szczelina pod Skośną / {"cave_id":"C-0158","object_id":"LEJ-0006"} | {"WERYF":{"before":0,"after":null}} | [] |
| A242 | 717dba7d-61bc-42ef-8f76-144786fc6700 | Tunel nad Kominem Flacha / {"cave_id":"C-0976","object_id":"MLZ-0103"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null}} | [] |
| A243 | 71e373c5-ceb5-409e-8b36-1ba95c7de17f | Dziura w Wielkiej Turni / {"cave_id":"C-0422","object_id":"KSW-0128"} | {"WERYF":{"before":0,"after":null}} | [] |
| A244 | 7214936d-edaa-436f-919f-4e57b947ea74 | Schron nad Progiem / {"cave_id":"C-0638","object_id":"KSW-0182"} | {"WERYF":{"before":0,"after":null}} | [] |
| A245 | 7231eca3-5040-4984-b295-cee9c9a20249 | Jaskinia pod Bramką / {"cave_id":"C-0825","object_id":"KSZ-0102"} | {"WERYF":{"before":0,"after":null}} | [] |
| A246 | 72c1a44a-0423-4c26-a336-2b5cb36b3fda | Rura nad Okapami / {"cave_id":"C-0875","object_id":"MLZ-0089"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null}} | [] |
| A247 | 7402023a-b0b7-480f-bdd4-14025c05695f | Cubryńska Dziura III / {"cave_id":"C-0122","object_id":"PL-0007"} | {"WERYF":{"before":0,"after":null}} | [] |
| A248 | 74d439c4-a2ff-4d08-b08e-52f3ae057d21 | Komórka nad Smytnią / {"cave_id":"C-0119","object_id":"LEJ-0004"} | {"WERYF":{"before":0,"after":null}} | [] |
| A249 | 74ebcfac-7bbb-4d82-a73f-524887f40151 | Studzienka przy Pomaranczarni / {"cave_id":"C-0884","object_id":"MLW-0036"} | {"DENIWELACJ":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A250 | 757d675f-2dc5-4c94-9629-133647c09738 | Jaskinia za Zaciskiem / {"cave_id":"C-0218","object_id":"MTZ-0020"} | {"WERYF":{"before":0,"after":null}} | [] |
| A251 | 75ca65a1-1e11-4fed-acd8-d90d58807394 | Jaskinia Mechata / {"cave_id":"C-0791","object_id":"LEJ-0025"} | {"WERYF":{"before":0,"after":null}} | [] |
| A252 | 76410591-1aee-45d6-8967-eba6905fcd65 | Jaskinia Trójotworowa / {"cave_id":"C-0424","object_id":"KSW-0129"} | {"WERYF":{"before":0,"after":null}} | [] |
| A253 | 764eec91-d596-4abc-968c-5ccb91c00716 | Schron z Watrą / {"cave_id":"C-0237","object_id":"KSW-0071"} | {"WERYF":{"before":0,"after":null}} | [] |
| A254 | 76ace9b4-c7ad-4b71-98c3-57bfb5d3d6b7 | Spękana Szczelina / {"cave_id":"C-0784","object_id":"KSW-0218"} | {"WERYF":{"before":0,"after":null}} | [] |
| A255 | 76f1665b-2cee-418e-bc2d-dc2cbe253e2a | Jaskinia nad Kotlinami / {"cave_id":"C-0331","object_id":"MLZ-0031"} | {} | [{"catalog_current":null,"field":"cave.system_name","source_after":"Jaskinia Wielka Śnieżna","source_before":"Jaskinia Wielka Śnieżna","source_field":"SYSTEM"}] |
| A256 | 7759c129-816f-4be2-9e60-be844111364e | Szczelina za Okrętem I / {"cave_id":"C-0591","object_id":"KSZ-0065"} | {"WERYF":{"before":0,"after":null}} | [] |
| A257 | 77790c30-a261-4635-adc8-290bcec94175 | Świstowa  Szczelina / {"cave_id":"C-0595","object_id":"MTZ-0043"} | {} | [{"catalog_current":"Świstowa Szczelina","field":"object.name_local","source_after":"Świstowa  Szczelina","source_before":"Świstowa  Szczelina","source_field":"NAZWA"},{"catalog_current":"Świstowa Szczelina","field":"cave.name","source_after":"Świstowa  Szczelina","source_before":"Świstowa  Szczelina","source_field":"NAZWA"}] |
| A258 | 77c43de2-6b32-42cd-ab72-bdbe4d57dd49 | Meander nad Kominem Flacha / {"cave_id":"C-0994","object_id":"MLZ-0106"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A259 | 78811f4c-ad7f-4979-998e-9e6f998f446c | Schron przy Smoczej Jamie / {"cave_id":"C-0821","object_id":"KSW-0223"} | {"WERYF":{"before":0,"after":null}} | [] |
| A260 | 788286a6-e1ad-4823-94e1-d398e379c89e | Korytarzyk w Żlebie Niedźwiedź / {"cave_id":"C-0195","object_id":"KSW-0056"} | {"WERYF":{"before":0,"after":null}} | [] |
| A261 | 78c698f2-4463-459c-ac37-e442a4b2604b | Jaskinia nad Smytnią / {"cave_id":"C-0788","object_id":"KSZ-0095"} | {"WERYF":{"before":0,"after":null}} | [] |
| A262 | 78d37af0-178c-446d-963e-95094f9eb1e1 | Jaskinia w Smreczyńskim Wierchu / {"cave_id":"C-0152","object_id":"PL-0011"} | {"WERYF":{"before":0,"after":null}} | [] |
| A263 | 7954af44-5e53-42d8-a3ec-2c817d4a5421 | Jaskinia nad Korytem / {"cave_id":"C-0713","object_id":"MLZ-0072"} | {} | [{"catalog_current":"Jaskinia nad Korytem - otwór północno-zachodni","field":"object.name_local","source_after":"NW","source_before":"NW","source_field":"OTWÓR"},{"catalog_current":null,"field":"cave.system_name","source_after":"Jaskinia nad Korytem","source_before":"Jaskinia nad Korytem","source_field":"SYSTEM"}] |
| A264 | 79d0b793-3f93-4fa0-93b4-e825c73ea1e7 | Schron przy Troistej I / {"cave_id":"C-0512","object_id":"CHW-0024"} | {"WERYF":{"before":0,"after":null}} | [] |
| A265 | 7a00ab50-fc9a-4c01-b7cc-5315ac461deb | Szczelina nad Zimną / {"cave_id":"C-0538","object_id":"KSW-0160"} | {"WERYF":{"before":0,"after":null}} | [] |
| A266 | 7a279a7b-800c-49ae-866a-10692fced29b | Dziura nad Nową Roztoką / {"cave_id":"C-0113","object_id":"PL-0006"} | {"WERYF":{"before":0,"after":null}} | [] |
| A267 | 7ad1abf3-d20d-4b73-b097-54f9a33061d7 | Tomanowy Okap / {"cave_id":"C-0688","object_id":"KSW-0197"} | {"WERYF":{"before":0,"after":null}} | [] |
| A268 | 7b2dfd58-b72f-49f9-9801-6159b9c9fe78 | Schron w Ścianie pod Szczytem / {"cave_id":"C-0515","object_id":"CHW-0025"} | {"WERYF":{"before":0,"after":null}} | [] |
| A269 | 7c6d7db0-b9e7-49d3-bb9b-419f9308ce82 | Schron pod Twardymi Spadami / {"cave_id":"C-0782","object_id":"MTZ-0060"} | {"WERYF":{"before":0,"after":null}} | [] |
| A270 | 7d4c5169-e788-4a65-9ecc-47531e12896b | Dziura w Zawiesistej / {"cave_id":"C-0014","object_id":"CHZ-0001"} | {"WERYF":{"before":0,"after":null}} | [] |
| A271 | 7dd54883-cd0b-4435-ac99-bd56a2f25fd5 | Jaskinia nad Arkadą / {"cave_id":"C-0178","object_id":"KSW-0050"} | {"WERYF":{"before":0,"after":null}} | [] |
| A272 | 7ddc257f-1586-457a-af54-46cdffb7ad7b | Jaskinia nad Prożkiem w Żlebie Na Spady / {"cave_id":"C-0132","object_id":"KSZ-0013"} | {"WERYF":{"before":0,"after":null}} | [] |
| A273 | 7e200520-8625-46cb-b5f0-27b8c0526fc8 | Jaskinia Dwuotworowa w Iwanówce / {"cave_id":"C-0796","object_id":"CHW-0040"} | {"WERYF":{"before":0,"after":null}} | [] |
| A274 | 7e79ee82-fad4-436c-9303-3e7fc76702ec | Zamczysko Wyżnie / {"cave_id":"C-0100","object_id":"KSW-0031"} | {"WERYF":{"before":0,"after":null}} | [] |
| A275 | 7e9c3d95-a09f-4d78-9629-c331f80c637f | Zielone Kominy / {"cave_id":"C-0401","object_id":"MTZ-0030"} | {"WERYF":{"before":0,"after":null}} | [] |
| A276 | 7fd8bab1-a46d-4aba-8dec-683933f2cafd | Sztolnia w Bramie Kantaka nr 1 / {"cave_id":"C-0967","object_id":"KSW-0251"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null},"WERYF":{"before":0,"after":null}} | [] |
| A277 | 8047be78-eec7-4f4b-b6f2-f9cf6781d3b1 | Jaworowa Szczelina / {"cave_id":"C-0425","object_id":"KSZ-0048"} | {"WERYF":{"before":0,"after":null}} | [] |
| A278 | 80df3da7-6e2f-4739-93cd-b86d5e600c5e | Lejek / {"cave_id":"C-0278","object_id":"KSW-0084"} | {"WERYF":{"before":0,"after":null}} | [] |
| A279 | 814f5451-68f8-4db0-a52f-d7469d588938 | Dziurawa Koleba / {"cave_id":"C-0436","object_id":"KSW-0134"} | {"WERYF":{"before":0,"after":null}} | [] |
| A280 | 81958d61-ecff-4a25-a80d-bc8cea1fc7df | Komora Gwiaździsta / {"cave_id":"C-0279","object_id":"MLZ-0028"} | {} | [{"catalog_current":"Komora Gwiaździsta","field":"object.name_local","source_after":"dolny","source_before":"dolny","source_field":"OTWÓR"}] |
| A281 | 82607f42-7b33-4cd6-a3fd-cd95e53d28d1 | Jaskinia Skośna / {"cave_id":"C-0692","object_id":"KSZ-0079"} | {"WERYF":{"before":0,"after":null}} | [] |
| A282 | 828e69b9-913c-4fec-bb29-a74214b52584 | Bardzo Niska Nyża / {"cave_id":"C-0069","object_id":"KSW-0021"} | {"WERYF":{"before":0,"after":null}} | [] |
| A283 | 8362ec78-4722-4729-a488-e1f8d32b741f | Jaskinia Gankowa / {"cave_id":"C-0428","object_id":"KSW-0131"} | {"WERYF":{"before":0,"after":null}} | [] |
| A284 | 8393a2d7-0bde-48e7-ae6e-089c8051b123 | Sztolnia w Dolinie Białego nr 3 / {"cave_id":"C-0960","object_id":"BIA-0007"} | {"WERYF":{"before":0,"after":null}} | [] |
| A285 | 840f8dd0-1013-4e80-9156-14863d013448 | Kalacka Nyża V / {"cave_id":"C-0882","object_id":"BYZ-0045"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A286 | 842a4d5f-b21f-4b09-b55c-e871eb54c356 | Jaskinia Mała pod Zamkiem / {"cave_id":"C-0298","object_id":"KSW-0091"} | {"WERYF":{"before":0,"after":null}} | [] |
| A287 | 84c4ba72-e422-48df-9815-6925b25376f3 | Jaskinia nad Dachem / {"cave_id":"C-0072","object_id":"MTW-0004"} | {} | [{"catalog_current":null,"field":"cave.system_name","source_after":"SYSTEM Ptasia Studnia","source_before":"SYSTEM Ptasia Studnia","source_field":"SYSTEM"}] |
| A288 | 859b300c-5f75-4bf0-8bcd-3465a16e5cd2 | Jaskinia Przeziorowa / {"cave_id":"C-0233","object_id":"KSW-0069"} | {"WERYF":{"before":0,"after":null}} | [] |
| A289 | 85c47996-efd6-465e-b51c-078860771ab7 | Zbójnicki Korytarzyk / {"cave_id":"C-0253","object_id":"KSW-0077"} | {"WERYF":{"before":0,"after":null}} | [] |
| A290 | 85de85a0-28dd-4f4f-9240-c1c497a96c0a | Nyża nad Prożkiem w Żlebie Na Spady / {"cave_id":"C-0202","object_id":"KSZ-0022"} | {"WERYF":{"before":0,"after":null}} | [] |
| A291 | 868aeffa-e2bd-400d-a8ba-df71a36172b4 | Szczelina w Niżniej Świstówce IV / {"cave_id":"C-0982","object_id":"MLW-0051"} | {"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A292 | 86e6e8c9-8495-4e9b-8e89-bc4bc2adec06 | Rura nad Okapami / {"cave_id":"C-0875","object_id":"MLZ-0089"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null}} | [] |
| A293 | 8700627c-cf7f-4ad8-8365-131fd3edc9be | Żeleźniakowa Brama / {"cave_id":"C-0838","object_id":"KSZ-0104"} | {"WERYF":{"before":0,"after":null}} | [] |
| A294 | 8708d7b1-a223-4e0b-947b-9f192ac8b3df | Tunel w Żlebie z Bramką / {"cave_id":"C-0785","object_id":"KSZ-0093"} | {"WERYF":{"before":0,"after":null}} | [] |
| A295 | 877b6e2d-0703-4f91-9343-a4ff4e9b2eeb | Dziura nad Głazem / {"cave_id":"C-0206","object_id":"KSW-0061"} | {"WERYF":{"before":0,"after":null}} | [] |
| A296 | 88801933-d166-488a-a718-584a7c9dc4c3 | Sztolnia na Klinowej Czubie nr 2 / {"cave_id":"C-0916","object_id":"CHW-0045"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null},"WERYF":{"before":0,"after":null}} | [] |
| A297 | 88b66b58-5cf2-4c92-b94f-41b67780a3f1 | Okap przed Bramą / {"cave_id":"C-0200","object_id":"CHW-0011"} | {"WERYF":{"before":0,"after":null}} | [] |
| A298 | 89115f60-c282-4c40-938a-229569ce132e | Schronisko nad Wiśniakową Jamą / {"cave_id":"C-0358","object_id":"KSZ-0043"} | {"WERYF":{"before":0,"after":null}} | [] |
| A299 | 8957dfc3-dd21-4e3c-94e6-374d9bcb1d9b | Schron w Upłazkowej Turni / {"cave_id":"C-0075","object_id":"KSW-0024"} | {"WERYF":{"before":0,"after":null}} | [] |
| A300 | 89707f71-adeb-45fd-bcc7-e742ba6867ff | Szczelina przy Tomanowym Okapie / {"cave_id":"C-0211","object_id":"KSW-0062"} | {"WERYF":{"before":0,"after":null}} | [] |
| A301 | 89a4ebbd-f7ff-4e0d-a814-f643e09c7d1f | Schron nad Mechami / {"cave_id":"C-0956","object_id":"KSW-0249"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A302 | 89fc0421-8243-453b-b724-dac2c28e9bf8 | Szczelina w Niżniej Świstówce III / {"cave_id":"C-1002","object_id":"MLW-0053"} | {"DENIWELACJ":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A303 | 8ad7a1a1-9eb3-4d42-bde3-d747332d0362 | Wąska Szczelina / {"cave_id":"C-0040","object_id":"KSW-0010"} | {"WERYF":{"before":0,"after":null}} | [] |
| A304 | 8ba5cccc-853a-4869-a9b6-0b3683ce65d1 | Szczelina w Smytniej / {"cave_id":"C-0186","object_id":"KSZ-0020"} | {"WERYF":{"before":0,"after":null}} | [] |
| A305 | 8cbfacd0-cff5-482c-a4ca-fbd837cc2ede | Jaskinia Krwawego Nosa / {"cave_id":"C-0471","object_id":"KSW-0144"} | {"WERYF":{"before":0,"after":null}} | [] |
| A306 | 8cc17f24-30c0-4247-8d59-5a4dbcb45eff | Schron pod Siodłową Turnią II / {"cave_id":"C-0924","object_id":"MLW-0040"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A307 | 8cd9cafe-ed57-456a-95da-79be5518d09a | Szczelina pod Smoczą Jamą / {"cave_id":"C-0790","object_id":"KSW-0219"} | {"WERYF":{"before":0,"after":null}} | [] |
| A308 | 8db4e0c9-74c4-4400-abab-bc433d108d36 | Nyża w Pośredniej Turni / {"cave_id":"C-0938","object_id":"MLZ-0099"} | {"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A309 | 8e0f8ad4-90c0-4c1a-afb2-4df81b3985f5 | Kopalnia Maturka / {"cave_id":"C-0603","object_id":"KSZ-0066"} | {"WERYF":{"before":0,"after":null}} | [] |
| A310 | 8ea8c6ef-b11f-40e9-8d87-239bebb14cce | Koleba w Zawracie Kasprowym / {"cave_id":"C-0977","object_id":"BYW-0043"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A311 | 8ff59a68-a36f-45f1-a1cd-0886cfcfa15c | Jaskinia Zawaliskowa w Stołach / {"cave_id":"C-0379","object_id":"KSZ-0044"} | {"WERYF":{"before":0,"after":null}} | [] |
| A312 | 905f9e2d-21d6-470f-9791-370e524c0953 | Sztolnia w Żlebie Banie / {"cave_id":"C-0926","object_id":"STR-0026"} | {"DENIWELACJ":{"before":0,"after":null},"DLUGOSC":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null},"WERYF":{"before":0,"after":null}} | [] |
| A313 | 90721570-515b-4eb9-a3f6-d01b25187407 | Wiśniakowa Jama / {"cave_id":"C-0479","object_id":"KSZ-0053"} | {"WERYF":{"before":0,"after":null}} | [] |
| A314 | 90938460-dadb-4d19-82ab-558b3a45ff85 | Lisia Jama / {"cave_id":"C-0477","object_id":"DZI-0002"} | {} | [{"catalog_current":null,"field":"cave.system_name","source_after":"SYSTEM Dziura Wyżnia","source_before":"SYSTEM Dziura Wyżnia","source_field":"SYSTEM"}] |
| A315 | 91874b53-afad-461f-b29c-7c2f0786f69b | Szczelina nad Tomanową II / {"cave_id":"C-0275","object_id":"KSW-0083"} | {"WERYF":{"before":0,"after":null}} | [] |
| A316 | 9202c685-6aa8-4e4b-95d6-ed9d24166bc3 | Kominek przy Bańdziochu / {"cave_id":"C-0391","object_id":"KSZ-0046"} | {"WERYF":{"before":0,"after":null}} | [] |
| A317 | 92311241-9eff-4428-ac24-fbe8be1e3564 | Arkada / {"cave_id":"C-0381","object_id":"KSW-0115"} | {"WERYF":{"before":0,"after":null}} | [] |
| A318 | 928043cc-4a91-42cf-8fcd-1bbbd1671b28 | Gawra w Zawieszce / {"cave_id":"C-0905","object_id":"DZI-0008"} | {"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A319 | 92d7f63f-b33b-4530-9dda-033a350887c0 | Komora w Kondratowych Basztach / {"cave_id":"C-0944","object_id":"BYZ-0052"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null}} | [] |
| A320 | 92e40144-6efd-4d36-b306-4d32b4e56d59 | Wyżnia Szczelina w Zadnim Kościelcu / {"cave_id":"C-0731","object_id":"SUW-0006"} | {"WERYF":{"before":0,"after":null}} | [] |
| A321 | 952af1cf-f646-4036-bbe0-b8301fcf727e | Trójkątny Schron / {"cave_id":"C-0670","object_id":"KSW-0190"} | {"WERYF":{"before":0,"after":null}} | [] |
| A322 | 95763b5b-269a-4a91-b8bb-0417988e978d | Jaskinia między Żleby / {"cave_id":"C-0435","object_id":"KSW-0133"} | {"WERYF":{"before":0,"after":null}} | [] |
| A323 | 95a15507-01c4-41cb-82da-858b44498fe4 | Dziura pod Zawaliskiem / {"cave_id":"C-0335","object_id":"KSW-0103"} | {"WERYF":{"before":0,"after":null}} | [] |
| A324 | 9633be48-b494-4d12-a92d-7a0900ca7d46 | Jaskinia za Siedmiu Progami / {"cave_id":"C-0412","object_id":"KSW-0123"} | {} | [{"catalog_current":null,"field":"cave.system_name","source_after":"SYSTEM Wysoka","source_before":"SYSTEM Wysoka","source_field":"SYSTEM"}] |
| A325 | 964db8e1-2be8-4126-a9d2-2da687c5cd0d | Ptasia Studnia dolny otwór / {"cave_id":"C-0997","object_id":"MTZ-0066"} | {"PRZEWYZSZE":{"before":0,"after":null}} | [{"catalog_current":null,"field":"cave.system_name","source_after":"SYSTEM Ptasia Studnia","source_before":"SYSTEM Ptasia Studnia","source_field":"SYSTEM"}] |
| A326 | 9685afdf-358b-42f1-8d65-9ba9310f4bc3 | Dziura nad Roztoką / {"cave_id":"C-0235","object_id":"PL-0013"} | {"WERYF":{"before":0,"after":null}} | [] |
| A327 | 96b9a3dd-2f35-400c-a96c-a5b21625ec24 | Kalacki Schron / {"cave_id":"C-0971","object_id":"BYZ-0056"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A328 | 98377d8a-8e3d-41e9-bd6d-da78e5e56745 | Gawra nad Wielką Równią / {"cave_id":"C-0906","object_id":"STR-0025"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null}} | [] |
| A329 | 986ecd98-049a-4271-9529-3bbd02230f1a | Tunel Wiatru / {"cave_id":"C-0270","object_id":"KSZ-0027"} | {"WERYF":{"before":0,"after":null}} | [] |
| A330 | 9884c999-570e-4e21-ab87-ae51e18cd9dc | Szczelina nad Mostkiem / {"cave_id":"C-0336","object_id":"KSZ-0041"} | {"WERYF":{"before":0,"after":null}} | [] |
| A331 | 99522c8a-640c-427c-9e08-21276a83b81e | Sztolnia na Klinowej Czubie nr 6 / {"cave_id":"C-0945","object_id":"CHW-0049"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null},"WERYF":{"before":0,"after":null}} | [] |
| A332 | 998c78c8-fe66-4ff5-a708-b7fceb35e0c8 | Szczelina pod Gankową I / {"cave_id":"C-0589","object_id":"KSW-0172"} | {"WERYF":{"before":0,"after":null}} | [] |
| A333 | 999266f2-d9fd-4e23-95c7-b33df9249882 | Schron przed Sową III / {"cave_id":"C-0125","object_id":"KSZ-0012"} | {"WERYF":{"before":0,"after":null}} | [] |
| A334 | 99c85ec0-9839-4442-8826-fd8732494723 | Nisza nad Żółtą Dziurą / {"cave_id":"C-0290","object_id":"KSW-0087"} | {"WERYF":{"before":0,"after":null}} | [] |
| A335 | 9a3dc135-ec51-475f-bbbd-15bdd3072f68 | Szczelina w Niżniej Świstówce II / {"cave_id":"C-0912","object_id":"MLW-0039"} | {"DENIWELACJ":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A336 | 9b08a3b1-416c-4516-8795-a87062191fd2 | Litworowa Studnia / {"cave_id":"C-0747","object_id":"MTW-0058"} | {"WERYF":{"before":0,"after":null}} | [] |
| A337 | 9b566416-3888-4900-b351-cf81fc2a387e | tunel w Skrajnej Giewonckiej Baszcie / {"cave_id":"C-0981","object_id":"MLW-0050"} | {"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [{"catalog_current":"tunel w Skrajnej Giewonckiej Baszcie - otwór S","field":"object.name_local","source_after":"S","source_before":"S","source_field":"OTWÓR"}] |
| A338 | 9c221920-8db8-42b8-9363-ff0d31eb6cbf | Szczelina Salicylowa / {"cave_id":"C-0886","object_id":"KSW-0242"} | {"DENIWELACJ":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A339 | 9d075cdd-fe40-48cb-baa5-f122fa171b14 | Szczelina przy Gładkim Żlebie / {"cave_id":"C-0276","object_id":"KSZ-0029"} | {"WERYF":{"before":0,"after":null}} | [] |
| A340 | 9de94a65-abfe-4fc6-bd5c-01dbb2f73308 | Tomanowa Szczelina II / {"cave_id":"C-0684","object_id":"KSW-0196"} | {"WERYF":{"before":0,"after":null}} | [] |
| A341 | 9e2ff59a-b458-4586-9af2-ebb54d5a38ba | Jaskinia Pajęcza / {"cave_id":"C-0231","object_id":"KSW-0068"} | {"WERYF":{"before":0,"after":null}} | [] |
| A342 | 9e5af934-eb7d-452d-b8ef-ffc609fceed2 | Schron w Organach / {"cave_id":"C-0724","object_id":"KSW-0206"} | {"WERYF":{"before":0,"after":null}} | [] |
| A343 | 9f5dfa29-ea7f-47b0-bbe0-6ae2d6a092b6 | Sowia Jama I / {"cave_id":"C-0294","object_id":"KSZ-0033"} | {"WERYF":{"before":0,"after":null}} | [] |
| A344 | 9f98e21a-0e26-4fec-a0a1-60f22c48fb42 | Sztolnia w Dolinie Białego nr 2 / {"cave_id":"C-0923","object_id":"BIA-0006"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null},"WERYF":{"before":0,"after":null}} | [] |
| A345 | 9fbcb569-4dd2-4aec-9545-dab3c03fcfe0 | Dziura pod Arkadą / {"cave_id":"C-0086","object_id":"KSW-0028"} | {"WERYF":{"before":0,"after":null}} | [] |
| A346 | 9fce27e5-17a3-432c-b0d7-79ac70fc2b89 | Schron nad Żlebem / {"cave_id":"C-0339","object_id":"KSZ-0042"} | {"WERYF":{"before":0,"after":null}} | [] |
| A347 | 9ff24bb9-330c-4043-8bee-46841b9a2dd6 | Zamulona Dziura / {"cave_id":"C-0421","object_id":"KSW-0127"} | {"WERYF":{"before":0,"after":null}} | [] |
| A348 | a00678a9-e909-4776-b57b-fe446d4fd3e0 | Jaskinia Kokonowa / {"cave_id":"C-0292","object_id":"CHZ-0009"} | {"WERYF":{"before":0,"after":null}} | [] |
| A349 | a13307dc-2052-437f-9665-620dd27ac861 | Jaskinia przy Grzędzie / {"cave_id":"C-0764","object_id":"MTZ-0058"} | {"WERYF":{"before":0,"after":null}} | [] |
| A350 | a3228025-863c-4833-9da9-2ac6337e1f66 | Schron w Zawracie Kasprowym / {"cave_id":"C-0877","object_id":"BYW-0038"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null}} | [] |
| A351 | a3403b9c-5a95-435e-b2d1-ee1cde1107b4 | Szczelina w Tomanowym Grzbiecie V / {"cave_id":"C-0572","object_id":"KSW-0168"} | {"WERYF":{"before":0,"after":null}} | [] |
| A352 | a34cad7d-c9f0-4951-b83c-23248b05b900 | Jaskinia Wielka Litworowa / {"cave_id":"C-0120","object_id":"MTW-0010"} | {} | [{"catalog_current":null,"field":"cave.system_name","source_after":"Jaskinia Wielka Śnieżna","source_before":"Jaskinia Wielka Śnieżna","source_field":"SYSTEM"}] |
| A353 | a353e919-b059-433c-8f20-9cd30ea994db | Nyża z Dzięglem / {"cave_id":"C-0366","object_id":"KSW-0111"} | {"WERYF":{"before":0,"after":null}} | [] |
| A354 | a5ac9b07-f788-4069-8d07-d7d775b1bf2c | Awen Odpękniętych Nacieków / {"cave_id":"C-0727","object_id":"LEJ-0023"} | {"WERYF":{"before":0,"after":null}} | [] |
| A355 | a5c7088e-a2fe-4898-ae2e-b0a9b420b17d | BEZ_NAZWY_001 / {"cave_id":"C-0903","object_id":"STR-0024"} | {"DENIWELACJ":{"before":0,"after":null},"DLUGOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null},"WERYF":{"before":0,"after":null}} | [{"catalog_current":"BEZ_NAZWY_001","field":"object.name_local","source_after":null,"source_before":null,"source_field":"NAZWA"},{"catalog_current":"BEZ_NAZWY_001","field":"cave.name","source_after":null,"source_before":null,"source_field":"NAZWA"}] |
| A356 | a5f01b51-0d1c-41da-8216-91fd41235ff7 | Sztolnia w Małym Reglu nr 1 / {"cave_id":"C-0936","object_id":"KSW-0246"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null},"WERYF":{"before":0,"after":null}} | [] |
| A357 | a607dca7-51ae-4907-b011-95ba6f6694d1 | Krakowski Schron / {"cave_id":"C-0142","object_id":"KSW-0041"} | {"WERYF":{"before":0,"after":null}} | [] |
| A358 | a675e53d-a2dc-46c9-98dd-96e7b8c8ee0a | Tylkowa Szczelina / {"cave_id":"C-0511","object_id":"LEJ-0016"} | {"WERYF":{"before":0,"after":null}} | [] |
| A359 | a6d3cbf7-d5dc-4d30-abea-215346b8a88c | Dziura w Organach IV / {"cave_id":"C-0826","object_id":"KSW-0225"} | {"WERYF":{"before":0,"after":null}} | [] |
| A360 | a6e27103-8d20-4ba4-bee8-3080f1de9cec | Korytarzyk pod Zamkiem / {"cave_id":"C-0474","object_id":"KSW-0145"} | {"WERYF":{"before":0,"after":null}} | [] |
| A361 | a6e61383-a092-42ae-9db1-a94025a44f16 | Szczelina w Ciemniaku / {"cave_id":"C-0176","object_id":"KSW-0049"} | {"WERYF":{"before":0,"after":null}} | [] |
| A362 | a6e61569-1de4-439e-826c-9e021e7003e1 | Dwuotworowa Szczelina / {"cave_id":"C-0261","object_id":"KSW-0079"} | {"WERYF":{"before":0,"after":null}} | [] |
| A363 | a7462111-5667-464e-ac98-6191f66412c5 | Jaskinia w Szerokiem / {"cave_id":"C-0728","object_id":"MTZ-0055"} | {"WERYF":{"before":0,"after":null}} | [] |
| A364 | a76ba967-9dd7-41ec-bb8b-6a96fd923a01 | Jaskinia w Małej Świstówce / {"cave_id":"C-0037","object_id":"MTZ-0004"} | {"WERYF":{"before":0,"after":null}} | [] |
| A365 | a7fdefb6-483a-4622-8243-c0f2ad7295c2 | Jasny Aven / {"cave_id":"C-0858","object_id":"MLZ-0085"} | {} | [{"catalog_current":"Jasny Awen","field":"object.name_local","source_after":"Jasny Aven","source_before":"Jasny Aven","source_field":"NAZWA"},{"catalog_current":"Jasny Awen","field":"cave.name","source_after":"Jasny Aven","source_before":"Jasny Aven","source_field":"NAZWA"},{"catalog_current":null,"field":"cave.system_name","source_after":"Jaskinia Wielka Śnieżna","source_before":"Jaskinia Wielka Śnieżna","source_field":"SYSTEM"}] |
| A366 | a8872736-80b6-4d68-bd07-7fe4f614cba5 | Szczelina nad Żlebem / {"cave_id":"C-0622","object_id":"KSZ-0069"} | {"WERYF":{"before":0,"after":null}} | [] |
| A367 | a8920edc-9f80-4b86-aa53-b0628cd02173 | Myslenicka Rura / {"cave_id":"C-0887","object_id":"BYZ-0046"} | {"DENIWELACJ":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A368 | a8fed4cd-2e6c-44e9-b7e7-37b6a0acb20a | Ptasi Schron / {"cave_id":"C-0801","object_id":"KSW-0220"} | {"WERYF":{"before":0,"after":null}} | [] |
| A369 | a9150d50-afb4-45bc-96aa-f74e1dddd2eb | Schron pod Kufą Zachodni / {"cave_id":"C-0712","object_id":"CHW-0035"} | {"WERYF":{"before":0,"after":null}} | [] |
| A370 | a92ff1d1-6b71-4a2f-995d-9f7f56003701 | Dziura pod Kotlinami / {"cave_id":"C-0861","object_id":"MLZ-0086"} | {"DENIWELACJ":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A371 | a976a565-9356-4c2d-9485-31f8f167e5d2 | Druga Krakowska Szczelina / {"cave_id":"C-0258","object_id":"KSW-0078"} | {"WERYF":{"before":0,"after":null}} | [] |
| A372 | a9827578-e5a0-4eb7-8e15-865dbece0b63 | Otwarty Schron / {"cave_id":"C-0296","object_id":"KSZ-0034"} | {"WERYF":{"before":0,"after":null}} | [] |
| A373 | a9bd9455-6c88-479a-a94c-acc54c9618f3 | Schron w Dolinie Litworowej / {"cave_id":"C-0101","object_id":"MTW-0007"} | {"WERYF":{"before":0,"after":null}} | [] |
| A374 | a9e23154-c63f-4925-a768-ba1c38776dab | Koliba w Smytniej / {"cave_id":"C-0208","object_id":"KSZ-0023"} | {"WERYF":{"before":0,"after":null}} | [] |
| A375 | aa0661a8-8994-4c95-b7e3-780eea9a3642 | Schron pod Jaskinią Goryckiego / {"cave_id":"C-0189","object_id":"KSW-0053"} | {"WERYF":{"before":0,"after":null}} | [] |
| A376 | ab3f50a0-8655-4b60-bf12-6e2c6211cdb5 | Radkowa Dziura I / {"cave_id":"C-0299","object_id":"KSW-0092"} | {"WERYF":{"before":0,"after":null}} | [] |
| A377 | acaf21e8-6600-4c10-8be9-09f9502ae7bd | Jaskinia Lejowa Wyżnia / {"cave_id":"C-0556","object_id":"LEJ-0017"} | {"WERYF":{"before":0,"after":null}} | [] |
| A378 | ae6a3054-552c-4bae-922e-e80f60cacbd4 | Jaskinia pod Kapliczką / {"cave_id":"C-0786","object_id":"KSZ-0094"} | {"WERYF":{"before":0,"after":null}} | [] |
| A379 | ae72e4c2-de63-4a82-bbde-eb4737e7c96e | Dziura w Miedzianym Kosturze II / {"cave_id":"C-0473","object_id":"PL-0026"} | {"WERYF":{"before":0,"after":null}} | [] |
| A380 | af10a02b-d9b1-4697-950c-c58015b51296 | Okap z Kotem / {"cave_id":"C-0870","object_id":"KSW-0238"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null},"WERYF":{"before":0,"after":null}} | [] |
| A381 | af3f0fd7-6a99-45b7-bebc-aa898e6642f0 | Szczelina przy Lodowej nad Kufą / {"cave_id":"C-0064","object_id":"LEJ-0001"} | {"WERYF":{"before":0,"after":null}} | [] |
| A382 | afb3118f-4982-4271-ab7e-544ccd7f4854 | Sztolnia w Przedniej Kopce nr 2 / {"cave_id":"C-0952","object_id":"KSZ-0111"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null},"WERYF":{"before":0,"after":null}} | [] |
| A383 | afc28da7-f21d-4303-8707-c5412dd4c64e | Gawra nad Pisaną / {"cave_id":"C-0868","object_id":"KSW-0237"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A384 | b029af6c-1ffc-4c64-9968-624eb5fd0ee8 | Jaskinia nad Percią / {"cave_id":"C-0383","object_id":"KSW-0116"} | {"WERYF":{"before":0,"after":null}} | [] |
| A385 | b0ffb97c-46f3-4f8d-8369-007c846bd050 | Zamczysko Niżnie / {"cave_id":"C-0743","object_id":"KSW-0209"} | {"WERYF":{"before":0,"after":null}} | [] |
| A386 | b105878a-d99e-4dea-b2dc-b8676f23f260 | Zbójnicka Szczelina / {"cave_id":"C-0318","object_id":"KSW-0100"} | {"WERYF":{"before":0,"after":null}} | [] |
| A387 | b143e13b-7fae-4e0f-a6da-0c2be556d604 | Ukryty Schron / {"cave_id":"C-0006","object_id":"KSW-0003"} | {"WERYF":{"before":0,"after":null}} | [] |
| A388 | b1f9faac-54c4-4e08-a474-cb2cead0f2a9 | Dudzia Dziura / {"cave_id":"C-0505","object_id":"KSW-0155"} | {"WERYF":{"before":0,"after":null}} | [] |
| A389 | b25bfb8d-e88f-4f14-9fda-d68eca2c621c | Świstowy Worek / {"cave_id":"C-0539","object_id":"MTZ-0041"} | {"WERYF":{"before":0,"after":null}} | [] |
| A390 | b3202807-f363-428a-b8f0-0e22a2fa66da | Jaskinia nad Wielką Równią / {"cave_id":"C-0986","object_id":"STR-0029"} | {"DENIWELACJ":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A391 | b33edd51-a246-4a3a-a8fa-8ce95eec525d | Korytarzyk w Szczelinie / {"cave_id":"C-0675","object_id":"KSW-0191"} | {"WERYF":{"before":0,"after":null}} | [] |
| A392 | b44a0859-1b37-4e14-ac6f-96782b89cb48 | Szczelina w Zadnim Kościelcu / {"cave_id":"C-0823","object_id":"SUW-0007"} | {"WERYF":{"before":0,"after":null}} | [] |
| A393 | b4f296bb-be0d-4795-aa39-094016ce4391 | Nyża w Smytniej / {"cave_id":"C-0709","object_id":"KSZ-0083"} | {"WERYF":{"before":0,"after":null}} | [] |
| A394 | b5ac9e3a-a89e-443f-b640-d28804a74046 | Sztolnia w Bramie Kantaka nr 2 / {"cave_id":"C-0942","object_id":"KSZ-0110"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null},"WERYF":{"before":0,"after":null}} | [] |
| A395 | b5ca4c9c-9bad-4dd7-a4f0-e321680cc2ec | Zagonna Studnia / {"cave_id":"C-0553","object_id":"MLZ-0055"} | {} | [{"catalog_current":null,"field":"cave.system_name","source_after":"SYSTEM Zośka","source_before":"SYSTEM Zośka","source_field":"SYSTEM"}] |
| A396 | b690f81b-8294-4b2c-80ca-db1e050499dc | Cubryńska Dziura I / {"cave_id":"C-0768","object_id":"PL-0043"} | {"WERYF":{"before":0,"after":null}} | [] |
| A397 | b6dbf7a1-8dee-4bae-bb45-d1c9470bba1d | Jaskinia w Kociołku pod Bańdziochem / {"cave_id":"C-0819","object_id":"KSZ-0101"} | {"WERYF":{"before":0,"after":null}} | [] |
| A398 | b6f7153b-1d72-4f3e-9b70-bebbf10e52cf | Schronisko przy Jeleniej Perci / {"cave_id":"C-0735","object_id":"KSZ-0087"} | {"WERYF":{"before":0,"after":null}} | [] |
| A399 | b72f5756-4820-4964-b98f-9abed6af0afc | Dudowy Okap / {"cave_id":"C-0031","object_id":"CHW-0004"} | {"WERYF":{"before":0,"after":null}} | [] |
| A400 | b73c1283-b3f4-4ea7-86de-f322b3f26c9e | Dziura Wyżnia / {"cave_id":"C-0775","object_id":"DZI-0005"} | {} | [{"catalog_current":null,"field":"cave.system_name","source_after":"SYSTEM Dziura Wyżnia","source_before":"SYSTEM Dziura Wyżnia","source_field":"SYSTEM"}] |
| A401 | b75566f2-6ca0-43c0-b9b2-a1af60965503 | Jaskinia nad Mostkiem Niżnia / {"cave_id":"C-0707","object_id":"KSZ-0082"} | {"WERYF":{"before":0,"after":null}} | [] |
| A402 | b79197f0-c5a7-4141-b05a-9e2aee44faa3 | Szczelina na Zakręcie I / {"cave_id":"C-0429","object_id":"KSW-0132"} | {"WERYF":{"before":0,"after":null}} | [] |
| A403 | b79a1681-7436-4251-b24b-a9abba32dffe | Szczelina w Wielkiej Turni / {"cave_id":"C-0937","object_id":"MLZ-0098"} | {"DENIWELACJ":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A404 | b847e094-6d0a-49d5-b2f0-9729d028c662 | Studzienka przy Pomarańczarni / {"cave_id":"C-0928","object_id":"MLW-0041"} | {"WERYF":{"before":0,"after":null}} | [] |
| A405 | b8bc1edd-8a32-4819-974b-7b55ca77221a | Schron w Małym szerokiem II / {"cave_id":"C-0999","object_id":"BYZ-0060"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A406 | b8c9f363-3509-48db-9abc-90e665ef74c3 | Smocza Jama / {"cave_id":"C-0219","object_id":"KSW-0065"} | {} | [{"catalog_current":"Smocza Jama","field":"object.name_local","source_after":"S","source_before":"S","source_field":"OTWÓR"}] |
| A407 | b918424f-9161-4841-8bc8-0051445a4d29 | Jaskinia Czarna / {"cave_id":"C-0699","object_id":"KSW-0240"} | {"DENIWELACJ":{"before":0,"after":null},"DLUGOSC":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [{"catalog_current":"Jaskinia Czarna III","field":"object.name_local","source_after":"N","source_before":"N","source_field":"OTWÓR"},{"catalog_current":null,"field":"cave.system_name","source_after":"Czarna","source_before":"Czarna","source_field":"SYSTEM"}] |
| A408 | b97d332c-9bd6-4d9f-9d91-1b352cc48f65 | Szczelina nad Tomanową I / {"cave_id":"C-0802","object_id":"KSW-0221"} | {"WERYF":{"before":0,"after":null}} | [] |
| A409 | b98082cd-d5a2-4039-9413-8869884e6fcd | Schron Zachodni w Iwanówce / {"cave_id":"C-0225","object_id":"CHW-0014"} | {"WERYF":{"before":0,"after":null}} | [] |
| A410 | b99b0cf7-4ca0-4b29-a31e-a74e68f936cd | Schron pod Sarnią Skałą / {"cave_id":"C-0894","object_id":"STR-0023"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A411 | b9ce3858-b5e7-46ff-9ed9-83e15d704972 | Sztolnia w Ornaczańskim Żlebie nr 3 / {"cave_id":"C-0929","object_id":"PL-0052"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null},"WERYF":{"before":0,"after":null}} | [] |
| A412 | ba3b354a-8bbe-4342-a993-a1988e9006d6 | Jaskinia Zimna / {"cave_id":"C-0297","object_id":"KSW-0090"} | {} | [{"catalog_current":"Jaskinia Zimna - otwór dolny","field":"object.name_local","source_after":"Dolny","source_before":"Dolny","source_field":"OTWÓR"},{"catalog_current":null,"field":"cave.system_name","source_after":"Zimna","source_before":"Zimna","source_field":"SYSTEM"}] |
| A413 | ba5bc846-7368-45fc-8c32-8a02085ff431 | Jaskinia Wysoka / {"cave_id":"C-0665","object_id":"KSW-0189"} | {} | [{"catalog_current":"Jaskinia Wysoka - Wysoka7Progow","field":"object.name_local","source_after":"górny","source_before":"górny","source_field":"OTWÓR"},{"catalog_current":null,"field":"cave.system_name","source_after":"SYSTEM Wysoka","source_before":"SYSTEM Wysoka","source_field":"SYSTEM"}] |
| A414 | ba97358d-c961-45b2-8a59-f1423ad3e8a9 | Dziura w Burcie / {"cave_id":"C-0874","object_id":"KSW-0239"} | {"GLEBOKOSC":{"before":0,"after":null},"WERYF":{"before":0,"after":null}} | [] |
| A415 | bab9e811-8d64-43ed-8ac8-f9d8021dbcdd | Schron nad Tomanową / {"cave_id":"C-0356","object_id":"KSW-0107"} | {"WERYF":{"before":0,"after":null}} | [] |
| A416 | bb1588fd-7c1c-45c8-bf65-2c4f8d461263 | Schron nad Zakosistą / {"cave_id":"C-0153","object_id":"KSW-0043"} | {"WERYF":{"before":0,"after":null}} | [] |
| A417 | bbd6e912-4ee2-48e3-a809-387572b8bdc5 | Dziura pod Nową / {"cave_id":"C-0286","object_id":"KSZ-0032"} | {"WERYF":{"before":0,"after":null}} | [] |
| A418 | bc23980d-6ed4-4690-81d0-4756446e8af5 | Jaskinia Nowa nad Raptawicką Granią / {"cave_id":"C-0277","object_id":"KSZ-0030"} | {"WERYF":{"before":0,"after":null}} | [] |
| A419 | be12c616-1780-44d3-ad82-398987c85b67 | Nyża nad Olczyską III / {"cave_id":"C-0902","object_id":"OLC-0006"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A420 | be32cef8-e322-487d-9eae-1dd5f6e79de9 | Dziura w Krzesanicy I / {"cave_id":"C-0348","object_id":"MTZ-0028"} | {"WERYF":{"before":0,"after":null}} | [] |
| A421 | bfbfb55b-f346-4792-a9a5-c486e522f931 | Szczelina w Krzesanicy III / {"cave_id":"C-0017","object_id":"MTZ-0002"} | {"WERYF":{"before":0,"after":null}} | [] |
| A422 | bfd29c11-0c0c-4f4f-9577-18e86ba1fbd1 | Szczelina na Grzędzie / {"cave_id":"C-0034","object_id":"KSZ-0002"} | {"WERYF":{"before":0,"after":null}} | [] |
| A423 | c127209a-a50e-45e7-a4a4-287cc1f110a2 | Wyżnia Koszowa Dziura / {"cave_id":"C-0575","object_id":"PL-0031"} | {"WERYF":{"before":0,"after":1},"WER_LOK":{"before":null,"after":"FF 08092026"}} | [] |
| A424 | c1595610-9dfa-44ba-a1c7-be8e66c772d4 | Radkowa Dziura II / {"cave_id":"C-0199","object_id":"KSW-0058"} | {"WERYF":{"before":0,"after":null}} | [] |
| A425 | c191bf30-8b3b-452f-a11f-b52de2d90dad | Komin w Niskiej Turni / {"cave_id":"C-0205","object_id":"KSW-0060"} | {"WERYF":{"before":0,"after":null}} | [] |
| A426 | c1f42c86-4857-40f9-881d-1fd7ea11d697 | Krowi Tunel / {"cave_id":"C-0723","object_id":"KSW-0205"} | {"WERYF":{"before":0,"after":null}} | [] |
| A427 | c334f817-a3eb-4a25-a18d-d32f83914a97 | Dziura w Organach II / {"cave_id":"C-0128","object_id":"KSW-0037"} | {"WERYF":{"before":0,"after":null}} | [] |
| A428 | c33e3764-68a6-4841-bdbc-5cb4916e5b2e | Szczelina w Kondratowych Basztach / {"cave_id":"C-0983","object_id":"BYZ-0057"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null}} | [] |
| A429 | c40cbae9-a473-4e5c-b91b-c62ee4db0801 | Okno nad Tomanową / {"cave_id":"C-0816","object_id":"KSW-0222"} | {"WERYF":{"before":0,"after":null}} | [] |
| A430 | c447e8b7-560c-4b40-96b5-805673528aa6 | Sztolnia na Klinowej Czubie nr 1 / {"cave_id":"C-0921","object_id":"CHW-0046"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null},"WERYF":{"before":0,"after":null}} | [] |
| A431 | c66a5090-e1e2-41ad-a9ff-a726548a8257 | Dziura z Konkrecjami Wyżnia / {"cave_id":"C-0313","object_id":"KSW-0097"} | {"WERYF":{"before":0,"after":null}} | [] |
| A432 | c67d8ce7-b0a2-49ec-ad61-7c1232f551c6 | Trzeszcząca Szczelina / {"cave_id":"C-0528","object_id":"MTZ-0039"} | {"WERYF":{"before":0,"after":null}} | [] |
| A433 | c79e6cc1-3c7b-4e74-9399-6aa3199c1a07 | Schron pod Kopą Kondracką / {"cave_id":"C-0949","object_id":"BYZ-0053"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A434 | c7a19e86-2c28-488a-b836-5bb95454937d | Wnęka na Grzędzie / {"cave_id":"C-0312","object_id":"KSZ-0037"} | {"WERYF":{"before":0,"after":null}} | [] |
| A435 | c7aa36ed-bd41-433f-95c9-19de153c6bd7 | Dziura nad Zawaliskiem / {"cave_id":"C-0216","object_id":"KSW-0063"} | {"WERYF":{"before":0,"after":null}} | [] |
| A436 | c8241e98-b50f-4e88-ad10-6c21fa19331d | Szczelina w Tomanowym Grzbiecie IV / {"cave_id":"C-0419","object_id":"KSW-0126"} | {"WERYF":{"before":0,"after":null}} | [] |
| A437 | c92929a3-56c0-4ce7-a989-3f2e432af387 | Sztolnia w Żlebie pod Czerwienicą / {"cave_id":"C-0871","object_id":"BYW-0037"} | {"DENIWELACJ":{"before":0,"after":null},"DLUGOSC":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null},"WERYF":{"before":0,"after":null}} | [] |
| A438 | c990316e-782b-4dbe-9950-85221e5b8b87 | Jaskinia Maleńka w Smreczyńskim Wierchu / {"cave_id":"C-0369","object_id":"PL-0021"} | {"WERYF":{"before":0,"after":null}} | [] |
| A439 | c9c3a324-ac15-4aec-8ad3-f139d6d5333a | Serowa Dziura / {"cave_id":"C-0343","object_id":"KSW-0105"} | {"WERYF":{"before":0,"after":null}} | [] |
| A440 | c9ddd04f-0398-4b91-a7c8-a5517c9a4733 | Szczelina pod Gankową II / {"cave_id":"C-0002","object_id":"KSW-0001"} | {"WERYF":{"before":0,"after":null}} | [] |
| A441 | c9e5d687-b39f-41e5-a4fd-6b5ba53c93ce | Dziura w Żabiem / {"cave_id":"C-0726","object_id":"PL-0039"} | {"WERYF":{"before":0,"after":null}} | [] |
| A442 | ca3a7955-cd7e-46c0-9a2a-9f8632b39057 | koleba w Białym Żlebku / {"cave_id":"C-0913","object_id":"PL-0050"} | {"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A443 | cbca9ab2-077a-44a4-aca8-973cee8b7111 | Wielka Nyża / {"cave_id":"C-0044","object_id":"KSZ-0004"} | {"WERYF":{"before":0,"after":null}} | [] |
| A444 | cc760b34-1792-4bd1-afa5-bf17a56567a5 | Grota w Rzędach / {"cave_id":"C-0448","object_id":"KSW-0138"} | {"WERYF":{"before":0,"after":null}} | [] |
| A445 | cdb29f70-dba3-45e2-baaa-ae1ebbc9156c | Jaskinia Zośka / {"cave_id":"C-0567","object_id":"MLZ-0057"} | {} | [{"catalog_current":null,"field":"cave.system_name","source_after":"SYSTEM Zośka","source_before":"SYSTEM Zośka","source_field":"SYSTEM"}] |
| A446 | cdc9487c-98bc-43ad-91df-170f50f8b734 | Schron w Zadnim Kościelcu / {"cave_id":"C-0315","object_id":"SUW-0002"} | {"WERYF":{"before":0,"after":null}} | [] |
| A447 | cecf8620-a1c8-4941-a5b1-6c2226dc1f88 | Jaskinia Mylna / {"cave_id":"C-0573","object_id":"KSZ-0064"} | {} | [{"catalog_current":"Jaskinia Mylna","field":"object.name_local","source_after":"S","source_before":"S","source_field":"OTWÓR"}] |
| A448 | cf3c3737-0919-4fda-bcba-aeae12604fa7 | Szczelina przy Wymytem / {"cave_id":"C-0900","object_id":"DZI-0007"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A449 | d082f240-a7b7-47f3-8b77-2ef9cd7ca163 | Jaskinia pod Płytą / {"cave_id":"C-0029","object_id":"MTZ-0003"} | {"WERYF":{"before":0,"after":null}} | [] |
| A450 | d0f30d83-c7af-4a7d-81e2-b46341936649 | Mała Gawra / {"cave_id":"C-0498","object_id":"KSW-0152"} | {"WERYF":{"before":0,"after":null}} | [] |
| A451 | d1372576-f8e4-440b-bfde-a01bfde6bcf2 | Schron przy Zagonie / {"cave_id":"C-0872","object_id":"MLZ-0088"} | {"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A452 | d1578a9f-222a-404a-b528-c5021ba7f00c | Płaska Komórka w Żeleźniaku / {"cave_id":"C-0700","object_id":"KSZ-0080"} | {"WERYF":{"before":0,"after":null}} | [] |
| A453 | d1d5d5f1-2530-4a20-92b4-e7e90bc5f5d7 | Dziura nad Wantulami III / {"cave_id":"C-0811","object_id":"MTZ-0062"} | {"WERYF":{"before":0,"after":null}} | [] |
| A454 | d22b7269-0b61-4d30-9e8e-d6bec62e1313 | Lejowa Szczelina / {"cave_id":"C-0303","object_id":"LEJ-0010"} | {"WERYF":{"before":0,"after":null}} | [] |
| A455 | d22b814f-00f6-46be-a245-547f46e810c1 | Dziura w Kondratowych Basztach / {"cave_id":"C-0873","object_id":"BYZ-0044"} | {"DENIWELACJ":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A456 | d29b67f7-2416-4f4e-9ff7-0d52c2acc9a8 | Niski Schron nad Tomanową / {"cave_id":"C-0463","object_id":"KSW-0142"} | {"WERYF":{"before":0,"after":null}} | [] |
| A457 | d2b67cf2-fa6a-4cc3-bd05-66f3e5552f65 | Jaskinia pod Ostrewką / {"cave_id":"C-0766","object_id":"KSW-0216"} | {"WERYF":{"before":0,"after":null}} | [] |
| A458 | d2fbd9b0-6e16-4d1a-8603-4f40cc72f199 | Dziura w Miedzianym Kosturze I / {"cave_id":"C-0353","object_id":"PL-0020"} | {"WERYF":{"before":0,"after":null}} | [] |
| A459 | d3a46284-758d-46c6-94e7-87bfece29160 | Szczelina w Głębowcu / {"cave_id":"C-0080","object_id":"KSZ-0008"} | {"WERYF":{"before":0,"after":null}} | [] |
| A460 | d3cbaa6b-3606-410f-966e-c456312ca3c2 | Szczelina przy Zawieszonej Skale I / {"cave_id":"C-0857","object_id":"KSZ-0108"} | {"WERYF":{"before":0,"after":null}} | [] |
| A461 | d3e44382-54a5-4808-9d3c-d316299f621c | Jaskinia w Małym Krakowie / {"cave_id":"C-0426","object_id":"KSW-0130"} | {"WERYF":{"before":0,"after":null}} | [] |
| A462 | d4b6be5e-3961-497f-8026-d8ee05839468 | Zimna Szczelina II / {"cave_id":"C-0433","object_id":"KSZ-0049"} | {"WERYF":{"before":0,"after":null}} | [] |
| A463 | d4ded967-2756-434f-b8c0-2f32b7f111ab | Krakowska Szczelina / {"cave_id":"C-0042","object_id":"KSW-0012"} | {"WERYF":{"before":0,"after":null}} | [] |
| A464 | d54f8971-a987-4ec7-9c67-dfe1b2f4ba0c | Nyża nad Bramką / {"cave_id":"C-0319","object_id":"KSZ-0038"} | {"WERYF":{"before":0,"after":null}} | [] |
| A465 | d6280ba6-c638-4087-b4f8-cf7aad8ba588 | Szczelina za Mechami / {"cave_id":"C-0909","object_id":"KSW-0244"} | {"DENIWELACJ":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A466 | d628c1dd-80c3-4323-9d0d-7700b4228f4a | Szczelina pod Niżnią Zbójnicką Turnią / {"cave_id":"C-0475","object_id":"KSW-0146"} | {"WERYF":{"before":0,"after":null}} | [] |
| A467 | d68c911f-8dfe-4317-bce6-9f1d9c76726f | Sarni Schron / {"cave_id":"C-0451","object_id":"KSZ-0050"} | {"WERYF":{"before":0,"after":null}} | [] |
| A468 | d6da794e-6cd4-4cdc-9342-b94be4734fca | Schron nad Sniezna / {"cave_id":"C-0889","object_id":"MLZ-0092"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A469 | d7c052e6-d584-4320-b886-367312d2219f | Szczelinka w Głębowcu / {"cave_id":"C-0484","object_id":"KSZ-0055"} | {"WERYF":{"before":0,"after":null}} | [] |
| A470 | d8ac40bd-78e3-43ce-a8ad-d30f91a16a0e | Jaskinia pod Wierchem / {"cave_id":"C-0635","object_id":"MTZ-0047"} | {"WERYF":{"before":0,"after":null}} | [] |
| A471 | d90aadc9-9e6c-4020-a409-4b4ffaeedbff | Dziura w Stołach / {"cave_id":"C-0459","object_id":"KSZ-0051"} | {"WERYF":{"before":0,"after":null}} | [] |
| A472 | d9f42427-2b5e-4f7f-8231-8e2d27f7ed45 | Zimny Aven / {"cave_id":"C-0679","object_id":"MTZ-0049"} | {"WERYF":{"before":0,"after":null}} | [] |
| A473 | da201294-463e-4f4d-8a60-d2f88fb17c1a | Sztolnia na Klinowej Czubie nr 4 / {"cave_id":"C-0988","object_id":"CHW-0056"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null},"WERYF":{"before":0,"after":null}} | [] |
| A474 | daf61259-946d-4d5e-8053-d5e69b732c09 | Sztolnia w Małym Reglu nr 2 / {"cave_id":"C-0948","object_id":"KSW-0247"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null},"WERYF":{"before":0,"after":null}} | [] |
| A475 | db33ac30-e5c0-436d-85c6-7aede2e905b5 | Nisza w Organach II / {"cave_id":"C-0676","object_id":"KSW-0192"} | {"WERYF":{"before":0,"after":null}} | [] |
| A476 | db52b34b-b408-408f-9073-4c18141a9053 | Jaskinia Pośrednia / {"cave_id":"C-0499","object_id":"KSW-0153"} | {} | [{"catalog_current":null,"field":"cave.system_name","source_after":"SYSTEM Wysoka","source_before":"SYSTEM Wysoka","source_field":"SYSTEM"}] |
| A477 | db9a3ad7-6249-4dae-8c11-d37c5d5b78bd | Schron w Zawraciku / {"cave_id":"C-0989","object_id":"BYW-0044"} | {"DENIWELACJ":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A478 | db9e0e2b-c3db-4109-98a8-186360ed8660 | Nyża w Ździarach / {"cave_id":"C-0722","object_id":"KSW-0204"} | {"WERYF":{"before":0,"after":null}} | [] |
| A479 | dbdfe727-c1a8-4f4a-bbe5-706906238f6e | Jaskinia Śnieżna Studnia / {"cave_id":"C-0581","object_id":"MLZ-0059"} | {"DLUGOSC":{"before":14441,"after":14670}} | [{"catalog_current":"Jaskinia Śnieżna Studnia","field":"object.name_local","source_after":"Śnieżna Studnia","source_before":"Śnieżna Studnia","source_field":"OTWÓR"},{"catalog_current":null,"field":"cave.system_name","source_after":"Śnieżna Studnia","source_before":"Śnieżna Studnia","source_field":"SYSTEM"}] |
| A480 | dca7bdc2-40f1-426b-95c8-3f7790f9ec0a | Jaskinia przy Żlebie / {"cave_id":"C-0146","object_id":"KSZ-0015"} | {"WERYF":{"before":0,"after":null}} | [] |
| A481 | dcad726e-957a-4c2f-81e7-a00da3ba74dc | Szczelina nad Ptasią / {"cave_id":"C-0776","object_id":"MTZ-0059"} | {"WERYF":{"before":0,"after":null}} | [] |
| A482 | dced0d83-3605-4170-b05e-17e9e331818b | Dziura pod Wantą / {"cave_id":"C-0317","object_id":"KSW-0099"} | {"WERYF":{"before":0,"after":null}} | [] |
| A483 | dd98d3f8-4a2a-48be-af9f-241928d09f11 | Dziura nad Wantulami I / {"cave_id":"C-0689","object_id":"MTZ-0050"} | {"WERYF":{"before":0,"after":null}} | [] |
| A484 | de4b21c2-445f-4edf-abff-4f472f6517db | Górne Kominy / {"cave_id":"C-0081","object_id":"MTZ-0007"} | {"WERYF":{"before":0,"after":null}} | [] |
| A485 | de56dd34-6e78-4d66-adf9-8d5efc5ae208 | Schron pomiędzy Żwirowymi Dziurami / {"cave_id":"C-0112","object_id":"KSW-0034"} | {"WERYF":{"before":0,"after":null}} | [] |
| A486 | de77ab43-68d1-4da8-8a18-5d6dfef2d4c7 | Nyża nad Kamieniem / {"cave_id":"C-0954","object_id":"BYZ-0054"} | {"GLEBOKOSC":{"before":0,"after":null}} | [] |
| A487 | deb5b651-b63d-4f90-b2c1-87823668250c | Schron przy Wielkiej Turni / {"cave_id":"C-0314","object_id":"KSW-0098"} | {"WERYF":{"before":0,"after":null}} | [] |
| A488 | df21dac8-e66a-4f29-979d-9e0703db68e2 | Rura pod Okapami / {"cave_id":"C-0935","object_id":"MLZ-0097"} | {"GLEBOKOSC":{"before":0,"after":null}} | [] |
| A489 | dfda05ba-3ef6-4ea3-9aea-4ff83789031d | Jaskinia pod Śnieżną Studnią / {"cave_id":"C-0617","object_id":"MLZ-0065"} | {"DENIWELACJ":{"before":0,"after":null},"DLUGOSC":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [{"catalog_current":null,"field":"cave.system_name","source_after":"Śnieżna Studnia","source_before":"Śnieżna Studnia","source_field":"SYSTEM"}] |
| A490 | e03549be-8cd5-4c62-865b-15fc23ec2ab2 | Ptasia Studnia / {"cave_id":"C-0167","object_id":"MTZ-0015"} | {"DLUGOSC":{"before":6874,"after":7153}} | [{"catalog_current":null,"field":"cave.system_name","source_after":"SYSTEM Ptasia Studnia","source_before":"SYSTEM Ptasia Studnia","source_field":"SYSTEM"}] |
| A491 | e047a83a-7ed8-4ea6-b943-087c74f91bae | Jaskinia pod Baranami / {"cave_id":"C-0209","object_id":"CHW-0013"} | {"WERYF":{"before":0,"after":null}} | [] |
| A492 | e160f1d7-59fc-4042-9091-3237857090b6 | Cubryńska Dziura II / {"cave_id":"C-0543","object_id":"PL-0028"} | {"WERYF":{"before":0,"after":null}} | [] |
| A493 | e1e6fd89-d23c-4b2e-818c-7f16faf9251a | Schron przed Sową II / {"cave_id":"C-0485","object_id":"KSZ-0056"} | {"WERYF":{"before":0,"after":null}} | [] |
| A494 | e2e3cebb-86bf-4564-9a8e-fbe69771f394 | Jaskinia Turoniowa / {"cave_id":"C-0852","object_id":"MTW-0066"} | {"WERYF":{"before":0,"after":null}} | [] |
| A495 | e306cfb8-de61-4e12-b244-dffe0aca3586 | Zapadlisko / {"cave_id":"C-0885","object_id":"MLZ-0090"} | {"DENIWELACJ":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A496 | e343c2cc-c0e6-4d8c-97ee-f27355fcaf4b | Szczelina Zawaliskowa nad Kufą / {"cave_id":"C-0454","object_id":"LEJ-0014"} | {"WERYF":{"before":0,"after":null}} | [] |
| A497 | e41c4554-66c1-4346-96ba-4c33d499d0c4 | Jaskinia Bańdzioch Kominiarski / {"cave_id":"C-0078","object_id":"LEJ-0002"} | {"WERYF":{"before":0,"after":null}} | [{"catalog_current":"Jaskinia Bańdzioch Kominiarski - otwór górny","field":"object.name_local","source_after":"Jaskinia Bańdzioch Kominiarski","source_before":"Jaskinia Bańdzioch Kominiarski","source_field":"NAZWA"}] |
| A498 | e47e074f-48f3-4ced-bcb9-1c04da9c8758 | Schron Wschodni pod Kufą / {"cave_id":"C-0616","object_id":"LEJ-0020"} | {"WERYF":{"before":0,"after":null}} | [] |
| A499 | e4876502-0ec3-4533-ae1c-7d9ddf912baa | Schron nad Doliną / {"cave_id":"C-0489","object_id":"KSZ-0058"} | {"WERYF":{"before":0,"after":null}} | [] |
| A500 | e595548b-803c-47bf-aa96-59b239b0ef8a | Upłazkowa Koleba / {"cave_id":"C-0541","object_id":"KSW-0162"} | {"WERYF":{"before":0,"after":null}} | [] |
| A501 | e5c5ffd1-d57c-4529-9532-f70bdfa3b79f | Kalacka Nyża III / {"cave_id":"C-0927","object_id":"BYZ-0050"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A502 | e5d3814d-74f8-4440-b456-1acf39f570a6 | Dziura w Ździarach Wyżnia / {"cave_id":"C-0462","object_id":"KSW-0141"} | {"WERYF":{"before":0,"after":null}} | [] |
| A503 | e64bc09b-435e-4d2a-86ff-f67516f671d6 | Jaskinia Rura Kominiarska / {"cave_id":"C-0048","object_id":"KSZ-0005"} | {"WERYF":{"before":0,"after":null}} | [] |
| A504 | e70a776d-c9ac-48bb-995f-303241b61670 | Jędrusiowa Dziura / {"cave_id":"C-0406","object_id":"MLZ-0039"} | {} | [{"catalog_current":null,"field":"cave.system_name","source_after":"SYSTEM Jędrusiowa Dziura","source_before":"SYSTEM Jędrusiowa Dziura","source_field":"SYSTEM"}] |
| A505 | e7505f82-a5f5-4c2d-bb98-7dd3399c5651 | Schron pod Siodłową Turnią I / {"cave_id":"C-0896","object_id":"MLW-0037"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null}} | [] |
| A506 | e7799056-8754-4539-9804-8a63d5c251b6 | Szczelina nad Korytem / {"cave_id":"C-0247","object_id":"KSW-0073"} | {"WERYF":{"before":0,"after":null}} | [] |
| A507 | e83ddd29-c1ed-4024-80e0-c661bffec1c2 | Szemrzący Schron / {"cave_id":"C-0693","object_id":"LEJ-0022"} | {"WERYF":{"before":0,"after":null}} | [] |
| A508 | e8a95d46-668d-4c6c-81ba-7d7934c67ac9 | Nyża przy Zagonie / {"cave_id":"C-0978","object_id":"MLZ-0104"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A509 | e939b7f8-14b9-4da3-96cc-4797b4ffc957 | Zbójnicka Rura / {"cave_id":"C-0066","object_id":"KSW-0019"} | {"WERYF":{"before":0,"after":null}} | [] |
| A510 | ea53b16c-7efe-4446-b312-53e2ef18a6ae | Szczelina w Tomanowym Grzbiecie II / {"cave_id":"C-0252","object_id":"KSW-0076"} | {"WERYF":{"before":0,"after":null}} | [] |
| A511 | ebee2dff-752f-4dbb-bb57-b7753d4025c7 | Szczelina przed Sową / {"cave_id":"C-0654","object_id":"KSZ-0074"} | {"WERYF":{"before":0,"after":null}} | [] |
| A512 | ec3d26e8-3ef2-429f-a9e2-9a0eae769683 | Nisza Wschodnia / {"cave_id":"C-0301","object_id":"KSZ-0035"} | {"WERYF":{"before":0,"after":null}} | [] |
| A513 | ec925837-5de2-441a-946a-b65996d0a6a4 | Mnichowa Nyza / {"cave_id":"C-0975","object_id":"MLW-0049"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A514 | eca70a41-1ad6-452f-861c-ed58d62e7f94 | Jaskinia Wilcza / {"cave_id":"C-0812","object_id":"MLZ-0081"} | {} | [{"catalog_current":null,"field":"cave.system_name","source_after":"Jaskinia Wielka Śnieżna","source_before":"Jaskinia Wielka Śnieżna","source_field":"SYSTEM"}] |
| A515 | ecc38262-2a49-49cd-a5f0-5024c91cb2c9 | Omszała Szczelina / {"cave_id":"C-0530","object_id":"MTZ-0040"} | {"WERYF":{"before":0,"after":null}} | [] |
| A516 | ecdf2ab2-13a3-4f53-8b99-1b2bfbee2d0a | Jaskinia Ciasna / {"cave_id":"C-0193","object_id":"KSW-0054"} | {"WERYF":{"before":0,"after":null}} | [] |
| A517 | ed64f5f8-e896-49ba-a753-d46df3028b87 | Nyża w Wąwozie Między Ściany / {"cave_id":"C-0207","object_id":"CHW-0012"} | {"WERYF":{"before":0,"after":null}} | [] |
| A518 | ee0f6f13-f675-43b3-8423-4bbb0b263580 | Grota nad Korytem / {"cave_id":"C-0162","object_id":"KSW-0046"} | {"WERYF":{"before":0,"after":null}} | [] |
| A519 | ee45b18b-1b00-45bc-b655-689834dbf031 | Schron przed Sową I / {"cave_id":"C-0191","object_id":"KSZ-0021"} | {"WERYF":{"before":0,"after":null}} | [] |
| A520 | eea9e82f-1da8-492e-b6e2-a9442252c3a2 | Dziura we Wysrankach / {"cave_id":"C-0908","object_id":"KSW-0243"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A521 | ef04f765-43fb-48ce-bec7-8ca010abffa8 | Jaskinia nad Mostkiem Wyżnia / {"cave_id":"C-0123","object_id":"KSZ-0011"} | {"WERYF":{"before":0,"after":null}} | [] |
| A522 | efd78893-dffa-45ab-b283-da40adbbccc0 | Dziurka od Klucza / {"cave_id":"C-0129","object_id":"LEJ-0005"} | {"WERYF":{"before":0,"after":null}} | [] |
| A523 | f056190d-1be8-4376-9b80-75370f3d0b4c | Dziurawiec / {"cave_id":"C-0310","object_id":"KSZ-0036"} | {"WERYF":{"before":0,"after":null}} | [] |
| A524 | f0614b4c-6c7e-47d4-8dec-5395464813fc | Wiciowy Schron / {"cave_id":"C-0673","object_id":"KSZ-0077"} | {"WERYF":{"before":0,"after":null}} | [] |
| A525 | f0c21dd8-6a0b-46a9-afce-1c3b4f668f8e | Szczelina w Krzesanicy I / {"cave_id":"C-0472","object_id":"MTZ-0034"} | {"WERYF":{"before":0,"after":null}} | [] |
| A526 | f0f06c12-762c-4c86-a5fc-cf3f9587d9a4 | Dziura nad Zabijakiem I / {"cave_id":"C-0114","object_id":"LEJ-0003"} | {"WERYF":{"before":0,"after":null}} | [] |
| A527 | f109b6a3-6abd-4eca-a4f6-7f342f61371c | Jaskinia nad Beczką / {"cave_id":"C-0643","object_id":"KSW-0183"} | {"WERYF":{"before":0,"after":null}} | [] |
| A528 | f194637e-621b-4b2c-8edf-283c3fa343c3 | Szczelina przy Bańdziochu / {"cave_id":"C-0514","object_id":"KSZ-0060"} | {"WERYF":{"before":0,"after":null}} | [] |
| A529 | f19e1c88-7dd7-442b-adac-22e66574977f | Szczelina ze Śniegiem / {"cave_id":"C-0669","object_id":"LEJ-0021"} | {"WERYF":{"before":0,"after":null}} | [] |
| A530 | f2070f6e-c2d9-4f91-a008-d243df354871 | Jaskinia przy Perci / {"cave_id":"C-0565","object_id":"KSW-0167"} | {"WERYF":{"before":0,"after":null}} | [] |
| A531 | f22edcd0-acfd-4797-b2a0-cfd5b325bc8e | tunel w Skrajnej Giewonckiej Baszcie / {"cave_id":"C-0947","object_id":"MLW-0044"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null},"WERYF":{"before":0,"after":null}} | [{"catalog_current":"tunel w Skrajnej Giewonckiej Baszcie - otwór N","field":"object.name_local","source_after":"N","source_before":"N","source_field":"OTWÓR"}] |
| A532 | f24a8a97-d766-469f-89fd-820e6dc620ae | Schronisko nad Trawersem w Żeleźniaku II / {"cave_id":"C-0606","object_id":"KSZ-0067"} | {"WERYF":{"before":0,"after":null}} | [] |
| A533 | f275b71f-8034-4305-8ecf-95ef2f9b4ae0 | Korytarz nad Mroźną / {"cave_id":"C-0995","object_id":"KSW-0254"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null}} | [] |
| A534 | f3936194-5679-46d0-a5b9-442ef199d660 | Okap w Ździarach / {"cave_id":"C-0234","object_id":"KSW-0070"} | {"WERYF":{"before":0,"after":null}} | [] |
| A535 | f39b8a6b-c967-491a-9e0a-c1e5c7b7e30e | Harnasiowa Szczelina / {"cave_id":"C-0212","object_id":"MTZ-0019"} | {"WERYF":{"before":0,"after":null}} | [] |
| A536 | f3b07f48-0f30-4692-bbca-96a387df1fc5 | Sztolnia w Żlebie Baniste / {"cave_id":"C-0963","object_id":"PL-0055"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null},"WERYF":{"before":0,"after":null}} | [] |
| A537 | f3b86672-b24b-4627-9f33-f0ec0514b52a | Sowia Jama III / {"cave_id":"C-0070","object_id":"KSZ-0007"} | {"WERYF":{"before":0,"after":null}} | [] |
| A538 | f40a4977-a74c-4c64-8d83-4908ce641ca0 | Studnia w Mnichu / {"cave_id":"C-0417","object_id":"PL-0025"} | {"WERYF":{"before":0,"after":null}} | [] |
| A539 | f412698d-1b79-42b1-bc65-3c2917e7877b | Ziobrowy Schron / {"cave_id":"C-0041","object_id":"KSW-0011"} | {"WERYF":{"before":0,"after":null}} | [] |
| A540 | f4458b31-fe66-4983-91c6-5d0cd1a11bc7 | Jaskinia przy Wymytem / {"cave_id":"C-0992","object_id":"DZI-0010"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A541 | f44f49d6-8702-477c-99cc-83278dfa8c32 | Sztolnia - Kopalnia w Wantulach I / {"cave_id":"C-0966","object_id":"MTW-0068"} | {"PRZEWYZSZE":{"before":0,"after":null},"WERYF":{"before":0,"after":null}} | [] |
| A542 | f471728a-5bf9-4f10-a72d-f29fda6d4d0f | Korytarz do Naciekowej / {"cave_id":"C-0839","object_id":"KSW-0230"} | {"WERYF":{"before":0,"after":null}} | [] |
| A543 | f4d11f48-14af-4a26-9fbc-a3366d5bf8d2 | Sztolnie w Żlebie pod Banie / {"cave_id":"C-0869","object_id":"PL-0047"} | {"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null},"WERYF":{"before":0,"after":null}} | [] |
| A544 | f4de5d37-5d76-4315-8bcc-4c57a5b68f1c | Jaskinia Raptawicka / {"cave_id":"C-0403","object_id":"KSZ-0047"} | {} | [{"catalog_current":"Jaskinia Raptawicka","field":"object.name_local","source_after":"górny","source_before":"górny","source_field":"OTWÓR"}] |
| A545 | f520650e-65c7-4376-9b23-e4938a42b514 | Szczelina w Krzesanicy II / {"cave_id":"C-0817","object_id":"MTZ-0064"} | {"WERYF":{"before":0,"after":null}} | [] |
| A546 | f56efd6c-15ff-48ce-bf53-a33738e3bddf | Mokra Szczelina / {"cave_id":"C-0752","object_id":"KSW-0211"} | {"WERYF":{"before":0,"after":null}} | [] |
| A547 | f5f0671b-91a8-4f03-a345-c44c3034508a | Nasza Dziura / {"cave_id":"C-0754","object_id":"KSW-0212"} | {"WERYF":{"before":0,"after":null}} | [] |
| A548 | f67b912e-f7aa-4f5e-af7e-ef9efeae6c64 | Szczelina nad Lejem / {"cave_id":"C-0394","object_id":"PL-0024"} | {"WERYF":{"before":0,"after":1},"WER_LOK":{"before":null,"after":"FF 08092026"}} | [] |
| A549 | f6a2aaa7-477e-4b9f-8807-fc928412dbe2 | Szczelina za Okrętem III / {"cave_id":"C-0239","object_id":"KSW-0072"} | {"WERYF":{"before":0,"after":null}} | [] |
| A550 | f6cd2736-d198-4677-843b-337bd1c3578e | Korytarz z Różą / {"cave_id":"C-0302","object_id":"KSW-0094"} | {"WERYF":{"before":0,"after":null}} | [] |
| A551 | f7e6368c-23ce-42cc-a0f2-533a9d18b1af | Schron z Napisami / {"cave_id":"C-0547","object_id":"KSW-0163"} | {"WERYF":{"before":0,"after":null}} | [] |
| A552 | f7ed4066-4249-46a1-bd73-0532d43bc278 | Wyżni Okap nad Tomanową / {"cave_id":"C-0683","object_id":"KSW-0195"} | {"WERYF":{"before":0,"after":null}} | [] |
| A553 | f80e3e91-d908-43a5-987d-65e6975d9b6d | Szczelina w Grani I / {"cave_id":"C-0842","object_id":"LEJ-0026"} | {"WERYF":{"before":0,"after":null}} | [] |
| A554 | f8892af0-67ae-47d1-8e94-9683fd539c7e | Jaskinia przy Tunelu Małołąckim / {"cave_id":"C-0899","object_id":"MLZ-0093"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null}} | [] |
| A555 | f8e1ec45-65d1-440f-9947-78b4ab6b08bd | Schron pod Kazalnicą / {"cave_id":"C-0806","object_id":"KSZ-0097"} | {"WERYF":{"before":0,"after":null}} | [] |
| A556 | f8ebfb04-fba4-43fb-b027-7b7c4d3bef30 | Jaskinia pod Wiśniakową Jamą / {"cave_id":"C-0639","object_id":"KSZ-0071"} | {"WERYF":{"before":0,"after":null}} | [] |
| A557 | f8efa103-21d1-4e22-9652-a4b21db05b28 | Jaskinia z Mułem / {"cave_id":"C-0387","object_id":"KSZ-0045"} | {"WERYF":{"before":0,"after":null}} | [] |
| A558 | f98e8983-73f8-411c-ac19-a8159d2509ee | Jaskinia Ziobrowa / {"cave_id":"C-0251","object_id":"KSW-0075"} | {"WERYF":{"before":0,"after":null}} | [{"catalog_current":null,"field":"cave.system_name","source_after":"SYSTEM Ziobrowa","source_before":"SYSTEM Ziobrowa","source_field":"SYSTEM"}] |
| A559 | f9c94562-fc14-4560-a452-5735cbd6f611 | Nyża w Kondratowych Basztach / {"cave_id":"C-0985","object_id":"BYZ-0058"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A560 | f9cbce03-e91c-4970-b373-56ea2205634b | Jaskinia Jagnięca / {"cave_id":"C-0325","object_id":"KSW-0101"} | {"WERYF":{"before":0,"after":null}} | [] |
| A561 | fa9ba8b6-5ed6-431d-b2d5-5df025111077 | Sztolnia na Klinowej Czubie nr 3 / {"cave_id":"C-0951","object_id":"CHW-0052"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null},"WERYF":{"before":0,"after":null}} | [] |
| A562 | fac8752a-acb1-4752-b26a-b7211f5a9fcd | Komin w Ździarach / {"cave_id":"C-0249","object_id":"KSW-0074"} | {"WERYF":{"before":0,"after":null}} | [] |
| A563 | faf49442-a9e8-400f-9bda-1b84e2cd305c | Ósemka / {"cave_id":"C-0010","object_id":"KSW-0005"} | {"WERYF":{"before":0,"after":null}} | [] |
| A564 | fb71f07a-6bac-40e0-9e45-7a32effe49c0 | Szczelina w Uwozisku / {"cave_id":"C-0461","object_id":"KSZ-0052"} | {"WERYF":{"before":0,"after":null}} | [] |
| A565 | fbfeaeee-59bd-41a0-80f7-5df22ccffdc4 | Schron przy Arkadzie / {"cave_id":"C-0557","object_id":"KSW-0164"} | {"WERYF":{"before":0,"after":null}} | [] |
| A566 | fc571a5a-9e84-46ef-b4b4-a9b2e1040d08 | Jaskinia przy Jędrusiowej Dziurze / {"cave_id":"C-0013","object_id":"MLZ-0002"} | {} | [{"catalog_current":null,"field":"cave.system_name","source_after":"SYSTEM Jędrusiowa Dziura","source_before":"SYSTEM Jędrusiowa Dziura","source_field":"SYSTEM"}] |
| A567 | fc5f97cd-c35e-4a49-8d19-4a40a0767a88 | Szczelina w Koprowym Żlebie / {"cave_id":"C-0993","object_id":"MLW-0052"} | {"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A568 | fc8f548f-3c7c-461c-82d4-25efdbaada1f | Schron nad Wymytem / {"cave_id":"C-0920","object_id":"DZI-0009"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A569 | fcc7a4d6-7779-45d7-b594-af18f1ebb840 | Schron za Smoczą Jamą / {"cave_id":"C-0721","object_id":"KSW-0203"} | {"WERYF":{"before":0,"after":null}} | [] |
| A570 | fcf9c91d-76ac-48f2-843e-3193db34edd4 | Studnia pod Okapami / {"cave_id":"C-0907","object_id":"MLZ-0095"} | {"DENIWELACJ":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A571 | fd099612-691d-4713-bc2f-d3005386d33a | Dziura pod Kazalnicą / {"cave_id":"C-0496","object_id":"KSZ-0059"} | {"WERYF":{"before":0,"after":null}} | [] |
| A572 | fdfe4d08-677f-4cc9-a415-958b7047e3b1 | Szczelina przy Arkadzie / {"cave_id":"C-0741","object_id":"KSW-0207"} | {"WERYF":{"before":0,"after":null}} | [] |
| A573 | fec43a16-1b32-4ed5-8350-9f92de65270f | Schron przy Zakosistej / {"cave_id":"C-0118","object_id":"KSW-0035"} | {"WERYF":{"before":0,"after":null}} | [] |
| A574 | ff043ca8-b739-4323-848e-6ff5898bb486 | Krucha Szczelina / {"cave_id":"C-0664","object_id":"MTZ-0048"} | {"WERYF":{"before":0,"after":null}} | [] |
| A575 | ff10baad-57ba-4ac9-b53e-33cd6fab8025 | Jaskinia Lodowa nad Kufą / {"cave_id":"C-0350","object_id":"LEJ-0012"} | {"WERYF":{"before":0,"after":null}} | [] |
| A576 | ff2e3d30-4435-485b-8b52-87596b98961b | Żwirowa Dziura Wyżnia / {"cave_id":"C-0559","object_id":"KSW-0166"} | {"WERYF":{"before":0,"after":null}} | [] |
| A577 | ffb80d84-7d5a-4986-ba87-1e8d5bc00181 | Schron w Małym Szerokiem I / {"cave_id":"C-0940","object_id":"BYZ-0051"} | {"DENIWELACJ":{"before":0,"after":null},"GLEBOKOSC":{"before":0,"after":null},"PRZEWYZSZE":{"before":0,"after":null}} | [] |
| A578 | ffcfab90-7cfa-42f5-8050-bc13f041a3ce | Nyża za Załomem / {"cave_id":"C-0344","object_id":"KSW-0106"} | {"WERYF":{"before":0,"after":null}} | [] |
