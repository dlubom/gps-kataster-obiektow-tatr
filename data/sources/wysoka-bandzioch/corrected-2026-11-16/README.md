# Wysoka i Bańdzioch — korekta obliczeń magnetycznych

[measurements.json](measurements.json) zachowuje przekazane współrzędne
końcowe, daty, opis dokładności GNSS i długości domiarów. To wyciąg danych
otrzymanych 2026-11-16, nie oryginalny raport ani nowe obserwacje terenowe.
Odpowiada wierszom 23–24 Zestawienia w [archiwalnym XLS i PDF](../../surveys/2026-11-16/README.md).
Źródło w katalogu pozostaje `inne` / `unknown:gnss`, a nowe pomiary mają
status `nieweryfikowany`.

| Obiekt | Otwór | Nowy pomiar i Best | Poprzedni Best |
| --- | --- | --- | --- |
| KSW-0189 | Wysoka, główny otwór W7-0 | m-004 | m-003 |
| KSZ-0112 | Bańdzioch Kominiarski, dolny | m-002 | m-001 |

Nowe pomiary wskazano ręcznie jako Best decyzją Dariusza Lubomskiego
z 2026-11-16. Poprzednie Best oznaczono jako `odrzucony` z powodu błędnej
poprawki magnetycznej; ich geometrię, daty i kolejność zachowano.
Współrzędne źródłowe to EPSG:2180: `input_x` = easting, `input_y` = northing.
Wysokości źródło określa jako EVRF2007 (`PL-EVRF2007-NH`). Wyniki pochodzą
z GNSS i domiarów, dlatego metoda to `siec_pomiarowa`, a źródło wysokości
`other`. Nie znamy sprzętu ani dokładności końcowych punktów osobno
w poziomie i pionie. Deklarowane „dokł. GNSS < 0,10 m” pozostaje opisem.

Dostępne są końcowe wartości, bez obserwacji domiarów i ich obliczeń.
Można skontrolować przepisanie współrzędnych i przypisanie do otworów,
ale nie niezależnie odtworzyć korektę tych dwóch ciągów.

Cztery pozycje zależne KSW-0264–KSW-0267 przeliczono z nową kotwicą
KSW-0189/m-004 na polecenie koordynatora. Ich m-002 zastępują w Best dawne
m-001, oznaczone jako `odrzucony` ze względu na błędną kotwicę; obie wersje
pozostają w historii. Nie wolno traktować tych pozycji
jako niezależnych fixów. [Pochodzenie nowych wyników](../../jktz/wysoka-entrances-2026-11-16/README.md).
