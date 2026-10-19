# Następny krok — niezależny review PR #12

Pracuj w /Users/dariuszlubomski/proj/gps-kataster-obiektow-tatr. Użyj $asdlc.
Wykonaj wyłącznie niezależny, read-only review PR #12:
https://github.com/dlubom/gps-kataster-obiektow-tatr/pull/12

Nie polegaj na historii czatu. Sprawdź aktualny Git/PR/head i origin/main;
zachowaj cudze zmiany. Przeczytaj AGENTS.md, dokumenty kanoniczne, tpn_sync_*,
PBI-095–101, manifest PBI-099 oraz PBI-101-review/review.md, zgody użytkownika,
verification.json, delivery-data-proof.json, review-equivalence.json i archiwum
superseded-v1. Końcowy SHA/CI/readback są w opisie PR; sprawdź je na żywo.

Zweryfikuj zgodność z decyzjami: A001–A578 approve bez zmian katalogu,
B001–B031 append pomiaru i osobny select_new auto, C001–C005 nowe Obiekty/
Jaskinie, D001–D026 defer do niezależnego badania. Razem 614 approve /
26 defer / 0 pending. Nie pytaj ponownie o zaakceptowane zakresy.
Zachowano 1876 dawnych pomiarów, wszystkie 1001 dawnych Jaskiń i 9 chronionych
plików. Wynik: 1012 Obiektów, 1006 Jaskiń, 1912 pomiarów. PBI-099 nadal
pending, bez chronionych migracji. Stan gałęzi nie jest jeszcze przyjętym main.

Sprawdź ścisłe raw API/hash/preimages, jawną precyzję pochodnych, ochronę
best, idempotencję, trwałość defer, odtworzenie w czystym checkout oraz
wszystkie joby/kroki/pełne logi CI aktualnego SHA i świeży readback eksportów.
Nie stosuj danych ponownie ręcznie i nie używaj historycznego build jako dowodu.
Raportuj konkretne usterki z lokalizacją, skutkiem i dowodem, osobno niepewność
domenową 26 odroczeń. Bez zmian, commitów, merge, review approval, tagu,
release, PBI-102–103 ani harmonogramu. Ewentualne poprawki wymagają osobnego
zlecenia; merge pozostaje osobną decyzją człowieka.
