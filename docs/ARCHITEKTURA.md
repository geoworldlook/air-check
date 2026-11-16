# Air Check — architektura (wersja 1.0)

Opis kodu w pakiecie `aircheck/`. Stan projektu i wyniki: `docs/STAN_I_PLAN.md`; zmiany wersji: `CHANGELOG.md`.

## 1. Przepływ

```text
EEA (pomiary ze stacji) ─┐
                         ├─▶ data/ (małe tabele CSV, stan potoku) ─▶ bramka jakości ─▶ miary ─▶ docs/showcase/
CAMS (prognoza)  ────────┘                                                                      │
                                                                     GitHub Pages (panel) ◀─────┘
```

Przebieg uruchamia GitHub Actions (`.github/workflows/daily.yml`) trzy razy dziennie (09:40, 13:40 i 18:40 UTC). Wystarczy jeden udany przebieg na dobę:
kolejny tego samego dnia zastępuje wcześniej zapisaną prognozę, a harmonogram GitHuba bywa spóźniony o kilka godzin. Po przebiegu automat zapisuje
zmiany w `data/` i `docs/showcase/` do repozytorium. Komputer autora nie jest potrzebny. To samo polecenie działa
lokalnie: `gwl air-check run` albo `python -m aircheck run`.

## 2. Moduły

| Moduł | Odpowiedzialność |
|---|---|
| `stations.csv` | Rejestr: miasto, stacja, współrzędne, kompletność danych, adresy plików EEA, status (`accepted` / `excluded`) |
| `registry.py` | Odczyt rejestru; budowa propozycji rejestru z metadanych EEA według zapisanej reguły |
| `sources/eea.py` | Pomiary: lista plików, odczyt pliku stacji, średnie dobowe (UTC), oznaczenie zaciętego czujnika |
| `sources/cams.py` | Prognoza CAMS przez Open-Meteo: archiwum (rekonstrukcja) i prognoza wydana dziś |
| `correct.py` | Korekta prognozy: regresja MOS (wybrana w protokole A2) oraz metody porównawcze: bieżąca korekta błędu, filtr Kalmana, metoda hybrydowa |
| `core.py` | Pary dni, RMSE, skill wobec reguły „jutro jak dziś”, CSI, przedział ufności (bootstrap blokowy), werdykt |
| `pipeline.py` | Kroki: pomiary, archiwum prognoz, prognoza na żywo, bramka jakości, miary; `run` i `render` |
| `publish.py` | Panel HTML (dane w środku pliku), dane JSON, punkty mapy (GeoJSON), stan przebiegu |
| `selftest.py` | Test bez sieci: testy jednostkowe, kontrola rejestru i protokołu, cały potok na danych syntetycznych |
| `config.py` | Ustawienia w jednym miejscu; wartości metody pochodzą z protokołu A1 |

Nowe źródło danych to nowy plik w `sources/` i nowe wiersze w `stations.csv`. Reszta kodu zostaje bez zmian.

## 3. Tabele (stan potoku)

| Plik | Klucz | Zawartość |
|---|---|---|
| `data/obs/obs_RRRR.csv` | date, station | średnia dobowa PM2.5, liczba godzin, źródło (`verified` / `utd`), flaga zaciętego czujnika |
| `data/forecast/archive_RRRR.csv` | date, station | prognoza z archiwum dostawcy (wyprzedzenie poniżej doby) |
| `data/forecast/live_RRRR.csv` | issue_date, date, station | prognoza zapisana w dniu wydania, wyprzedzenie 0–3 dni, czas przebiegu modelu; dla prognozy na jutro także wartość skorygowana (`pm25_corr`), policzona w dniu wydania |

Zapis według klucza: ten sam wiersz nie jest dopisywany drugi raz. Dane zweryfikowane mają pierwszeństwo przed
bieżącymi. Przy każdym przebiegu archiwum prognoz jest pobierane dla ostatnich 10 dni, więc dziury po nieudanym
przebiegu same się zamykają.

## 4. Bramka jakości danych

Publikacja jest wstrzymana (kod wyjścia 2, panel bez zmian), gdy:

- świeży pomiar (z ostatnich 4 dni) ma mniej niż połowa stacji, albo
- dzisiejsza prognoza jest dla mniej niż 90% stacji.

Awaria samego archiwum prognoz (np. limit zapytań u dostawcy) nie zatrzymuje przebiegu: prognoza wydana dziś jest
zapisywana w pierwszej kolejności, a archiwum uzupełni się przy następnym przebiegu. Stan przebiegu ma wtedy ostrzeżenie.

Każdy nieudany przebieg w GitHub Actions zakłada zgłoszenie (issue) w repozytorium albo dopisuje komentarz do otwartego.
Pierwszy udany przebieg sam zamyka to zgłoszenie z komentarzem.

## 5. Wynik (`docs/showcase/`)

| Plik | Dla kogo |
|---|---|
| `aircheck_panel.html` | panel publiczny (GitHub Pages); działa też otwarty z dysku |
| `aircheck_data.json` | te same dane dla notatnika na blog |
| `map_points.geojson` | punkty dla mapy monitorowania na stronie geoworldlook |
| `status.json` | stan ostatniego przebiegu, bramka, postęp testu potwierdzającego |

## 6. Testy

`python -m aircheck selftest` (około minuty, bez sieci): średnie dobowe i przesunięcie czasu, zacięty czujnik, miary
na ręcznie policzonym przykładzie, powtarzalność bootstrapu, rejestr stacji, suma kontrolna protokołu, cały potok
na czterech syntetycznych stacjach (dwa kolejne dni, 100 dni prognoz na żywo, zamknięcie testu, bramka jakości).
CI uruchamia linter, ten test oraz budowę obrazu Dockera przy każdej zmianie kodu.
