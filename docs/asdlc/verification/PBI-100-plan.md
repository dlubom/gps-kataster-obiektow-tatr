# PBI-100 — plan wykonania

Baza: otwarty draft PR #12, czysty `codex/tpn-sync-planning`,
`ab7dd2d3cb6a9fd5cc8b80b964c5f1b67be6997c`.
Zakres i opis zachowania są zatwierdzone zleceniem PBI-100 oraz kontraktem
PBI-095; rutynowe szczegóły wykonawcze poniżej wybiera wykonawca.

1. Ścisły protokół zmian i decyzji: odtworzenie raportu z utrwalonego
   commitu bazy i snapshotu, jawne propozycje akcji oraz rozliczenie wszystkich
   rekordów wymagających decyzji. Brak nieznanych pól/kluczy/wersji.
2. Jeden plan w pamięci: ID całej partii, wspólna historia i best obiektu,
   metadata tylko z allowlisty, append notes, referencje, nowe otwory/jaskinie.
   PBI-099 działa bez wyjątków; manifest pending nie uprawnia do migracji.
3. Trwały wynik i ponowienie: hashe wszystkich zmienionych plików i całego
   katalogu; ponowienie sprawdza wynik przed dawnym preimage. Zmiana decyzji
   przelicza wynik od bazy, zachowując poprzednie decyzje jako dowody.
4. Transakcja: pełna kopia `data`, walidacja/readback przed publikacją,
   atomowa zamiana katalogów na macOS/Linux. Nieobsługiwany system plików
   odmawia zapisu; awaria przed zamianą zachowuje starą całość, po zamianie
   istnieje nowa całość. Blokada procesu i ponowne hashe przed publikacją.
5. CLI prepare/dry-run/apply/check i obowiązkowa bramka CI sprawdzająca
   końcowy diff względem bazy, pending i trwałą kolejkę defer. Dry-run
   pokazuje diff YAML, best i wiersze punktów używane przez eksporty.
6. Testy offline na syntetycznych fixture'ach, awarie I/O/procesu, dwa cykle,
   ręczna edycja wyniku, nieaktualne dane, kolizje ID, ochrona historii.
   Pełny pytest/Ruff/validate/build/readback i celowane mutacje.
7. Dokumentacja/status/kontekst, commit/push, odczyt końcowego SHA i wszystkich
   jobów CI. Stop po PBI-100; brak produkcyjnego importu i PBI-101.

Review focus: ostatnia błędna decyzja nie zapisuje nic; wiele GUID jednego
obiektu nie przestawia best pośrednio; same daty/notes nie tworzą pomiaru;
zmiana decyzji nie usuwa edycji człowieka; awaria publikacji nie rozdziela
katalogu i stanu. Każda z tych granic ma otrzymać test zachowania.
