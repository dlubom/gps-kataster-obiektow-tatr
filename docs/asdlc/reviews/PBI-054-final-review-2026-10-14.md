# Niezależny review PBI-054 — 2026-10-14

Baza i końcowy stan produktu:
`336e9bbfa860b96361678776f641bb925e923d5c`, branch `codex/review-remediation`.
Zakres: diff całej serii względem
`a3dd1a671d3d93cd6958242fc68ddcf1d37cf846`, specyfikacja, R01–R13,
regresje i limity PBI-055–067. Oddzielny agent tylko do odczytu;
właściciel PBI niezależnie ponowił oba publiczne przypadki. Kod produktu,
testy, schema, konfiguracja i dane nie zostały zmienione w tym review.

Werdykt: **nie rekomenduję zamknięcia PBI-054 ani merge przed naprawami
PBI-068/069 i ponowieniem końcowego odbioru**. Brak nowego P1;
dwa nowe, odtworzone P2 poniżej. Pozytywna pełna bramka obecnego katalogu
nie obejmuje wszystkich błędnych/szerszych legalnych wejść.

## Findings

1. **P2 — dopasowanie TPN pomija dalsze typed numery jaskini.**
   `src/gps_kataster_obiektow_tatr/tpn_staging.py:963–965` i helper
   `_first_external_ref_id:1106`. Zwykły review TPN dopisuje numer
   inwentarzowy do legalnej historii ref. Następny rekord wskazujący
   drugą ref, z nowym GLOBALID i inną nazwą, daje `new` oraz propozycję
   nowego obiektu/jaskini. Odwrócenie wyłącznie kolejności ref daje
   `matched` po `nr_inwent`. Akceptacja propozycji new materializuje
   duplikat: 2 obiekty/2 jaskinie, zero ERROR, dwa warningi braku
   dokładności. Osobna karta: [PBI-068](../verification/PBI-068.md).
2. **P2 — nieparsowalny URL załącznika przerywa publiczną walidację.**
   `src/gps_kataster_obiektow_tatr/validator.py:995–997`.
   `https://[`, `http://[abc]` i NFKC-invalid netloc przechodzą schema,
   a `urlparse` rzuca nieobsłużony `ValueError`. `validate_data_dir`
   i `apply_review_decisions` nie zwracają oczekiwanej diagnostyki
   `ATTACHMENT_URL_INVALID`. Brak zmiany finalnych bajtów, bez wykazanego
   obejścia blokady zapisu. Osobna karta: [PBI-069](../verification/PBI-069.md).

[Trwała reprodukcja](../verification/PBI-054-final-discoveries.py) używa
wyłącznie danych tymczasowych; asercje wymagają obecnych niepowodzeń.
Wyniki w [rejestrze artefaktów](../verification/PBI-054-final-artifacts.json).

## Ocena jawnych limitów dotychczasowych kampanii

| PBI | Ocena limitów przez niezależny review |
|---|---|
| 059 | Brak całego rows/proza diagnostyk: brak dowodu utraty aktywnej blokady; schema/indeksy nadal chronią błędny raport. |
| 060 | Dalsze diagnostyki/indeksy/opisy po wcześniejszym ERROR: krótszy raport, bez utraty blokady całej partii. |
| 061 | Strict/format/current fields: poprawne w obecnym modelu DBF, bez dowodu usterki. |
| 062 | Proza i prefilter nazwy/kategorii: ograniczona ocena względem invariants obecnego modelu, bez twierdzenia o ekwiwalencji dowolnego wejścia. |
| 063 | Defaults normalizowane/metadane błędów nieosiągalne po publicznej walidacji: nieblokujące dla bieżącego publicznego builda. |
| 064 | Publiczne atrybuty/locale/malformed ring/default tolerancji kompensowany wrapperem: jawne granice asercji, bez odtworzonej usterki. |
| 065 | PIG ID w issue odrzuconego wejścia/invalid timestamp/locale: limity diagnostyk, bez wykazanej utraty legalnej treści źródła. |
| 066 | Nazwy dodatkowo pokryte 062, valid catalog/defaults/standalone cave_id: dotychczasowe limity nieblokujące, lecz kilka typed NR ujawniło osobny P2 068. |
| 067 | Proza/malformed schema branch: limity nieblokujące; schema-valid malformed URL ujawnił osobny P2 069. |

Nie jest to deklaracja ekwiwalencji wszystkich survivors ani 100% pokrycia.
Pełna nowa kampania stanowi osobny dowód; jej audit i wynik końcowy
zostaną dopisane po faktycznym ukończeniu.

Niezależne regresje reviewera:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider \
  tests/test_review_validation.py tests/test_review_writes.py \
  tests/test_typed_source_matching.py tests/test_validator_references.py \
  tests/test_dbf_numeric.py tests/test_yaml_policy.py tests/test_data_directories.py
```

Exit 0, **1052 passed in 110.96s**. Przenośny helper nowych findings
ponowiono także po dodaniu mocnych asercji, exit 0.

## Audit helperów dowodowych — w toku

Capture sprawdza dokładny komplet 17 ścieżek z konfiguracji, zestaw
generated AST ID, raw metadata, mapowanie, czasy i każdy diff. Replay
ma identyczny union testów clean/forced-fail, zapis actual pytest 0/1
i wykrycie `MutmutProgrammaticFailException`; ledger wymaga wszystkich
i wyłącznie pending/timeout, z fingerprint przed/po. Zauważoną lukę P3
tożsamości runtime poprawiono przed pierwszym capture/replay: Python,
ścieżka interpretera oraz wersje siedmiu użytych bibliotek są porównywane
i włączone do fingerprint. Ta korekta dotyczy wyłącznie helperów dowodów.
Delta review helperów i kart 068/069: approve, brak otwartych uwag helperów.
Sześć negatywnych syntetycznych sond odrzuca drift Python, pyshp,
konfiguracji, dodatkowego instrumented source, test mapping i duration
mapping; dwie kontrole pozytywne przechodzą, exit 0. To próby guardów,
nie wykonanie mutacji. Kontrole clean/forced-fail na prawdziwej generacji
i końcowy audit jej wyników nadal oczekują na kampanię.

Po ENOSPC całą pierwszą generację odrzucono. Niezależny audit
`PBI-054-final-run.py` / capture / replay: **approve, 19 sond PASS,
exit 0**, bez otwartych uwag narzędziowych. Sondy obejmują zachowanie
parametrów/pluginów/mapowania pytest i środowiska TMPDIR/cache;
real-test exit 1, low-space/disk_usage/mkdtemp/runner/cleanup → 35;
ENOSPC w chain/context/ExceptionGroup/cyklu; post-call spadek miejsca;
forced-control abort 35 mimo braku markera i oryginalny programmatic-fail
po cleanup; parent cleanup dokładnego PID po wait (42 nie usuwa 420);
replay marker refusal i sprzątanie TMPDIR przy timeout bez wyniku.
Rzeczywisty zwykły pytest StatsCollector zachował mapowanie/duration,
a probe widział MutmutProgrammaticFailException bez invalid markera.
Faktyczny celowy pytest exit 1 jest sukcesem kontroli forced-fail.

Granica ochrony: bufor miejsca, pre/post-check i probe odrzucają widoczne
awarie dysku; nie deklarujemy wszechwiedzącego rozpoznawania awarii
całkowicie stłumionej przez produkt. Raw 35/marker zawsze odrzuca generację.
Po wait parent sprząta także temp workerów zakończonych SIGXCPU/SIGKILL;
nie zmienia oryginalnego timeout_checker ani surowych timeoutów mutmut.
Dokładne SHA helperów i surowy stdout audytu są w rejestrze artefaktów.
