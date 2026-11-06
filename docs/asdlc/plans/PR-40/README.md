# PR #40 — kolejne uproszczenia

Ten katalog jest punktem startu po wyczyszczeniu kontekstu. Zawiera zlecenia
dalszych prac nad [PR #40](https://github.com/dlubom/gps-kataster-obiektow-tatr/pull/40),
bez konieczności odtwarzania rozmowy. Przygotowanie kart nie oznacza wykonania
zadań. Realizuj jedną kartę wskazaną przez użytkownika i zakończ po jej odbiorze.

## Jak rozpocząć

1. Przeczytaj repozytoryjne [AGENTS.md](../../../../AGENTS.md) i sprawdź aktualny Git/PR.
2. Przeczytaj [specyfikację serii](spec.md), [projekt](design.md) oraz
   [procedurę wykonania i odbioru](development.md).
3. Wybierz wskazaną kartę z tabeli. Jej sekcje **Spec**, **Design** i
   **Development** określają zakres, miejsce zmiany i dowód zakończenia.
4. Przed kodowaniem potwierdź zależności w kodzie; status dokumentu nie zastępuje Git/CI.

## Numeracja i stan

Wcześniejsza lista w rozmowie nazywała kontrolę katalogów U02, a fazy U03.
Opublikowane commity wdrożyły fazy jako **U02**. Zachowujemy numerację Git:
**U03 oznacza teraz kompletność wejścia**, a dawnych faz nie implementujemy ponownie.
U01 obejmuje też neutralne deklaracje pól i brak dziedziczenia historii z Best;
nie są to kolejne osobne zadania.

Ta tabela jest jedynym rejestrem statusów tej serii. `gotowe` oznacza gotową
kartę do podjęcia na polecenie użytkownika; `oczekuje` — niezakończone zależności.
`w odbiorze` oznacza wdrożenie lokalne oczekujące na zakończone CI/dostarczenie.
Kolejność tabeli jest zalecana; zależności w ostatniej kolumnie są obowiązkowe.

| ID | Zlecenie | Status | Zależności |
|---|---|---|---|
| U01 | Wspólne, niezmienne `ExportData` | wykonane | commit `df82738d` |
| U02 | Granice źródła, propozycji, SQL i historii | wykonane | U01; `eb7804e1`, poprawka `c0fbfc90` |
| [U03](tasks/U03-input-completeness.md) | Komplet wymaganych katalogów wejściowych | wykonane | U02; `80123268`, odbiór w karcie |
| [U04](tasks/U04-canonical-proposals.md) | Kanoniczny model zmian i adapter legacy/staging | wykonane | U03; `6121b570`, odbiór w karcie |
| [U05](tasks/U05-spatial-read-model.md) | Grupowanie GPX z geografii policzonej w SQL | wykonane | U01, U02; `4bc02341`, odbiór w karcie |
| [U06](tasks/U06-write-result.md) | Writer zwraca rzeczywiście zmienione pliki | wykonane | U04; `c4f4cb43`, odbiór w karcie |
| [U07](tasks/U07-production-path-tests.md) | Testy przez produkcyjne wejścia i kanoniczne fixtures | wykonane | U03, U04, U06; `caf55948`, odbiór w karcie |
| [U08](tasks/U08-shared-helpers.md) | Wspólne parsowanie i formatowanie raportów | wykonane | U02; `9c615d0a`, odbiór w karcie |
| [U09](tasks/U09-id-allocation.md) | Jeden mechanizm przydzielania kolejnych ID | wykonane | U04, U08; `487375c7`, odbiór w karcie |
| [U10](tasks/U10-artifacts-and-cli.md) | Jeden zestaw artefaktów i wspólne elementy CLI | wykonane | U05, U07, U08; `478365a1`, odbiór w karcie |
| [U11](tasks/U11-ci-setup.md) | Wspólne przygotowanie runtime w CI | wykonane | U10; `59741d25`, odbiór i ograniczenie mutation w karcie |

Zadania U03–U11 są podzadaniami PBI-119; nie zajmują numerów nowych PBI.
Serię U01–U11 zakończono. Dalsze usprawnienia wymagają osobnego zakresu.

Nowe zlecenie z 2026-11-06 rozpisano jako
[U12–U17: wycofanie dawnych ścieżek i ochrona ID](next/README.md).
Ten osobny indeks posiada ich statusy i kontrakt; obejmuje także issue #33.
Przygotowanie planu nie oznacza rozpoczęcia implementacji.

## Zweryfikowany punkt odniesienia U01/U02

Przegląd z 2026-11-05 dotyczy kodu `c0fbfc9003ef77c9161020c4c629ef2345539a8e`.
Zaakceptowana baza historii to osobny commit
`ad5fa191a36d5a5f45f0b2de523bd39125827573`; kolejne sesje ustalają ją na nowo
według zdarzenia Git, a nie kopiują tego SHA bez sprawdzenia.

- U01: `prepare_export_data` wywoływane raz w pełnym buildzie; Best, Excel,
  GeoPackage i statystyki dostają te same dane. GeoPackage nie importuje Excela.
- U02: `validated_catalog_source`, `validated_proposal`, `validate_catalog`
  i `history_checked_catalog` rozdzielają kontrole. Review tworzy jedną bazę
  dla wejścia, drugą tylko dla zmienionej propozycji; cleanup poprzedza zapis.
- Bilans `src/**/*.py` i `scripts/**/*.py`: U01 +328/−437, U02 +369/−262;
  razem **−2 linie netto**. U02 ogranicza powtórne wykonanie kontroli,
  ale samo zwiększa rozmiar kodu o 107 linii.
- [Validate code and data](https://github.com/dlubom/gps-kataster-obiektow-tatr/actions/runs/42046122616)
  zakończone sukcesem dla tego head: 1187 PASS / 2 SKIP; oddzielny wymagany
  smoke zarządzanego Dockera: 1 PASS.
- [Preview](https://github.com/dlubom/gps-kataster-obiektow-tatr/actions/runs/42046122857)
  zakończone sukcesem. Pobrany ZIP ma SHA-256
  `7bbfe99ad0603a3144963aba2e0bad6f24dbf7b4731cd64c9be22e1ca10a4ccb`;
  manifest wskazuje powyższy head/base oraz merge `3f8c5834a1eafbd5b631993e22cc87dbdc22bb41`.
- Ponowne lokalne testy `test_export_data.py` i `test_validation_phases.py`:
  **38 PASS**. Sprawdzono 14 sum paczki, provenance i strukturę/liczby formatów;
  natywne odtworzenie dumpa dało identyczne fingerprints wszystkich tabel
  i obu widoków Best jak aktualny katalog. Odczyt potwierdził 1029 obiektów,
  1019 jaskiń, 1946 pomiarów i 27 manual Best. Nie jest to nowy pełny
  test równoważności z kodem sprzed U01; jego wcześniejszy odbiór opisuje
  [PBI-119](../../verification/PBI-119.md).

W podstawie zadania potwierdzono lukę U03: brak `publications/` oraz zwykły
plik tej nazwy przyjmowano jako pustą bibliografię. Wspólny guard ją zamyka;
[wynik odbioru U03](tasks/U03-input-completeness.md#odbiór) jest w karcie. Pozostałe
karty opisują uproszczenia projektu; nie należy przedstawiać ich jako znalezionych
regresji U01/U02. W szczególności stare schematy są nadal potrzebne do historii.

## Po U11

Wszystkie karty U01–U11 są odebrane. Kolejny uzgodniony zakres prowadzi do
[osobnego indeksu U12–U17](next/README.md); realizacja nadal wymaga zlecenia karty.
Zakres uruchomienia mutation i istniejący błąd mutmut odtworzony sprzed U11
opisano w [karcie U11](tasks/U11-ci-setup.md#ograniczenie-mutation).
Naprawa tego toolingu wymaga osobnego zlecenia. PR #40 pozostaje draftem;
zakończenie serii nie upoważnia do merge, taga ani wydania.
