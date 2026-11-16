# Air Check — stan i plan

Stan na 2026-11-14, wersja 1.0.0. Jedna strona do orientacji; szczegóły w dokumentach z §6.

**Najważniejszy wynik (rekonstrukcja, ostatnie 365 dni do 2026-11-13):** prognoza pyłu PM2.5 z Copernicus (CAMS)
jest wyraźnie lepsza od reguły „jutro jak dziś” w 9 z 28 miast, wyraźnie gorsza w 7, a w 12 nie ma wyraźnej różnicy.
To wynik opisowy. Test potwierdzający na żywo trwa od 2026-11-16 do 2027-02-13.

**Przepływ danych (jedno zdanie):** pomiary ze stacji (EEA) i prognoza (CAMS) → co rano automat w GitHub Actions
→ małe tabele w repozytorium → panel publiczny (GitHub Pages) i punkty mapy dla strony geoworldlook.

**Cel:** mieszkaniec, dziennikarz albo urzędnik widzi, czy prognozie smogu w jego mieście można ufać.
Nie mówimy nic o zdrowiu ani o normach prawnych.

## 1. Wersja 1.0.0 — produkt

- **Panel (EN):** 28 miast w 7 krajach (Polska, Włochy, Francja, Szwajcaria, Norwegia, Szwecja, Finlandia).
  Mapa, prognoza na jutro, werdykt dla miasta, wykres ostatnich 120 dni, dni z wysokim pyłem w każdym roku od 2022.
- **Automat:** przebieg trzy razy dziennie (09:40, 13:40 i 18:40 UTC) w GitHub Actions; bramka jakości danych; przy błędzie zgłoszenie
  w repozytorium, które pierwszy udany przebieg sam zamyka.
- **Rekonstrukcja:** pomiary od 2022-01-01, prognozy z archiwum od 2023-11-01.
- **Kod:** pakiet `aircheck`, test bez sieci, CI (linter, test, budowa obrazu Dockera).

## 2. Co jest sprawdzone

| Co | Wynik | Status |
|---|---|---|
| Prognoza wobec reguły „jutro jak dziś”, 28 miast, ostatnie 365 dni | lepsza w 9, bez różnicy w 12, gorsza w 7 | opisowy (rekonstrukcja) |
| Zawyżenie prognozy zimą | Milano +19,3; Katowice +12,3; Warszawa +9,2; Torino +6,8 µg/m³ | opisowy |
| Dni powyżej 25 µg/m³: trafność prognozy wobec reguły | w wielu miastach bez przewagi prognozy (np. Warszawa 0,41 wobec 0,48) | opisowy |
| H-A1: prognoza na jutro lepsza w co najmniej 2/3 stacji | test w toku | protokół A1 |
| H-A2: prognoza lepiej trafia dni z wysokim pyłem | test w toku | protokół A1 |

## 3. Czego nie mówimy (granice)

- Jedna stacja na miasto i tylko PM2.5.
- Stacja to punkt, prognoza to kwadrat około 10 km.
- Archiwum zawiera prognozy o wyprzedzeniu poniżej doby. Prawdziwą prognozę na jutro mierzy dopiero test na żywo.
- Pomiary z bieżącego roku są niezweryfikowane.
- Przyczyny zawyżenia prognozy zimą nie badaliśmy.
- 19 z 47 miast-kandydatów nie weszło do rejestru (brak stacji tła w obu zbiorach EEA albo za dużo braków),
  w tym Kraków, Kopenhaga, Sztokholm i Oslo. Powody są w `aircheck/stations.csv`.

## 4. Decyzje

- **D-096:** Air Check jest projektem nr 3 w standardzie GeoWorldLook; Water Check projektem nr 4.
- **D-097:** rekonstrukcja od 2022 ma status opisowy; test potwierdzający tylko na danych po zapisaniu protokołu.
- **D-098:** oceniamy prognozy, nie reanalizę (reanaliza wchłania pomiary z tych samych stacji).
  Pomiary z EEA; prognozy przez Open-Meteo, docelowo wprost z serwisu Copernicus ADS.
- **D-100:** system działa w GitHub Actions; stan potoku to małe tabele w `data/`, wynik w `docs/showcase/`.
- **D-102:** stacja może mieć osobny punkt pomiarowy w danych zweryfikowanych i w bieżących; reguła wyboru
  stacji jest zapisana w `aircheck/registry.py` i nie była zmieniana po obejrzeniu wyników dla miast.

## 5. Dalej (propozycje do decyzji autora)

| Co | Kiedy | Uwagi |
|---|---|---|
| Werdykt testu A1 | po 2027-02-20 | te same reguły; wynik negatywny też raportujemy |
| Krajowe źródła danych bieżących (GIOŚ dla Krakowa i Rybnika) | po starcie | nowy plik w `sources/`, reguła wyboru bez zmian |
| Prognozy wprost z Copernicus ADS | po założeniu konta | prawdziwe archiwum prognoz na jutro z ostatnich 3 lat |
| Wymiana danych bieżących 2026 na zweryfikowane | jesień 2027 | `python -m aircheck backfill`, opis różnic |
| Wpis na blog | po werdykcie A1 | liczby z potoku, także to, co nie wyszło |

## 6. Gdzie co jest

| Temat | Dokument |
|---|---|
| Kod i moduły | `docs/ARCHITEKTURA.md` |
| Przejście przez jeden dzień systemu | `docs/PRZEWODNIK.md` |
| Uruchomienie i co robić przy błędzie | `docs/URUCHOMIENIE_LOKALNE.md` |
| Protokół testu potwierdzającego | `docs/evidence/A1_protokol_prognozy.md` |
| Przegląd stacji i przykład eksploracyjny | `docs/evidence/A0_przeglad_stacji.md` |
| Plan wdrożenia | `docs/plans/Plan_v1_air_check.md` |
| Zmiany wersji | `CHANGELOG.md` |
