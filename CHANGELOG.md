# Changelog

Wszystkie istotne zmiany w projekcie "GPS Kataster Obiektow Tatr" sa
udokumentowane w tym pliku.

Format jest oparty o [Keep a Changelog](https://keepachangelog.com/), a
wersjonowanie od `v1.0.0` stosuje [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Zmieniono

- Usunieto dodatkowa runtime'owa bramke licencyjna z workflow release;
  licencja CC BY 4.0 pozostaje opisana w `LICENSE` i dokumentacji.
- Doprecyzowano dokumentacje AS-DLC/spec/operacyjna: release pozostaje reczny,
  semverowy i tagowany, bez automatycznego buildu po `main`.

## [v1.0.1] - 2026-05-17

Patch release z korekta wysokosci dla Jaskini Bandzioch Kominiarski.

### Naprawiono

- Uzupelniono wysokosc recznego pomiaru GNSS gornego otworu Bandziocha
  Kominiarskiego (`LEJ-0002`, `BandziochKom:136`) na `1675.02 m`.
- Dolny otwor Bandziocha (`KSZ-0112`, `BandziochKom:000`) pozostaje z
  wysokoscia `1451.06 m`; eksporty `best-measurements` zawieraja teraz
  wysokosci obu otworow.

## [v1.0.0] - 2026-05-17

Pierwsze formalne wydanie semver dla katalogu GPS/GNSS obiektow tatrzanskich.

### Dodano

- Changelog jako zrodlo notatek do GitHub Release.
- Link do najnowszego wydania w README.
- Opis recznego procesu wydania: wpis w changelogu, commit, annotated tag
  `vX.Y.Z` i push taga.

### Zmieniono

- Wersjonowanie repo przechodzi z tagow kalendarzowych `v2026.05.x` na semver
  `vX.Y.Z`, analogicznie do Jaskiniowego Katastru Tatr Zachodnich.
- GitHub Release jest publikowany wylacznie po recznym pushu taga `v*`, a
  notatki release sa wyciagane z odpowiadajacej sekcji `CHANGELOG.md`.
- Dokumentacja operacyjna opisuje recznie tagowane wydania zamiast cyklicznych
  paczek danych.

### Usunieto

- Automatyczny workflow budujacy artefakty po kazdym pushu na `main`.
