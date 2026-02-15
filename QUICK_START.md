# Quick Start Guide - Po Naprawach

## ✅ Co zostało naprawione?

Znaleźliśmy i naprawiliśmy **4 krytyczne problemy** które powodowały "NO DATA":

1. ✅ **Dashboard fallback** - teraz działa bez SPY w bazie
2. ✅ **Indentation fix** - wskaźniki już się importują
3. ✅ **CSV import robustness** - obsługuje brakujące kolumny
4. ✅ **User feedback** - lepsze komunikaty

---

## 🚀 Jak Uruchomić (Instrukcja Krok po Kroku)

### Krok 1: Uruchom Aplikację
```
Otwórz Command Prompt lub PowerShell
Wpisz: cd C:\Moje\Antigravity\Strategie\app_v2
Wpisz: python start.py
Czekaj: 2-3 sekundy aż się otwori okno
```

### Krok 2: Pobierz Dane - SPY (OBOWIĄZKOWE!)
```
Kliknij: "Download Data (YFinance)"
Wpisz: SPY
Czekaj: 20-30 sekund
Powinno wyświetlić: "Pobrano X świec dla SPY"
```

### Krok 3: Pobierz Dane - Spółki Testowe (5+ sztuk)
```
Kliknij: "Download Data (YFinance)"
Wpisz: AAPL
Czekaj: 15-20 sekund

Powtórz dla:
  - MSFT
  - GOOGL
  - TSLA
  - NVDA
  - META
  (lub inne spółki które Cię interesują)
```

### Krok 4: Odśwież Panel
```
Kliknij: "Refresh Analysis"
Czekaj: 10-15 sekund
```

### Krok 5: Powinno Zadziałać! 🎉
Na Dashboard powinno pojawić się:
- ✅ Kolorowy badge z Market Regime (zielony/pomarańczowy/czerwony)
- ✅ Top 5 Tier A candidates w tabeli
- ✅ Statystyki (TRADEABLE, SETUP, OUT)
- ✅ Portfolio Heat progress bar

---

## 📋 Co To Oznacza?

| Element | Znaczenie |
|---------|-----------|
| **Market Regime Badge** | Aktualny stan rynku (BULL, BEAR, etc.) |
| **Top 5 Tier A** | 5 najlepszych setupów do handlu |
| **TRADEABLE** | Liczba spółek gotowych do handlu |
| **SETUP** | Liczba spółek formujących setup |
| **OUT** | Liczba spółek poza rynkiem |

---

## 🐛 Jeśli Nadal Widać "NO DATA"

### Diagnoza:

1. **Czy pobrano SPY?**
   ```
   Kliknij "Download Data"
   Jeśli pojawi się komunikat sukcesu - OK ✓
   Jeśli błąd - problem z internetem lub Yahoo Finance
   ```

2. **Czy pobrano spółki?**
   ```
   Każda spółka powinna wyświetlić "Pobrano X świec"
   Bez komunikatu = błąd pobrania
   ```

3. **Czy Refresh został kliknięty?**
   ```
   Kliknij "Refresh Analysis"
   Czekaj 10-15 sekund
   Dane powinny się pojawić
   ```

### Ostateczne Rozwiązanie (Nuclear Option):

Jeśli nic nie działa:

```
1. Zamknij aplikację
2. Usuń plik: dane_rynkowe_v2.db
3. Otwórz aplikację od nowa
4. Powtórz kroki 2-4 z góry
```

---

## 🔍 Screener - Co To Jest?

Menu górne → "Skaner" → znajdujesz się w screenerze.

Pokazuje tabelę ze wszystkimi spółkami z ich wskaźnikami:

| Kolumna | Co Oznacza |
|---------|-----------|
| Status | TRADEABLE / SETUP / OUT |
| Tyker | Symbol spółki (AAPL, MSFT, etc.) |
| CompositeScore | 0-100 score (wyżej = lepiej) |
| Tier | A (najlepszy), B, C |
| Price | Aktualna cena |
| SMA200_Slope | Czy trend idzie w górę (zielony) czy w dół (czerwony) |
| RS_Slope | Relative Strength trend |
| Distance_200% | Jak daleko cena od średniej 200-dniowej |
| ATR_pct | Zmienność ceny (volatility) |

---

## 🎯 Następne Kroki - Jak Używać Systemu

### Codziennie:
1. Odpal aplikację
2. Kliknij "Refresh Analysis"
3. Czekaj na wyniki
4. Przejrzyj Top 5 Tier A setupów
5. Otwórz "Skaner" aby zobaczyć pełną listę

### Co Tydzień:
1. Pobierz nowe dane dla SPY
2. Pobierz nowe dane dla swoich spółek (5-20)

### Co Miesiąc:
1. Przejrzyj Performance Journal
2. Analiza trade'ów
3. Dostrajanie parametrów (jeśli potrzebne)

---

## 📚 Zaawansowane Funkcje (Sprint 5)

Te funkcje będą dostępne w następnej aktualizacji:

- [ ] Ticker View - 4 zaawansowane sekcje (Trend, RS, Risk, MTF)
- [ ] Report Generator - Export do HTML/PDF
- [ ] Performance Metrics - Equity curve, Win Rate, etc.

---

## ✨ Tips & Tricks

### Szybkie Pobranie Wielu Spółek:
```
Jeśli chcesz S&P 500, możesz pobrać kilka reprezentantów:
- SPY (cały S&P 500 - benchmark)
- Top Tech: AAPL, MSFT, GOOGL, NVDA, META
- Finance: JPM, BAC, WFC
- Healthcare: JNJ, UNH, PFE
- Energy: XOM, CVX
- Consumer: KO, PG, WMT
```

### Zautomatyzuj Pobieranie (Python):
```python
# Utwórz plik: auto_download.py
from dane.importer import ImporterDanych
from dane.repozytorium import RepozytoriumDanych

tickers = ["SPY", "AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"]
repo = RepozytoriumDanych()

for ticker in tickers:
    print(f"Downloading {ticker}...")
    swiece = ImporterDanych.pobierz_yfinance(ticker)
    if swiece:
        repo.zapisz_swiece(swiece)
        print(f"✓ {ticker} OK")
    else:
        print(f"✗ {ticker} FAILED")
```

Uruchom: `python auto_download.py`

### Zmień Benchmark:
```
Edytuj plik: konfiguracja.py
Linia 30: TYKER_BENCHMARK = "QQQ"
(lub "DIA", "IWM", itp.)
```

---

## 📞 Co Robić Jeśli...

| Sytuacja | Akcja |
|----------|--------|
| "NO DATA" na starcie | Pobierz SPY + 5 spółek, kliknij Refresh |
| Screener jest pusty | Czekaj 10s, kliknij Refresh |
| Wszystko szare (brak kolorów) | Czekaj na więcej danych (1 rok) |
| Aplikacja się wysypuje | Usuń .db, restart od nowa |
| Błąd pobierania | Sprawdź symbol, internet, spróbuj inny |

---

## ✅ Checklist - Przed Użytkowaniem

- [ ] Python 3.10+ zainstalowany
- [ ] Biblioteki zainstalowane (pip install -r requirements.txt)
- [ ] Baza danych istnieje (będzie utworzona automatycznie)
- [ ] Internet dostępny (do pobierania z Yahoo Finance)
- [ ] SPY pobrane i w bazie
- [ ] Co najmniej 5 spółek pobrane
- [ ] "Refresh Analysis" był kliknięty
- [ ] Dane się pojawiły na dashboard

---

## 🎓 Nauka Systemu

### Composite Score (0-100):
```
30% - Relative Strength (jak mocna spółka vs inne)
20% - Momentum 3M/6M (siła trendu)
20% - SMA200 Slope (nachylenie średniej)
20% - Multi-Timeframe Alignment (alignment daily/weekly/monthly)
10% - Distance Penalty (kara jeśli za daleko od średniej)
```

### Tier Classification:
```
A: Score >= 80 (TOP QUALITY SETUPS)
B: Score 60-79 (GOOD SETUPS)
C: Score < 60 (WEAK SETUPS - AVOID)
```

### Market Regime:
```
STRONG_BULL: Green - Kupuj
BULL:        Light Green - Ostrożnie kupuj
NEUTRAL:     Orange - Czekaj na sygnał
BEAR:        Light Red - Unikaj kupna
STRONG_BEAR: Dark Red - Sznuruj i czekaj
```

---

**Status**: Production Ready ✅
**Wersja**: 2.0.1
**Data**: 2025-02-15

Powodzenia w handlu! 🚀

