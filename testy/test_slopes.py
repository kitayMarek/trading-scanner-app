"""
Testy dla SlopeMetrics - obliczanie nachyleń technicznych.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Dodaj ścieżkę do parent directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from analiza.slope import SlopeMetrics, SlopeStatus


class TestSlopeMetrics:
    """Test suite dla SlopeMetrics"""

    @pytest.fixture
    def sample_data(self):
        """Generuje sample DataFrame z danymi trend'u wzrostowego"""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        # Trend wzrostowy: 100 -> 150
        close_prices = np.linspace(100, 150, 100) + np.random.normal(0, 1, 100)
        df = pd.DataFrame({
            'date': dates,
            'close': close_prices
        })
        df.set_index('date', inplace=True)
        return df

    @pytest.fixture
    def downtrend_data(self):
        """Generuje sample DataFrame z danymi trend'u spadkowego"""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        # Trend spadkowy: 150 -> 100
        close_prices = np.linspace(150, 100, 100) + np.random.normal(0, 1, 100)
        df = pd.DataFrame({
            'date': dates,
            'close': close_prices
        })
        df.set_index('date', inplace=True)
        return df

    def test_calculate_linear_slope_positive(self):
        """Test obliczania nachylenia dla danych wzrostowych"""
        # Prosta seria rosnąca
        values = np.array([100, 101, 102, 103, 104, 105])
        slope = SlopeMetrics._calculate_linear_slope(values)

        # Powinno być dodatnie
        assert slope > 0, "Slope dla trendu wzrostowego powinno być dodatnie"

    def test_calculate_linear_slope_negative(self):
        """Test obliczania nachylenia dla danych spadkowych"""
        # Prosta seria spadająca
        values = np.array([105, 104, 103, 102, 101, 100])
        slope = SlopeMetrics._calculate_linear_slope(values)

        # Powinno być ujemne
        assert slope < 0, "Slope dla trendu spadkowego powinno być ujemne"

    def test_calculate_linear_slope_flat(self):
        """Test obliczania nachylenia dla danych płaskich"""
        # Płaska seria
        values = np.array([100, 100, 100, 100, 100, 100])
        slope = SlopeMetrics._calculate_linear_slope(values)

        # Powinno być bliskie 0
        assert abs(slope) < 0.1, "Slope dla płaskich danych powinno być bliskie 0"

    def test_calculate_linear_slope_short_series(self):
        """Test obsługi krótkich serii"""
        values = np.array([100])
        slope = SlopeMetrics._calculate_linear_slope(values)

        # Powinno zwrócić 0
        assert slope == 0.0, "Slope dla 1-elementowej serii powinno być 0"

    def test_get_slope_status_rising(self):
        """Test klasyfikacji statusu - Rising"""
        status = SlopeMetrics.get_slope_status(0.005)
        assert status == SlopeStatus.RISING, "Status powinno być RISING"

    def test_get_slope_status_falling(self):
        """Test klasyfikacji statusu - Falling"""
        status = SlopeMetrics.get_slope_status(-0.005)
        assert status == SlopeStatus.FALLING, "Status powinno być FALLING"

    def test_get_slope_status_flat(self):
        """Test klasyfikacji statusu - Flat"""
        status = SlopeMetrics.get_slope_status(0.0)
        assert status == SlopeStatus.FLAT, "Status powinno być FLAT"

    def test_get_slope_status_string(self):
        """Test zwracania string'a statusu"""
        status_str = SlopeMetrics.get_slope_status_string(0.005)
        assert status_str == "Rising", "String status powinno być 'Rising'"

    def test_calculate_sma_slope_basic(self, sample_data):
        """Test obliczania slope dla SMA"""
        # Dodaj SMA do danych
        sample_data['SMA200'] = sample_data['close'].rolling(window=200, min_periods=50).mean()

        # Oblicz slope
        slopes = SlopeMetrics.calculate_sma_slope(sample_data, 'SMA200', window=20)

        # Powinno mieć taką samą długość co DataFrame
        assert len(slopes) == len(sample_data), "Liczba slope'ów powinna zgadzać się z wejściowymi danymi"

    def test_calculate_sma_slope_rising_trend(self, sample_data):
        """Test slope dla wzrastającej SMA"""
        sample_data['SMA50'] = sample_data['close'].rolling(window=50, min_periods=20).mean()

        slopes = SlopeMetrics.calculate_sma_slope(sample_data, 'SMA50', window=20)

        # Ostatnie slope'y powinny być dodatnie (trend wzrostowy)
        last_non_na = slopes.dropna()
        if len(last_non_na) > 0:
            assert last_non_na.iloc[-1] > 0, "Ostatnie slope'y dla wzrostowego trendu powinny być dodatnie"

    def test_calculate_sma_slope_falling_trend(self, downtrend_data):
        """Test slope dla spadającej SMA"""
        downtrend_data['SMA50'] = downtrend_data['close'].rolling(window=50, min_periods=20).mean()

        slopes = SlopeMetrics.calculate_sma_slope(downtrend_data, 'SMA50', window=20)

        # Ostatnie slope'y powinny być ujemne (trend spadkowy)
        last_non_na = slopes.dropna()
        if len(last_non_na) > 0:
            assert last_non_na.iloc[-1] < 0, "Ostatnie slope'y dla spadającego trendu powinny być ujemne"

    def test_calculate_rs_slope(self):
        """Test obliczania slope dla RS"""
        # Simpler RS seria
        rs_values = pd.Series([0.95, 0.96, 0.97, 0.98, 0.99, 1.00, 1.01, 1.02])

        slopes = SlopeMetrics.calculate_rs_slope(rs_values, window=4)

        # Powinno mieć taką samą długość co wejście
        assert len(slopes) == len(rs_values), "Liczba slope'ów RS powinna zgadzać się"

    def test_calculate_multi_slope_with_data(self, sample_data):
        """Test obliczania wielokrotnych slope'ów"""
        # Przygotuj DataFrame z wymaganymi kolumnami
        sample_data['SMA200'] = sample_data['close'].rolling(window=50, min_periods=20).mean()
        sample_data['SMA50'] = sample_data['close'].rolling(window=25, min_periods=10).mean()
        sample_data['RS_Ratio'] = np.linspace(0.9, 1.1, len(sample_data))

        result = SlopeMetrics.calculate_multi_slope(sample_data)

        # Sprawdzenie struktury wyniku
        assert 'sma200_slope' in result, "Wynik powinno zawierać sma200_slope"
        assert 'sma50_slope' in result, "Wynik powinno zawierać sma50_slope"
        assert 'rs_slope' in result, "Wynik powinno zawierać rs_slope"
        assert isinstance(result['sma200_slope'], float), "Wartości powinny być float"

    def test_cache_functionality(self):
        """Test cache'owania (jeśli implementacyjne)"""
        # SlopeMetrics ma _cache dict
        assert hasattr(SlopeMetrics, '_cache'), "SlopeMetrics powinno mieć _cache"
        assert isinstance(SlopeMetrics._cache, dict), "_cache powinno być dict"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
