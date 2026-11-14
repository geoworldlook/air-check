# Protokół A1: czy prognoza PM2.5 na jutro jest lepsza od reguły „jutro jak dziś”

Wersja 1, zapisana 2026-11-14, przed pierwszym dniem testu. Suma kontrolna SHA-256 tego pliku jest w
`aircheck/config.py` (`PROTOCOL_SHA256`); test `python -m aircheck selftest` sprawdza, że plik się nie zmienił.
Zmiana reguł oznacza nową wersję protokołu, a wynik poprzedniej wersji zostaje w repozytorium.

## 1. Pytanie

Czy dobowa prognoza pyłu PM2.5 z usługi Copernicus (CAMS, zespół modeli, siatka ok. 10 km), wydana dzień wcześniej,
ma mniejszy błąd wobec pomiaru ze stacji niż najprostsza reguła: „jutro będzie tak jak dziś”?

## 2. Dane

- **Pomiar:** średnia dobowa PM2.5 (doba UTC) z jednej stacji tła miejskiego na miasto. Źródło: EEA, dane bieżące
  (niezweryfikowane) według stanu z dnia oceny. Doba liczy się przy co najmniej 18 ważnych godzinach albo gdy
  sieć podaje wartość dobową. Doby z zaciętym czujnikiem (najwyżej 2 różne wartości) odpadają.
- **Prognoza na jutro:** średnia dobowa (UTC, co najmniej 18 godzin) dla punktu stacji, z prognozy pobranej i zapisanej
  w dniu D-1 (`issue_date`) dla dnia docelowego D (`lead = 1`). Prognoza nie jest poprawiana po fakcie.
- **Reguła odniesienia:** pomiar z dnia D-1.
- **Stacje:** wszystkie stacje ze statusem `accepted` w `aircheck/stations.csv` w wersji z commita tego protokołu.

## 3. Okno testu

Dni docelowe od 2026-11-16 do 2027-02-13 (90 dni). Ocena końcowa najwcześniej 7 dni po końcu okna, żeby spóźnione
pomiary zdążyły dojść. Wyniki sprzed okna i wszystkie wyniki z archiwum prognoz mają status opisowy.

## 4. Miary

Dla każdej stacji, na dniach z kompletem (pomiar w D, prognoza na D, pomiar w D-1):

- RMSE prognozy i RMSE reguły;
- dla dni z pomiarem powyżej 25 µg/m³: trafienia, pominięcia i fałszywe alarmy; wskaźnik CSI = trafienia /
  (trafienia + pominięcia + fałszywe alarmy), osobno dla prognozy i dla reguły.

Stacja wchodzi do testu, gdy ma w oknie co najmniej 60 dni z kompletem.

## 5. Hipotezy i reguły decyzji

- **H-A1.** Udział stacji, w których RMSE prognozy jest mniejszy niż RMSE reguły, wynosi co najmniej 2/3.
  Potwierdzona, gdy udział ≥ 2/3; inaczej niepotwierdzona. Podajemy też 95% przedział Wilsona dla udziału.
- **H-A2.** Wśród stacji z co najmniej 10 dniami powyżej 25 µg/m³ w oknie prognoza ma wyższy CSI niż reguła
  w ponad połowie stacji. Gdy takich stacji jest mniej niż 5, hipoteza jest nietestowalna.

Obie hipotezy raportujemy niezależnie od wyniku. Wynik negatywny jest wynikiem.

## 6. Moc testu

Przy 28 stacjach przedział Wilsona dla udziału bliskiego 2/3 ma szerokość około ±17 punktów procentowych.
Test rozstrzyga więc tylko wyraźne różnice. Jeśli prawdziwy udział jest bliski 2/3, wynik może wypaść w obie strony.

## 7. Co już widzieliśmy przed zapisaniem protokołu

- Przegląd eksploracyjny z 2026-11-14: 20 miast, XI 2023 – X 2026, prognozy z archiwum (wyprzedzenie poniżej doby).
  Prognoza miała mniejszy RMSE niż reguła w 13 z 20 miast, a wyższy CSI w 7 z 13 miast z co najmniej 20 dniami
  powyżej progu. Próg 2/3 w H-A1 został wybrany ze znajomością tego wyniku.
- Dane z okna testu nie istniały w chwili zapisania protokołu.

## 8. Znane ograniczenia

- Reguła odniesienia korzysta z pełnego pomiaru z dnia D-1, którego rano w dniu D-1 jeszcze nie ma. To działa
  na korzyść reguły, a nie prognozy.
- Stacja mierzy w punkcie, prognoza opisuje kwadrat ok. 10 km.
- Pomiary bieżące nie są zweryfikowane przez sieci krajowe. Po publikacji danych zweryfikowanych powtarzamy
  obliczenie i raportujemy różnicę jako analizę dodatkową; werdykt z punktu 5 się nie zmienia.
- Część sieci podaje w danych bieżących czas z przesunięciem; przyjmujemy UTC+1 dla wszystkich plików EEA.
