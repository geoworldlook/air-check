# A1: odstępstwa od protokołu

Protokół `A1_protokol_prognozy.md` ma sumę kontrolną i nie jest zmieniany. Odstępstwa zapisujemy tutaj,
z datą i powodem.

## 2026-11-16: jedna stacja usunięta z rejestru

- **Co:** stacja Bergen (NO0108A) usunięta z `aircheck/stations.csv`. Rejestr ma teraz 27 stacji zamiast 28.
- **Dlaczego:** stacja nie ma danych bieżących: 43 z ostatnich 90 dni, 9 z ostatnich 30, ostatni pomiar 2026-11-09.
  Reguła rejestru dostała warunek „co najmniej 75% dni z ostatnich 90 dni” (`aircheck/registry.py`).
- **Kiedy:** w pierwszym dniu okna testu, zanim powstała pierwsza para dni z prognozą zapisaną na żywo. Decyzja nie
  mogła zależeć od wyniku testu, bo wyniku jeszcze nie było.
- **Skutek dla testu:** H-A1 i H-A2 liczymy na 27 stacjach. Przy 27 stacjach przedział Wilsona dla udziału bliskiego
  2/3 ma podobną szerokość jak przy 28 (około ±17 punktów procentowych).

## 2026-11-16: wiersze miast odrzuconych usunięte z pliku rejestru

- **Co:** `stations.csv` zawiera tylko stacje przyjęte. Lista miast odrzuconych z powodami została w
  `A0_przeglad_stacji.md`.
- **Skutek dla testu:** żaden; miasta odrzucone nigdy nie wchodziły do testu.
