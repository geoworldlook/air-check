# Protokół A2: skorygowana prognoza PM2.5 (regresja MOS)

Wersja 1, zapisana 2026-11-16, przed policzeniem okresu odłożonego. Suma kontrolna SHA-256 tego pliku jest w
`aircheck/config.py` (`PROTOCOL_A2_SHA256`); test `python -m aircheck selftest` sprawdza, że plik się nie zmienił.
Protokół A1 (prognoza surowa) zostaje bez zmian i jego test trwa dalej.

## 1. Po co

Rekonstrukcja z protokołu A1 pokazała, że surowa prognoza CAMS w części miast przegrywa z regułą „jutro jak dziś”,
głównie przez stały błąd (zimą zawyżenie). Literatura od lat opisuje proste korekty takiego błędu na stacjach:
bieżącą korektę błędu, filtr Kalmana i regresję MOS (przegląd: Bertrand i in. 2023, Atmos. Chem. Phys. 23, 5317;
Delle Monache i in. 2006; Kang i in. 2008; dla CAMS nad Włochami: Riccio i Chianese 2024, Atmos. Chem. Phys. 24, 1673).
Pytanie: czy prosta korekta daje prognozę lepszą od reguły „jutro jak dziś” i od prognozy surowej?

## 2. Metoda (zamrożona)

Regresja liniowa dopasowana osobno dla każdej stacji:

`pomiar(D) = a + b · prognoza(D) + c · pomiar(D − lag)`

- dopasowanie metodą najmniejszych kwadratów na ostatnich 365 dniach z kompletem danych, co najmniej 30 dni;
- współczynniki na dzień D pochodzą wyłącznie z dni wcześniejszych (korekta jest przyczynowa);
- wynik ujemny zastępujemy zerem; gdy danych jest za mało, zostaje prognoza surowa;
- `lag = 1` dla prognoz z archiwum (wyprzedzenie poniżej doby);
- `lag = 2` dla prognozy na jutro wydanej w dniu D − 1: wczorajsza doba nie jest wtedy jeszcze pełna.
  Regresja uczy się na prognozach z archiwum; w miarę upływu czasu zastępują je prognozy zapisane na żywo.

Kod: `aircheck/correct.py`, funkcja `mos`.

## 3. Jak metoda została wybrana

Eksperyment `notebooks/experiments/A2_wybor_korekty.py` porównał 12 wariantów pięciu metod (bieżąca korekta addytywna
i mnożnikowa, filtr Kalmana, metoda hybrydowa, regresja MOS) na okresie rozwojowym: dni do 2025-11-15.
Kryterium: liczba stacji z RMSE mniejszym niż reguła, potem mediana skill. Wynik: `docs/evidence/A2_wybor_korekty.csv`.
Wygrała regresja MOS z oknem 365 dni (27 z 27 stacji, mediana skill 0,43). Okres odłożony nie był przy tym liczony.

## 4. Okres odłożony (ocena jednorazowa)

Dni od 2025-11-16 do 2026-11-15, prognozy z archiwum, `lag = 1`, wszystkie stacje z rejestru.

- **H-A3.** Prognoza skorygowana ma mniejszy RMSE niż reguła „jutro jak dziś” w co najmniej 2/3 stacji.
- **H-A4.** Prognoza skorygowana ma mniejszy RMSE niż prognoza surowa w co najmniej 2/3 stacji.

Wyniki prognozy surowej dla tego okresu były znane z rekonstrukcji A1. Wyniki prognozy skorygowanej dla tego okresu
nie były liczone przed zapisaniem tego protokołu.

## 5. Test na żywo

Te same hipotezy H-A3 i H-A4 dla skorygowanej prognozy na jutro (`lag = 2`), zapisywanej w dniu wydania razem
z prognozą surową. Okno: dni docelowe od 2026-11-18 do 2027-02-15 (90 dni). Stacja wchodzi do testu przy co najmniej
60 dniach z kompletem. Ocena końcowa najwcześniej 7 dni po końcu okna. Wynik raportujemy niezależnie od kierunku.

## 6. Znane ograniczenia

- Korekta potrzebuje świeżych pomiarów ze stacji. Bez nich wraca do prognozy surowej.
- Archiwum zawiera prognozy o wyprzedzeniu poniżej doby; test na żywo sprawdza prawdziwą prognozę na jutro z `lag = 2`.
- Regresja liniowa poprawia średni błąd, ale może wygładzać skrajne epizody. Dlatego raportujemy też trafność dla dni
  powyżej 25 µg/m³ (opisowo, bez progu).
- Wybór metody na okresie rozwojowym był porównaniem 12 wariantów; okres odłożony i test na żywo chronią przed
  przypadkowym „zwycięzcą”.
