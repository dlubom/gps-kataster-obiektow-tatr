# Operator review staging - format decyzji

PBI-015 wprowadza jawny plik decyzji operatora. Importery PIG/TPN nadal tworza
tylko staging w `build/staging/*`; finalne YAML pod `data/` powstaje dopiero po
uruchomieniu:

```bash
uv run python scripts/importers/apply_review.py --decisions path/to/decisions.yml
```

Domyślnie `--data-dir` musi istnieć i być katalogiem. Dla pierwszego
importu do nowego celu użyj jawnej inicjalizacji:

```bash
uv run python scripts/importers/apply_review.py \
  --decisions path/to/decisions.yml --data-dir path/to/new-data --init-data-dir
```

Nowy cel jest na czas walidacji pustym katalogiem w pamięci. Dopiero
poprawna partia (np. `create_cave` + `create_object`) tworzy katalog i YAML.
`--dry-run`, puste decyzje oraz błędna partia nie tworzą celu; raport
diagnostyczny nadal może powstać w `--output-dir`. Flaga nie ignoruje
istniejących danych, plików zamiast katalogów ani zerwanych linków.
API odpowiada argument `initialize_data_dir=True`. Zwykły odczyt
`load_dataset` pozostaje ścisły; oddzielny `load_import_target_dataset`
służy wyłącznie do przygotowania nowego celu importu. Staging TPN zachowuje
możliwość przygotowania propozycji dla jeszcze nieistniejącego celu,
bez tworzenia finalnych YAML; PIG nadal rezerwuje numery z nazw plików.

Minimalny plik:

```yaml
reviewed_at: "2026-05-16T10:00:00Z"
reviewed_by: dl
decisions:
  - action: create_cave
    source: PIG
    record_number: 1
  - action: create_object
    source: PIG
    record_number: 1
  - action: add_measurement
    source: TPN
    record_number: 1
  - action: link_cave
    object_id: KSW-0001
    cave_id: C-0001
  - action: reject
    source: TPN
    record_number: 2
    reason: "Duplicated source row."
  - action: unresolved
    source: TPN
    record_number: 3
    reason: "Needs field review."
```

## Akcje

| `action` | Znaczenie | Efekt na finalne YAML |
|---|---|---|
| `create_cave` | Nowa `Jaskinia` ze staging PIG/TPN. | Tworzy `data/caves/{CAVE-ID}.yml`. |
| `create_object` | Nowy `Obiekt` ze staging PIG/TPN. | Tworzy `data/objects/{PREFIX}/{OBJECT-ID}.yml`. |
| `add_measurement` | Nowy `Pomiar` dla istniejacego albo wczesniej utworzonego `Obiektu`. | Dopisuje pomiar i referencje TPN, a dla `best_measurement.mode: auto` przelicza wskazanie. |
| `link_cave` | Powiazanie obiektu z jaskinia. | Ustawia `Obiekt.cave_id`, usuwa obiekt z `object_ids` poprzedniej jaskini i dopisuje go do `object_ids` docelowej jaskini. |
| `reject` | Rekord importu odrzucony. | Nie zapisuje finalnego YAML, ale trafia do raportu review. |
| `unresolved` | Rekord zostaje nierozstrzygniety. | Nie zapisuje finalnego YAML, ale trafia do raportu review. |

`source` jest wymagane dla akcji opartych o staging i przyjmuje `PIG` albo
`TPN`. `record_number` wskazuje numer wiersza z raportu staging. `link_cave`
dziala na finalnych ID i nie wymaga `source`.

`link_cave` przy przeniesieniu A→B zapisuje obiekt i obie jaskinie wraz
z `updated_at` / `updated_by` z decyzji. Zachowuje trwałe ID, pomiary,
`best_measurement`, referencje i pozostałe pola. Stara jaskinia może zostać
bez otworów. Ponowne powiązanie z tą samą jaskinią nie dodaje duplikatu
ani nie usuwa i nie przestawia wpisu; aktualizuje audyt obiektu i jaskini.
Można również przypisać obiekt, który dotąd nie miał `cave_id`.
Walidator sprawdza oba kierunki powiązań i odrzuca wskazanie jednego
obiektu przez dwie różne jaskinie. Wejście i pełny wynik review
są walidowane przed zapisem (PBI-040).

Aktualizacje `add_measurement` i `link_cave` zachowują ścieżkę oraz
rozszerzenie wczytanego pliku (`.yml` albo `.yaml`), także dla obu jaskiń
przy przeniesieniu. Nowe rekordy powstają w ścieżkach `.yml` z tabeli.
Dwa pliki z tym samym ID obiektu lub jaskini (także o identycznej treści)
blokują całą partię przed zastosowaniem decyzji: `FINAL_DATA_INVALID`
wskazuje ID i obie ścieżki. Reguła działa również dla `--dry-run`.
Operator musi rozstrzygnąć konflikt w danych; review nie wybiera pliku
według rozszerzenia ani nie scala historii automatycznie.

## Bezpieczenstwo

Klucze YAML muszą być unikalne na każdym poziomie: np. drugi `action`
w jednej decyzji jest błędem także przy identycznej wartości. Aliasy
`*nazwa` i scalanie `<<` są niedozwolone; wartości zapisuj jawnie.
Obowiązuje wspólna [polityka YAML](../operations.md#reguły-zapisu-yaml)
dla decyzji i finalnych danych, z zachowaniem dotychczasowego parsowania dat.
Powtórzony klucz w finalnych danych również blokuje całą partię review.

`apply_review.py` sprawdza cały wejściowy katalog przed indeksowaniem po ID.
Błędy schematu, ścieżek, duplikatów, powiązań lub relacji kończą operację
jako `FINAL_DATA_INVALID`. Review nie naprawia błędnego wejścia przy okazji
innych decyzji; najpierw popraw dane i uruchom walidator.

Decyzje są stosowane na kopii. Struktura kontenerów staging jest sprawdzana przed indeksowaniem
(`STAGING_REPORT_INVALID`). Kształt wybranych propozycji i pomiarów
jest sprawdzany przed użyciem (`STAGING_PROPOSAL_INVALID`), a pełny wynik
całej partii przed pierwszym zapisem (`PROPOSED_DATA_INVALID`). Sprawdzane
są również niezmienione relacje, oryginalne ścieżki oraz nowe ścieżki `.yml`.
Komunikaty zawierają kody walidatora, ścieżki i opis błędu. Sama propozycja
obiektu z brakującą jaskinią albo jaskini z brakującym otworem jest błędem;
para `create_object` + `create_cave` w jednej partii działa w obu kolejnościach.
`--dry-run` wykonuje te same kontrole, bez zapisywania finalnego YAML.
Ostrzeżenia katalogu nie blokują review; ich pełny wykaz daje `validate.py`.

W `add_measurement` można podać `target_object_id`. Referencje katalogowe
trafiają do faktycznej jaskini tego obiektu po całej partii,
nie do starego `target_cave_id` raportu staging. Jawny `target_cave_id`
w decyzji musi zgadzać się z tym powiązaniem (`TARGET_CAVE_MISMATCH`).
Jeżeli nie ma jaskini dla referencji, operacja daje `TARGET_CAVE_MISSING`;
utwórz/powiąż ją w tej samej partii. Pomiar bez referencji katalogowych
może być dodany do obiektu bez jaskini.

Błąd walidacji blokuje wszystkie zapisy partii. Po walidacji PBI-041
serializuje całą partię, przygotowuje pliki i kopie oryginalnych bajtów
w `data/.review-recovery/`, a dopiero potem zastępuje finalne pliki.
Obsługiwany błąd zapisu lub zastąpienia uruchamia rollback: oryginalne
pliki wracają, nowe są usuwane. Puste katalogi utworzone na potrzeby
nowych rekordów mogą pozostać. Tryb uprawnień istniejących plików jest
zachowywany. `REVIEW_WRITE_FAILED` oznacza niepowodzenie bez pozostawienia
zmienionych finalnych plików; po usunięciu przyczyny można ponowić decyzje.

Nieudany rollback lub sprzątanie daje `REVIEW_RECOVERY_REQUIRED`,
ścieżkę dowodów i instrukcję odzyskania. Status decyzji to `write_failed`,
a `written_paths` jest puste: nie jest to gwarancja braku częściowych zmian.
Przy błędzie sprzątania po zakończonym zapisie cały wynik może już istnieć.
CLI kończy się kodem 1, drukuje diagnostykę przed próbą zapisania raportu
i nie ogłasza sukcesu. Awaria samego raportu po udanym zapisie również
daje kod 1 i liczbę potwierdzonych zapisów; nie należy ponawiać decyzji
bez sprawdzenia katalogu.

### Odzyskiwanie po bledzie zapisu

Każda pozostałość `data/.review-recovery` (także pusty katalog lub link)
blokuje następne review, również `--dry-run`, przed wczytaniem katalogu.
Nie kasuj jej automatycznie. W czasie jednej operacji nie uruchamiaj
innych zapisów review ani ręcznej edycji tego katalogu. Wyłączność tworzenia
katalogu recovery chroni aktywny zapis, lecz nie zapewnia izolacji całego
cyklu odczyt–decyzje–zapis ani blokady dla innych narzędzi.

1. Zatrzymaj zapisujących i skopiuj cały katalog danych wraz z recovery
   poza katalog roboczy. Zachowaj komunikat błędu i raport, jeśli powstał.
2. Odczytaj `manifest.json`: `entries` zawiera względną `path`, numer `index`
   i `original` informujący, czy plik istniał. `N.original` zawiera oryginalne
   bajty, `N.prepared` jest przygotowanym nowym plikiem (po zastąpieniu może
   go już nie być). `restore.tmp` i `committed.tmp` są plikami roboczymi.
3. Jeśli manifest i wszystkie wymagane kopie są kompletne, można przywrócić
   **całą** partię: dla `original: true` skopiuj `N.original` do wskazanej
   ścieżki, zachowując uprawnienia; dla `original: false` usuń tylko wskazany
   nowy plik, jeśli istnieje. Nie używaj niezweryfikowanych ścieżek spoza
   katalogu danych. Porównaj przywrócone pliki bajtowo z kopiami.
4. `COMMITTED` jest publikowany dopiero po wszystkich zastąpieniach i oznacza
   zakończony zapis przed sprzątaniem. W takim przypadku preferuj weryfikację
   nowego katalogu względem decyzji i pozostawienie wyniku, bez ponawiania.
   Brak tego znacznika nie dowodzi braku zmian. Przy częściowym sprzątaniu
   mogą już brakować manifestu lub kopii; wtedy ustal stan na podstawie
   zachowanej kopii, raportu, decyzji i zmian Git. Nie odtwarzaj brakujących
   oryginałów ze staging ani nie resetuj niezacommitowanych zmian operatora.
   Nie usuwaj recovery, dopóki wynik nie jest jednoznaczny.
5. Sprawdź `git diff` i `uv run --frozen python scripts/validate.py
   --data-dir ścieżka/do/data`. Dopiero po odtworzeniu oryginałów lub
   potwierdzeniu całego nowego wyniku usuń recovery. Ponowienie decyzji
   jest właściwe tylko po odtworzeniu stanu sprzed partii.

Gwarancja dotyczy obsługiwanych wyjątków I/O podczas działania procesu.
Nie jest to transakcja systemu plików: brak gwarancji przy SIGKILL,
utracie zasilania lub awarii dysku, brak fsync i atomowości całej partii.
Przerwanie procesu może zostawić częściowy katalog i recovery; stosuj
powyższą procedurę. Przy niekompletnych dowodach potrzebna jest kopia
operatora lub Git z uwzględnieniem lokalnych zmian, a nie automatyczne retry.

`apply_review.py` sprawdza także caly plik decyzji. Jezeli ktorakolwiek
decyzja ma blad, finalne YAML nie sa zapisywane. Błąd parsowania pliku
decyzji jest zgłaszany na stderr z plikiem i linią, bez tworzenia raportów.
Po poprawnym odczycie decyzji powstaje raport, także przy błędzie finalnego
YAML:

- `build/staging/review/staging-review.json`
- `build/staging/review/staging-review.md`

Raport zawiera zmaterializowane decyzje, odrzucone/nierozstrzygniete rekordy,
ostrzezenia i liste zapisanych plikow YAML.
