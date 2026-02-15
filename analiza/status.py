import pandas as pd
from .wskazniki import SilnikWskaznikow

class SilnikStatusu:
    @staticmethod
    def okresl_status(ostatni_wiersz: pd.Series) -> str:
        """
        Określa status tykera: TRADEABLE, SETUP, OUT.
        
        Kryteria TRADEABLE:
        - Close > SMA200
        - SMA200 Slope > 0
        - Close > SMA50
        - RS rośnie (Slope > 0) LUB RS Ratio > wysokie (np. nad SMA50)
          (W prompcie: RS slope > 0 LUB RS ratio > RS_MA)
        
        Kryteria SETUP:
        - Close > SMA200
        - SMA200 Slope >= 0
        - (Ale np. korekta: Close <= SMA50 LUB RS słabnie)
        
        Kryteria OUT:
        - Pozostałe (Bessa)
        """
        # Pobranie wartości (z domyślnymi 0 w razie braku)
        cena = ostatni_wiersz['close']
        sma200 = ostatni_wiersz.get('SMA200', 0)
        sma50 = ostatni_wiersz.get('SMA50', 0)
        slope200 = ostatni_wiersz.get('SMA200_Slope', 0)
        rs_slope = ostatni_wiersz.get('RS_Slope', 0)
        rs_ratio = ostatni_wiersz.get('RS_Ratio', 0)
        rs_ma = ostatni_wiersz.get('RS_SMA50', 0)
        
        # ===== GATING LAYER (Status Determination) =====
        # Wymaga: Close > SMA200 ORAZ SMA200_slope > 0 w OBU przypadkach
        # Bez tego warunku -> OUT (brak trendu)

        cena_nad_sma200 = cena > sma200
        sma200_rosnie = slope200 > 0  # STRICT: musi być Rising (slope > 0)

        # Jeśli brakuje podstawowego trendu -> OUT
        if not (cena_nad_sma200 and sma200_rosnie):
            return "OUT"

        # ===== TRADEABLE CRITERIA (Wszystkie wymagane!) =====
        # 1. Close > SMA200 ✓ (już sprawdzono wyżej)
        # 2. SMA200 slope > 0 ✓ (już sprawdzono wyżej)
        # 3. Close > SMA50 (Short-term trend OK)
        # 4. RS strength: RS_slope > 0 OR RS_ratio > RS_SMA50

        cena_nad_sma50 = cena > sma50
        rs_slope_positive = rs_slope > 0
        rs_ratio_strong = rs_ratio > rs_ma if rs_ma > 0 else rs_ratio > 1.0
        rs_silne = rs_slope_positive or rs_ratio_strong

        jest_tradeable = cena_nad_sma50 and rs_silne

        if jest_tradeable:
            return "TRADEABLE"

        # ===== SETUP CRITERIA =====
        # Spełnia: Close > SMA200 + SMA200_slope >= 0
        # ALE brakuje jednej siły: (Close <= SMA50 OR RS_slope <= 0)
        # To oznacza: Trend jest, ale trzeba czekać na wejście

        sma200_slope_non_negative = slope200 >= 0
        ma_jedna_slabosc = (not cena_nad_sma50) or (not rs_silne)

        jest_setup = cena_nad_sma200 and sma200_slope_non_negative and ma_jedna_slabosc

        if jest_setup:
            return "SETUP"

        # ===== OUT (DEFAULT) =====
        # Wszystko inne (bear market, brak trendu, itd.)
        return "OUT"
