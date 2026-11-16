# Pomiary GNSS i domiary — korekta otrzymana 2026-11-16

[Zestawienie.tsv](Zestawienie.tsv) i [Report.tsv](Report.tsv) są wyciągami
wartości z arkuszy XLS, nie oryginalnym plikiem ani nowym pomiarem terenowym.
Zachowują liczby z pełną precyzją dostarczonego arkusza, teksty, puste pola
i numery wierszy źródłowych (`source_row`). Litery kolumn odpowiadają XLS;
daty zapisane liczbowo w Zestawieniu są numerami seryjnymi Excela (system 1900).
TSV nie zawiera formuł, formatowania ani metadanych pliku. [Oryginalne XLS
i PDF](../../surveys/2026-11-16/README.md) zachowano w archiwum repozytorium.
Wyciąg obejmuje 18 poniższych
punktów. Report przypisuje obliczenia Markowi Jędrzejczakowi (Speleoclub
Wrocław), a zespoły terenowe wymienia osobno przy domiarach.

Korekta zmienia znak uchylenia magnetycznego przy przejściu z azymutu
magnetycznego do siatki PL-1992:

```text
uchylenie = deklinacja - zbieżność południków
azymut PL-1992 = azymut magnetyczny + uchylenie
```

W [poprzednim arkuszu](../2026-10-17/corrected-2026-11-04/20261017%20Tatry.xls)
uchylenie było odejmowane. Nowe rekordy dopisano na końcach historii;
dziesięć wcześniejszych wyników domiarów z 2026-10-17 oznaczono jako
`odrzucony`, dopisując przyczynę i ID pomiaru zastępującego. Ich geometria,
daty i kolejność pozostały zachowane. Źródłem geometrii jest PL-1992:
`input_x` = E (kolumna D), `input_y` = N (kolumna C), `input_srid: 2180`.
Kolumna E podaje wysokość EVRF2007, zapisaną jako `PL-EVRF2007-NH`.
Współrzędne porównawcze J:L nie są nowymi pomiarami.

| Wiersz Zestawienia | Obiekt | Nowy pomiar | Data Zestawienia | Wynik w Report | Best |
| ---: | --- | --- | --- | ---: | --- |
| 3 | MTZ-0018 | m-005 | 2026-10-17 | 36 | nowy |
| 4 | MTZ-0055 | m-004 | 2026-10-17 | 68 | nowy |
| 5 | MTZ-0013 | m-004 | 2026-10-17 | 99 | nowy |
| 6 | MTZ-0027 | m-005 | 2026-10-17 | 130 | nowy |
| 7 | MTW-0013 | m-004 | 2026-10-17 | 161 | nowy |
| 8 | MTW-0076 | m-002 | 2026-10-17 | 193 | nowy |
| 9 | MTW-0010 | m-004 | 2026-10-17 | 225 | nowy |
| 10 | MTW-0016 | m-004 | 2026-10-17 | 256 | nowy |
| 11 | MTW-0050 | m-004 | 2026-10-17 | 267 | nowy |
| 12 | MTW-0008 | m-004 | 2026-10-17 | 298 | nowy |
| 13 | MTW-0036 | m-004 | 2026-10-17 | 315 | nowy |
| 14 | MTW-0054 | m-004 | 2026-10-17 | 332 | nowy |
| 15 | MTZ-0066 | m-004 | 2026-11-12 | 366 | nowy |
| 16 | MTW-0004 | m-003 | 2026-11-12 | 399 | nowy |
| 17 | MTW-0023 | m-003 | 2026-11-12 | 430 | nowy |
| 18 | MTZ-0017 | m-003 | 2025-11-10 | 467 | nowy |
| 19 | MTZ-0016 | m-003 | 2025-11-10 | 502 | nowy |
| 20 | MTZ-0023 | m-003 | 2025-11-10 | 527 | dotychczasowy m-002 |

Kozia II ma w źródle puste ID; odpowiada istniejącemu MTW-0076. Numerację
Koziej i obu Grzęd zachowano zgodnie z wcześniejszym rozstrzygnięciem
[issue #43](https://github.com/dlubom/gps-kataster-obiektow-tatr/issues/43).
`MTW-004` przy Nad Dachem jest skróconym zapisem MTW-0004. Ptasia Studnia
oznacza dolny otwór MTZ-0066.

Niebieska Studnia i Pod Wantą są pomiarami bezpośrednimi GNSS: długość domiaru
wynosi zero, wartości końcowe nie zmieniły się i korekta magnetyczna ich nie
dotyczy. Pozostałe pozycje są wynikami domiarów (`siec_pomiarowa`, wysokość
`other`), nie bezpośrednimi pomiarami GNSS otworów. Deklaracja „dokł. GNSS”
nie rozdziela dokładności poziomej/pionowej ani nie określa błędu końcowego
domiaru; pola dokładności w YAML pozostają `null`. Nowe pomiary zachowują
status `nieweryfikowany`; wybór Best jest osobną decyzją koordynatora
z 2026-11-16, nie poświadczeniem nowej weryfikacji terenowej.

## Ograniczenia źródła

- Piwnica Miętusia, Miętusia Wyżnia i Miętusia: Zestawienie i data obliczenia
  deklinacji podają 2025-11-10, lecz obserwacje GNSS są z 2024-07-20.
  `observed_date` zachowuje datę Zestawienia; odrębnej daty terenowego
  domiaru źródło nie podaje. Nie zastąpiono jej datą otrzymania pliku.
- Miętusia: według autora pomiar statyczny przy braku zasięgu i słabych
  warunkach dał duże błędy po wyrównaniu. Służy jako potwierdzenie obecnej
  lokalizacji. Zgodnie z decyzją koordynatora pozostał Best m-002 i jego
  dotychczasowa polityka auto. W Report wiersz 521 ma etykietę MW1,
  ale współrzędne kotwicy pochodzą z M2 (wiersz 509).
- Wiersze porównania 366, 399 i 430 w Report mają datę odczytu 2026-10-27,
  podczas gdy Zestawienie podaje 2026-11-12. Nie są to daty obserwacji GNSS
  i nie zostały przeniesione do `observed_date` ani `source_date`.
- Nagłówek Report nadal wskazuje projekt 20261017 i datę 2026-10-19, mimo
  późniejszych obserwacji. Nie jest datą publikacji całego zestawu;
  `source_date` pozostaje nieznana.
