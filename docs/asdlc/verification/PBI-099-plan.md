# PBI-099 — plan wykonania

Baza: `6a0d415221a23ad5a31949612abdb68af06dccf9`, otwarty draft PR #12,
`codex/tpn-sync-planning`. Kontrakt: tpn_sync_contract §6, plan §7.
Wyłącznie ochrona i audyt best. Bez zastosowania snapshotu/decyzji PBI-100.

1. Test-first: pełna historia GNSS (dowolne source/status/accuracy), manual,
   własne zweryfikowane, raporty/znaczniki; przypadek kontrolny niechronionego auto.
2. Czysty strażnik `tpn_best_guard.py`: odrębne keep/select_new, walidacja
   wskazanego ID i jawnego trybu, propozycja before/after bez mutacji wejścia.
   Ochrona blokuje select_new; auto→manual chronionego obiektu jest propozycją
   wymagającą akceptacji manifestu, nigdy ubocznym skutkiem dopisania pomiaru.
3. Audyt całego katalogu i deterministyczny manifest konkretnych auto→manual,
   związany z hashami obiektów/katalogu i polityki. CLI tylko do odczytu.
   Raport porównania PBI-097–098 pokazuje ochronę także przy historii.
4. Manifest do jawnej akceptacji użytkownika. Bez niej katalog pozostaje
   bajtowo niezmieniony i ochrona obowiązuje. Brak CLI apply w tej karcie.
5. Pełna bramka runbooka, celowane mutacje, porównanie danych i eksportów
   przed/po, readback SQLite/formatów, CLI z czystego checkoutu bez build.
6. Dowody, status/context/handoff, commit/push, odczyt zdalnego SHA i
   wszystkich jobów CI tego SHA. Stop po PBI-099, bez merge/tagu/release.

Szczegółowe logi w nowym `build/verification/PBI-099/`. Zmiany pomiarów,
statusów i dokładności są zabronione. Ogólny selektor auto bez zmian.
Niejasna geodezja w tekstach: pytanie domenowe do użytkownika przed wdrożeniem.
