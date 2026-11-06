# U17 — oceń bezpośredni odczyt danych eksportowych

Czytaj [indeks](README.md), [spec](spec.md) i [odbiór](../development.md).
Zależność: U16. To ograniczona analiza/prototyp, nie zgoda na zmianę
produkcyjnego modelu eksportu. Wynikiem może być pozostawienie obecnego kodu.

## Zakres i interfejs

Porównaj `postgres.Catalog.dataset()` → `prepare_export_data()` z bezpośrednim
odczytem SQL do obecnego `ExportData`. `export_data.py`, `postgres.py` i
`schema/catalog.sql` są obszarem badania; eksportery zachowują pola, typy,
kolejność i sposób wywołania. Prototyp trzymaj poza produkcyjnymi ścieżkami.

## Kroki i kryteria

- [ ] Policz pozostałych odbiorców zagnieżdżonej projekcji po U15. Oddziel
  historię źródła od pól potrzebnych Best/Full oraz informacji o regionach.
- [ ] Zbuduj minimalny prototyp na małym katalogu: manual/auto Best,
  historia z null, obie geometrie źródłowe, bibliografia, referencje,
  relacje, załączniki oraz puste legalne zbiory.
- [ ] Porównaj wszystkie pola i kolejność z niezależnymi oczekiwaniami;
  dla pełnego katalogu porównaj wszystkie eksporty ze stałymi metadanymi.
- [ ] Zmierz łączny bilans Python+SQL, liczbę zapytań/konwersji i miejsca
  wymagające zmiany przy dodaniu pola. Samo przeniesienie kodu do SQL
  lub nowego modułu nie jest redukcją.
- [ ] Zapisz zwięzły wynik w tej karcie: rekomendowany wariant, bilans,
  zgodność i ograniczenia. Gdy wariant upraszcza całość, przedstaw konkretny
  interfejs oraz osobną kartę wdrożenia do akceptacji; inaczej zakończ temat.
- [ ] Dostarcz wyłącznie wynik analizy, bez pozostawiania prototypu w runtime,
  bez rozszerzania liczby formatów i bez samodzielnego rozpoczęcia implementacji.
