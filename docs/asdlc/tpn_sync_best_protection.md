# Ochrona GNSS/geodezji i best — PBI-099

Implementacja [kontraktu §6](tpn_sync_contract.md) i [planu §7](tpn_sync_plan.md).
Nie zmienia ogólnego algorytmu auto, katalogu ani historii. Nie stosuje
snapshotu, decyzji ani migracji. Producent/walidator/applier paczki to PBI-100.

## Audyt z czystego checkoutu

```bash
uv run --frozen --no-sync --offline python scripts/audit_tpn_best.py \
  --output-dir "$PWD/build/tpn-best/NOWY-KATALOG"
uv run --frozen --no-sync --offline python scripts/fetch_tpn_snapshot.py verify \
  data/sources/tpn/snapshots/pbi-096-live-20261019
uv run --frozen --no-sync --offline python scripts/compare_tpn_snapshot.py \
  --snapshot data/sources/tpn/snapshots/pbi-096-live-20261019 \
  --batch-id NOWY-ID --qualify-new --protect-best \
  --output-dir "$PWD/build/tpn-reviews/NOWY-KATALOG"
```

Audyt nie wymaga snapshotu ani sieci. Czyta wszystkie obiekty, także bez
referencji TPN, np. KSZ-0112. Zapisuje wyłącznie nowy katalog pod build:
manifest.json, report.md, checksums.json, z kontrolą bajtów po zapisie.
Odmawia nadpisania i symlinków; błąd publikacji usuwa własny nowy katalog.
Brak opcji apply/migrate. Porównanie z `--protect-best` dołącza ten sam audyt
jako `best_protection` do JSON i do Markdown, bez zmiany records/best/actions.
Bez flagi pozostaje wcześniejszy raport tylko do odczytu.

## Polityka i dowody

`tpn-best-protection-v1` ma osobną treść/hash w audycie. Nie zmienia
niezmiennej polityki ani snapshotów PBI-096. Manifest wiąże cały catalog_hash,
ścieżkę i SHA-256 każdego obiektu oraz pełny dotychczasowy best.

Ochrona dotyczy całego obiektu, gdy występuje choć jeden z dowodów:

- obecny tryb manual;
- method=gnss, elevation_source=gnss, tag gnss lub gnss_anchor w dowolnym pomiarze;
- jawny znacznik kwalifikacji geodezyjnej: tag geodetic lub geodezja;
- własny zweryfikowany pomiar;
- załącznik kind=raport_gnss, także bez przypisania do konkretnego pomiaru.

Tagi kwalifikacji są wykonawczą reprezentacją jawnego znacznika w istniejącej
liście tags, bez zmiany schematu. Powinny mieć uzasadnienie operatora w notes;
strażnik nie nadaje ich na podstawie tekstu i nie dowodzi jakości pomiaru.
Nie dodano żadnego znacznika do danych katalogu.

Source, status (także odrzucony), accuracy=null i niewskazanie jako best
nie znoszą ochrony GNSS/geodezji. Raport wskazuje ID pomiaru/załącznika i
konkretną podstawę; selected_measurement zachowuje wartości obecnego best.

Niejasne wzmianki w source_ref/device/notes/tags pomiaru, path/caption
załącznika lub notes obiektu są dowodem do review. Jawny wzorzec PL/EN
(GNSS, DGNSS, RTK, PPK, geodez-/geodet-/geodes-, tachim-/tachym-) i pola
są częścią hashowanej polityki. Podkreślniki są separatorem podczas
skanowania, więc survey_gnss i pomiar_geodezyjny również dają review. Review blokuje select_new, bez automatycznej
kwalifikacji geodezyjnej. Zwykły GPS ani sama nieznana dokładność nie dają
tej kwalifikacji. To konserwatywna realizacja kontraktu §6; wzorzec nie jest
klasyfikatorem wszystkich możliwych opisów geodezji. Operator powinien
utrwalić rozpoznaną kwalifikację jawnym znacznikiem/raportem.

## Czysty strażnik dla przyszłej ścieżki TPN

`assess_protection(obj)` zwraca protected, requires_review, evidence i
review_evidence. Błędna historia/best blokuje ocenę. Pola nie są zmieniane.

`plan_best_action(obj, additions, best_action)` przyjmuje istniejący obiekt,
niepustą listę proponowanych pomiarów source=TPN i dokładnie:

```json
{"action":"keep","measurement_id":"m-001","resulting_mode":"manual","reason":"Zachować wskazany punkt eksportu."}
```

- keep wymaga **wskazanego obecnego ID**, nie ponownego obliczenia starego
  auto. Jeśli po dodaniu historii auto wskazuje inny pomiar, trzeba jawnie
  podać manual i reason; sam strażnik nie dopisuje pomiaru ani nie zmienia trybu.
- select_new wymaga ID z additions oraz osobnego niepustego powodu. Każdy
  chroniony obiekt lub niejasny dowód geodezji daje TPN_BEST_PROTECTED.
- Auto jest dozwolone tylko, gdy wybiera wskazane ID. Inny wybór wymaga
  jawnego manual. Keep istniejącego manual zachowuje jego powód i audyt.
- Brak/nieznana akcja, pole, ID, tryb, powód albo kolizja ID/nieskończone
  liczby blokują plan. Nie ma domyślnej zgody ani wyłączenia ochrony.

Wynik pokazuje before, proponowane after, default_after, mode_change,
protection, blockers i can_apply. **can_apply jest wyłącznie wynikiem tej
kontroli**, nie zatwierdzeniem człowieka ani kompletnym preflight paczki.
Chronione auto→manual zawsze ma blocker migration_manifest_approval_required;
review geodezji daje geodetic_evidence_review_required. Brak zgody nie znosi
blokady select_new. Nie dodano argumentu umożliwiającego obejście ochrony.
Nowa propozycja best nie kopiuje starego autora/czasu do nowego uzasadnienia;
prawdziwy audyt ustala dopiero uprawnione zastosowanie po akceptacji.

PBI-100 musi użyć tego strażnika przy planowaniu łącznym wszystkich akcji
obiektu oraz przy ponownej kontroli przed zapisem. Nadal musi zweryfikować
pełny payload/proweniencję TPN, preimages, decyzje człowieka i transakcję.
Istniejący apply_review.py CSV/XLSX nie jest applierem tego protokołu;
nie używać go do snapshotów ani przykładów decisions.yml synchronizacji.

## Manifest rzeczywistych propozycji

[JSON](verification/PBI-099-protection-manifest.json) i
[wersja czytelna](verification/PBI-099-protection-manifest.md):
9 chronionych obiektów, 6 już manual, 3 propozycje:
KSW-0201/m-003, KSW-0240/m-002, KSZ-0112/m-001.
Każda ma before/after, podstawę ochrony, uzasadnienie i hash pliku.

Status **pending**, bez akceptacji i bez migracji. Akceptacja wymaga
konkretnych obiektów/manifestu, kontroli aktualności preimages i zapisu
rzeczywistego autora/czasu; nie wolno potraktować samego commitu raportu jako
zgody. Zachować wskazane ID oraz wszystkie pomiary, współrzędne, wysokości,
statusy i dokładności. W tej karcie katalog pozostał bajtowo niezmieniony.
