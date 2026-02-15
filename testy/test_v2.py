import pytest
import pandas as pd
import numpy as np
from analiza.wskazniki import SilnikWskaznikow
from analiza.rezim import SilnikRezimu
from ryzyko.zarzadzanie import ZarzadzanieRyzykiem

def test_wskazniki_slope():
    # Prosta seria rosnąca
    data = {
        'close': np.linspace(100, 110, 100), # Liniowy wzrost
        'high': np.linspace(101, 111, 100),
        'low': np.linspace(99, 109, 100),
        'open': np.linspace(100, 110, 100),
        'volume': [1000] * 100
    }
    df = pd.DataFrame(data)
    df = SilnikWskaznikow.oblicz_wskazniki(df)
    
    assert 'SMA50' in df.columns
    # Slope powinien być dodatni (bo cena rośnie)
    # SMA50 slope też powinien być > 0 w pewnym momencie
    # Porównujemy ostatnią wartość z pierwszą dostępną (indeks 50, bo window=50)
    assert df['SMA50'].iloc[-1] > df['SMA50'].iloc[50]

def test_ryzyko_pozycji():
    # Portfel 100k, wejście 100, stop 90 (ryzyko 10), target 130 (zysk 30) -> R:R 3
    wynik = ZarzadzanieRyzykiem.oblicz_pozycje(
        wielkosc_portfela=100000,
        cena_wejscia=100,
        stop_loss=90,
        cena_celowana=130,
        procent_ryzyka=0.01
    )
    
    # 1% z 100k = 1000 ryzyka
    # Ryzyko na akcję = 10
    # Akcje = 1000 / 10 = 100
    assert wynik.liczba_akcji == 100
    assert wynik.wspolczynnik_rr == 3.0
    assert wynik.jest_poprawny_rr == True

def test_rezim_bessa():
    # Test dla Bear regime (v2.0 uses MarketRegime enum + requires DatetimeIndex)
    dates = pd.date_range(start='2023-01-01', periods=210, freq='D')
    data = {
        'close': [100] * 200 + [90] * 10,  # Spadek poniżej średniej
        'high': [100] * 210,
        'low': [90] * 210,
        'SMA200': [100] * 210,
        'SMA50': [95] * 210,
        'SMA200_Slope': [-0.05] * 210
    }
    df = pd.DataFrame(data, index=dates)  # DatetimeIndex required for resample

    # New v2.0 API returns (MarketRegime enum, description)
    status_str, opis = SilnikRezimu.wykryj_rezim(df)

    # New names in v2.0
    assert status_str in ["BEAR", "STRONG_BEAR", "BESSA", "SILNA BESSA"]  # Support both old and new names
