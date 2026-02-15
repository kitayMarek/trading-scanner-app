"""
SlopeMetrics - Moduł do obliczania nachyleń (slope) wskaźników technicznych.
Implementuje regresję liniową na 20-dniowych oknach dla SMA, RS i innych metryk.
"""

import pandas as pd
import numpy as np
from enum import Enum
from konfiguracja import Konfiguracja


class SlopeStatus(Enum):
    """Klasyfikacja nachylenia"""
    RISING = "Rising"
    FALLING = "Falling"
    FLAT = "Flat"


class SlopeMetrics:
    """
    Klasa do obliczania slope'ów (nachyleń) serii czasowych.
    Używa regresji liniowej na configurowalnym oknie (domyślnie 20 dni).
    """

    # Cache dla obliczonych slope'ów (unikanie reobliczeń)
    _cache = {}

    @staticmethod
    def _calculate_linear_slope(series: np.ndarray) -> float:
        """
        Oblicza nachylenie regresji liniowej serii wartości.

        Args:
            series: np.ndarray z wartościami

        Returns:
            float: Nachylenie (slope) znormalizowane do średniej wartości w %
        """
        if len(series) < 2:
            return 0.0

        y = series
        x = np.arange(len(y))

        try:
            # Regresja liniowa: y = mx + c, gdzie m to slope
            coeffs = np.polyfit(x, y, 1)
            m = coeffs[0]

            # Normalizacja: % zmiany na dzień w stosunku do średniej wartości
            avg_value = np.mean(y)
            if avg_value == 0:
                return 0.0

            # Slope znormalizowany do % (zmiana procentowa na dzień)
            normalized_slope = (m / avg_value) * 100
            return normalized_slope
        except Exception as e:
            print(f"Error calculating slope: {e}")
            return 0.0

    @staticmethod
    def calculate_sma_slope(df: pd.DataFrame, sma_column: str,
                           window: int = None) -> pd.Series:
        """
        Oblicza slope dla wskazanej kolumny SMA (np. SMA50, SMA200).

        Args:
            df: DataFrame z danymi OHLCV
            sma_column: Nazwa kolumny SMA (np. 'SMA200', 'SMA50')
            window: Okno regresji (domyślnie z konfiguracji)

        Returns:
            pd.Series: Seria z obliczonymi slope'ami
        """
        if window is None:
            window = Konfiguracja.OKRES_NACHYLENIA

        if sma_column not in df.columns:
            return pd.Series(0.0, index=df.index)

        def calc_slope(series):
            return SlopeMetrics._calculate_linear_slope(series.values)

        slopes = df[sma_column].rolling(window=window).apply(calc_slope, raw=False)
        return slopes

    @staticmethod
    def calculate_rs_slope(rs_series: pd.Series, window: int = None) -> pd.Series:
        """
        Oblicza slope dla serii RS (Relative Strength).

        Args:
            rs_series: pd.Series z wartościami RS
            window: Okno regresji (domyślnie z konfiguracji)

        Returns:
            pd.Series: Seria z obliczonymi slope'ami RS
        """
        if window is None:
            window = Konfiguracja.OKRES_NACHYLENIA

        def calc_slope(series):
            return SlopeMetrics._calculate_linear_slope(series.values)

        slopes = rs_series.rolling(window=window).apply(calc_slope, raw=False)
        return slopes

    @staticmethod
    def calculate_multi_slope(df: pd.DataFrame, benchmark_df: pd.DataFrame = None) -> dict:
        """
        Oblicza nachylenia dla wszystkich kluczowych wskaźników:
        - SMA200 slope (daily)
        - SMA50 slope (daily)
        - RS slope (daily)
        - SMA200 slope (weekly - jeśli dostępne dane weekly)

        Args:
            df: DataFrame z danymi daily (musi mieć SMA50, SMA200, RS_Ratio)
            benchmark_df: DataFrame z danymi benchmarku (opcjonalnie dla RS)

        Returns:
            dict z slope'ami dla poszczególnych wskaźników
        """
        result = {
            'sma200_slope': 0.0,
            'sma50_slope': 0.0,
            'rs_slope': 0.0,
            'sma200_slope_weekly': 0.0
        }

        if df.empty:
            return result

        # SMA200 slope
        if 'SMA200' in df.columns:
            result['sma200_slope'] = df['SMA200'].iloc[-1] if len(df) > 0 else 0.0
            # Rzeczywisty slope - ostatnia wartość z rolling calculation
            sma200_slopes = SlopeMetrics.calculate_sma_slope(df, 'SMA200')
            if not sma200_slopes.empty:
                result['sma200_slope'] = sma200_slopes.iloc[-1] if not pd.isna(sma200_slopes.iloc[-1]) else 0.0

        # SMA50 slope
        if 'SMA50' in df.columns:
            sma50_slopes = SlopeMetrics.calculate_sma_slope(df, 'SMA50')
            if not sma50_slopes.empty:
                result['sma50_slope'] = sma50_slopes.iloc[-1] if not pd.isna(sma50_slopes.iloc[-1]) else 0.0

        # RS slope (jeśli dostępny RS_Ratio)
        if 'RS_Ratio' in df.columns:
            rs_slopes = SlopeMetrics.calculate_rs_slope(df['RS_Ratio'])
            if not rs_slopes.empty:
                result['rs_slope'] = rs_slopes.iloc[-1] if not pd.isna(rs_slopes.iloc[-1]) else 0.0

        # Weekly SMA200 slope (jeśli da się obliczyć z daily data)
        # Uproszczona wersja: resample do weekly i oblicz slope
        if len(df) >= Konfiguracja.OKRES_NACHYLENIA:
            try:
                df_weekly = df.resample('W').agg({'SMA200': 'last'}).dropna()
                if len(df_weekly) >= Konfiguracja.OKRES_NACHYLENIA:
                    weekly_slopes = SlopeMetrics.calculate_sma_slope(
                        df_weekly, 'SMA200',
                        window=Konfiguracja.OKRES_NACHYLENIA
                    )
                    if not weekly_slopes.empty:
                        result['sma200_slope_weekly'] = weekly_slopes.iloc[-1] if not pd.isna(weekly_slopes.iloc[-1]) else 0.0
            except Exception as e:
                print(f"Error calculating weekly slope: {e}")
                result['sma200_slope_weekly'] = 0.0

        return result

    @staticmethod
    def get_slope_status(slope_value: float,
                        rising_threshold: float = None,
                        falling_threshold: float = None) -> SlopeStatus:
        """
        Klasyfikuje nachylenie jako Rising, Falling lub Flat.

        Args:
            slope_value: Wartość nachylenia (%)
            rising_threshold: Próg dla Rising (domyślnie z konfiguracji)
            falling_threshold: Próg dla Falling (domyślnie z konfiguracji)

        Returns:
            SlopeStatus: Rising, Falling lub Flat
        """
        if rising_threshold is None:
            rising_threshold = Konfiguracja.SLOPE_RISING_THRESHOLD
        if falling_threshold is None:
            falling_threshold = Konfiguracja.SLOPE_FALLING_THRESHOLD

        if slope_value > rising_threshold:
            return SlopeStatus.RISING
        elif slope_value < falling_threshold:
            return SlopeStatus.FALLING
        else:
            return SlopeStatus.FLAT

    @staticmethod
    def get_slope_status_string(slope_value: float) -> str:
        """
        Zwraca tekstową reprezentację statusu nachylenia.

        Args:
            slope_value: Wartość nachylenia (%)

        Returns:
            str: "Rising", "Falling" lub "Flat"
        """
        status = SlopeMetrics.get_slope_status(slope_value)
        return status.value


# Test/Demo
if __name__ == "__main__":
    # Prostych test
    sample_data = np.array([100, 101, 102, 103, 104, 105, 104, 103, 104, 105])
    slope = SlopeMetrics._calculate_linear_slope(sample_data)
    print(f"Sample slope: {slope:.4f}%")
    print(f"Status: {SlopeMetrics.get_slope_status_string(slope)}")
