# PBI-104 — paczka danych w każdym PR

> **Dla wykonawcy:** realizacja przez `superpowers:subagent-driven-development`
> lub `superpowers:executing-plans`; poniższe kroki wyznaczają jeden PBI.

**Cel:** każda PR-ka, zaczynając od #12, przed rzeczywistym merge udostępnia
w swoim opisie paczkę pozwalającą sprawdzić wszystkie pliki przyszłego eksportu wydania.

**Architektura:** workflow `PR data exports` buduje syntetyczny merge PR
z jego bazą, korzystając z tego samego buildera co wydanie. Publikuje ZIP
GitHub Actions z dziewięcioma plikami release, `preview.json` i `SHA256SUMS`.
Osobny publisher aktualizuje oznaczony fragment opisu PR na podstawie
metadanych API GitHub; jego kod pochodzi z zaufanej gałęzi domyślnej.

**Stos:** Python 3.12 / uv, istniejący builder eksportów, GitHub Actions,
`actions/upload-artifact@v4`, Node.js / GitHub API.

**Specyfikacja:** [§11.4 i §13](../../specyfikacja_gps_kataster_obiektow_tatr_v_2.md),
[karta PBI-104](backlog_v1.md#pbi-104-paczka-danych-w-opisie-każdego-pr).

## Granice

- Kontynuować PR #12. Zachować bajty `data/`, `config/`, `schema/` i źródeł.
- Zdarzenia PR obejmują otwarcie, nowe commity i ponowne otwarcie, także draft.
- Budować dokładny `github.sha` syntetycznego merge; sprawdzić jego rodziców
  względem base/head zdarzenia. Konflikt lub błąd buildu nie daje paczki sukcesu.
- Zachować zestaw i semantykę eksportów release; dodatkowe pliki opisują
  pochodzenie podglądu i sumy SHA-256. Etykieta: `pr-{number}-{head12}`.
- Retencja testowego artefaktu PR: 14 dni, w granicach polityki repozytorium.
  Pobranie wymaga zalogowania do GitHub. Ponowienie runu jest możliwe przez
  30 dni i zachowuje stare zdarzenie oraz jego SHA; po wygaśnięciu paczki
  ma sens tylko przy niezmienionych head/base. Nowy commit lub close/reopen
  PR odświeża bazę oraz tworzy nową paczkę dla aktualnych źródeł.
- Build ma uprawnienia odczytu. Publisher może pisać wyłącznie opis PR;
  nie wykonuje kodu PR ani nie pobiera jego artefaktów.
- Nie zmieniać PBI-102–103, harmonogramu, tagów, changeloga ani procedury
  oficjalnego wydania. Merge wykonuje człowiek.

## Miejsca wymagające review

- Nowy commit albo nowsze uruchomienie nie może zostać przykryte wynikiem
  starszego runu; opis wskazuje head/base/merge i stan bieżącej paczki.
- Niepełny albo obcy wynik z forka nie może zostać przypisany do innego PR.
- Publisher zachowuje ręcznie napisany opis poza markerami
  `<!-- pr-data-preview:start -->` / `<!-- pr-data-preview:end -->`.
- ZIP ma dziewięć plików release w katalogu głównym oraz manifest i sumy;
  brak pliku albo stara zawartość katalogu wyjściowego jest błędem.
- Ludzki merge workflow do main jest jednorazową instalacją publishera.
  Każdy podgląd buduje `pull_request` przed rzeczywistym merge danego PR;
  pierwszą paczkę #12 opisuje ta sama logika lokalnie przez API.

## Wykonanie

### 1. Packager i zgodność wydania

- [x] Dodać `tests/test_pr_data_preview.py` RED dla
  `scripts/build_pr_data_preview.py`: komplet plików,
  pochodzenie head/base/merge/run/attempt, sumy i błędne wejście.
- [x] Oprzeć packager na `build_release_artifacts`, z wyjściem
  `build/pr-data/exports/`; zapisać `preview.json` oraz `SHA256SUMS`.
  Wspólny `RELEASE_ASSET_FILENAMES` w `release_artifacts.py` musi zgadzać
  się z dziewięcioma uploadami istniejącego `release.yml`.
- [x] Potwierdzić GREEN testów oraz zgodność danych z kanonicznym buildem
  release przy tych samych źródłach i parametrach generowania.

### 2. Publisher i workflow

- [x] Dodać `tests/test_pr_data_publisher.cjs` RED dla zachowania opisu,
  aktualizacji stanu,
  starego SHA/runu, forka i błędnych metadanych API.
- [x] Dodać `.github/workflows/pr-data.yml` z odczytem repozytorium,
  kontrolą merge i uploadem eksportów na 14 dni.
- [x] Dodać `.github/workflows/publish-pr-data.yml` na `workflow_run`
  (`in_progress` / `completed`), z zaufanym checkoutem `workflow_sha`.
- [x] Dodać `.github/scripts/publish_pr_data.cjs`; dane z API traktować
  jako dane, bez pobierania artefaktu lub uruchamiania kodu z PR.
- [ ] Potwierdzić GREEN przez `node --test tests/test_pr_data_publisher.cjs`.
- [x] Dodać `tests/test_pr_data_workflows.py` dla wyzwalaczy i uprawnień;
  uruchamiać test publishera w `validate.yml` z Node.js 24.

### 3. Odbiór i dostarczenie

- [x] Uruchomić testy celowane, pełną bramkę projektu i readback wszystkich
  formatów; potwierdzić niezmienność wejść i `git diff --check`.
- [x] Zapisać wyniki w [PBI-104](verification/PBI-104.md), przejrzeć diff,
  commit/push do #12 i potwierdzić zdalny SHA oraz CI tego SHA.
- [x] Pobrać faktyczny ZIP Actions, zweryfikować jego komplet, manifest,
  sumy i zawartość eksportów; umieścić link w opisie #12 przez publisher API.
- [x] Odczytać opis PR. Utrwalić ograniczenie startowe publishera
  oraz URL runu/artefaktu; zakończyć bez merge, tagu i release.
