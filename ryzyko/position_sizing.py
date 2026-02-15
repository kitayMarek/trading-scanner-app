"""
PositionSizing - Moduł do obliczania wielkości pozycji.
Obsługuje 3 mody: Fixed %, Volatility Adjusted, Kelly Fraction.
"""

import pandas as pd
import numpy as np
from enum import Enum
from konfiguracja import Konfiguracja


class PositionSizingMode(Enum):
    """Mody obliczania position sizing'u"""
    FIXED_RISK = "Fixed_Risk"
    VOLATILITY_ADJUSTED = "Volatility_Adjusted"
    KELLY_FRACTION = "Kelly_Fraction"


class PositionSizing:
    """
    Oblicza wielkość pozycji na podstawie ryzyka, volatility i stop loss'u.
    """

    @staticmethod
    def calculate_fixed_risk(account_size: float, risk_percent: float,
                            entry_price: float, stop_loss: float,
                            price_per_share: float = None) -> dict:
        """
        Oblicza wielkość pozycji na bazie Fixed % ryzyka portfela.

        Formula:
            Risk Amount = Account Size * Risk %
            Risk per Share = Entry Price - Stop Loss
            Shares = Risk Amount / Risk per Share

        Args:
            account_size: Rozmiar konta
            risk_percent: % konta na ryzyko (np. 0.01 = 1%)
            entry_price: Cena wejścia
            stop_loss: Cena stop loss'u
            price_per_share: Cena per share (domyślnie = entry_price)

        Returns:
            dict: {
                'shares': float,
                'risk_amount': float,
                'position_size': float (risk_amount / entry_price * shares)
            }
        """
        if price_per_share is None:
            price_per_share = entry_price

        if account_size <= 0 or entry_price <= 0 or stop_loss >= entry_price:
            return {'shares': 0, 'risk_amount': 0.0, 'position_size': 0.0}

        risk_amount = account_size * risk_percent
        risk_per_share = entry_price - stop_loss

        if risk_per_share <= 0:
            return {'shares': 0, 'risk_amount': 0.0, 'position_size': 0.0}

        shares = risk_amount / risk_per_share
        position_value = shares * entry_price

        return {
            'shares': int(shares),
            'risk_amount': round(risk_amount, 2),
            'position_size': round(position_value, 2)
        }

    @staticmethod
    def calculate_volatility_adjusted(account_size: float, base_risk_percent: float,
                                     atr_percentile: float = None,
                                     entry_price: float = None,
                                     stop_loss: float = None,
                                     atr_value: float = None) -> dict:
        """
        Oblicza position sizing dostosowany do zmienności.
        Wyższa zmienność = mniejsza pozycja, niższa zmienność = większa pozycja.

        Formula:
            volatility_factor = ATR_Percentile / 50  (50 to neutral)
            adjusted_risk_percent = base_risk_percent / volatility_factor
            Następnie jak Fixed Risk

        Args:
            account_size: Rozmiar konta
            base_risk_percent: Bazowy % ryzyka
            atr_percentile: ATR percentile (0-100, domyślnie 50)
            entry_price: Cena wejścia
            stop_loss: Cena stop loss'u
            atr_value: Wartość ATR (opcjonalne - alternatywa do percentile)

        Returns:
            dict: {
                'shares': float,
                'risk_amount': float,
                'position_size': float,
                'volatility_factor': float,
                'adjusted_risk_percent': float
            }
        """
        if atr_percentile is None:
            atr_percentile = 50.0

        # Volatility factor: 50 percentyl = 1.0x, 100 = 2.0x, 0 = 0.5x
        volatility_factor = atr_percentile / 50.0

        # Adjust risk: wysoka zmienność = mniejszy risk, niska zmienność = większy risk
        adjusted_risk_percent = base_risk_percent / volatility_factor

        result = {
            'volatility_factor': round(volatility_factor, 2),
            'adjusted_risk_percent': round(adjusted_risk_percent, 4),
            'shares': 0,
            'risk_amount': 0.0,
            'position_size': 0.0
        }

        if entry_price is not None and stop_loss is not None and entry_price > 0:
            fixed_calc = PositionSizing.calculate_fixed_risk(
                account_size, adjusted_risk_percent, entry_price, stop_loss
            )
            result.update(fixed_calc)

        return result

    @staticmethod
    def calculate_kelly_fraction(win_rate: float, avg_win: float, avg_loss: float,
                                account_size: float = None,
                                entry_price: float = None,
                                stop_loss: float = None) -> dict:
        """
        Oblicza position sizing na bazie Kelly Fraction (zaawansowany).
        Kelly % = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win

        Zwykle używa się fractional Kelly (0.25) dla bezpieczeństwa.

        Args:
            win_rate: Win rate (0-1, np. 0.55)
            avg_win: Średnia wygrana (%)
            avg_loss: Średnia strata (%)
            account_size: Rozmiar konta (opcjonalne)
            entry_price: Cena wejścia (opcjonalne)
            stop_loss: Cena stop loss'u (opcjonalne)

        Returns:
            dict: {
                'kelly_percent': float,
                'fractional_kelly': float (0.25 * kelly),
                'shares': float (jeśli entry_price podany),
                'position_size': float
            }
        """
        result = {
            'kelly_percent': 0.0,
            'fractional_kelly': 0.0,
            'shares': 0,
            'position_size': 0.0,
            'message': ''
        }

        # Walidacja
        if not (0 <= win_rate <= 1):
            result['message'] = "Win rate must be 0-1"
            return result

        if avg_win <= 0 or avg_loss <= 0:
            result['message'] = "Average win/loss must be positive"
            return result

        # Kelly formula
        kelly_percent = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win

        # Clamp do 0-100%
        kelly_percent = max(0.0, min(1.0, kelly_percent))

        # Fractional Kelly dla bezpieczeństwa (0.25 = 1/4 Kelly)
        fractional_kelly = kelly_percent * 0.25

        result['kelly_percent'] = round(kelly_percent * 100, 2)
        result['fractional_kelly'] = round(fractional_kelly * 100, 2)

        if account_size is not None and entry_price is not None and stop_loss is not None:
            fixed_calc = PositionSizing.calculate_fixed_risk(
                account_size, fractional_kelly, entry_price, stop_loss
            )
            result.update(fixed_calc)

        return result

    @staticmethod
    def calculate(mode: str, account_size: float, risk_percent: float = None,
                 entry_price: float = None, stop_loss: float = None,
                 atr_percentile: float = None,
                 win_rate: float = None, avg_win: float = None, avg_loss: float = None,
                 atr_multiple: float = Konfiguracja.MULTIPLE_ATR_FOR_STOP) -> dict:
        """
        Uniwersalna metoda do obliczania position sizing'u.

        Args:
            mode: 'fixed_risk', 'volatility_adjusted' lub 'kelly_fraction'
            account_size: Rozmiar konta
            risk_percent: % ryzyka na transakcję
            entry_price: Cena wejścia
            stop_loss: Cena stop loss'u
            atr_percentile: ATR percentile (dla volatility_adjusted)
            win_rate: Win rate (dla kelly_fraction)
            avg_win: Średnia wygrana (dla kelly_fraction)
            avg_loss: Średnia strata (dla kelly_fraction)
            atr_multiple: Mnożnik ATR (dla obliczania stop loss'u)

        Returns:
            dict: Wynik position sizing'u
        """
        if risk_percent is None:
            risk_percent = Konfiguracja.DOMYSLNE_RYZYKO_PROCENT

        mode = mode.lower()

        if mode == 'fixed_risk':
            return PositionSizing.calculate_fixed_risk(
                account_size, risk_percent, entry_price, stop_loss
            )

        elif mode == 'volatility_adjusted':
            return PositionSizing.calculate_volatility_adjusted(
                account_size, risk_percent, atr_percentile, entry_price, stop_loss
            )

        elif mode == 'kelly_fraction':
            return PositionSizing.calculate_kelly_fraction(
                win_rate, avg_win, avg_loss, account_size, entry_price, stop_loss
            )

        else:
            return {'error': f'Unknown mode: {mode}'}

    @staticmethod
    def calculate_portfolio_heat(positions: list, account_size: float) -> dict:
        """
        Oblicza całkowite ryzyko portfela (portfolio heat).

        Args:
            positions: Lista dict'ów z polami:
                {
                    'entry_price': float,
                    'stop_loss': float,
                    'shares': float,
                    'is_open': bool (domyślnie True)
                }
            account_size: Rozmiar konta

        Returns:
            dict: {
                'total_heat': float (% konta),
                'heat_amount': float ($),
                'max_heat': float (maksymalny % z konfiguracji),
                'is_within_limit': bool,
                'positions_count': int
            }
        """
        result = {
            'total_heat': 0.0,
            'heat_amount': 0.0,
            'max_heat': Konfiguracja.MAX_PORTFOLIO_HEAT_PERCENT,
            'is_within_limit': True,
            'positions_count': 0,
            'open_positions': 0
        }

        if not positions or account_size <= 0:
            return result

        total_risk = 0.0
        open_count = 0

        for pos in positions:
            if not isinstance(pos, dict):
                continue

            # Sprawdzenie czy pozycja jest otwarta
            is_open = pos.get('is_open', True)
            if not is_open:
                continue

            open_count += 1

            try:
                entry = pos.get('entry_price', 0)
                stop = pos.get('stop_loss', 0)
                shares = pos.get('shares', 0)

                if entry > 0 and stop >= 0 and shares > 0:
                    risk_per_share = abs(entry - stop)
                    position_risk = risk_per_share * shares
                    total_risk += position_risk

            except Exception as e:
                print(f"Error calculating position heat: {e}")
                continue

        heat_pct = (total_risk / account_size) * 100 if account_size > 0 else 0.0

        result['total_heat'] = round(heat_pct, 2)
        result['heat_amount'] = round(total_risk, 2)
        result['positions_count'] = len(positions)
        result['open_positions'] = open_count
        result['is_within_limit'] = heat_pct <= Konfiguracja.MAX_PORTFOLIO_HEAT_PERCENT

        return result


if __name__ == "__main__":
    print("PositionSizing module loaded")
