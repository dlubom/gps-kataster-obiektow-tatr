# Ochrona best — manifest do akceptacji

Status: pending. Raport nie zatwierdza ani nie wykonuje migracji.

Katalog: `4b028a27efff27eb77eff21a07e26b0eb82ad07bd16b09a8ff3f373ed1e8989e`

| Obiekt | Best | Tryb | Podstawa |
|---|---|---|---|
| KSW-0189 | m-003 | manual | elevation_gnss, manual, method_gnss, tag_gnss |
| KSW-0201 | m-003 | auto | own_verified, tag_gnss_anchor |
| KSW-0240 | m-002 | auto | own_verified, tag_gnss_anchor |
| KSW-0257 | m-002 | manual | elevation_gnss, manual, method_gnss, tag_gnss |
| KSZ-0047 | m-003 | manual | elevation_gnss, manual, method_gnss, tag_gnss |
| KSZ-0064 | m-003 | manual | elevation_gnss, manual, method_gnss, tag_gnss |
| KSZ-0090 | m-003 | manual | elevation_gnss, manual, method_gnss, tag_gnss |
| KSZ-0112 | m-001 | auto | elevation_gnss, method_gnss, tag_gnss |
| LEJ-0002 | m-003 | manual | elevation_gnss, manual, method_gnss, tag_gnss |

## Proponowane migracje auto → manual

- KSW-0201/m-003: Ochrona istniejącego wyboru best przed synchronizacją TPN: own_verified, tag_gnss_anchor. Zachowano pomiar m-003; bez zmiany współrzędnych, statusu i dokładności.
- KSW-0240/m-002: Ochrona istniejącego wyboru best przed synchronizacją TPN: own_verified, tag_gnss_anchor. Zachowano pomiar m-002; bez zmiany współrzędnych, statusu i dokładności.
- KSZ-0112/m-001: Ochrona istniejącego wyboru best przed synchronizacją TPN: elevation_gnss, method_gnss, tag_gnss. Zachowano pomiar m-001; bez zmiany współrzędnych, statusu i dokładności.
