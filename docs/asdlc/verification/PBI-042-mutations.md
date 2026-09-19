# PBI-042 — analiza ocalałych mutantów

Wynik łączny: **1336 unikalnych mutantów, 862 zabite, 474 ocalałe**,
0 timeoutów, awarii i mutantów bez testów w zaliczonym zakresie.
To agregacja pierwszej poprawnej kampanii i dwóch powtórek, nie pojedynczy przebieg.
Szczegóły komend i ograniczeń: [log PBI-042](PBI-042.md).

Pełny identyfikator: `gps_kataster_obiektow_tatr.` + funkcja + `__mutmut_N`.
Zakresy numerów obejmują dokładnie ocalałe identyfikatory. Nie są wyłączeniami z mutmut.

| Funkcja | N | Analiza |
|---|---|---|
| `coordinates.x_coordinate_consistency_error_m` | 3–4 | Usunięcie pojedynczego sprawdzenia cache przed odejmowaniem; sprawdzenie skończoności wyniku nadal odrzuca złą wartość. Redundantna bariera, bez przepuszczenia danych. |
| `numeric.x_nonfinite_paths` | 1 | Domyślny path maskowany przez trampoline mutmut, które przekazuje jawny argument. Test sprawdza rzeczywiste ścieżki zagnieżdżonych pól. |
| `numeric.x_parse_decimal` | 20 | Identyczny AST po normalizacji literału NBSP; parsowanie spacji/przecinka objęte testem. |
| `pig_staging.x__parse_pig_point` | 22–24, 29, 46, 70, 81, 89–109, 116 | 22–24: tekst braku współrzędnej; 29/46/70/81: identyfikator w diagnostyce, numer wiersza/pole i odrzucenie zachowane; 89–116: wcześniejsze luki daty źródłowej/fallbacku i jego komunikatów. Nowe reguły liczb i kod/severity błędu objęte regresjami. |
| `pig_staging.x_write_staging_files` | 1, 3, 5, 9–10, 13–14, 16, 18, 21–23, 26–27, 30–31, 34, 36, 38, 41 | Stare luki mkdir/nazw plików (1/3/5/9/10/13/14), lokalne kodowanie lub kosmetyka JSON/Markdown. allow_nan=None jest falsey i nadal odrzuca NaN. Zmiana na True/usunięcie guarda zabite. |
| `source_profile.x__profile_numeric_column` | 21 | Nazwa kolumny w obiekcie metadanych; numeric/invalid/missing oraz zakres liczb nadal poprawne. |
| `source_profile.x_write_report_files` | 16, 18, 21–23, 26–27, 33–34, 37, 39, 41, 43, 47 | Formatowanie/escaping JSON i Markdown, kodowanie lub data raportu Markdown. allow_nan=None nadal odrzuca NaN; True/usunięcie guarda zabite. |
| `staging_review.x_write_review_report_files` | 10, 14, 16, 18, 21–23, 26–27, 30–31, 34, 36, 38, 41 | Case nazw plików na macOS, kodowanie, formatowanie i escaping; allow_nan=None nadal blokuje NaN, usunięcie/True zabite. |
| `tpn_staging.x__load_existing_candidates` | 7–21, 23–102 | Cała grupa po nowym guardzie: wcześniejsza konstrukcja/metadane kandydatów. Brak dodatniego testu dopasowania przez współrzędne rzeczywistego katalogu YAML (m.in. 42/50/51/59/60/81–88). Guard nonfinite ma zabite mutanty; niezależnie przejrzano AST. |
| `tpn_staging.x__load_pig_staging_candidates` | 6, 8, 18, 20, 29, 31, 41, 44–45, 48, 52–54, 66–67, 78–94, 96–97, 100–101, 104, 106 | 8 równoważne UTF-8, 6 kodowanie środowiska; pozostałe stare luki struktury, referencji, nazw, współrzędnych dopasowania i metadanych po nowym guardzie. Guard nonfinite ma zabite mutanty; niezależnie przejrzano AST. |
| `tpn_staging.x__parse_tpn_point` | 16–18, 58–59, 71–74, 82–83 | 16–18: tekst braku współrzędnej; 58/59/71/72: identyfikatory w diagnostyce projekcji, numer/powód i odmowa zachowane; 73/74/82/83: stare luki dat źródłowych. Finite/optional-null i kod/severity błędu są chronione. |
| `tpn_staging.x_build_tpn_staging` | 41–46, 61–94, 112, 114, 126, 128–129, 135–139, 147–155, 157–160, 169, 172–192, 195, 199–200, 209–212, 214–215, 217, 223–224, 226, 229, 232–234, 238, 248–262, 271–272, 281–282, 285, 294–297, 299–300, 306–307, 310–311 | Stare luki nazw/braku GLOBALID, matching/unresolved, ostrzeżeń odległości, metadanych dopasowania/propozycji, numeracji i raportu. Niezależna analiza review: guard finite nie jest obchodzony; mutacje 50/51/97–100/109 zabite po dodaniu dwóch wierszy i kontroli proweniencji. |
| `tpn_staging.x_write_staging_files` | 1, 3, 5, 9–10, 13–14, 16, 18, 21–23, 26–27, 30–31, 34, 36, 38, 41 | Jak PIG writer: istniejące luki mkdir/nazw plików oraz kosmetyka/encoding. Guard JSON zabity dla True/usunięcia; None jest równoważne False. |
| `validator.x__validate_object_measurements` | 2, 9, 11–13, 18–19, 26–27, 29–31, 35, 46, 68–69, 73–74, 88–91, 96–115 | Stare komunikaty/ostrzeżenia accuracy/source_ref, lokalizacji i tolerancji. 46/68: break zamiast continue ogranicza dalszą diagnostykę już błędnego rekordu, ale zapis nadal zablokowany. Mutacje nowego COORDINATE_INVALID (57–67) zabite w retry. |
| `validator.x__validate_prefix_matches_best_measurement` | 3–4, 6–25, 27, 31, 33, 36–37, 40–52 | Stare luki ostrzeżenia OBJECT_PREFIX_MISMATCH, metadanych oraz równoważne operacje split dla poprawnego ID. Zmiany te nie obchodzą NON_FINITE_NUMBER/COORDINATE_INVALID. Zapisane do pełnej kampanii PBI-054 i weryfikacji prefixów PBI-044/052. |
| `validator.x_validate_dataset` | 8, 16–18, 21–23, 26–28, 32, 45 | 8: niestandardowy schema_dir; 16–28: etykiety typów ID; 32: metadane etykiety; 45: pominięcie dodatkowego filtra obiektów, lecz NON_FINITE_NUMBER i helper współrzędnych nadal blokują zapis. |

Nie deklarujemy 100% pokrycia. Luki poza nową gwarancją są jawne:
daty i metadane stagingu, dodatnie dopasowanie kandydatów, ostrzeżenia walidatora,
portability kodowania/case i nazwy raportów wymagają pełnego przeglądu PBI-054.
Nie zmieniono źródłowego katalogu ani reguł dopasowania w celu zabicia tych mutantów.
Nowe guardy skończoności, odrzucenie punktu, ochrona JSON i obsługa Infinity
w numerze wiersza mają zabite mutacje naruszające te gwarancje.
