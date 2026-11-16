# A2: wyniki skorygowanej prognozy (regresja MOS)

Przebieg z 2026-11-16, protokół `A2_protokol_korekta.md` (wersja 1, commit sprzed policzenia okresu odłożonego).
Liczby pochodzą z potoku (`docs/showcase/aircheck_data.json`), nie z obliczeń poza nim.

## 1. Werdykt (okres odłożony 2025-11-16 – 2026-11-15, 27 stacji)

| Hipoteza | Wynik | Werdykt |
|---|---|---|
| H-A3: prognoza skorygowana ma mniejszy RMSE niż reguła „jutro jak dziś” w co najmniej 2/3 stacji | 27 z 27 | potwierdzona |
| H-A4: prognoza skorygowana ma mniejszy RMSE niż prognoza surowa w co najmniej 2/3 stacji | 27 z 27 | potwierdzona |

Dla porównania: prognoza surowa wygrywa z regułą w 13 z 27 stacji.

| Miara (mediana po stacjach) | Prognoza surowa | Prognoza skorygowana | Reguła „jutro jak dziś” |
|---|---|---|---|
| RMSE, µg/m³ | 5,47 | 3,95 | 5,15 |
| Skill wobec reguły | −0,03 | 0,46 | 0 |

## 2. Stacje (od najmniejszej poprawy)

| Miasto | Dni | RMSE surowa | RMSE skorygowana | RMSE reguła | Skill surowa | Skill skorygowana |
|---|---|---|---|---|---|---|
| Grenoble | 358 | 5,62 | 3,90 | 4,38 | −0,65 | 0,21 |
| Annecy | 304 | 4,57 | 3,30 | 3,81 | −0,44 | 0,25 |
| Torino | 337 | 9,00 | 5,66 | 6,75 | −0,78 | 0,30 |
| Bolzano | 361 | 5,67 | 3,95 | 4,83 | −0,38 | 0,33 |
| Bordeaux | 360 | 5,08 | 4,59 | 5,63 | 0,19 | 0,34 |
| Brescia | 346 | 9,42 | 7,14 | 8,87 | −0,13 | 0,35 |
| Wrocław | 345 | 8,79 | 6,11 | 7,63 | −0,33 | 0,36 |
| Lugano | 330 | 5,47 | 4,08 | 5,15 | −0,13 | 0,37 |
| Zürich | 330 | 5,29 | 4,21 | 5,37 | 0,03 | 0,39 |
| Napoli | 316 | 6,55 | 3,50 | 4,53 | −1,09 | 0,40 |
| Roma | 327 | 5,50 | 4,63 | 6,08 | 0,18 | 0,42 |
| Łódź | 365 | 7,32 | 4,97 | 6,53 | −0,26 | 0,42 |
| Katowice | 365 | 18,78 | 4,81 | 6,45 | −7,47 | 0,44 |
| Strasbourg | 365 | 5,80 | 4,21 | 5,73 | −0,03 | 0,46 |
| Toulouse | 365 | 3,34 | 2,99 | 4,07 | 0,33 | 0,46 |
| Warszawa | 323 | 10,16 | 5,55 | 7,67 | −0,75 | 0,48 |
| Basel | 321 | 4,43 | 2,94 | 4,10 | −0,17 | 0,49 |
| Milano | 348 | 17,37 | 6,71 | 9,53 | −2,32 | 0,50 |
| Oulu | 346 | 1,83 | 1,51 | 2,16 | 0,28 | 0,51 |
| Göteborg | 353 | 3,47 | 2,66 | 3,79 | 0,16 | 0,51 |
| Marseille | 320 | 2,48 | 2,21 | 3,31 | 0,44 | 0,55 |
| Gdańsk | 360 | 6,43 | 5,26 | 7,89 | 0,34 | 0,56 |
| Tampere | 354 | 2,18 | 2,15 | 3,27 | 0,56 | 0,57 |
| Paris | 357 | 3,76 | 3,23 | 5,00 | 0,44 | 0,58 |
| Lyon | 350 | 3,64 | 3,36 | 5,63 | 0,58 | 0,64 |
| Malmö | 346 | 2,61 | 2,41 | 4,05 | 0,58 | 0,65 |
| Helsinki | 365 | 2,58 | 2,20 | 3,86 | 0,56 | 0,68 |

## 3. Dni z wysokim pyłem (opisowo, bez progu)

Wskaźnik trafień CSI dla dni powyżej 25 µg/m³ w miastach z największą liczbą takich dni:

| Miasto | Surowa | Skorygowana | Reguła |
|---|---|---|---|
| Milano | 0,53 | 0,74 | 0,65 |
| Brescia | 0,71 | 0,73 | 0,65 |
| Katowice | 0,47 | 0,61 | 0,48 |
| Wrocław | 0,59 | 0,67 | 0,60 |
| Torino | 0,54 | 0,59 | 0,51 |
| Łódź | 0,50 | 0,56 | 0,50 |
| Warszawa | 0,42 | 0,54 | 0,48 |
| Gdańsk | 0,65 | 0,69 | 0,49 |

W kilku miastach z małą liczbą takich dni trafność prognozy skorygowanej zostaje poniżej reguły:
Basel (0,17 wobec 0,33), Annecy (0,00 wobec 0,33), Bordeaux (0,20 wobec 0,23).

## 4. Wybór metody (okres rozwojowy, dni do 2025-11-15)

Plik `A2_wybor_korekty.csv`. Liczba stacji z RMSE mniejszym niż reguła (z 27) i mediana skill:

| Metoda | Stacje | Mediana skill |
|---|---|---|
| Regresja MOS, okno 365 dni (wybrana) | 27 | 0,43 |
| Regresja MOS, okno 60 dni | 27 | 0,42 |
| Regresja MOS, okno 120 dni | 27 | 0,40 |
| Korekta mnożnikowa, 14 dni | 24 | 0,32 |
| Filtr Kalmana, r = 0,15 | 22 | 0,37 |
| Metoda hybrydowa | 21 | 0,24 |
| Korekta addytywna, 7 dni | 19 | 0,27 |

## 5. Co z tego wynika i czego nie

- Prosta korekta na stacji zamienia prognozę, która w połowie miast przegrywa z regułą, w prognozę lepszą od reguły
  wszędzie. Największy zysk jest tam, gdzie prognoza surowa ma duży stały błąd.
- Korekta korzysta z pomiaru z poprzedniego dnia. To ta sama informacja, z której korzysta reguła „jutro jak dziś”,
  więc porównanie jest uczciwe; część zysku pochodzi właśnie z tego pomiaru, a część z prognozy.
- Wynik dotyczy prognoz z archiwum (wyprzedzenie poniżej doby). Prawdziwą prognozę na jutro (z pomiarem sprzed dwóch
  dni) sprawdza test na żywo: okno 2026-11-18 – 2027-02-15.
- Korekta nie tłumaczy, dlaczego prognoza surowa zawyża zimą. Tego nie badaliśmy.
