# Następny krok — niezależny review PR #12

Pracuj w /Users/dariuszlubomski/proj/gps-kataster-obiektow-tatr. Użyj $asdlc.
Wykonaj wyłącznie niezależny, read-only review PR #12:
https://github.com/dlubom/gps-kataster-obiektow-tatr/pull/12

Nie polegaj na historii czatu. Sprawdź aktualny Git/PR/head i origin/main;
zachowaj cudze zmiany. Przeczytaj AGENTS.md, dokumenty kanoniczne, tpn_sync_*,
PBI-095–101, manifest PBI-099 oraz PBI-101-review/review.md, zgody użytkownika,
verification.json, delivery-data-proof.json, review-equivalence.json i archiwum
superseded-v1. Końcowy SHA/CI/readback są w opisie PR; sprawdź je na żywo.
Przeczytaj także PBI-101-D26.md i PBI-101-D26-resolution.json: wykonują
późniejsze jawne decyzje użytkownika, zachowując pierwotne dowody.

Zweryfikuj zgodność z decyzjami: A001–A578 approve bez zmian katalogu,
B001–B031 append pomiaru i osobny select_new auto, C001–C005 nowe Obiekty/
Jaskinie, historycznie D001–D026 defer do badania. Pierwotnie 614 approve /
26 defer / 0 pending. Nie pytaj ponownie o zaakceptowane zakresy.
Oryginalna paczka zachowała 1876 dawnych pomiarów, wszystkie 1001 dawnych
Jaskiń i 9 chronionych plików. Wynik: 1012 Obiektów, 1006 Jaskiń, 1912 pomiarów.
Następnie użytkownik osobno zatwierdził w tym samym PR trzy przypięcia
auto→manual: KSW-0201/m-003, KSW-0240/m-002, KSZ-0112/m-001.
[Zgoda i hashe](PBI-099-manual-selection.json) wiążą oryginalny plan i manifest;
check osobno sprawdza tylko tryb/powód/audyt tych trzech best. Historia,
ID i współrzędne pomiarów oraz plik Wysokiej KSW-0189 pozostają niezmienione.
Oryginalny JSON PBI-099 pending jest historyczny i zachowuje bajty.
Plan/apply starej paczki nadal odrzuca późniejsze zmiany katalogu.
Stan gałęzi nie jest jeszcze przyjętym main.

Suplement D26 tworzy 23 Obiekty, 21 Jaskiń i 26 pomiarów; wynik 1035/1027/1938.
D003=D014 i D008=D010 to po jednym Obiekcie z dwoma źródłami/pomiarami;
D002/D010 są dwoma Obiektami wspólnej Jaskini. D006 jest nowym otworem
C-0219, D009/D021 odrębnymi Jaskiniami, D022 dopisuje źródło/pomiar
do MLW-0050 i zachowuje m-001 przez manual. Pozostałe są nowe osobno.
640 approve / 0 defer / 0 pending dotyczy nowego kandydata stanu; pierwotne
decyzje i receipt nadal zachowują 26 defer. Wszystkie 1912 pomiarów bazy
suplementu i 9 chronionych plików muszą pozostać bez zmian. Dziesiąty
chroniony wybór to osobno zatwierdzony keep D022. Sprawdź noty publikacji
lub krótkie „Dokumentacji nie odnaleziono.” oraz pełne odtworzenie receipt
z podstawy Git; hashe nie mogą dopuścić obcej zmiany danych.

Obie kontrole receipt wymagają przodków HEAD: `83e1d383…` dla przypięć
manual i `d1f958bc…` dla D26. Merge musi zachować te commity; squash/rebase
zastępujący historię uniemożliwi późniejsze odtworzenie tej bramki.

Sprawdź ścisłe raw API/hash/preimages, jawną precyzję pochodnych, ochronę
best, idempotencję, trwałość defer, odtworzenie w czystym checkout oraz
wszystkie joby/kroki/pełne logi CI aktualnego SHA i świeży readback eksportów.
Nie stosuj danych ponownie ręcznie i nie używaj historycznego build jako dowodu.
Raportuj konkretne usterki z lokalizacją, skutkiem i dowodem, osobno pozostałą
niepewność domenową. Bez zmian, commitów, merge, review approval, tagu,
release, PBI-102–103 ani harmonogramu. Ewentualne poprawki wymagają osobnego
zlecenia; merge pozostaje osobną decyzją człowieka.
