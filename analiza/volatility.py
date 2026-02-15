"""
VolatilityMetrics - Moduł do analizy zmienności (volatility) i ATR percentile'ów.
Implementuje volatility regime classification (Low, Medium, High).
"""

import pandas as pd
import numpy as np
from enum import Enum
from konfiguracja import Konfiguracja


class VolatilityRegime(Enum):
    """Klasyfikacja reżimu zmienności"""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class VolatilityMetrics:
    """
    Klasa do obliczania metryk zmienności na podstawie ATR i True Range.
    """

    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = None) -> pd.Series:
        """
        Oblicza Average True Range (ATR).

        Args:
            df: DataFrame z kolumnami 'high', 'low', 'close'
            period: Okres ATR (domyślnie z konfiguracji)

        Returns:
            pd.Series: Serie ATR
        """
        if period is None:
            period = Konfiguracja.OKRES_ATR

        if df.empty or 'high' not in df.columns or 'low' not in df.columns:
            return pd.Series(0.0, index=df.index)

        # Obliczanie True Range
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())

        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)

        # ATR = EMA(True Range) - Exponential Moving Average
        atr = true_range.ewm(span=period, adjust=False).mean()

        return atr

    @staticmethod
    def calculate_atr_percentile(df: pd.DataFrame, atr_column: str = 'ATR14',
                                lookback: int = None) -> pd.Series:
        """
        Oblicza ATR percentile w historii (domyślnie 1 rok = 252 dni).
        Wskazuje, na którym percentilem obecny ATR jest w stosunku do przeszłości.

        Args:
            df: DataFrame z kolumną ATR
            atr_column: Nazwa kolumny ATR (domyślnie 'ATR14')
            lookback: Liczba dni do uwzględnienia (domyślnie 252 = 1 rok)

        Returns:
            pd.Series: ATR percentile (0-100)
        """
        if lookback is None:
            lookback = 252  # 1 rok trading danych

        if atr_column not in df.columns or df.empty:
            return pd.Series(0.0, index=df.index)

        # Obliczanie percentile na rolling oknie
        def percentile_rank(x):
            """Zwraca percentyl wartości ostatniej w oknie"""
            if len(x) == 0:
                return 0.0
            last_val = x.iloc[-1]
            # Percentyl: ile % wartości w oknie jest <= last_val
            percentile = (x <= last_val).sum() / len(x) * 100
            return percentile

        atr_percentile = df[atr_column].rolling(window=lookback).apply(
            percentile_rank, raw=False
        )

        return atr_percentile

    @staticmethod
    def calculate_atr_as_percent(df: pd.DataFrame, atr_column: str = 'ATR14',
                                close_column: str = 'close') -> pd.Series:
        """
        Konwertuje ATR na procent ceny zamknięcia.
        Wskazuje, jaki % ceny stanowi ATR (używane do oceny zmienności).

        Args:
            df: DataFrame z kolumnami ATR i close
            atr_column: Nazwa kolumny ATR
            close_column: Nazwa kolumny close (domyślnie 'close')

        Returns:
            pd.Series: ATR jako % ceny
        """
        if atr_column not in df.columns or close_column not in df.columns:
            return pd.Series(0.0, index=df.index)

        # Unikamy dzielenia przez 0
        atr_pct = (df[atr_column] / df[close_column]) * 100
        atr_pct = atr_pct.fillna(0.0)

        return atr_pct

    @staticmethod
    def get_volatility_regime(atr_percentile: float,
                             low_threshold: float = None,
                             high_threshold: float = None) -> VolatilityRegime:
        """
        Klasyfikuje reżim zmienności na podstawie ATR percentile'a.

        Args:
            atr_percentile: Wartość ATR percentile (0-100)
            low_threshold: Próg dla Low regime (domyślnie 33)
            high_threshold: Próg dla High regime (domyślnie 67)

        Returns:
            VolatilityRegime: Low, Medium lub High
        """
        if low_threshold is None:
            low_threshold = 33
        if high_threshold is None:
            high_threshold = 67

        if atr_percentile < low_threshold:
            return VolatilityRegime.LOW
        elif atr_percentile > high_threshold:
            return VolatilityRegime.HIGH
        else:
            return VolatilityRegime.MEDIUM

    @staticmethod
    def get_volatility_regime_string(atr_percentile: float) -> str:
        """
        Zwraca tekstową reprezentację reżimu zmienności.

        Args:
            atr_percentile: Wartość ATR percentile (0-100)

        Returns:
            str: "Low", "Medium" lub "High"
        """
        regime = VolatilityMetrics.get_volatility_regime(atr_percentile)
        return regime.value

    @staticmethod
    def calculate_volatility_metrics(df: pd.DataFrame) -> dict:
        """
        Oblicza wszystkie metryki zmienności dla DataFrame'a.

        Args:
            df: DataFrame z danymi OHLCV

        Returns:
            dict: Słownik z wszystkimi obliczonymi metrykami zmienności
        """
        result = {
            'atr': 0.0,
            'atr_pct': 0.0,
            'atr_percentile': 0.0,
            'volatility_regime': 'Medium',
            'atr_level': 'Unknown'
        }

        if df.empty:
            return result

        try:
            # Obliczanie ATR
            atr = VolatilityMetrics.calculate_atr(df)
            latest_atr = atr.iloc[-1] if not atr.empty and not pd.isna(atr.iloc[-1]) else 0.0
            result['atr'] = latest_atr

            # ATR jako % ceny
            if 'close' in df.columns and latest_atr > 0:
                atr_pct = (latest_atr / df['close'].iloc[-1]) * 100 if df['close'].iloc[-1] != 0 else 0.0
                result['atr_pct'] = atr_pct

                # ATR percentile (1 rok = 252 dni)
                df['ATR14'] = atr
                atr_pct_series = VolatilityMetrics.calculate_atr_as_percent(df, 'ATR14')
                atr_percentile = VolatilityMetrics.calculate_atr_percentile(
                    df[['ATR14']].assign(ATR14_pct=atr_pct_series),
                    'ATR14',
                    lookback=252
                )
                latest_percentile = atr_percentile.iloc[-1] if not atr_percentile.empty and not pd.isna(atr_percentile.iloc[-1]) else 0.0
                result['atr_percentile'] = latest_percentile

                # Volatility regime
                regime = VolatilityMetrics.get_volatility_regime_string(latest_percentile)
                result['volatility_regime'] = regime

                # Poziom zmienności (Low/Medium/High) - używany do position sizing
                if latest_percentile < 33:
                    result['atr_level'] = 'Low'
                elif latest_percentile > 67:
                    result['atr_level'] = 'High'
                else:
                    result['atr_level'] = 'Medium'

        except Exception as e:
            print(f"Error calculating volatility metrics: {e}")

        return result


# Test/Demo
if __name__ == "__main__":
    # Prosty test
    sample_prices = np.array([100, 101, 102, 101, 100, 99, 100, 101, 102, 103])
    sample_high = sample_prices * 1.02
    sample_low = sample_prices * 0.98

    df = pd.DataFrame({
        'close': sample_prices,
        'high': sample_high,
        'low': sample_low
    })

    atr = VolatilityMetrics.calculate_atr(df)
    print(f"Latest ATR: {atr.iloc[-1]:.2f}")

    atr_pct = VolatilityMetrics.calculate_atr_as_percent(df, atr.name or 'ATR14')
    print(f"ATR as % of close: {atr_pct.iloc[-1]:.2f}%")
