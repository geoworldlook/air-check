# Air Check — uruchomienie

Air Check działa sam: GitHub Actions uruchamia przebieg trzy razy dziennie (09:40, 13:40 i 18:40 UTC) i sam publikuje panel.
Ta instrukcja jest potrzebna tylko wtedy, gdy chcesz uruchomić coś ręcznie.

## 1. Jedno polecenie

Z folderu `GeoWorldLook` na pulpicie:

```bash
scripts\gwl.cmd air-check test
```

```bash
scripts\gwl.cmd air-check run
```

`test` sprawdza kod bez sieci (około minuty). `run` robi to samo co automat: pobiera pomiary i prognozę,
sprawdza jakość danych i przelicza panel.

## 2. Wszystkie polecenia

| Polecenie | Co robi |
|---|---|
| `python -m aircheck run` | przebieg dzienny |
| `python -m aircheck backfill` | rekonstrukcja od 2022 (raz, kilka minut) |
| `python -m aircheck render` | panel z zapisanych tabel, bez sieci |
| `python -m aircheck publish` | commit i push `data/` oraz `docs/showcase/` |
| `python -m aircheck selftest` | testy bez sieci |
| `python -m aircheck settings` | ustawienia i stan ostatniego przebiegu |
| `python -m aircheck stations` | propozycja rejestru stacji z metadanych EEA (`--write` zapisuje) |

Środowisko: conda `aircheck` (`environment.yml`). Na tym komputerze polecenia uruchamiaj przez `gwl` albo
`conda run -n aircheck ...`; sam `python.exe` ze środowiska bez aktywacji kończy obliczenia bez komunikatu.

## 3. Gdzie są wyniki

- Panel publiczny: https://geoworldlook.github.io/air-check/showcase/aircheck_panel.html
- Panel na dysku: `projects/air-check/docs/showcase/aircheck_panel.html` (otwiera się bez serwera)
- Stan ostatniego przebiegu lokalnego: `projects/air-check/data/logs/last_run.json`
- Historia przebiegów automatu: zakładka Actions w repozytorium, zadanie `daily`

## 4. Gdy coś nie działa

| Objaw | Co to znaczy | Co zrobić |
|---|---|---|
| Kod wyjścia 2, napis „bramka jakości” | za mało świeżych pomiarów albo brak prognozy; panel celowo bez zmian | poczekać do jutra; automat spróbuje ponownie |
| Zgłoszenie „Daily run failed” w repozytorium | przebieg automatu się nie udał | zwykle nic: następny udany przebieg sam zamknie zgłoszenie; gdy wisi dłużej niż dobę, otworzyć log z linku |
| Błąd „Open-Meteo niedostępne” albo „limit zapytań (429)” | dostawca prognoz odrzucił zapytanie z serwera GitHuba | nic: automat ponawia do kilku minut i próbuje jeszcze dwa razy tego dnia |
| Brak prognoz na żywo z jakiegoś dnia | automat tego dnia nie zadziałał | tego nie da się odtworzyć; dzień wypada z testu potwierdzającego |

## 5. Raz w roku

Gdy EEA opublikuje dane zweryfikowane za poprzedni rok (zwykle jesienią), uruchom `python -m aircheck backfill`.
Dane zweryfikowane zastąpią bieżące, a różnicę opisz w `docs/evidence/`.
