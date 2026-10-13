# PBI-065 — analiza 14 ocaleń finalnej kampanii

Zakres: 263 ID siedmiu funkcji. Każdy ID i diff, surowy kod oraz wynik
powtórki jest w `PBI-065-mutations.json`. Nie deklarujemy 100% pokrycia
ani globalnej ekwiwalencji. Wskazane 31 utrat treści i dodatkowy fallback
`Z` (32 ID) są killed. Ocalenia pozostają do oceny PBI-054.

- `staging_review.x__append_unique_dicts__mutmut_5`: continue→break dla
  elementu niebędącego dict. Legalne listy ref są sprawdzane schematem
  przed scalaniem; taki element blokuje całą transakcję wcześniej. Nie
  jest to utrata legalnej ref w testowanej publicznej ścieżce ani globalna
  ekwiwalencja dla dowolnych prywatnych wejść helpera.
- `pig_staging.x__parse_pig_point__mutmut_22/23/24`: zmiana komunikatu
  wyjątku przy brakujących współrzędnych. Nie zmienia odrzucenia rekordu,
  kodu issue ani zachowania poprawnej treści staging→YAML. Literalny tekst
  diagnostyki błędnego wejścia nie jest objęty tym odbiorem; brak globalnej
  ekwiwalencji tekstowej (22 usuwa objaśnienie).
- `pig_staging.x__parse_pig_point__mutmut_29/46/70/81`: utrata pig_id
  w issue dla niepoprawnych/brakujących współrzędnych lub błędu konwersji.
  To konkretna pozostała luka asercji diagnostyk odrzuconego wejścia,
  a nie ekwiwalent. Poprawna ścieżka i ostrzeżenie fallbacku roku mają
  sprawdzaną proweniencję; te mutacje nadal wymagają oceny PBI-054.
- `pig_staging.x__parse_pig_point__mutmut_107/108/109`: dekoracja albo
  zmiana wielkości liter opisu fallbacku roku. Zachowane są kod, severity,
  record_number, pig_id, treść wyjaśnienia i wynik obu dat. Nie obiecujemy
  identycznego tekstu dla każdej mutacji komunikatu.
- `pig_staging.x__date_part__mutmut_7/8`: brak zamiany Z na +00:00.
  Przypięty Python 3.12.13 sam akceptuje końcowe Z w fromisoformat; oba
  publiczne przypadki (+02:00 i Z) zachowują oczekiwaną datę. Ekwiwalencja
  tylko w badanym środowisku i dla tych znaczników, bez uogólnienia na
  inny parser/runtime. Mutant 9 psujący samą zamianę jest killed.
- `pig_staging.x__date_part__mutmut_10`: datetime.now(None) zamiast UTC
  przy niepoprawnym generated_at. Ścieżka z błędnym timestampem i inną
  datą lokalną/UTC nie jest sprawdzana w fixture; to limit, nie ekwiwalent.
  Odbiór dotyczy brakującego roku przy poprawnych ISO timestampach.

Produkt i katalog nie zmieniły się. Te ID dotyczą mutowanego kodu,
nie dowodzą występowania błędu w oryginalnym importerze. Pełna kampania
wszystkich modułów oraz końcowa ocena limitów należą do PBI-054.
