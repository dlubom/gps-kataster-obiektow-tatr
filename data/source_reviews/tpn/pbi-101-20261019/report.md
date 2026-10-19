# Paczka pbi-101-20261019 — pending

Użytkownik po przedstawieniu propozycji polecił: „Na razie pozostaw wszystko pending”.
640 decyzji ma status pending, reviewed_by/at=null. Nie wykonano apply.
Nie ma nowego przyjętego stanu źródła ani application.json. Bramka CI ma
blokować gotowość tej paczki do merge.

[Propozycje po rekordzie, przed/po i kandydaci](../../../../docs/asdlc/verification/PBI-101-review/review.md).
[Zalecenia według ID](../../../../docs/asdlc/verification/PBI-101-review/recommendations.json).
[Warunkowy diff izolowanej symulacji](../../../../docs/asdlc/verification/PBI-101-review/simulated-domain.patch).
[Dowody i warunki kontynuacji](../../../../docs/asdlc/verification/PBI-101.md).

Pełne wejścia i execution są w changes.json; decyzje pending w decisions.yml.
Propozycje: A001–A578 bez zmian katalogu, B001–B031 dopisanie lokalizacji
i osobne keep best/jawny tryb, C001–C005 nowy Obiekt/Jaskinia,
D001–D026 odroczenia ze wskazaniem kandydatów. To zalecenia, bez akceptacji.

Snapshot pbi-101-live-20261019 utrwalono przed przygotowaniem paczki
w 60afeca2d17bbc4b5aa690abc83da1d25d89a506. Przyjęty stan pochodzi
wyłącznie z origin/main b98fd3febb400c7ee520046682c1bb16238429ee.
Nie nadpisywać wejść, nie stosować zalecanych decyzji bez rozstrzygnięcia użytkownika.
