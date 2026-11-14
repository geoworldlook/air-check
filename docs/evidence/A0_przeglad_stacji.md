# A0: przegląd stacji i przykład eksploracyjny

Zapis z 2026-11-14, przed protokołem A1. Wyniki z tego dokumentu są eksploracyjne.

## 1. Źródła i co sprawdzono

| Co | Źródło | Zakres | Sprawdzone 2026-11-14 |
|---|---|---|---|
| Pomiary zweryfikowane | EEA, zbiór E1a | 2021–2025 | odczyt plików bez klucza |
| Pomiary bieżące | EEA, zbiór UTD | 2026, do bieżącej godziny | odczyt plików bez klucza |
| Prognoza | CAMS przez Open-Meteo | prognozy od X 2023; reanaliza od 2013 | odczyt bez klucza |
| Prognoza (docelowo) | CAMS, serwis ADS | archiwum kroczące 3 lata | według strony ADS; wymaga konta |

## 2. Reguła wyboru stacji

Zapisana w `aircheck/registry.py`. Dla każdego miasta:

1. punkty pomiarowe PM2.5 do 15 km od centrum (20 km dla dużych aglomeracji);
2. stacja typu „background” w obszarze miejskim lub podmiejskim;
3. plik w zbiorze zweryfikowanym i w zbiorze bieżącym (mogą to być dwa punkty pomiarowe tej samej stacji);
4. wygrywa stacja o najwyższej najmniejszej rocznej kompletności dni 2022–2026;
5. miasto wchodzi do rejestru przy kompletności co najmniej 75% w każdym roku.

## 3. Wynik: 28 z 47 miast

| Kraj | Kandydaci | Przyjęte | Odrzucone i powód |
|---|---|---|---|
| Polska | 9 | 5 | Kraków, Rybnik, Nowy Sącz: brak stacji tła w danych bieżących EEA; Poznań: 70% dni w 2023 |
| Włochy | 10 | 6 | Bologna, Venezia, Padova: brak w danych bieżących; Firenze: 43% |
| Francja | 9 | 8 | Lille: brak danych w jednym z lat |
| Szwajcaria | 4 | 3 | Bern: jedyna stacja z danymi stoi przy ulicy |
| Norwegia | 5 | 1 | Oslo 65%, Stavanger 73%; Trondheim, Tromsø: brak stacji tła w danych bieżących |
| Szwecja | 5 | 2 | Stockholm 57%, Uppsala 58% (braki w 2026); Umeå: brak stacji tła |
| Dania | 2 | 0 | brak stacji tła w danych bieżących |
| Finlandia | 3 | 3 | — |

Pełna lista z kompletnością w każdym roku: `aircheck/stations.csv`.

Uwagi:

- Szwajcaria podaje w danych zweryfikowanych wartości dobowe, a w bieżących godzinowe. Potok obsługuje oba rodzaje.
- Filtr miast w usłudze EEA zwracał błędne stacje dla Włoch, dlatego reguła używa odległości od centrum.
- W Krakowie stacje tła (ul. Bujaka, os. Piastów) są tylko w danych zweryfikowanych. W danych bieżących EEA
  jest stacja przy ulicy i stacja przemysłowa, których reguła nie dopuszcza.

## 4. Dlaczego nie oceniamy prognoz sprzed XI 2023

Archiwum prognoz u dostawcy zaczyna się w X 2023. Za wcześniejsze lata dostępna jest tylko reanaliza CAMS.
Reanaliza wchłania pomiary z tych samych stacji, więc jej zgodność ze stacjami jest pozorna: w próbie
(Warszawa, Paryż, Lyon, I 2022 – IX 2023) korelacja dobowa wyniosła 0,98–0,99. Reanalizy nie używamy jako dowodu.

## 5. Przykład eksploracyjny (przed protokołem)

20 miast z pierwszej, roboczej listy stacji, XI 2023 – X 2026, średnie dobowe, prognozy z archiwum:

| Miara | Wynik |
|---|---|
| Prognoza ma mniejszy RMSE niż „jutro jak dziś” | 13 z 20 miast |
| Miasta, gdzie prognoza przegrywa lub remisuje | Warszawa, Katowice, Łódź, Torino, Grenoble, Strasbourg, Annecy |
| Dni powyżej 25 µg/m³: prognoza trafia lepiej (miasta z co najmniej 20 takimi dniami) | 7 z 13 miast |

Ten wynik był znany przy pisaniu protokołu A1 i jest tam ujawniony (punkt 7 protokołu).
