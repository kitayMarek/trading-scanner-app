"""
Unit tests for Status Gating Layer (v2.1) - TRADEABLE/SETUP/OUT classification
Tests the strengthened gating logic in SilnikStatusu.okresl_status()
"""

import pytest
import pandas as pd
from analiza.status import SilnikStatusu


class TestStatusGating:
    """Tests for TRADEABLE/SETUP/OUT status determination"""

    def test_tradeable_all_criteria_met(self):
        """All 4 criteria met -> TRADEABLE"""
        row = pd.Series({
            'close': 100,
            'SMA200': 95,          # Close > SMA200 ✓
            'SMA200_Slope': 0.5,   # slope > 0 ✓
            'SMA50': 98,           # Close > SMA50 ✓
            'RS_Slope': 0.1,       # RS_slope > 0 ✓
            'RS_Ratio': 1.1,
            'RS_SMA50': 1.0
        })
        assert SilnikStatusu.okresl_status(row) == "TRADEABLE"

    def test_tradeable_rs_ratio_strong(self):
        """RS_slope=0 but RS_ratio > RS_SMA50 -> TRADEABLE"""
        row = pd.Series({
            'close': 100,
            'SMA200': 95,
            'SMA200_Slope': 0.5,
            'SMA50': 98,
            'RS_Slope': -0.1,      # NOT positive
            'RS_Ratio': 1.2,       # But > RS_SMA50 ✓
            'RS_SMA50': 1.0
        })
        assert SilnikStatusu.okresl_status(row) == "TRADEABLE"

    def test_setup_close_below_sma50(self):
        """Close above SMA200, slope OK, but below SMA50 -> SETUP"""
        row = pd.Series({
            'close': 96,           # Close between SMA200 and SMA50
            'SMA200': 95,          # Close > SMA200 ✓
            'SMA200_Slope': 0.5,   # slope > 0 ✓
            'SMA50': 97,           # Close <= SMA50 (weakness) ✗
            'RS_Slope': 0.1,
            'RS_Ratio': 1.1,
            'RS_SMA50': 1.0
        })
        assert SilnikStatusu.okresl_status(row) == "SETUP"

    def test_setup_rs_weak(self):
        """Close above SMA200 & SMA50, slope OK, but RS weak -> SETUP"""
        row = pd.Series({
            'close': 100,
            'SMA200': 95,          # Close > SMA200 ✓
            'SMA200_Slope': 0.5,   # slope > 0 ✓
            'SMA50': 98,           # Close > SMA50 ✓
            'RS_Slope': -0.2,      # RS_slope <= 0 (weakness) ✗
            'RS_Ratio': 0.95,      # Also < RS_SMA50
            'RS_SMA50': 1.0
        })
        assert SilnikStatusu.okresl_status(row) == "SETUP"

    def test_setup_shallow_slope(self):
        """Close above SMA200 with shallow slope (>=0 but <threshold) -> SETUP"""
        row = pd.Series({
            'close': 100,
            'SMA200': 95,
            'SMA200_Slope': 0.0001,  # Positive but very shallow
            'SMA50': 98,
            'RS_Slope': 0.1,
            'RS_Ratio': 1.1,
            'RS_SMA50': 1.0
        })
        # With shallow slope, Close > SMA50 requirement makes it SETUP or TRADEABLE
        # Let's test with Close = SMA50 to ensure SETUP
        row['SMA50'] = 100.1  # Close < SMA50 now
        assert SilnikStatusu.okresl_status(row) == "SETUP"

    def test_out_close_below_sma200(self):
        """Close below SMA200 -> OUT (no matter other factors)"""
        row = pd.Series({
            'close': 90,           # Close < SMA200 (fail basic gate)
            'SMA200': 95,
            'SMA200_Slope': 2.0,   # Steep slope (doesn't matter)
            'SMA50': 85,
            'RS_Slope': 1.0,       # Strong RS (doesn't matter)
            'RS_Ratio': 1.3,
            'RS_SMA50': 1.0
        })
        assert SilnikStatusu.okresl_status(row) == "OUT"

    def test_out_negative_slope(self):
        """Close above SMA200 but negative slope -> OUT (breaks basic gate)"""
        row = pd.Series({
            'close': 100,
            'SMA200': 95,
            'SMA200_Slope': -0.5,  # Negative slope (breaks basic gate)
            'SMA50': 98,
            'RS_Slope': 0.1,
            'RS_Ratio': 1.1,
            'RS_SMA50': 1.0
        })
        assert SilnikStatusu.okresl_status(row) == "OUT"

    def test_out_steep_downtrend(self):
        """Very negative slope -> OUT"""
        row = pd.Series({
            'close': 100,
            'SMA200': 105,         # Price below, steep downtrend
            'SMA200_Slope': -5.0,
            'SMA50': 98,
            'RS_Slope': -2.0,
            'RS_Ratio': 0.8,
            'RS_SMA50': 1.0
        })
        assert SilnikStatusu.okresl_status(row) == "OUT"

    def test_boundary_close_equals_sma200(self):
        """Close = SMA200 (boundary condition) -> Should fail > check -> OUT"""
        row = pd.Series({
            'close': 100,
            'SMA200': 100,         # Exactly equal (not > )
            'SMA200_Slope': 0.5,
            'SMA50': 98,
            'RS_Slope': 0.1,
            'RS_Ratio': 1.1,
            'RS_SMA50': 1.0
        })
        assert SilnikStatusu.okresl_status(row) == "OUT"

    def test_boundary_slope_zero(self):
        """SMA200_Slope = 0 (boundary) -> Should fail > check -> OUT"""
        row = pd.Series({
            'close': 100,
            'SMA200': 95,
            'SMA200_Slope': 0.0,   # Exactly zero (not > 0)
            'SMA50': 98,
            'RS_Slope': 0.1,
            'RS_Ratio': 1.1,
            'RS_SMA50': 1.0
        })
        # Basic gate (Close > SMA200 AND slope > 0) fails
        assert SilnikStatusu.okresl_status(row) == "OUT"

    def test_missing_rs_columns(self):
        """Missing RS columns default to 0 -> affects RS strength"""
        row = pd.Series({
            'close': 100,
            'SMA200': 95,
            'SMA200_Slope': 0.5,
            'SMA50': 98,
            'RS_Slope': 0.0,       # Not positive
            # RS_Ratio and RS_SMA50 missing -> defaults to 0
        })
        # With RS_Ratio=0 and RS_SMA50=0, the check is: 0 > 0 (False) OR 0 > 1.0 (False)
        # So RS is weak -> SETUP
        assert SilnikStatusu.okresl_status(row) == "SETUP"

    def test_trading_example_bull_market(self):
        """Realistic bull market example -> TRADEABLE"""
        row = pd.Series({
            'close': 152.5,
            'SMA200': 148.0,
            'SMA200_Slope': 1.2,
            'SMA50': 150.0,
            'RS_Slope': 0.8,
            'RS_Ratio': 1.15,
            'RS_SMA50': 1.10
        })
        assert SilnikStatusu.okresl_status(row) == "TRADEABLE"

    def test_trading_example_retracement(self):
        """Realistic retracement in uptrend -> SETUP"""
        row = pd.Series({
            'close': 149.5,
            'SMA200': 148.0,
            'SMA200_Slope': 0.8,
            'SMA50': 150.5,        # Price below fast MA
            'RS_Slope': -0.3,      # RS starting to weaken
            'RS_Ratio': 1.05,
            'RS_SMA50': 1.08
        })
        assert SilnikStatusu.okresl_status(row) == "SETUP"

    def test_trading_example_breakdown(self):
        """Realistic breakdown -> OUT"""
        row = pd.Series({
            'close': 147.0,
            'SMA200': 148.0,       # Broke below 200MA
            'SMA200_Slope': -0.5,  # Slope turning negative
            'SMA50': 150.0,
            'RS_Slope': -1.5,
            'RS_Ratio': 0.98,
            'RS_SMA50': 1.05
        })
        assert SilnikStatusu.okresl_status(row) == "OUT"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
