# PBI-054 — analiza końcowej kampanii Linux 2026-10-14

PBI-054 pozostaje **zablokowane** przez trzy odtworzone P2: 068/069/074.
Wykonano pełną nową kampanię 17 modułów: 10193 kontrolowane przebiegi i 25
pustych mapowań. 10218 unikalnych ID: 8472 killed / 1721 survived / 25 no tests.
Bez końcowych pending, timeout ani błędów narzędzia. 245 krytycznych referencji
z 058–067 odpowiada 243 unikalnym ID; wszystkie 243 killed. Nie jest to 100%
pokrycia ani dowód poprawności dla wszystkich legalnych/błędnych wejść.

Źródło: [pełny ledger](PBI-054-final-mutations.json), [artefakty](PBI-054-final-artifacts.json),
[przenośny audit](PBI-054-audit-ledger.py), [niezależny review](../reviews/PBI-054-final-review-2026-10-14.md).
Ledger zawiera wszystkie surowe metadata, diffy i outcomes, mapowanie i czasy,
10193 wyniki subprocess i 16 par kontrolnych. Każda kontrola: clean pytest 0,
forced pytest 1 z obserwowanym programmatic fail, identyczny union 1595 testów.
Kopie powtarzających się list testów zredukowano dopiero po ich dokładnym
sprawdzeniu; rekonstrukcja przez mapped_function i sort(duration,testID).

## Pochodzenie i bilans

Jedna generacja na GitHub Actions 38566650123, input commit
97428eb9950b0fc8bc42b137c01d6d20525e4161. Python 3.12.13 / x64 / Ubuntu 24.04,
zamrożone dependencies, 17 ścieżek dokładnie z pyproject. Oficjalne API
mutmut generowało instrumentację/mapowanie; żadnego wyniku CLI nie
zaliczono. 16 rozłącznych subsetów sorted-ID index::16, osobny subprocess
każdego ID, przypisany mu limit ceil((sum durations+1)*15) i osobny TMPDIR.
Collector sprawdził pełne pokrycie ID bez duplikatów oraz runtime,
RunID/attempt/source SHA/archive SHA/capture SHA/fingerprint. Wszystkie 18 jobów
oraz wymagane kroki i Complete job zakończone sukcesem. Trwały JSON koryguje wyłącznie
starą etykietę CLI i dodaje provenance; wyniki, diffy i controls są niezmienione.
Raw ledger SHA: 84a8df61bf0966ec6cbec0ea2567de78e9317c4eb6e148759e01cdb054060243.

Fingerprint: 66f62c6c2a9ea3edd6346923085837cfc4dba7ca0ae3a4b3e83982b4f42a02b8.
105 input files zgodne ze źródłem (103 hashe + pyproject/lock w archiwum).
Archiwum SHA: e189c75d11a9dbff5d99316cbe1a4037a31322939e0b7124df194456a8f96e72.
Obie przerwane generacje Mac i 631 częściowych JSON replay są wyłączone,
nie dodane do wyniku. Zachowano je w zweryfikowanych archiwach; aktualna
kampania nie potrzebuje tych lokalnych katalogów do kontynuacji.

| Moduł | Killed | Survived | No tests | Razem |
|---|---:|---:|---:|---:|
| archive_metadata | 60 | 10 | 0 | 70 |
| best_measurement | 106 | 1 | 0 | 107 |
| best_measurements_export | 685 | 287 | 10 | 982 |
| build_db | 522 | 35 | 0 | 557 |
| coordinates | 61 | 0 | 0 | 61 |
| data_loader | 141 | 14 | 0 | 155 |
| dbf_numeric | 17 | 1 | 0 | 18 |
| numeric | 52 | 2 | 0 | 54 |
| pig_staging | 684 | 220 | 0 | 904 |
| prefix_resolver | 292 | 13 | 0 | 305 |
| review_writer | 148 | 43 | 0 | 191 |
| source_profile | 201 | 142 | 15 | 358 |
| staging_review | 2763 | 459 | 0 | 3222 |
| tpn_staging | 1633 | 353 | 0 | 1986 |
| validator | 1027 | 117 | 0 | 1144 |
| yaml_loader | 61 | 24 | 0 | 85 |
| yaml_paths | 19 | 0 | 0 | 19 |

## Interpretacja i znane zadania

25 no-tests nie wykonano: 10 best_measurements_export._utc_timestamp,
5 source_profile._format_duplicate_example i 10 _format_row_numbers.
Publiczny export bez generated_at może wywołać UTC helper; to brak testów,
nie dead code. Dawne exit_code_for_issues/date_part/resolve_prefix mają
teraz mapowanie, którego brak nie jest już aktualnym ograniczeniem.

Trzy P2 odtworzono na oryginale: kolejne typed numery jaskini zmieniają
matching i pozwalają zapisać duplikat (068), malformed URL powoduje
ValueError preflight (069), skrajne schema-valid timestampy powodują
OverflowError w walidacji/buildzie/review (074). Podane błędne wejścia nie
zmieniły bajtów; przy 068 zaakceptowana propozycja tworzy duplikat bez ERROR.
Dla 074 wymagany jest poprawny best i obsługa legalnych chwil, bez arbitralnej
nowej granicy dat, silent drop lub min fallback. Odrzucenie ERROR było propozycją
reviewera, nie wymaganiem dowiedzionym ze specyfikacji.

Luki regresji P3 mają osobne karty 070–073/075–077: eksport/profil,
alokacja ID, pełny wiersz relacji SQLite, pojedyncze wymiary ref,
audit/liczniki/ERROR reports, nazwy/daty/kontynuacja stagingu. Nie zaczęto
ich implementacji. Ocalenie mutanta nie dowodzi błędu oryginału.
Każdy dokładny diff i jego status pozostają w ledgerze.

[Wąskie granice rodzin](../reviews/PBI-054-remaining-family-review.md)
rozróżniają reprezentację JSON od byte equivalence, locale/codec alias,
normalized defaults, schema/invariants i rzeczywiste zaniki treści.
Korekta historycznego allow_missing: caller NIE przekazuje jawnie False;
wrapper mutmut wiąże oryginalny default i przekazuje go mutantowi. Zmiany
sygnatur mogą być zamaskowane przez instrumentację. Nie są globalnymi
ekwiwalentami źródła. Spec/core gwarancje oceniać także z regresji i
niezależnego przeglądu, nie tylko procentu killed.

[Audit 100 diffów sharda13](PBI-054-linux-shard13-review.json) zachowuje
wcześniejszą ocenę cząstkową. Końcowa [ocena wszystkich 1746 ID](PBI-054-nonkilled-review.json)
ma dokładne current status, diff/SHA, źródłowy kontekst, konkretny efekt,
wąską granicę i referencję do rodziny/PBI. SHA:
4a6ea5f6595f459834ba304c040e6c55312075e22abeeb7e9e6c47a946881fea.
530 uzasadnień użyto wyłącznie przy exact diff match; nie przeniesiono
statusów poprzednich generacji. 299 ma jawne reguły dokładnych granic,
pozostałe konkretną ocenę pola/gałęzi/prezentacji. Brak nieprzypisanych ID.

[Końcowy niezależny audit](../reviews/PBI-054-linux-final-audit.md):
**approve checkpointu dowodów; PBI-054 pozostaje blocked**. Nie wykazano
kolejnego błędu oryginalnego produktu. Jawne limity obejmują reprezentację,
locale, diagnostyki po wcześniejszym błędzie, prywatne helpery i publiczne
custom schema/resolver forwarding poza stałą konfiguracją V1. Nie są
zbiorczą ekwiwalencją. Doprecyzowano odbiór 070/072/075/076/077, bez napraw.

Odtworzenie kontroli tożsamości ledger i wszystkich ocen (CPython3.12,
jak w kampanii, dla dokładnych sum floating point):

```bash
UV_CACHE_DIR=build/verification/uv-cache uv run --frozen --no-sync --python 3.12.13 python \
  docs/asdlc/verification/PBI-054-audit-ledger.py \
  --ledger docs/asdlc/verification/PBI-054-final-mutations.json \
  --review docs/asdlc/verification/PBI-054-nonkilled-review.json
```

Właściciel i reviewer: exit0, 1746 ocen zgodnych. Audit sprawdza integralność;
semantyczny werdykt pochodzi z osobnego niezależnego review. Pierwsze
wywołanie właściciela przez systemowy Python3.9 miało inną semantykę sum,
więc go nie zaliczono; helper jawnie odrzuca obcy interpreter. Wszystkie
wyniki produktu/mutacji pochodzą ze wskazanego pinned runtime3.12.13.
