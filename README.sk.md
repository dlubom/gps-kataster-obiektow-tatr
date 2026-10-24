[🇵🇱 Polski](README.md) | [🇬🇧 English](README.en.md) | 🇸🇰 **Slovenčina**

# GPS kataster objektov Tatier

[![Latest Release](https://img.shields.io/github/v/release/dlubom/gps-kataster-obiektow-tatr)](https://github.com/dlubom/gps-kataster-obiektow-tatr/releases/latest)

**[Stiahnuť GPS body — GPX](https://github.com/dlubom/gps-kataster-obiektow-tatr/releases/latest/download/best-measurements.gpx)** · [Všetky súbory a popis vydania](https://github.com/dlubom/gps-kataster-obiektow-tatr/releases/latest)

## Čo tu nájdete

Súradnice jaskynných vchodov a štôlní v Tatrách spolu so zdrojmi údajov
a históriou meraní. Každý vchod je samostatný bod — jedna jaskyňa tak môže
mať viac bodov. Súbor údajov sa rozrastá a nie je úplným súpisom objektov
na poľskej ani slovenskej strane Tatier.

Jaskyniar si môže nahrať body do GPS prijímača a kartograf
ich využiť v mapovom programe, napríklad QGIS. Hotové súbory si stiahnete
bez účtu GitHub a bez inštalácie programátorských nástrojov.

## Stiahnutie údajov

[Otvorte najnovšie vydanie](https://github.com/dlubom/gps-kataster-obiektow-tatr/releases/latest), rozbaľte **Assets** (súbory na stiahnutie)
a vyberte názov z tabuľky.

| Chcem… | Súbor na stiahnutie |
|---|---|
| Nahrať body do GPS prijímača | [GPX — `best-measurements.gpx`](https://github.com/dlubom/gps-kataster-obiektow-tatr/releases/latest/download/best-measurements.gpx) |
| Otvoriť prehľadnú tabuľku v Exceli | `katalog.xlsx` — hárky **Best** a **Full** |
| Stiahnuť tabuľku CSV | [CSV — `best-measurements.csv`](https://github.com/dlubom/gps-kataster-obiektow-tatr/releases/latest/download/best-measurements.csv) |
| Pracovať s bodovou vrstvou v QGIS alebo inom mapovom programe | `best-measurements.geojson` alebo `best-measurements.shp.zip` |
| Analyzovať celú históriu meraní | `katalog.sqlite.zip` — databáza pre pokročilých používateľov |

Excel bude dostupný vo vydaniach po v1.0.4. **Best** obsahuje vybrané body,
**Full** podrobné údaje a históriu meraní vrátane starších a zamietnutých.
Súbor má filtre a ukotvené hlavičky. Názvy stĺpcov sú po poľsky.

### Menšie súbory GPX

Úplný `best-measurements.gpx` obsahuje celý súbor údajov. Pre aplikácie
s limitom importu vznikajú aj tri ďalšie súbory, každý najviac s **500 bodmi**:

| Súbor | Oblasť |
|---|---|
| `chocholowska-lejowa-koscieliska.gpx` | Celé doliny Chochołowska, Lejowa a Kościeliska. |
| `mietusia-sucha-woda.gpx` | Od Miętusiej cez Małej Łąki a podhorské doliny po Bystrej, Olczyskú a Suchej Wody. |
| `pozostale-pl-sk.gpx` | Body v Poľsku a na Slovensku mimo hraníc našich regiónov dolín. |

Tieto tri súbory spolu obsahujú všetky body, každý práve raz. Východná
a západná časť každej doliny zostávajú spolu. Zaradenie vychádza z polohy
vybraného merania. Súbory budú dostupné vo vydaniach po v1.2.1.

## Presnosť a overenie

Mnohé polohy pochádzajú z katalógov a neboli potvrdené v teréne.
„Najlepšie dostupné meranie“ je výber z údajov, ktoré máme, nie záruka
presnej polohy vchodu. Neuvedená presnosť znamená **neznámu presnosť**.

Vo vydaniach po v1.0.4 zobrazujú štítky GPX názvy vchodov a ďalších objektov;
ID bodu zostáva v popise (pri chýbajúcom názve aj v štítku).
GPX obsahuje zdroj a poznámky, ale nemá samostatné polia pre stav
overenia a presnosť. Nájdete ich v [tabuľke CSV](https://github.com/dlubom/gps-kataster-obiektow-tatr/releases/latest/download/best-measurements.csv): otvorte ju v tabuľkovom
procesore a vyhľadajte kód bodu v stĺpci `object_id`. V Exceli mu zodpovedá
„ID obiektu“: overenie a presnosť sú v Best, úplné poznámky vo Full.

| Stĺpec v tabuľke | Ako ho čítať |
|---|---|
| `verification_status` | `nieweryfikowany`: zatiaľ nepotvrdené v projekte, nie nevyhnutne chybné. `zweryfikowany`: prijaté po posúdení zdrojov alebo kontrole v teréne. `odrzucony`: považované za chybné alebo nevhodné. |
| `horizontal_accuracy_m` | Uvedená vodorovná presnosť v metroch. Prázdne pole znamená, že údaj chýba. |
| `source`, `source_ref` | Pôvod merania a odkaz na zdroj, napríklad TPN alebo PIG. |
| `measurement_notes` | Poznámky k meraniu, rozdielom a obmedzeniam polohy. |

## Koľko údajov je overených

Vydania po v1.0.4 budú na [stránke najnovšieho vydania](https://github.com/dlubom/gps-kataster-obiektow-tatr/releases/latest) obsahovať
rozbaľovacie **Štatistiky vydania (SK)**, aj po poľsky a anglicky. Tabuľky
sa vytvárajú automaticky z toho istého balíka údajov. Uvádzajú počty objektov,
jaskýň a meraní, druhy objektov, zdroje, stavy overenia a počty bodov s uvedenou
a neznámou presnosťou. Body na stiahnutie a celá história meraní sa počítajú
oddelene. Vydanie v1.0.4 a staršie tieto tabuľky neobsahujú.

## Body na mape

![Rozmiestnenie bodov zo súboru údajov na mape Tatier](docs/images/tatry-regiony-osm.png)

**[Otvoriť veľkú mapu s čitateľnou legendou](docs/images/tatry-regiony-osm.png?raw=true)**

Farby označujú regióny dolín; čísla v legende sú počty objektov v súbore,
nie počty jaskýň ani úplnosť prieskumu doliny. PL a SK označujú body mimo
vymedzených regiónov dolín. Farba nevyjadruje presnosť ani stav overenia.
Popisy v mapách sú po poľsky.

<details>
<summary>Zobraziť detail: Dolina Kościeliska a okolie</summary>

![Body v Doline Kościeliskej a okolí s označenými príkladmi jaskýň](docs/images/dolina-koscieliska-osm.png)

[Otvoriť detail v plnej veľkosti](docs/images/dolina-koscieliska-osm.png?raw=true).
Ružové body predstavujú jedno vybrané meranie každého objektu v zábere.

</details>

Obe mapy sú statické náhľady z **2026-10-16** a neaktualizujú sa so súbormi
na stiahnutie. Mapový podklad: © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright)
(ODbL). [Zdroj a príprava ilustrácií](docs/images/README.md).

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

## Kontakt a opravy

Máte lepšie meranie, poznáte chýbajúci vchod alebo ste našli chybu? Najjednoduchšie
je napísať Darkovi e-mail: **darek.lubomski [zavináč] gmail [bodka] com**.
Nahraďte `[zavináč]` znakom `@` a `[bodka]` znakom `.` a odstráňte medzery.

Môžete tiež [nahlásiť meranie alebo chybu na GitHube](https://github.com/dlubom/gps-kataster-obiektow-tatr/issues/new?title=Meranie+alebo+oprava&body=Jasky%C5%88a+a+vchod+%2F+k%C3%B3d+bodu%3A%0AS%C3%BAradnice%3A%0AD%C3%A1tum+a+zariadenie+%2F+met%C3%B3da%3A%0APresnos%C5%A5+%28ak+je+zn%C3%A1ma%29%3A%0AZdroj+a+popis+opravy%3A%0AFotografia+alebo+pozn%C3%A1mky%3A%0A). Formulár obsahuje
pomôcky a vyžaduje účet GitHub. Hlásenia sú verejné.

Uveďte názov jaskyne a konkrétneho vchodu (alebo kód bodu), súradnice, dátum,
zariadenie alebo metódu, známu presnosť a zdroj údajov. Fotografia vchodu
alebo popis prístupu pomôže s identifikáciou. Neznáme údaje označte ako neznáme;
súbory projektu nemusíte upravovať sami.

## Pre vývojárov a správcov údajov

Zdrojom pravdy sú súbory YAML v `data/`. SQLite, GeoJSON, GPX, CSV, Excel a Shapefile
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
