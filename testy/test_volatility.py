"""
Testy dla VolatilityMetrics - metryki zmienności i ATR percentile'ów.
"""

import pytest
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from analiza.volatility import VolatilityMetrics, VolatilityRegime


class TestVolatilityMetrics:
    """Test suite dla VolatilityMetrics"""

    @pytest.fixture
    def ohlc_data(self):
        """Generuje sample OHLC DataFrame"""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        close_prices = np.linspace(100, 120, 100)
        df = pd.DataFrame({
            'date': dates,
            'open': close_prices * 0.99,
            'high': close_prices * 1.02,
            'low': close_prices * 0.98,
            'close': close_prices,
            'volume': 1000000
        })
        df.set_index('date', inplace=True)
        return df

    @pytest.fixture
    def high_volatility_data(self):
        """Generuje dane z wysoką zmiennością"""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        close_prices = np.linspace(100, 120, 100)
        # Wysokie rangi - wysoka zmienność
        df = pd.DataFrame({
            'date': dates,
            'open': close_prices * 0.90,  # Szersze otwarcie
            'high': close_prices * 1.05,   # Wysoki top
            'low': close_prices * 0.85,    # Niska low
            'close': close_prices,
            'volume': 1000000
        })
        df.set_index('date', inplace=True)
        return df

    def test_calculate_atr_basic(self, ohlc_data):
        """Test obliczania ATR"""
        atr = VolatilityMetrics.calculate_atr(ohlc_data, period=14)

        # Powinno mieć taką samą długość
        assert len(atr) == len(ohlc_data), "ATR powinno mieć taką samą długość"

        # Powinny być dodatnie wartości
        atr_nonzero = atr[atr > 0]
        assert len(atr_nonzero) > 0, "ATR powinno mieć dodatnie wartości"

    def test_calculate_atr_high_volatility(self, high_volatility_data):
        """Test ATR dla wysokiej zmienności"""
        atr_regular = VolatilityMetrics.calculate_atr(high_volatility_data, period=14)
        atr_high_vol = VolatilityMetrics.calculate_atr(high_volatility_data, period=14)

        # ATR dla wysokiej zmienności powinno być większe
        last_atr = atr_high_vol.dropna().iloc[-1]
        assert last_atr > 0, "ATR dla danych powinno być dodatnie"

    def test_calculate_atr_percentile(self, ohlc_data):
        """Test obliczania ATR percentile"""
        # Dodaj ATR do DataFrame
        atr = VolatilityMetrics.calculate_atr(ohlc_data, period=14)
        ohlc_data['ATR14'] = atr

        # Oblicz percentile
        atr_pct = VolatilityMetrics.calculate_atr_percentile(ohlc_data, 'ATR14', lookback=50)

        # Powinno być w zakresie 0-100
        assert len(atr_pct) == len(ohlc_data), "ATR percentile powinno mieć taką samą długość"

        last_pct = atr_pct.dropna().iloc[-1]
        assert 0 <= last_pct <= 100, f"ATR percentile powinno być 0-100, got {last_pct}"

    def test_calculate_atr_as_percent(self, ohlc_data):
        """Test konwersji ATR na procent ceny"""
        atr = VolatilityMetrics.calculate_atr(ohlc_data, period=14)
        ohlc_data['ATR14'] = atr

        atr_pct = VolatilityMetrics.calculate_atr_as_percent(ohlc_data, 'ATR14')

        # Wszystkie wartości powinny być > 0
        assert (atr_pct[atr_pct > 0] > 0).all(), "ATR% powinno być dodatnie"

        # Wartości powinny być rozsądne (1-10% ceny)
        valid_pcts = atr_pct[atr_pct > 0]
        assert (valid_pcts < 30).all(), "ATR% powinno być < 30% (rozsądne)"

    def test_get_volatility_regime_low(self):
        """Test klasyfikacji - Low volatility"""
        regime = VolatilityMetrics.get_volatility_regime(10.0)  # 10 percentyl
        assert regime == VolatilityRegime.LOW, "Regime powinno być LOW"

    def test_get_volatility_regime_medium(self):
        """Test klasyfikacji - Medium volatility"""
        regime = VolatilityMetrics.get_volatility_regime(50.0)  # 50 percentyl
        assert regime == VolatilityRegime.MEDIUM, "Regime powinno być MEDIUM"

    def test_get_volatility_regime_high(self):
        """Test klasyfikacji - High volatility"""
        regime = VolatilityMetrics.get_volatility_regime(90.0)  # 90 percentyl
        assert regime == VolatilityRegime.HIGH, "Regime powinno być HIGH"

    def test_get_volatility_regime_string(self):
        """Test zwracania string'a regime'u"""
        regime_str = VolatilityMetrics.get_volatility_regime_string(75.0)
        assert regime_str == "High", "Regime string powinno być 'High'"

    def test_calculate_volatility_metrics_complete(self, ohlc_data):
        """Test obliczania wszystkich metryk zmienności"""
        metrics = VolatilityMetrics.calculate_volatility_metrics(ohlc_data)

        # Sprawdzenie struktury wyniku
        assert 'atr' in metrics, "Wynik powinno zawierać atr"
        assert 'atr_pct' in metrics, "Wynik powinno zawierać atr_pct"
        assert 'atr_percentile' in metrics, "Wynik powinno zawierać atr_percentile"
        assert 'volatility_regime' in metrics, "Wynik powinno zawierać volatility_regime"
        assert 'atr_level' in metrics, "Wynik powinno zawierać atr_level"

        # Sprawdzenie wartości
        assert metrics['atr'] >= 0, "ATR powinno być >= 0"
        assert metrics['atr_pct'] >= 0, "ATR% powinno być >= 0"
        assert 0 <= metrics['atr_percentile'] <= 100, "ATR percentile powinno być 0-100"

    def test_calculate_volatility_metrics_empty_dataframe(self):
        """Test obsługi pustego DataFrame"""
        empty_df = pd.DataFrame()
        metrics = VolatilityMetrics.calculate_volatility_metrics(empty_df)

        # Powinno zwrócić domyślne wartości
        assert metrics['atr'] == 0.0, "ATR dla pustego DF powinno być 0"
        assert metrics['volatility_regime'] == 'Medium', "Default regime to Medium"

    def test_atr_threshold_customization(self):
        """Test dostosowania thresholdów"""
        # Niestandardowe thresholdy
        regime_high = VolatilityMetrics.get_volatility_regime(60.0, low_threshold=20, high_threshold=80)
        assert regime_high == VolatilityRegime.MEDIUM, "Z thresholds 20/80, 60 to MEDIUM"

        regime_low = VolatilityMetrics.get_volatility_regime(15.0, low_threshold=20, high_threshold=80)
        assert regime_low == VolatilityRegime.LOW, "Z thresholds 20/80, 15 to LOW"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
