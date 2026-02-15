import pandas as pd
import numpy as np
from konfiguracja import Konfiguracja

class SilnikWskaznikow:
    @staticmethod
    def oblicz_nachylenie(czesc_serii):
        """Oblicza nachylenie (slope) regresji liniowej znormalizowane do ceny."""
        y = czesc_serii.values
        x = np.arange(len(y))
        
        # Prosta regresja liniowa: y = mx + c
        # m = slope
        try:
            m, c = np.polyfit(x, y, 1)
            # Normalizacja: % zmiany na dzień w okresie regresji
            # Aby to było porównywalne, dzielimy przez średnią cenę z okresu
            srednia_cena = np.mean(y)
            if srednia_cena == 0: return 0
            scaled_slope = (m / srednia_cena) * 100
            return scaled_slope
        except:
            return 0.0

    @staticmethod
    def oblicz_wskazniki(df: pd.DataFrame, benchmark_df: pd.DataFrame = None) -> pd.DataFrame:
        """
        Oblicza SMA, ATR, Momentum, RS oraz metryki Slope.
        Wymaga DataFrame z indeksem DateTime i kolumnami 'close', 'high', 'low'.
        Używamy angielskich nazw kolumn wewnątrz pandas dla kompatybilności.
        """
        if df.empty:
            return df
        
        # Dostosowanie nazw jeśli przyszły polskie
        if 'zamkniecie' in df.columns:
            df = df.rename(columns={
                'zamkniecie': 'close', 
                'otwarcie': 'open', 
                'najwyzszy': 'high', 
                'najnizszy': 'low', 
                'wolumen': 'volume'
            })

        # SMA
        df['SMA50'] = df['close'].rolling(window=Konfiguracja.SMA_SZYBKA).mean()
        df['SMA200'] = df['close'].rolling(window=Konfiguracja.SMA_WOLNA).mean()
        
        # Distance Metrics (%)
        df['Dist_SMA50'] = ((df['close'] - df['SMA50']) / df['SMA50']) * 100
        df['Dist_SMA200'] = ((df['close'] - df['SMA200']) / df['SMA200']) * 100
        
        # SMA Slopes (Regresja)
        # To jest kosztowne obliczeniowo, więc robimy to efektywnie używając rolling_apply
        # lub uproszczoną metodę (różnica), ale prompt prosił o regresję.
        # Dla wydajności w pandasie użyjemy sztuczki z wektorami lub rolling apply.
        
        okres_nachylenia = Konfiguracja.OKRES_NACHYLENIA
        
        def calc_slope(x):
            return SilnikWskaznikow.oblicz_nachylenie(x)

        # Używamy rolling().apply() dla SMA200 (ale to może być wolne na dużych danych)
        # Optymalizacja: Slope SMA200 to trend samej średniej.
        # Jeśli Prompt chce slope ceny, czy slope średniej? "SMA200 slope" sugeruje nachylenie Linii Średniej.
        # Więc liczymy regresję na wartościach SMA200.
        
        # Aby przyspieszyć, policzmy na ostatnich 252 dniach tylko, jeśli to live view. 
        # Ale tu robimy backfill. Rolling apply jest ok dla kilku tysięcy wierszy.
        
        if len(df) > okres_nachylenia + 200:
            df['SMA50_Slope'] = df['SMA50'].rolling(window=okres_nachylenia).apply(calc_slope, raw=False)
            df['SMA200_Slope'] = df['SMA200'].rolling(window=okres_nachylenia).apply(calc_slope, raw=False)
        else:
            df['SMA50_Slope'] = 0.0
            df['SMA200_Slope'] = 0.0

        # ATR
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        df['ATR14'] = true_range.rolling(window=Konfiguracja.OKRES_ATR).mean()
        df['ATR_Pct'] = (df['ATR14'] / df['close']) * 100

        # Momentum
        df['Mom3M'] = df['close'].pct_change(periods=Konfiguracja.MOMENTUM_KROTKIE)
        df['Mom6M'] = df['close'].pct_change(periods=Konfiguracja.MOMENTUM_DLUGIE)

        # Initialize RS columns with defaults (before benchmark calculation)
        # This ensures columns ALWAYS exist even if benchmark fails to load
        df['RS_Ratio'] = 1.0        # Neutral performance vs benchmark
        df['RS_SMA50'] = 1.0         # Neutral SMA
        df['RS_Slope'] = 0.0         # No trend

        # Relative Strength vs Benchmark (will overwrite defaults if benchmark available)
        if benchmark_df is not None and not benchmark_df.empty:
            # Upewnij się co do nazw kolumn benchmarku
            if 'zamkniecie' in benchmark_df.columns:
                benchmark_df = benchmark_df.rename(columns={'zamkniecie': 'close'})

            wspolny_indeks = df.index.intersection(benchmark_df.index)
            if not wspolny_indeks.empty:
                ceny = df.loc[wspolny_indeks, 'close']
                ceny_bench = benchmark_df.loc[wspolny_indeks, 'close']
                
                rs_ratio = ceny / ceny_bench
                
                df.loc[wspolny_indeks, 'RS_Ratio'] = rs_ratio
                df['RS_SMA50'] = df['RS_Ratio'].rolling(window=50).mean()
                
                # RS Slope (20 sesji)
                df['RS_Slope'] = df['RS_Ratio'].rolling(window=okres_nachylenia).apply(calc_slope, raw=False)
        
        return df

    @staticmethod
    def filtruj_stan_nachylenia(wartosc_nachylenia):
        if wartosc_nachylenia > 0.05: return "ROSNĄCY" # Rising
        if wartosc_nachylenia < -0.05: return "SPADAJĄCY" # Falling
        return "PŁASKI" # Flat
