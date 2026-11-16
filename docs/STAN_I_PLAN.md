# Air Check — stan i plan

Stan na 2026-11-16, wersja 1.1.0. Jedna strona do orientacji; szczegóły w dokumentach z §6.

**Najważniejszy wynik (okres odłożony 2025-11-16 – 2026-11-15, protokół A2):** prognoza pyłu PM2.5 z Copernicus
po prostej korekcie na stacji jest lepsza od reguły „jutro jak dziś” w 27 z 27 miast i lepsza od prognozy surowej
w 27 z 27. Prognoza surowa wygrywa z regułą tylko w 13 z 27 miast. Mediana błędu spada z 5,5 do 4,0 µg/m³.
Metoda korekty została wybrana na wcześniejszych danych i zamrożona przed policzeniem tego roku.

**Przepływ danych (jedno zdanie):** pomiary ze stacji (EEA) i prognoza (CAMS) → trzy razy dziennie automat w GitHub
Actions → małe tabele w repozytorium → panel publiczny (GitHub Pages) i punkty mapy dla strony geoworldlook.

**Cel:** mieszkaniec, dziennikarz albo urzędnik widzi, czy prognozie smogu w jego mieście można ufać, i dostaje
prognozę poprawioną. Nie mówimy nic o zdrowiu ani o normach prawnych.

## 1. Wersja 1.1.0 — produkt

- **Panel (EN):** 27 miast w 6 krajach (Polska, Włochy, Francja, Szwajcaria, Szwecja, Finlandia). Mapa, skorygowana
  i surowa prognoza na jutro, ostatni pomiar ze stacji, błędy obu prognoz i reguły, wykres ostatnich 120 dni.
- **Korekta prognozy:** regresja na stacji (pomiar = a + b · prognoza + c · ostatni znany pomiar), okno 365 dni,
  bez zaglądania w przyszłość. Skorygowana prognoza na jutro jest zapisywana w dniu wydania.
- **Automat:** przebieg trzy razy dziennie (09:40, 13:40 i 18:40 UTC) w GitHub Actions; bramka jakości danych; przy
  błędzie zgłoszenie w repozytorium, które pierwszy udany przebieg sam zamyka.
- **Rekonstrukcja:** pomiary od 2022-01-01, prognozy z archiwum od 2023-11-01.
- **Kod:** pakiet `aircheck`, test bez sieci (51 sprawdzeń), CI (linter, test, budowa obrazu Dockera).

## 2. Co jest sprawdzone

| Co | Wynik | Status |
|---|---|---|
| H-A3: prognoza skorygowana lepsza od reguły w co najmniej 2/3 stacji (okres odłożony) | 27 z 27 | potwierdzona (A2) |
| H-A4: prognoza skorygowana lepsza od surowej w co najmniej 2/3 stacji (okres odłożony) | 27 z 27 | potwierdzona (A2) |
| Prognoza surowa wobec reguły, okres odłożony | lepsza w 13 z 27 | opisowy |
| Prognoza surowa, ostatnie 365 dni, werdykt z przedziałem ufności | lepsza w 9, bez różnicy w 11, gorsza w 7 | opisowy |
| Zawyżenie prognozy surowej zimą | Milano +19; Katowice +12; Warszawa +9; Torino +7 µg/m³ | opisowy |
| H-A1, H-A2: prognoza surowa na jutro, test na żywo | w toku do 2027-02-13 | protokół A1 |
| H-A3, H-A4: prognoza skorygowana na jutro, test na żywo | w toku do 2027-02-15 | protokół A2 |

## 3. Czego nie mówimy (granice)

- Jedna stacja na miasto i tylko PM2.5.
- Stacja to punkt, prognoza to kwadrat około 10 km.
- Archiwum zawiera prognozy o wyprzedzeniu poniżej doby. Prawdziwą prognozę na jutro mierzą dopiero testy na żywo.
- Korekta potrzebuje świeżych pomiarów; bez nich wraca do prognozy surowej.
- Część zysku korekty pochodzi z pomiaru z poprzedniego dnia, a nie z samej prognozy.
- Przyczyny zawyżenia prognozy surowej zimą nie badaliśmy.
- 20 z 47 miast-kandydatów nie ma w rejestrze (brak stacji tła w obu zbiorach EEA, za dużo braków albo brak danych
  bieżących), w tym Kraków, Kopenhaga, Sztokholm, Oslo i Bergen.

## 4. Decyzje

- **D-096:** Air Check jest projektem nr 3 w standardzie GeoWorldLook; Water Check projektem nr 4.
- **D-097:** rekonstrukcja od 2022 ma status opisowy; test potwierdzający tylko na danych po zapisaniu protokołu.
- **D-098:** oceniamy prognozy, nie reanalizę (reanaliza wchłania pomiary z tych samych stacji).
  Pomiary z EEA; prognozy przez Open-Meteo, docelowo wprost z serwisu Copernicus ADS.
- **D-100:** system działa w GitHub Actions; stan potoku to małe tabele w `data/`, wynik w `docs/showcase/`.
- **D-102:** stacja może mieć osobny punkt pomiarowy w danych zweryfikowanych i w bieżących.
- **D-105:** rejestr zawiera tylko stacje z danymi bieżącymi (co najmniej 75% dni z ostatnich 90); Bergen usunięty.
- **D-106:** prognoza skorygowana regresją MOS jest drugim, równoległym produktem. Metoda wybrana na danych do
  2025-11-15, zamrożona w protokole A2 przed policzeniem okresu odłożonego. Prognoza surowa i jej test A1 zostają.

## 5. Dalej (propozycje do decyzji autora)

| Co | Kiedy | Uwagi |
|---|---|---|
| Werdykty testów na żywo A1 i A2 | po 2027-02-22 | te same reguły; wynik negatywny też raportujemy |
| Prognozy wprost z Copernicus ADS | po założeniu konta | prawdziwe archiwum prognoz na jutro z ostatnich 3 lat |
| Kolejne zanieczyszczenia (PM10, NO2) | po werdykcie | ta sama metoda, nowy protokół |
| Krajowe źródła danych bieżących (np. GIOŚ dla Krakowa) | odłożone | decyzja autora z 2026-11-16: na razie nie |
| Wymiana danych bieżących 2026 na zweryfikowane | jesień 2027 | `python -m aircheck backfill`, opis różnic |

## 6. Gdzie co jest

| Temat | Dokument |
|---|---|
| Kod i moduły | `docs/ARCHITEKTURA.md` |
| Przejście przez jeden dzień systemu | `docs/PRZEWODNIK.md` |
| Uruchomienie i co robić przy błędzie | `docs/URUCHOMIENIE_LOKALNE.md` |
| Protokół i odstępstwa: prognoza surowa | `docs/evidence/A1_protokol_prognozy.md`, `docs/evidence/A1_odstepstwa.md` |
| Protokół i wyniki: prognoza skorygowana | `docs/evidence/A2_protokol_korekta.md`, `docs/evidence/A2_wyniki.md`, `docs/evidence/A2_wybor_korekty.csv` |
| Przegląd stacji i przykład eksploracyjny | `docs/evidence/A0_przeglad_stacji.md` |
| Plan wdrożenia | `docs/plans/Plan_v1_air_check.md` |
| Zmiany wersji | `CHANGELOG.md` |
