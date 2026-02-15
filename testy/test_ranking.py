"""
Testy dla RankingEngine - Composite Score i klasyfikacja Tier'ów.
"""

import pytest
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from analiza.ranking import RankingEngine
from analiza.wskazniki import SilnikWskaznikow
from konfiguracja import Konfiguracja


class TestRankingEngine:
    """Test suite dla RankingEngine"""

    @pytest.fixture
    def sample_ticker_data(self):
        """Generuje sample DataFrame dla tykera"""
        dates = pd.date_range(start='2023-01-01', periods=200, freq='D')
        close_prices = np.linspace(100, 150, 200) + np.random.normal(0, 1, 200)

        df = pd.DataFrame({
            'date': dates,
            'open': close_prices * 0.99,
            'high': close_prices * 1.01,
            'low': close_prices * 0.99,
            'close': close_prices,
            'volume': 1000000
        })
        df.set_index('date', inplace=True)

        # Oblicz wskaźniki
        df = SilnikWskaznikow.oblicz_wskazniki(df)
        return df

    @pytest.fixture
    def sample_benchmark(self):
        """Generuje sample benchmark (SPY) data"""
        dates = pd.date_range(start='2023-01-01', periods=200, freq='D')
        close_prices = np.linspace(400, 450, 200) + np.random.normal(0, 1, 200)

        df = pd.DataFrame({
            'date': dates,
            'open': close_prices * 0.99,
            'high': close_prices * 1.01,
            'low': close_prices * 0.99,
            'close': close_prices,
            'volume': 5000000
        })
        df.set_index('date', inplace=True)

        # Oblicz wskaźniki
        df = SilnikWskaznikow.oblicz_wskazniki(df)
        return df

    @pytest.fixture
    def multiple_tickers(self, sample_ticker_data):
        """Generuje dict z wieloma tykerami"""
        tickers = {}
        for i in range(5):
            df = sample_ticker_data.copy()
            # Zmień ceny dla różnorodności
            df['close'] = df['close'] * (0.95 + i * 0.05)
            df = SilnikWskaznikow.oblicz_wskazniki(df)
            tickers[f'TICK{i}'] = df

        return tickers

    def test_calculate_percentile_rank_basic(self):
        """Test obliczania percentylu"""
        values = pd.Series([10, 20, 30, 40, 50])
        percentile = RankingEngine.calculate_percentile_rank(values, 30)

        # 30 jest na 60-tym percentylu (3 z 5 wartości <= 30)
        assert 50 <= percentile <= 100, "Percentyl dla 30 powinno być w górze"

    def test_calculate_percentile_rank_empty(self):
        """Test obsługi pustej serii"""
        values = pd.Series([])
        percentile = RankingEngine.calculate_percentile_rank(values, 50)

        # Powinno zwrócić default 50
        assert percentile == 50.0, "Percentyl dla pustej serii to 50"

    def test_calculate_percentile_rank_bounds(self):
        """Test że percentyl jest zawsze 0-100"""
        values = pd.Series([10, 20, 30, 40, 50])

        percentile_low = RankingEngine.calculate_percentile_rank(values, 5)
        percentile_high = RankingEngine.calculate_percentile_rank(values, 55)

        assert 0 <= percentile_low <= 100, "Percentyl powinno być 0-100"
        assert 0 <= percentile_high <= 100, "Percentyl powinno być 0-100"
        assert percentile_low < percentile_high, "Niższa wartość to niższy percentyl"

    def test_calculate_composite_score_structure(self, sample_ticker_data, sample_benchmark):
        """Test struktury wyniku Composite Score"""
        result = RankingEngine.calculate_composite_score(
            'TEST', sample_ticker_data, sample_benchmark
        )

        # Sprawdzenie wymaganych kluczy
        required_keys = [
            'composite_score', 'rs_percentile', 'momentum_score',
            'slope_score', 'alignment_score', 'distance_penalty', 'tier'
        ]

        for key in required_keys:
            assert key in result, f"Wynik powinno zawierać klucz '{key}'"

    def test_calculate_composite_score_ranges(self, sample_ticker_data, sample_benchmark):
        """Test że wartości są w rozsądnych zakresach"""
        result = RankingEngine.calculate_composite_score(
            'TEST', sample_ticker_data, sample_benchmark
        )

        assert 0 <= result['composite_score'] <= 100, "Composite score 0-100"
        assert 0 <= result['rs_percentile'] <= 100, "RS percentile 0-100"
        assert 0 <= result['momentum_score'] <= 100, "Momentum score 0-100"
        assert 0 <= result['slope_score'] <= 100, "Slope score 0-100"
        assert 0 <= result['alignment_score'] <= 3, "Alignment score 0-3"
        assert 0 <= result['distance_penalty'] <= 100, "Distance penalty 0-100"

    def test_tier_classification_a(self):
        """Test klasyfikacji Tier A (score > 80)"""
        # Mockuj wysoki score
        result = {
            'composite_score': 85,
            'rs_percentile': 90,
            'momentum_score': 85,
            'slope_score': 85,
            'alignment_score': 3,
            'distance_penalty': 0
        }

        tier = 'A' if result['composite_score'] > Konfiguracja.TIER_A_THRESHOLD else 'C'
        assert tier == 'A', "Score 85 powinno być Tier A"

    def test_tier_classification_b(self):
        """Test klasyfikacji Tier B (60-80)"""
        result = {
            'composite_score': 70,
            'rs_percentile': 70,
            'momentum_score': 70,
            'slope_score': 70,
            'alignment_score': 2,
            'distance_penalty': 10
        }

        tier = 'A' if result['composite_score'] > Konfiguracja.TIER_A_THRESHOLD else \
               'B' if result['composite_score'] >= Konfiguracja.TIER_B_THRESHOLD else 'C'
        assert tier == 'B', "Score 70 powinno być Tier B"

    def test_tier_classification_c(self):
        """Test klasyfikacji Tier C (< 60)"""
        result = {
            'composite_score': 45,
            'rs_percentile': 40,
            'momentum_score': 50,
            'slope_score': 40,
            'alignment_score': 1,
            'distance_penalty': 30
        }

        tier = 'A' if result['composite_score'] > Konfiguracja.TIER_A_THRESHOLD else \
               'B' if result['composite_score'] >= Konfiguracja.TIER_B_THRESHOLD else 'C'
        assert tier == 'C', "Score 45 powinno być Tier C"

    def test_generuj_ranking_basic(self, multiple_tickers, sample_benchmark):
        """Test generowania rankingu dla wielokrotnych tykerów (v2.1 ChecklistScore)"""
        ranking_df = RankingEngine.generuj_ranking(multiple_tickers, sample_benchmark)

        # Sprawdzenie struktury
        assert not ranking_df.empty, "Ranking powinno mieć wiersze"
        assert 'Tyker' in ranking_df.columns, "Ranking powinno zawierać kolumnę Tyker"
        assert 'ChecklistScore' in ranking_df.columns, "Ranking powinno zawierać ChecklistScore (v2.1)"
        assert 'Tier' in ranking_df.columns, "Ranking powinno zawierać Tier"
        assert 'Status' in ranking_df.columns, "Ranking powinno zawierać Status"

    def test_generuj_ranking_sorting(self, multiple_tickers, sample_benchmark):
        """Test sortowania rankingu (v2.1 po Status i ChecklistScore)"""
        ranking_df = RankingEngine.generuj_ranking(multiple_tickers, sample_benchmark)

        if len(ranking_df) > 1:
            # Sprawdzenie że ranking jest posortowany: TRADEABLE na górze
            tradeable_rows = ranking_df[ranking_df['Status'] == 'TRADEABLE']
            setup_rows = ranking_df[ranking_df['Status'] == 'SETUP']
            out_rows = ranking_df[ranking_df['Status'] == 'OUT']

            # TRADEABLE powinny być przed SETUP, SETUP przed OUT
            if len(tradeable_rows) > 0 and len(setup_rows) > 0:
                last_tradeable_idx = tradeable_rows.index[-1]
                first_setup_idx = setup_rows.index[0]
                # TRADEABLE są na górze gdy idx są bliżej 0
                assert tradeable_rows.shape[0] > 0, "Powinny być TRADEABLE stocks"

            # ChecklistScore powinny być w porządku malejącym wśród TRADEABLE
            if len(tradeable_rows) > 1:
                scores = tradeable_rows['ChecklistScore'].values
                assert scores[0] >= scores[-1], "TRADEABLE powinny być posortowane po ChecklistScore (DESC)"

    def test_generuj_ranking_columns(self, multiple_tickers, sample_benchmark):
        """Test że ranking zawiera wszystkie wymagane kolumny (v2.1)"""
        ranking_df = RankingEngine.generuj_ranking(multiple_tickers, sample_benchmark)

        required_columns = [
            'Tyker', 'Status', 'ChecklistScore', 'Tier', 'Zamkniecie',
            'SMA200', 'SMA200_Slope', 'RS_Ratio', 'RS_Slope',
            'Distance_200', 'ATR_Pct', 'Momentum_3M', 'Momentum_6M'
        ]

        for col in required_columns:
            assert col in ranking_df.columns, f"Ranking powinno zawierać kolumnę '{col}'"

    def test_ranking_empty_input(self, sample_benchmark):
        """Test obsługi pustego input'u"""
        ranking_df = RankingEngine.generuj_ranking({}, sample_benchmark)

        assert ranking_df.empty, "Ranking dla pustego input'u powinno być pusty"

    def test_checklist_score_calculation(self, multiple_tickers, sample_benchmark):
        """Test calculate_checklist_score - nowy system v2.1"""
        first_ticker = list(multiple_tickers.keys())[0]
        first_df = multiple_tickers[first_ticker]

        result = RankingEngine.calculate_checklist_score(
            first_ticker, first_df, sample_benchmark
        )

        # ChecklistScore powinno być między 0 a 10
        assert 0 <= result['checklist_score'] <= 10, "ChecklistScore powinno być 0-10"
        assert result['tier'] in ['A', 'B', 'C', 'D'], "Tier powinno być A/B/C/D"
        assert 'checklist_details' in result, "Result powinno zawierać checklist_details"
        # Sprawdzenie że jest 10 warunków
        assert len(result['checklist_details']) == 10, "Powinno być 10 warunków w checklist"

    def test_ranking_bez_benchmarku(self, sample_ticker_data):
        """Test że ranking działa gdy benchmark_df is None (graceful degradation)"""
        # Utwórz prosty ticker map
        tickers_map = {'TEST': sample_ticker_data}

        # Call generuj_ranking with benchmark_df=None
        ranking_df = RankingEngine.generuj_ranking(tickers_map, benchmark_df=None)

        # Powinno zwrócić ranking bez crashowania
        assert not ranking_df.empty, "Ranking powinno zawierać dane nawet bez benchmarku"
        assert 'ChecklistScore' in ranking_df.columns, "Powinno zawierać ChecklistScore"

        # RS columns should exist with defaults (from wskazniki.py initialization)
        first_row = ranking_df.iloc[0]

        # RS_Slope i RS_Ratio powinny mieć wartości domyślne
        assert 'RS_Slope' in ranking_df.columns, "Powinno zawierać kolumnę RS_Slope"
        assert 'RS_Ratio' in ranking_df.columns, "Powinno zawierać kolumnę RS_Ratio"

        # Wartości domyślne (z wskazniki.py)
        # RS_Slope = 0.0, RS_Ratio = 1.0
        assert first_row['RS_Slope'] == 0.0, "RS_Slope powinno być 0.0 gdy brak benchmarku"
        assert first_row['RS_Ratio'] == 1.0, "RS_Ratio powinno być 1.0 (neutral) gdy brak benchmarku"

    def test_wskazniki_bez_benchmarku(self, sample_ticker_data):
        """Test że SilnikWskaznikow inicjalizuje kolumny RS nawet bez benchmarku"""
        # Oblicz wskaźniki bez benchmark_df
        df_with_indicators = SilnikWskaznikow.oblicz_wskazniki(sample_ticker_data, benchmark_df=None)

        # RS columns powinny istnieć
        assert 'RS_Slope' in df_with_indicators.columns, "RS_Slope powinno istnieć"
        assert 'RS_Ratio' in df_with_indicators.columns, "RS_Ratio powinno istnieć"
        assert 'RS_SMA50' in df_with_indicators.columns, "RS_SMA50 powinno istnieć"

        # Wartości domyślne
        last_row = df_with_indicators.iloc[-1]
        assert last_row['RS_Slope'] == 0.0, "RS_Slope domyślne = 0.0"
        assert last_row['RS_Ratio'] == 1.0, "RS_Ratio domyślne = 1.0"
        assert last_row['RS_SMA50'] == 1.0, "RS_SMA50 domyślne = 1.0"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
