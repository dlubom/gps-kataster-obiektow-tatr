# Porównanie silników

[summary.json](summary.json) zawiera wynik 601 stacji, osiem otworów, kontrole
wag i walidację natywną. `walls-source.lst` używa snapshotu GPS v1.3.1;
`walls-new-anchor.lst` nowej kotwicy Raptawickiej. To rzeczywiste raporty Walls.
16 SRV, WPJ i OTWORY są bajtowo identyczne między sprawdzonym `2c82f5d`
a publikowanym `880cbde`; hashe są w podsumowaniu. Zmienił się tylko README.

Po [odbudowaniu sieci](../rebuild_network.py) z nową kotwicą, z katalogu repo:

```sh
python3 docs/asdlc/verification/PBI-117/engines/compare.py --walls-lst docs/asdlc/verification/PBI-117/engines/walls-new-anchor.lst --survex-dump /tmp/pawlikowski-consumer/dump.txt --output /tmp/engine-comparison.json
python3 docs/asdlc/verification/PBI-117/engines/emulate_weights.py --network /tmp/pawlikowski-consumer --walls-lst docs/asdlc/verification/PBI-117/engines/walls-new-anchor.lst --output /tmp/engine-weight-controls
```

Druga komenda wymaga Survex 1.4.24 i nowego katalogu wyjściowego. Zmienia
kolejność powtórzeń i wariancje wyłącznie w kopiach kontrolnych. Odtwarza
Walls do dokładności zapisu `.3d`; produkcyjny wzorzec pozostaje Survex.

[sources.json](sources.json) przypina wersje, hashe i dokumentację.
`walls-export-driver.c` rozszerza sterownik ze wskazanego skilla JKTZ o LST;
kompilacja MinGW wymaga `-luser32`. Natywny przebieg wymaga osobnego
Wine prefixu i świeżego katalogu, zgodnie z tym skillem. EXE nie jest dołączony.
