# Air Check — przewodnik krok po kroku

Ten dokument prowadzi przez jeden dzień pracy systemu, od pobrania danych do liczby na panelu.
Przy każdym kroku jest plik z kodem, w którym ten krok się dzieje.

## 1. Co system sprawdza

Usługa Copernicus (CAMS) codziennie prognozuje pył PM2.5 dla całej Europy. Air Check odpowiada na jedno pytanie:
czy w danym mieście ta prognoza jest lepsza niż zgadywanie „jutro będzie tak jak dziś”?

Jeśli prognoza nie wygrywa z tak prostą regułą, to w tym mieście niewiele wnosi.

## 2. Dzień z życia systemu

Automat startuje o 09:40 UTC (`.github/workflows/daily.yml`) i wykonuje `python -m aircheck run`.
Kroki są w `aircheck/pipeline.py`, w funkcji `run`.

### Krok 1. Pomiary ze stacji (`sources/eea.py`)

- Dla każdej stacji z rejestru (`aircheck/stations.csv`) pobieramy plik z danymi bieżącymi z EEA.
- Z godzin liczymy średnią dobową. Doba liczy się przy co najmniej 18 godzinach.
- Czas w plikach EEA jest w UTC+1. Przesuwamy go o godzinę, żeby doba była ta sama co w prognozie.
- Gdy czujnik pokazuje cały dzień tę samą wartość, doba jest oznaczona jako „zacięty czujnik” i nie wchodzi do miar.
- Wynik trafia do `data/obs/obs_RRRR.csv`.

### Krok 2. Prognoza z archiwum (`sources/cams.py`, funkcja `archive`)

- Pobieramy prognozy z ostatnich 10 dni z archiwum dostawcy i dopisujemy brakujące dni.
- To są prognozy o krótkim wyprzedzeniu (poniżej doby). Służą do rekonstrukcji: jak system wyglądałby, gdyby działał wcześniej.
- Wynik: `data/forecast/archive_RRRR.csv`.

### Krok 3. Prognoza wydana dziś (`sources/cams.py`, funkcja `live`)

- Pobieramy prognozę na dziś i trzy kolejne dni.
- Zapisujemy ją z dzisiejszą datą wydania. Jutro już jej nie zmienimy.
- To jest serce systemu: prognozę „na jutro” oceniamy dokładnie taką, jaka była dostępna dzień wcześniej.
- Wynik: `data/forecast/live_RRRR.csv` (kolumna `lead` to wyprzedzenie w dniach).

### Krok 4. Bramka jakości (`pipeline.py`, funkcja `gate`)

- Jeśli świeży pomiar ma mniej niż połowa stacji albo brakuje dzisiejszej prognozy, panel się nie aktualizuje.
- Lepiej pokazać wczorajszy poprawny panel niż dzisiejszy z dziurami.

### Krok 5. Miary (`core.py`)

Dla każdej stacji składamy pary dni: pomiar z dnia D, prognoza na dzień D i pomiar z dnia D-1.

| Miara | Co mówi |
|---|---|
| RMSE prognozy | typowy błąd prognozy w µg/m³ |
| RMSE reguły | typowy błąd zgadywania „jutro jak dziś” |
| Skill | 1 − (błąd prognozy / błąd reguły)², powyżej zera wygrywa prognoza |
| CSI | trafność dla dni z wysokim pyłem (powyżej 25 µg/m³): trafienia dzielone przez trafienia, pominięcia i fałszywe alarmy |

Werdykt dla miasta (`better`, `similar`, `worse`) zapada tylko wtedy, gdy przedział ufności dla skill nie obejmuje zera.
Przedział liczymy bootstrapem blokowym: losujemy tygodniowe bloki dni ze zwracaniem, 400 razy.

### Krok 6. Publikacja (`publish.py`)

- Panel to jeden plik HTML z danymi w środku: `docs/showcase/aircheck_panel.html`.
- Obok zapisujemy dane (`aircheck_data.json`), punkty dla mapy na stronie (`map_points.geojson`) i stan (`status.json`).
- Automat zapisuje zmiany do repozytorium, a GitHub Pages pokazuje nowy panel.

## 3. Dwa rodzaje wyników

| Rodzaj | Skąd | Status |
|---|---|---|
| Rekonstrukcja | archiwum prognoz od XI 2023, pomiary od 2022 | opisowy: reguły powstały po tych danych |
| Test na żywo | prognozy zapisywane codziennie od dnia startu | potwierdzający: reguły zapisane wcześniej w protokole A1 |

Protokół (`docs/evidence/A1_protokol_prognozy.md`) ma sumę kontrolną w kodzie. Test `selftest` nie przejdzie,
jeśli ktoś zmieni protokół po fakcie.

## 4. Jak dodać miasto albo źródło

- **Miasto:** dopisz je do listy `CITIES` w `registry.py`, uruchom `python -m aircheck stations --write`,
  potem `python -m aircheck backfill`.
- **Nowe źródło pomiarów:** nowy plik w `sources/` z funkcją, która zwraca średnie dobowe w tym samym układzie
  co `eea.read_daily`.

## 5. Jak sprawdzić, że rozumiesz

Otwórz `data/obs/obs_2026.csv` i `data/forecast/archive_2026.csv`, wybierz jedną stację i 10 kolejnych dni.
Policz ręcznie błąd prognozy i błąd reguły „jutro jak dziś”. Powinny być bliskie liczbom z panelu dla ostatnich 30 dni
(nie identyczne, bo panel liczy z 30 dni).
