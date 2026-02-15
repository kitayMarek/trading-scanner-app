"""
DynamicStop - Moduł do sugerowania dynamicznych stop loss'ów.
Obsługuje 4 metody: ATR-based, Below SMA50, Below SMA200, Structure Low.
"""

import pandas as pd
import numpy as np
from enum import Enum
from konfiguracja import Konfiguracja


class StopMethod(Enum):
    """Metody obliczania stop loss'u"""
    ATR_BASED = "ATR_Based"
    BELOW_SMA50 = "Below_SMA50"
    BELOW_SMA200 = "Below_SMA200"
    STRUCTURE_LOW = "Structure_Low"


class DynamicStop:
    """
    Oblicza sugestie stop loss'ów na podstawie różnych metod.
    Pomaga w pozycjonowaniu ryzyka zgodnie z techniką i zmiennością.
    """

    @staticmethod
    def calculate_atr_based_stop(df: pd.DataFrame, atr_multiple: float = None) -> float:
        """
        Oblicza stop loss na bazie ATR: Stop = Close - (multiple * ATR).

        Args:
            df: DataFrame z danymi (musi mieć 'close' i 'ATR14')
            atr_multiple: Mnożnik ATR (domyślnie 2x)

        Returns:
            float: Cena stop loss'u
        """
        if df.empty or 'close' not in df.columns or 'ATR14' not in df.columns:
            return 0.0

        if atr_multiple is None:
            atr_multiple = Konfiguracja.MULTIPLE_ATR_FOR_STOP

        last_close = df['close'].iloc[-1]
        last_atr = df['ATR14'].iloc[-1]

        if pd.isna(last_atr) or last_atr == 0:
            return 0.0

        stop_loss = last_close - (atr_multiple * last_atr)
        return max(0.0, stop_loss)

    @staticmethod
    def calculate_below_sma50_stop(df: pd.DataFrame) -> float:
        """
        Oblicza stop loss poniżej SMA50.
        Stop = SMA50 (lub SMA50 - ATR dla bezpieczności).

        Args:
            df: DataFrame z danymi (musi mieć 'SMA50')

        Returns:
            float: Cena stop loss'u
        """
        if df.empty or 'SMA50' not in df.columns:
            return 0.0

        last_sma50 = df['SMA50'].iloc[-1]

        if pd.isna(last_sma50):
            return 0.0

        # Opcjonalnie: odejmij 1 ATR dla bezpieczności
        last_atr = df['ATR14'].iloc[-1] if 'ATR14' in df.columns else 0
        if not pd.isna(last_atr) and last_atr > 0:
            stop_loss = last_sma50 - (0.5 * last_atr)
        else:
            stop_loss = last_sma50

        return max(0.0, stop_loss)

    @staticmethod
    def calculate_below_sma200_stop(df: pd.DataFrame) -> float:
        """
        Oblicza stop loss poniżej SMA200.
        Stop = SMA200 (lub SMA200 - ATR dla bezpieczności).

        Args:
            df: DataFrame z danymi (musi mieć 'SMA200')

        Returns:
            float: Cena stop loss'u
        """
        if df.empty or 'SMA200' not in df.columns:
            return 0.0

        last_sma200 = df['SMA200'].iloc[-1]

        if pd.isna(last_sma200):
            return 0.0

        # Opcjonalnie: odejmij 1 ATR dla bezpieczności
        last_atr = df['ATR14'].iloc[-1] if 'ATR14' in df.columns else 0
        if not pd.isna(last_atr) and last_atr > 0:
            stop_loss = last_sma200 - (0.5 * last_atr)
        else:
            stop_loss = last_sma200

        return max(0.0, stop_loss)

    @staticmethod
    def calculate_structure_low_stop(df: pd.DataFrame, lookback: int = 20) -> float:
        """
        Oblicza stop loss poniżej ostatniego swing low'u.
        Szuka najniższego low'u w ostatnich N świecach.

        Args:
            df: DataFrame z danymi (musi mieć 'low')
            lookback: Liczba świec do przeszukania (domyślnie 20)

        Returns:
            float: Cena ostatniego swing low'u
        """
        if df.empty or 'low' not in df.columns or len(df) < lookback:
            return 0.0

        # Szukaj najniższego low'u w ostatnich lookback świecach
        recent_lows = df['low'].iloc[-lookback:]
        structure_low = recent_lows.min()

        if pd.isna(structure_low):
            return 0.0

        return max(0.0, structure_low)

    @staticmethod
    def suggest_stops(df: pd.DataFrame) -> dict:
        """
        Sugeruje stop loss'y ze wszystkich 4 metod.

        Args:
            df: DataFrame z danymi OHLCV (musi mieć: close, high, low, ATR14, SMA50, SMA200)

        Returns:
            dict: {
                'atr_based': float,
                'below_sma50': float,
                'below_sma200': float,
                'structure_low': float,
                'recommended': float (default = atr_based)
            }
        """
        result = {
            'atr_based': 0.0,
            'below_sma50': 0.0,
            'below_sma200': 0.0,
            'structure_low': 0.0,
            'recommended': 0.0
        }

        if df.empty or len(df) < 20:
            return result

        try:
            # Oblicz wszystkie metody
            atr_stop = DynamicStop.calculate_atr_based_stop(df)
            sma50_stop = DynamicStop.calculate_below_sma50_stop(df)
            sma200_stop = DynamicStop.calculate_below_sma200_stop(df)
            structure_stop = DynamicStop.calculate_structure_low_stop(df)

            result['atr_based'] = round(atr_stop, 2)
            result['below_sma50'] = round(sma50_stop, 2)
            result['below_sma200'] = round(sma200_stop, 2)
            result['structure_low'] = round(structure_stop, 2)

            # Rekomendacja: użyj ATR-based domyślnie (mały ale bezpieczny)
            # Alternatywa: użyj SMA50 (bardziej agresywny) dla trendów
            last_close = df['close'].iloc[-1]
            last_sma200 = df['SMA200'].iloc[-1] if 'SMA200' in df.columns else last_close

            # Jeśli cena > SMA200 (trend up), użyj ATR
            # Jeśli cena < SMA200 (trend down), użyj SMA50 (węższy stop)
            if last_close > last_sma200:
                result['recommended'] = result['atr_based']
            else:
                # Trend down - bardziej agresywny stop
                result['recommended'] = max(result['below_sma50'], result['structure_low'])

        except Exception as e:
            print(f"Error in suggest_stops: {e}")

        return result

    @staticmethod
    def validate_setup(entry_price: float, stop_loss: float, target_price: float,
                      min_rr_ratio: float = None) -> dict:
        """
        Waliduje setup na podstawie risk:reward ratio.

        Args:
            entry_price: Cena wejścia
            stop_loss: Cena stop loss'u
            target_price: Cena celu (exit)
            min_rr_ratio: Minimalny R:R ratio (domyślnie z konfiguracji)

        Returns:
            dict: {
                'is_valid': bool,
                'risk_amount': float,
                'reward_amount': float,
                'rr_ratio': float,
                'message': str
            }
        """
        if min_rr_ratio is None:
            min_rr_ratio = Konfiguracja.MIN_RR

        result = {
            'is_valid': False,
            'risk_amount': 0.0,
            'reward_amount': 0.0,
            'rr_ratio': 0.0,
            'message': ''
        }

        if entry_price <= 0 or stop_loss < 0 or target_price <= 0:
            result['message'] = "Invalid prices"
            return result

        # Stop powinien być na drugiej stronie entry
        if entry_price > target_price:  # Short
            if stop_loss <= target_price:
                result['message'] = "Invalid stop for short (stop must be above target)"
                return result
            risk = stop_loss - entry_price
            reward = entry_price - target_price
        else:  # Long
            if stop_loss >= entry_price:
                result['message'] = "Invalid stop for long (stop must be below entry)"
                return result
            risk = entry_price - stop_loss
            reward = target_price - entry_price

        if risk == 0:
            result['message'] = "Risk cannot be zero"
            return result

        rr_ratio = reward / risk
        result['risk_amount'] = abs(risk)
        result['reward_amount'] = abs(reward)
        result['rr_ratio'] = round(rr_ratio, 2)

        if rr_ratio >= min_rr_ratio:
            result['is_valid'] = True
            result['message'] = f"Valid setup - R:R {rr_ratio:.2f}"
        else:
            result['message'] = f"Invalid setup - R:R {rr_ratio:.2f} (min {min_rr_ratio})"

        return result


if __name__ == "__main__":
    # Demo
    print("DynamicStop module loaded")
