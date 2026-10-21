# PR #12 — korekta opisów i bibliografii

## Zakres i plan

Zatwierdzone przez użytkownika 2026-10-20: bibliografia raz w AF (`cave.notes`),
uwagi otworu w AE (`object.notes`), bez oznaczeń Dxxx i powtórzeń w tych opisach;
uzupełnienie odnalezionych źródeł, zachowanie historii pomiarów; commit/push,
CI i odczyt nowej paczki eksportów, bez merge.

Podstawa: `8c18ee573e5224b8f02044d4f4b823459b6cbcd7` na istniejącym PR #12.
Kontrakt eksportu Full pozostaje bez zmian.

1. Osobny, ograniczony zapis korekty opisów: dokładne preimage, dopuszczone
   rekordy i pola, operator `agent:codex`; oryginalne decyzje i receipt D26
   pozostają niezmienione. Odtwarzanie wyłącznie w `check`, bez zgody na replay.
2. Testy ochrony historii, best, referencji, stanu źródłowego i zakresu korekty;
   następnie korekta YAML oraz aktualizacja wyłącznie hashy kontekstu TPN.
3. Walidacja, testy, odczyt eksportów i porównanie wszystkich pomiarów z podstawą.
4. Niezależny przegląd, commit/push, CI dla końcowego SHA i odczyt paczki CI.

## Źródła

- C-1005: J. Nowak, „Z archiwum «J» cz. VIII – Dolina Mułowa”, *Jaskinie*
  85 (2016), s. 28 — opis i plan Jaskini w Kozim Grzbiecie.
  http://jaskinie.org.pl/files/Jaskinie__85_2016.pdf#page=28
- C-1009: ten sam artykuł, s. 27–28 — Jaskinia Lodowa Ponorowa.
  http://jaskinie.org.pl/files/Jaskinie__85_2016.pdf#page=27
- C-1007: F. Filar, „Uzupełnienia z dolinek reglowych”, *Jaskinie* 101
  (2020), s. 31–32 — Okno przy Źródle (opis i plan na s. 32).
  http://jaskinie.org.pl/files/Jaskinie__101_2020.pdf#page=32

Odczytano treść i obrazy odpowiednich stron PDF. Nie odnaleziono niezależnej
publikacji dla C-1006 i C-1008; to wynik przeszukania, nie twierdzenie o jej
nieistnieniu. Istniejące źródła D26 przenoszone są bez zmiany identyfikacji.
Różne metryki historyczne TPN/KKTJ pozostają rozróżnione.

## Weryfikacja

Niezależny strukturalny diff względem podstawy potwierdził 52 zmienione YAML:
wyłącznie `notes`, `updated_at`, `updated_by`. Wszystkie **1938 pomiarów**, **1035
wyborów best**, referencje 2062 encji i 640 decyzji źródłowych pozostają takie
same. W stanie TPN zmieniono wyłącznie `result_hashes`/`result_catalog_hash`.
Pozostałe **2063 pliki data zachowują bajty**, w tym snapshoty i historyczne
changes/decisions/application. Receipt D26 pozostaje bajtowo niezmieniony.

Niezależny readback **10/10 artefaktów** obejmuje SQLite i jego ZIP, CSV,
GeoJSON, GPX, SHP ZIP, metadane, statystyki JSON/Markdown oraz Excel. Odczytano
wszystkie pola historii SQLite i każdą komórkę Best/Full; AE/AF odpowiadają YAML
we wszystkich 1938 wierszach Full. Opisy nie zawierają Dxxx; w poprawionych
opisach jaskiń URL występuje raz, a opisy otworów nie powielają bibliografii.
Wśród 26 nowych Jaskiń 9 ma odnośnik, a 17 informację o nieodnalezieniu
dokumentacji. KKTJ dla istniejącego C-0981 przeniesiono do opisu Jaskini.
Bibliografia w AF naturalnie powtarza się między wierszami różnych pomiarów;
nie jest powielona wewnątrz pojedynczego opisu. Historyczne uzasadnienia
w referencjach i wyborze best zachowano.

Walidacja: 0 błędów, 2133 istniejące ostrzeżenia; TPN check dla bazy
`b98fd3febb400c7ee520046682c1bb16238429ee`: `ready=true`.
Symulacja przyszłego porównania tego samego snapshotu z kandydatem stanu:
640 approve / 395 informational, zero `stale_resolution`, `requires_pr=false`.
To sprawdzenie nie zmienia stanu zaakceptowanego na main.
Ruff format/check, **67 testów Node i 1191 testów Python PASS**. Pełny zbiór
Python odebrano w czterech zakończonych przebiegach: 1159 pozostałych, 30
testów guardów oraz osobno 1 test zachowania historii i 1 test check/replay.
Przerwany wcześniejszy przebieg nie jest podstawą tego odbioru.
Test nowej funkcji najpierw nie przechodził (brak implementacji); po wdrożeniu
potwierdzono także zabicie **2/2 celowanych mutantów**: dopisywanie starych
opisów zamiast zastąpienia oraz zmiana współrzędnej historycznego pomiaru.
Testy obejmują ponowne przeliczenie fałszywych hashy, obce pola/rekordy,
zmianę preimage/operatora/bazy i starego receipt, brak receipt, a także
odrzucenie ponownego plan/apply pierwotnej paczki.

Niezależny przegląd nie znalazł krytycznych ani istotnych usterek. Uzupełniono
wskazaną drobną lukę dokumentacji: check wymaga zachowania przodka
`8c18ee573e5224b8f02044d4f4b823459b6cbcd7`, oprócz baz wcześniejszych guardów.
Nie zmienia to osobnej ścieżki odczytu zaakceptowanego source state.

Szczegółowe logi, skrypty audytu i paczki pozostają w ignorowanym
`build/verification/pr12-notes-20261020/`. Końcowy SHA, wszystkie joby/kroki CI
i ponowny odczyt paczki zbudowanej dla tego SHA zostaną utrwalone w opisie
[PR #12](https://github.com/dlubom/gps-kataster-obiektow-tatr/pull/12) po push,
bez kolejnych commitów wpisujących własne SHA. Brak merge, tagu i release.

## Uporządkowanie trzech rodzajów uwag — 2026-10-21

Podstawa: `87a19510580364f96a85edea69e0099ffc4f9a4d`, ten sam PR #12.
Zlecenie użytkownika: „usuń TPN revision z uwag, zostaw go w plikach
synchronizacji, dodaj brakujące tagi tpn i uporządkuj trzy rodzaje uwag
według proponowanego podziału […] zachowując historię i wybór best”.

Plan realizowany w tej sesji:

- [x] Test reprodukcji braku tagów i technicznych hashy w uwagach; zachowanie
      starego formatu wykonywania paczek do odtwarzania historycznych decyzji.
- [x] Deterministyczna korekta: pomiar — pochodzenie i ograniczenia lokalizacji;
      obiekt — rozpoznanie i stan otworu; jaskinia — aliasy, morfometria,
      literatura. Usunięcie komunikatów importu, poprawa kodowania i języka.
- [x] Osobny receipt i kontrola korekty względem stałej podstawy; stare decyzje,
      snapshoty, receipty i hashe rewizji źródeł pozostają niezmienione.
- [x] Porównanie wszystkich pól poza notes/tags i audytem; pełna bramka,
      kontrola TPN, odczyt eksportów oraz niezależny review.

Wynik commit/push, zdalny SHA, CI i paczka końcowego SHA są utrzymywane w
opisie istniejącego PR #12. Dostawa nie obejmuje merge, tagu ani release.

Zmiany notes/tags nie stanowią nowych decyzji o tożsamości, pomiarach lub
best. Kontrakt synchronizacji jest hashowanym historycznym wejściem;
zachowujemy jego bajty. Zaktualizowane zasady redakcyjne opisuje specyfikacja
i instrukcja operatora, a źródłowe wersje treści pozostają w Git/audycie.

### Odbiór korekty

Receipt: [PBI-101-editorial-correction.json](PBI-101-editorial-correction.json).
Deterministyczne reguły i kontrola odtwarzania są w `tpn_editorial_notes.py`
i `tpn_editorial_correction.py`; receipt nie przyjmuje dowolnych patchy danych.
Kontrola wymaga zachowania przodka `87a1951…`. Starsze guardy sprawdzają
swoje historyczne bajty, a następnie osobna kontrola porównuje cały rzeczywisty
wynik z odtworzoną korektą i sprawdza niezmienność pięciu dawnych dokumentów
wejściowych. Oryginalne plan/apply nadal odrzuca replay starej paczki.

Niezależny strukturalny diff potwierdził:

- Zmieniono notes/audyt wszystkich 1035 Obiektów i 1027 Jaskiń; 1935 pomiarów
  ma poprawioną treść notes. Wszystkie 1938 pomiarów zachowują pozostałe pola,
  kolejność i identyfikatory; jedyny wyjątek poza notes to 62 dodania tagu `tpn`.
- Wszystkie 1066 pomiarów TPN mają tag `tpn`; w uwagach nie ma `TPN revision`
  ani powielonego `LAST_EDITED_DATE`. Wyjaśnienie nieznanej daty terenowej
  pozostaje przy 62 nowych ustaleniach TPN.
- Wszystkie 1035 struktur best i 3617 referencji są identyczne z podstawą.
  W source state zmieniono wyłącznie `result_hashes` i `result_catalog_hash`;
  640 rozstrzygnięć, hashe rewizji, powiązania i historia pozostają te same.
- Pozostałe 51 plików data, pięć dawnych dokumentów wejściowych i kontrakt
  zachowują bajty. Nie dodano nowych źródeł ani rozstrzygnięć tożsamości.
- Zastrzeżenia lokalizacji pozostają przy pomiarach; uwagi o zasypaniu otworu
  są przy obiekcie, o morfometrii i literaturze przy jaskini. Dwie cytacje
  Jaskinie 118–119/2025 i 116–117/2024 przeniesiono z dawnych notes obiektów,
  bez nowego badania bibliograficznego. Starsze i nowsze metryki TPN oraz
  źródłowe zera pozostają rozróżnione. Poprawiono 25 zapisów Chochołowskiej.

Lokalny readback 10/10 artefaktów: wszystkie tabele i pola SQLite, ZIP SQLite,
CSV, GeoJSON, GPX, wszystkie rekordy SHP, metadane, statystyki i Excel
Best/Full (121983 sprawdzone komórki). Integralność i FK poprawne.

Testy najpierw odtworzyły brak tagu/hash w notes i błędne przeniesienie źródła
morfometrii. Dwa celowane mutanty zabite: zmiana historycznej współrzędnej
oraz pominięcie kontroli dokumentów historycznych. Niezależny review
odtworzył lukę drugiego typu; dodano kontrolę bieżących bajtów manifestu
PBI-099 i remaining-26 oraz dwa testy RED→GREEN. Po poprawce brak dalszych
krytycznych/istotnych uwag review. Test chronionych best uwzględnia wyłącznie
zatwierdzoną redakcję notes, zachowując porównanie wszystkich pozostałych pól,
ostrzeżenie „unknown GNSS”, źródłowy preimage i dokładny hash nowego pliku.

Lokalnie: Ruff format/check, 67 testów Node, pięć testów dokumentacji, walidacja
bez błędów (2133 istniejące ostrzeżenia), kontrola TPN `ready=true`. Pierwszy
pełny przebieg Python: 1278 PASS / 1 FAIL — stare porównanie całych notes
chronionego pomiaru. Po opisanej aktualizacji testu cały jego zestaw 54/54
PASS; pozostałe testy przeszły w pełnym przebiegu. Nowy zestaw korekty:
18/18 PASS. Wynik wszystkich 1279 testów końcowego SHA jest wskazywany w
opisie PR dopiero po zakończeniu CI; lokalnego pierwszego FAIL nie
przedstawiamy jako zielonego przebiegu.
Logi i niezależne skrypty porównań: ignorowany
`build/verification/pr12-notes-rethink-20261021/`.
