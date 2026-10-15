# Przegląd main z 2026-10-12 — podstawa nowego planu

Baza: `a3dd1a671d3d93cd6958242fc68ddcf1d37cf846`. Świeży fetch 2026-10-15
potwierdził, że origin/main nadal wskazuje tę samą bazę. Zapis przeniesiono
z lokalnych artefaktów review do Git podczas PBI-078; nie jest to ponowne
przeprowadzenie pełnego przeglądu ani deklaracja naprawy.

[Obserwacje i hashe źródeł](main-review-2026-10-12.json),
[aktualne karty](../backlog_v1.md#naprawy-main-po-przegladzie-2026-10-12).
Numery R1–R8 należą do tego review, nie do dawnego raportu R01–R13.

| ID | Priorytet | Obserwacja | Naprawa |
|---|---|---|---|
| R1 | P1 | Brakujący katalog przechodzi walidację; build nadpisuje poprawny release pustymi wynikami | PBI-079 |
| R2 | P1 | Drugi klucz measurements zastępuje wcześniejszą historię bez błędu | PBI-080 |
| R3 | P1 | Review zapisuje pomiar lat=0 przy niezgodnych PL-1992 i raportuje has_errors=false | PBI-081 |
| R4 | P2, dane | 354 wartości WER_LOK i 25 UWAGI nie występuje w powiązanych YAML | PBI-082 |
| R5 | P2 | x_1992=.nan przechodzi walidację; GeoJSON zawiera NaN, SQLite kończy się wyjątkiem | PBI-084 |
| R6 | P2 | Dwa measurement.id w jednym obiekcie przechodzą walidację, SQLite odrzuca klucz | PBI-085 |
| R7 | P2 | link_cave pozostawia object_ids starej jaskini; walidator nie wykrywa sprzeczności | PBI-086 |
| R8 | P2, dane | STR-0024 ma jaskinia_otwor mimo GENEZA=sztolnia; CHZ-0011 ma charakter mieszany | PBI-083 |

## Reprodukcje kodu bez zależności od build

Przygotuj tymczasowe `data/objects/KSW`, `data/caves`, `data/relations`.
Skopiuj z tej bazy `data/objects/KSW/KSW-0001.yml` i powiązaną jaskinię
`data/caves/C-0002.yml`; w kopii jaskini pozostaw `object_ids: [KSW-0001]`.
Taki bazowy fixture ma dwa pomiary i zero błędów walidacji.
Każdy przypadek poniżej używa osobnej kopii; nie modyfikuje finalnych danych.

- **R1:** zbuduj release z fixture, zapisz hashe siedmiu artefaktów, następnie
  wywołaj `build_release_artifacts` na tych samych wyjściach z nieistniejącym
  `data_dir`. Na bazie kończy się sukcesem i zmienia liczniki 1/1/2 na 0/0/0.
- **R2:** do tekstu obiektu dopisz drugi klucz `measurements`, zawierający
  tylko pomiar wskazany przez best. `load_dataset` zwraca jeden pomiar,
  a `validate_data_dir` nie zwraca błędu.
- **R3:** w `StagingReports.tpn.matched_measurements` umieść kopię poprawnego
  pomiaru z nowym ID `m-999`, `lat=0`, niezmienionymi PL-1992 i nowym source_ref.
  Powiąż `record_number=1` i target z fixture. Decyzja `add_measurement`
  zapisuje dwa YAML przy `has_errors=false`; późniejsza walidacja wykazuje
  `COORDINATE_MISMATCH` i `MEASUREMENT_OUTSIDE_PL_SK`.
- **R5:** w wybranym pomiarze fixture ustaw `x_1992: .nan`. Walidacja ma
  zero błędów, bezpośredni eksport tworzy GeoJSON z NaN, SQLite zgłasza
  `NOT NULL constraint failed: measurements.x_1992`.
- **R6:** dopisz drugi pomiar o istniejącym ID, z odmiennymi notes.
  Walidacja ma zero błędów, SQLite zgłasza
  `UNIQUE constraint failed: measurements.object_id, measurements.id`.
- **R7:** dodaj pustą jaskinię `C-9999` i wywołaj decyzję `link_cave` dla
  `KSW-0001`. Obiekt wskazuje nową jaskinię, ale jest na obu listach
  `object_ids`; walidacja ma zero błędów.

Karty PBI wymagają również poprawnych kontroli i testów granicznych.
Zapisany wynik historyczny nie zastępuje testu przed/po na realizowanym SHA.

## Fakty dotyczące obecnych danych

Katalog: 1009 obiektów, 1003 jaskinie, 1875 pomiarów, 0 relacji.
Walidacja: 0 błędów, 2066 ostrzeżeń — 1875 braków dokładności, 103 poza
dolinami, 72 odległości i 16 rozbieżności prefixu. 1007 z 1009 best ma
status `nieweryfikowany`. Jest to stan źródeł, nie dowód błędności punktów.
Nie wykryto obecnych duplikatów kluczy YAML, ID pomiarów, NaN ani
niesymetrycznych powiązań. Eksporty zawierały po 1009 punktów;
SQLite integrity/FK i odczyt wszystkich rekordów DBF były poprawne.

R4 dotyczy tekstu lokalnego
`data/sources/tpn/tpn_otwory_jaskin.xlsx.-.Export.csv` dopasowanego po GLOBALID.
Przykłady brakujących uwag: MTW-0047 „przybliżona lokalizacja”,
CHZ-0021 „Trzeba uściślić położenie”, BYW-0015/BYW-0031 „Opis dojścia
w inwentarzu jest błędny”. Pełna lista braków jest w JSON. To braki
w powiązanych rekordach domenowych, a nie utrata zachowanego surowego CSV.

R8: rekord TPN 273 ma GLOBALID `{A5C7088E-A2FE-4898-AE2E-B0A9B420B17D}`,
`GENEZA=sztolnia`, uwagę „zasypana, ale widoczne belkowanie stropu”;
STR-0024 ma kategorię `jaskinia_otwor`. TPN 530/CHZ-0011 ma
`GENEZA=jaskinia/sztolnia`; mieszanej informacji nie należy rozstrzygać
automatycznie na podstawie słowa w nazwie.

Ryzyka danych: największe odległości między pomiarami dotyczą PL-0019
(2490,53 m) i MLZ-0045 (1897,61 m); 11 grup obejmuje obiekty o identycznych
best po zaokrągleniu WGS84 do siedmiu miejsc. Nie dowodzi to duplikatu
encji ani nie wskazuje poprawnego źródła. PBI-083 ma utrwalić ocenę
i brakujące dowody. Nie wykonano weryfikacji terenowej ani nowego pobrania
PIG/TPN; historycznie przeszło 123 testy i Ruff, bez pełnej kampanii mutacji.
