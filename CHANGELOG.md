# Changelog

Wszystkie istotne zmiany w projekcie "GPS Kataster Obiektow Tatr" sa
udokumentowane w tym pliku.

Format jest oparty o [Keep a Changelog](https://keepachangelog.com/), a
wersjonowanie od `v1.0.0` stosuje [Semantic Versioning](https://semver.org/).

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
