import pytest
import pandas as pd
import numpy as np
from analiza.entry_engine import SilnikWejscia
from analiza.top1_engine import SilnikDecyzyjny

def test_entry_pullback():
    """Testuje wykrywanie Setupu A (Pullback)"""
    # Symulacja: Cena nad SMA50, spada blisko średniej
    df = pd.DataFrame({
        'close': [100, 105, 102], # Ostatnia blisko 100
        'low': [99, 104, 100],
        'high': [102, 106, 104],
        'volume': [1000, 1000, 1000],
        'SMA50': [100, 100, 100]
    })
    # Musimy zasymulować 'SMA50' w colunach bo entry engine tego wymaga
    # w kodzie produkcyjnym oblicz_wskazniki to robi
    
    # Entry Engine oczekuje kolumn w df, oblicz setup bierze df
    result = SilnikWejscia.ocen_setup(df)
    
    # Warunki:
    # dotkniecie_sma50 = (low_3 <= 101) and (102 > 100) -> True
    # blisko_sma50 = (diff 2%) -> True
    # ret5d... w małym df pct_change zwróci nan, więc może nie przejść
    # Ale w teście entry engine sprawdza ret5d.
    # Musimy mieć >5 wierszy
    
    dane = {
        'close': [100]*50 + [102],
        'low': [100]*50 + [100.5], # Low close to SMA50
        'high': [105]*51,
        'volume': [1000]*51,
        'SMA50': [100]*51
    }
    df_long = pd.DataFrame(dane)
    
    res = SilnikWejscia.ocen_setup(df_long)
    assert 'A (Pullback)' in res['typ']
    
def test_market_gate_block():
    """Testuje blokadę gdy rynek jest pod SMA200"""
    market = pd.DataFrame({
        'close': [90],
        'SMA200': [100],
        'SMA200_Slope': [-0.1]
    })
    status = SilnikDecyzyjny.analizuj_rynek(market)
    assert status == "BLOCK"
    
def test_market_gate_allow():
    """Testuje ALLOW gdy rynek rośnie"""
    market = pd.DataFrame({
        'close': [110],
        'SMA200': [100],
        'SMA200_Slope': [0.1] # Positive Slope
    })
    status = SilnikDecyzyjny.analizuj_rynek(market)
    assert status == "ALLOW"
