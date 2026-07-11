[🇵🇱 Polski](README.md) | 🇸🇰 **Slovenčina**

# GPS kataster objektov Tatier

[![Latest Release](https://img.shields.io/github/v/release/dlubom/gps-kataster-obiektow-tatr)](https://github.com/dlubom/gps-kataster-obiektow-tatr/releases/latest)

[Stiahnite si najnovšie údaje](https://github.com/dlubom/gps-kataster-obiektow-tatr/releases/latest)

## Popis projektu

GPS kataster objektov Tatier je otvorený, priebežne rozvíjaný súbor súradníc
vchodov do jaskýň a ďalších objektov dôležitých pre speleológiu a kras na
oboch stranách Tatier: štôlní, ponorov, vyvieračiek a príbuzných objektov.

Projekt spája terénne merania GPS a GNSS s katalógovými a inštitucionálnymi
údajmi. Pri každej polohe zachováva jej zdroj, presnosť, stav overenia a
históriu. Každý konkrétny vchod je samostatným objektom, preto možno správne
opísať aj jaskyne s viacerými vchodmi.

Jaskyniar si môže stiahnuť body do GPS prijímača alebo telefónu a kartograf či
výskumník ich môže použiť v GIS a zistiť, do akej miery bola daná poloha
overená.

## Stiahnutie údajov

Tu si môžete stiahnuť najnovšiu verziu údajov:
[GitHub Releases](https://github.com/dlubom/gps-kataster-obiektow-tatr/releases/latest).

Každé vydanie obsahuje hotové súbory na prácu v teréne aj pri počítači:

| Formát | Na čo sa najlepšie hodí |
|---|---|
| GPX | body v GPS prijímači alebo terénnej aplikácii |
| GeoJSON a Shapefile | mapa, analýza a spájanie vrstiev v QGIS alebo inom GIS |
| CSV | prezeranie, filtrovanie a spájanie údajov v tabuľke |
| SQLite | podrobnejšia analýza objektov, jaskýň, meraní a ich histórie |

Balík obsahuje aj `metadata.json` s verziou údajov a základnými informáciami
o počte záznamov vo vydaní.

## Presnosť a overenie

Body pochádzajú z rôznych rokov, zariadení a zdrojov, preto nemajú rovnakú
presnosť. Označenie „najlepšie dostupné meranie“ automaticky neznamená, že
bolo potvrdené v teréne. Pred použitím bodu skontrolujte zdroj, stav overenia,
deklarovanú presnosť a poznámky.

V prvých vydaniach môže mať väčšina najlepších meraní stav
`verification_status: nieweryfikowany` (neoverené). Znamená to, že bod pochádza
z importovaných alebo prepísaných zdrojových údajov a zatiaľ nebol overený v
teréne ani skontrolovaný správcom projektu. Neznamená to automaticky chybu ani
chýbajúci zdroj; kým nebude k dispozícii lepšie meranie, zostáva najlepšou
dostupnou polohou.

## Tri prepojené projekty

Tri repozitáre opisujú rovnaké územie z rôznych pohľadov:

| Projekt | Odpovedá na otázku | Čo poskytuje |
|---|---|---|
| **GPS kataster objektov Tatier** (tento projekt) | Kde sa nachádza konkrétny vchod alebo iný terénny objekt? | Najlepšie dostupné súradnice spolu so zdrojom, históriou a stavom overenia. |
| [Tatranský kataster jaskýň](https://github.com/dlubom/Jaskiniowy-Kataster-Tatr-Zachodnich) | Kadiaľ vedú polygónové ťahy a aká je geometria podzemia? | Jaskynné merania pre Walls a Survex, 2D vizualizácie a [3D model](https://dlubom.github.io/Jaskiniowy-Kataster-Tatr-Zachodnich/) jaskýň s dostupnými meraniami; hotové súbory sú v [najnovšom vydaní](https://github.com/dlubom/Jaskiniowy-Kataster-Tatr-Zachodnich/releases/latest). |
| [Georeferencer](https://github.com/dlubom/Georeferencer) | Ako možno naskenovaný plán jaskyne umiestniť na mapu? | Georeferencované skeny plánov vo formáte GeoTIFF, aj pre jaskyne bez údajov z meraní v Tatranskom katastri jaskýň; balík je v [najnovšom vydaní](https://github.com/dlubom/Georeferencer/releases/latest). |

GPS kataster je spoločným zdrojom súradníc vchodov: Tatranský kataster
jaskýň aj Georeferencer používajú najlepšie merania zverejnené v tomto
projekte.

## Ako môžete pomôcť

Ak máte presnejšie meranie GPS/GNSS, poznáte chýbajúci vchod alebo vidíte
nesprávne priradenie, vytvorte
[hlásenie](https://github.com/dlubom/gps-kataster-obiektow-tatr/issues) alebo
pripravte pull request. Uveďte názov jaskyne a konkrétneho vchodu, súradnice,
dátum, metódu alebo zariadenie, odhadovanú presnosť a zdroj údajov. Rozlíšenie
jednotlivých vchodov tej istej jaskyne je mimoriadne dôležité.

## Pre vývojárov a správcov údajov

Zdrojom pravdy sú súbory YAML v `data/`. SQLite, GeoJSON, GPX, CSV a Shapefile
sú artefakty generované z týchto súborov.

`Obiekt` označuje konkrétny bod v teréne a `Jaskinia` je katalógový záznam,
ktorý zoskupuje jeden alebo viac vchodov. Každý objekt uchováva úplnú históriu
meraní a určenie najlepšieho aktuálneho merania.

### Rýchly štart

```bash
uv sync
uv run pytest
uv run python scripts/validate.py
uv run python scripts/build_release_artifacts.py
```

Lokálne artefakty vznikajú v `build/` a neukladajú sa do Gitu.

### Dokumentácia projektu

- [Špecifikácia a doménový model](specyfikacja_gps_kataster_obiektow_tatr_v_2.md)
- [Pridávanie a overovanie meraní](docs/operations.md)
- [Formáty a polia súborov vydania](docs/release_artifacts.md)
- [CHANGELOG.md](CHANGELOG.md)

Verejné vydania používajú sémantické verzovanie a tagy v tvare `vX.Y.Z`;
publikujú sa ručne. Repozitár, dokumentácia a generované exporty údajov sú
licencované za podmienok Creative Commons Attribution 4.0 International podľa
súboru [LICENSE](LICENSE).
