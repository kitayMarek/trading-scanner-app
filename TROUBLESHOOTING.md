# Troubleshooting Guide - Trend Following Strategy v2.0

## 🔴 Problemy Startowe

### Problem: "NO DATA" na Dashboard
**Symptom**: Panel pokazuje szary badge "NO DATA" bez względu na to co robisz

**Rozwiązanie** (Kroki po kolei):

1. **Pobierz dane dla SPY (benchmark)**
   ```
   Kliknij: "Download Data (YFinance)"
   Wpisz: SPY
   Czekaj: 20-30 sekund
   ```

2. **Pobierz dane dla co najmniej 5 spółek**
   ```
   Kliknij: "Download Data (YFinance)"
   Wpisz: AAPL
   Kliknij: "Download Data (YFinance)"
   Wpisz: MSFT
   ... powtórz dla innych (GOOGL, TSLA, NVDA, etc.)
   ```

3. **Odśwież panel**
   ```
   Kliknij: "Refresh Analysis"
   Czekaj: Kolory i dane powinny się pojawić
   ```

---

### Problem: "WAITING" status na Dashboard
**Symptom**: Panel pokazuje żółty badge "WAITING" po starcie

**OK - To Normalne!**
- Oznacza że aplikacja czeka na dane
- Pobierz dane zgodnie z instrukcją wyżej

---

### Problem: Błąd "Invalid ticker symbol" przy pobieraniu
**Symptom**: Komunikat błędu przy pobieraniu danych dla tickera

**Rozwiązanie**:
1. Sprawdź czy symbol jest **WIELKIE LITERY** (SPY, nie spy)
2. Sprawdź czy symbol **ISTNIEJE** na Yahoo Finance
3. Spróbuj znowu - czasami Yahoo Finance ma problemy

**Popularne symbole do testowania**:
- SPY (S&P 500 - benchmark)
- AAPL (Apple)
- MSFT (Microsoft)
- GOOGL (Google)
- TSLA (Tesla)
- NVDA (NVIDIA)
- META (Meta)
- AMZN (Amazon)

---

### Problem: Aplikacja się wysypuje (Crash)
**Symptom**: Aplikacja zamyka się bez komunikatu błędu

**Rozwiązanie**:
1. Usuń bazę danych: `C:\Moje\Antigravity\Strategie\app_v2\dane_rynkowe_v2.db`
2. Uruchom aplikację od nowa
3. Pobierz dane od początku (SPY + 5 spółek)

---

## 🟡 Problemy z Danymi

### Problem: Screener pokazuje puste wyniki
**Symptom**: Tabela w "Skaner" jest pusta mimo że pobrano dane

**Rozwiązanie**:
1. Kliknij "Refresh Analysis" w głównym panelu
2. Czekaj 10-15 sekund (obliczenia są intensywne)
3. Dane powinny się pojawić w screenerze

---

### Problem: Slope'y w Screenerze są wszystkie szare
**Symptom**: Kolumna "SMA200_Slope" nie ma kolorów (powinny być zielone/czerwone)

**OK - To Znormalne Przy Małej Ilości Danych**
- Slope'y wymagają co najmniej 200 świec (1 roku danych)
- Jeśli masz mniej niż 1 rok danych, slope'y będą niedostępne
- Czekaj na więcej danych lub pobierz dane z dłuższego okresu

---

### Problem: "Tier" kolumna pokazuje wszystko jako "C"
**Symptom**: Ranking pokazuje tylko Tier C, brak A i B setupów

**Możliwe Przyczyny**:
1. Za mało spółek w bazie (potrzeba co najmniej 10-20)
2. Zbyt nowe dane (algorytm wymaga co najmniej 200 świec na spółkę)
3. Słaby market (nielubiany spółkami trend)

**Rozwiązanie**:
1. Pobierz więcej spółek (20+ symboli)
2. Pobierz dane z YFinance dla każdej (opcja "2y" - ostatnie 2 lata)
3. Czekaj kilka minut na przetworzenie danych

---

## 🟢 FAQ

### P: Ile spółek powinienem dodać?
**O**: Co najmniej 5 dla testów, 20+ dla produkcji. System działa lepiej z większą próbką.

### P: Jak często powinienem odświeżać dane?
**O**: Co dzień przed sesją. Możesz to zautomatyzować - zobacz `Advanced Setup` poniżej.

### P: Czy mogę zmienić benchmark z SPY na inny?
**O**: Tak! Edytuj `konfiguracja.py`:
```python
TYKER_BENCHMARK = "QQQ"  # Lub "DIA", "IWM", etc.
```

### P: Czy system obsługuje akacje międzynarodowe?
**O**: Tak! Yahoo Finance obsługuje większość symboli (np. ASML.AS dla holenderskich akcji)

---

## 🔧 Advanced Setup

### Zautomatyzuj pobieranie danych (Windows Task Scheduler)
1. Utwórz skrypt `auto_download.py`:
```python
from dane.importer import ImporterDanych
from dane.repozytorium import RepozytoriumDanych

tickers = ["SPY", "AAPL", "MSFT", "GOOGL", "TSLA"]
repo = RepozytoriumDanych()

for ticker in tickers:
    swiece = ImporterDanych.pobierz_yfinance(ticker)
    if swiece:
        repo.zapisz_swiece(swiece)
        print(f"✓ {ticker} updated")
```

2. Zaplanuj w Windows Task Scheduler codziennie o 9:00

---

## 📊 Performance Tips

### Aby przyspieszyć przetwarzanie:
1. **Zmniejsz lookback period** w `konfiguracja.py`:
   ```python
   ATR_PERCENTILE_LOOKBACK = 126  # Zamiast 252 (6 miesięcy zamiast 1 roku)
   ```

2. **Zmniejsz liczbę spółek** w screenerze (20-30 zamiast 100+)

3. **Wyłącz multi-timeframe checks** jeśli są powolne:
   ```python
   # W ranking.py linia 168-177: zakomentuj weekly check
   ```

---

## 🐛 Raportowanie Błędów

Jeśli problem się utrzymuje:

1. **Zbierz logi**:
   ```
   Czekaj aż błąd się pojawi
   Skopiuj komunikat błędu do notatnika
   ```

2. **Sprawdź konsolę** (jeśli uruchamiasz z PowerShell):
   ```powershell
   cd C:\Moje\Antigravity\Strategie\app_v2
   python start.py
   # Czekaj na komunikaty błędu
   ```

3. **Wyślij raport** z:
   - Komunikatem błędu (cały tekst)
   - Wersją Python (`python --version`)
   - Co robiłeś przed błędem

---

## ✅ Health Check

Aby sprawdzić czy wszystko działa:

```bash
cd C:\Moje\Antigravity\Strategie\app_v2
python -m pytest testy/test_v2.py -v
```

Powinno wyświetlić:
```
test_wskazniki_slope PASSED
test_ryzyko_pozycji PASSED
test_rezim_bessa PASSED

3 passed in X.XXs
```

Jeśli widać `FAILED` - zgłoś błąd!

---

## 📞 Szybka Pomoc

| Problem | Szybka Naprawa |
|---------|-----------------|
| "NO DATA" | Pobierz SPY + 5 spółek, kliknij "Refresh" |
| Crash | Usuń `.db`, restart |
| Pusty screener | Czekaj 10s, kliknij "Refresh" |
| Puste Tiers | Pobierz 20+ spółek |
| Szare slopes | Czekaj na więcej danych (1 rok) |

---

**Ostatnia Aktualizacja**: 2025-02-15
**Status**: Production Ready ✅
**Wersja**: 2.0

