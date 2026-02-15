Zrefaktoryzuj system rankingowy w aplikacji Trend Following 2.0 pod kątem małej, ręcznie wybranej watchlisty (5–30 spółek).

Cel:
Ranking ma nie porządkować „najlepszych z wszystkich”, tylko wskazywać:
1) które spółki są TRADEABLE,
2) które są SETUP,
3) które są OUT.

Nie przebudowuj całej aplikacji.
Zmień logikę klasyfikacji i prezentacji wyników.

---------------------------------------
I. DODAJ SYSTEM STATUS (GATING LAYER)
---------------------------------------

Dodaj kolumnę: Status

Logika:

TRADEABLE jeśli:
- Close > SMA200
- SMA200 slope > 0
- Close > SMA50
- RS slope > 0 LUB RS ratio > RS_MA
- AlignmentScore >= 2 (dla D/W lub D/W/M)

SETUP jeśli:
- Close > SMA200
- SMA200 slope >= 0
- AlignmentScore >= 1
- ale RS slope <= 0 LUB Close <= SMA50

OUT w pozostałych przypadkach.

Status ma być wyliczany przed rankingiem.
Ranking ma być liczony tylko dla TRADEABLE.

---------------------------------------
II. CHECKLIST SCORE (ZAMIANA COMPOSITE SCORE)
---------------------------------------

Zamiast jednego composite score z wagami, wprowadź checklist scoring (0–10 punktów):

+2 jeśli Close > SMA200
+1 jeśli Close > SMA50
+2 jeśli SMA200 slope > 0
+1 jeśli SMA50 slope > 0
+2 jeśli RS slope > 0
+1 jeśli Momentum 3M > 0
+1 jeśli Momentum 6M > 0

Wyświetl:
ChecklistScore (0–10)

Tier:
A = 8–10
B = 6–7
C = 4–5
D = 0–3

---------------------------------------
III. RANKING LOGIKA
---------------------------------------

1) Najpierw filtruj tylko TRADEABLE
2) Sortuj TRADEABLE po:
   - ChecklistScore (malejąco)
   - RS slope
   - SMA200 slope

3) Spółki SETUP i OUT wyświetl poniżej, bez numeru rankingowego (lub z osobną sekcją)

---------------------------------------
IV. UI ZMIANY
---------------------------------------

1) Dodaj kolumny:
   - Status
   - ChecklistScore

2) Kolorowanie:
   TRADEABLE = zielony wiersz
   SETUP = żółty
   OUT = czerwony (lekko przygaszony)

3) Na Dashboard:
   - liczba TRADEABLE
   - liczba SETUP
   - liczba OUT

---------------------------------------
V. ZASADY IMPLEMENTACJI
---------------------------------------

- Nie usuwaj dotychczasowych obliczeń (slope, alignment, RS).
- Wykorzystaj istniejące dane.
- Zachowaj modularność: dodaj plik analysis/status_engine.py
- Checklist scoring w ranking_engine.py

---------------------------------------
VI. OUTPUT
---------------------------------------

1) Najpierw opisz zmiany logiczne.
2) Pokaż zmodyfikowaną strukturę projektu.
3) Następnie wygeneruj kod tylko zmienionych plików.
4) Na końcu pokaż przykład działania na aktualnej watchliście (NET, HL, OKLO itd.).

Priorytet:
System ma pomagać podjąć decyzję „czy to jest teraz grywalne”.
Ranking ma być wtórny wobec statusu.
