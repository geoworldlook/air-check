# Plan v1 — Air Check

Status: WDROŻONY 2026-11-14 (kroki 0 i A1–A8), decyzje D-096–D-098, D-100, D-102. Test potwierdzający A1 w toku.

## 1. Pytanie i odbiorca

Czy prognozie smogu z Copernicus można ufać w moim mieście? Odbiorca: mieszkaniec, dziennikarz, urzędnik.
Punkt odniesienia: reguła „jutro będzie jak dziś”.

## 2. Zasady

- **Prosto:** dwa źródła danych i trzy małe tabele.
- **Automatycznie:** przebieg dzienny w GitHub Actions, bez komputera autora.
- **Modułowo:** `stations.csv`, `sources/`, `core.py`, `publish.py`. Nowy kraj to nowy plik w `sources/`.
- **Od 2022 (D-097):** rekonstrukcja wstecz ma status opisowy; test potwierdzający tylko na danych po zapisaniu protokołu.

## 3. Kroki i kryteria akceptacji

| Krok | Co | Kryterium akceptacji | Stan |
|---|---|---|---|
| 0 | Repozytorium, środowisko, licencje danych | licencje zapisane w README | zrobione |
| A1 | Rejestr stacji według zapisanej reguły | każde miasto ma stację tła z co najmniej 75% dni albo jest odrzucone z powodem | zrobione: 28 przyjętych, 19 odrzuconych |
| A2 | Pomiary EEA i kontrola jakości | test bez sieci przechodzi | zrobione |
| A3 | Prognozy CAMS | prognoza zapisana z datą wydania | zrobione (przez Open-Meteo) |
| A4 | Rekonstrukcja | pomiary od 2022, prognozy od XI 2023 | zrobione |
| A5 | Miary i protokół zapisany przed testem | protokół z sumą kontrolną w repozytorium przed pierwszym dniem testu | zrobione (A1, 2026-11-14) |
| A6 | Panel i dane do publikacji | panel otwiera się bez serwera | zrobione |
| A7 | Automat: Docker, GitHub Actions, alarm, CI | 7 kolejnych przebiegów bez ręcznej poprawki | w toku od 2026-11-15 |
| A8 | README (EN), dokumentacja (PL), przewodnik, wersja 1.0.0 | README pozwala uruchomić projekt jednym poleceniem | zrobione |
| A9 | Korekta prognozy metodą z literatury, protokół A2 (wersja 1.1.0) | metoda zamrożona przed policzeniem okresu odłożonego; H-A3 i H-A4 | zrobione: obie potwierdzone (27 z 27) |

## 4. Decyzje

- **D-096:** Air Check jest projektem nr 3; kolejność: Air Check, potem Water Check.
- **D-097:** rekonstrukcja od 2022 opisowa; test potwierdzający na żywo.
- **D-098:** oceniamy prognozy, nie reanalizę; pomiary z EEA; prognozy przez Open-Meteo, docelowo z ADS.
- **D-100:** stan potoku w repozytorium (`data/`), wynik w `docs/showcase/`, przebieg w GitHub Actions.
- **D-102:** wybór na poziomie stacji; punkt pomiarowy może być inny w danych zweryfikowanych i bieżących.
- **D-105:** rejestr zawiera tylko stacje z danymi bieżącymi (co najmniej 75% dni z ostatnich 90); Bergen usunięty.
- **D-106:** prognoza skorygowana regresją MOS jest drugim, równoległym produktem; prognoza surowa i jej test A1 zostają.

## 5. Ryzyka

- Zewnętrzne usługi (EEA, Open-Meteo) mogą zmienić format albo zasady. Stąd jeden plik na źródło, bramka i alarm.
- Dzień, w którym automat nie zadziała, wypada z testu na żywo i nie da się go odtworzyć.
- Open-Meteo jest darmowe tylko dla użytku niekomercyjnego. Przy użyciu komercyjnym trzeba przejść na ADS.
