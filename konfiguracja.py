class Konfiguracja:
    # Baza Danych
    NAZWA_BAZY = "dane_rynkowe_v2.db"

    # Wskaźniki
    SMA_SZYBKA = 50
    SMA_WOLNA = 200
    OKRES_ATR = 14
    MOMENTUM_KROTKIE = 63  # 3 miesiące
    MOMENTUM_DLUGIE = 126  # 6 miesięcy
    OKRES_NACHYLENIA = 20  # Dni do regresji liniowej

    # Slope Metrics (nowe)
    SLOPE_WINDOW = 20  # Okno regresji do nachylenia
    SLOPE_RISING_THRESHOLD = 0.001  # Próg % dla Rising status
    SLOPE_FALLING_THRESHOLD = -0.001  # Próg % dla Falling status

    # Volatility Metrics (nowe)
    ATR_PERCENTILE_LOOKBACK = 252  # 1 rok = lookback dla ATR percentile
    VOLATILITY_LOW_THRESHOLD = 33  # Percentyl dla Low regime
    VOLATILITY_HIGH_THRESHOLD = 67  # Percentyl dla High regime

    # Ryzyko
    DOMYSLNE_RYZYKO_PROCENT = 0.01  # 1% kapitału
    MIN_RR = 3.0  # Obniżone do 3.0 zgodnie z nową logiką, choć prompt mówi o 5:1 w risk engine, ale 3:1 w MVP. Zostawmy 3 dla elastyczności.
    MULTIPLE_ATR_FOR_STOP = 2.0  # Mnożnik ATR dla stop loss (2x ATR)
    MAX_PORTFOLIO_HEAT_PERCENT = 6.0  # Max % całego portfela na ryzyko otwartych pozycji

    # Reżim Rynkowy
    TYKER_BENCHMARK = "SPY"
    BREADTH_STRONG_BULL_THRESHOLD = 0.75  # 75% spółek >200MA dla STRONG_BULL
    BREADTH_STRONG_BEAR_THRESHOLD = 0.25  # 25% spółek >200MA dla STRONG_BEAR

    # UI
    TYTUL_APLIKACJI = "Strategia Trend Following 2.0"
    ROZMIAR_OKNA = (1400, 900)

    # ===== RANKING v2.0 (Composite Score - DEPRECATED) =====
    # Stary system (0-100) - zachowany dla backward compatibility
    WAGI_RANKINGU = {
        'rs_percentile': 0.30,
        'momentum': 0.20,
        'sma200_slope': 0.20,
        'mtf_alignment': 0.20,
        'distance_penalty': 0.10
    }

    TIER_A_THRESHOLD = 80  # Score >= 80 = Tier A (old system)
    TIER_B_THRESHOLD = 60  # Score >= 60 = Tier B (old system)

    # ===== RANKING v2.1 (ChecklistScore - NOWY SYSTEM) =====
    # System 0-10 punktowy z 10 warunkami binarnymi
    CHECKLIST_TIER_A_MIN = 8      # Score 8-10 = Tier A
    CHECKLIST_TIER_B_MIN = 6      # Score 6-7 = Tier B
    CHECKLIST_TIER_C_MIN = 4      # Score 4-5 = Tier C
    CHECKLIST_TIER_D_MIN = 0      # Score 0-3 = Tier D

    # Progi dla poszczególnych warunków ChecklistScore
    ATR_MAX_PCT = 4.0             # Maksymalna zmienność % dla punktu 10
    DISTANCE_MIN_PCT = -20.0      # Minimalna dystans % od SMA200 dla punktu 9
    DISTANCE_MAX_PCT = 20.0       # Maksymalna dystans % od SMA200 dla punktu 9

    # Distance Metrics (legacy - kept for old system)
    DISTANCE_PENALTY_THRESHOLD = 30  # % - jeśli cena >30% od SMA200, to penalty

    # ===== BACKTESTING v1.0 =====
    BACKTEST_KAPITAL   = 100_000.0   # Domyślny kapitał startowy (USD)
    BACKTEST_PROWIZJA  = 0.001       # Prowizja ułamkowa (0.001 = 0.1% per trade)
