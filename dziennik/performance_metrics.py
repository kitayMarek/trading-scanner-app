"""
PerformanceMetrics - Moduł do obliczania metryk performance'u trade'ów.
R-multiple, expectancy, profit factor, MAE/MFE, equity curve, rolling win rate.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from enum import Enum


class TradeStatus(Enum):
    """Status trade'u"""
    OPEN = "Open"
    CLOSED = "Closed"
    WIN = "Win"
    LOSS = "Loss"
    BREAKEVEN = "Breakeven"


class PerformanceMetrics:
    """
    Oblicza zaawansowane metryki performance'u dla trade'ów.
    """

    @staticmethod
    def calculate_r_multiple(entry_price: float, exit_price: float, stop_loss: float) -> float:
        """
        Oblicza R-multiple: ile razy zysk/strata jest większy od ryzyka.

        Formula:
            R = (exit - entry) / (entry - stop)
            R > 1 = zysk, R < 0 = strata, R = 0 = breakeven

        Args:
            entry_price: Cena wejścia
            exit_price: Cena wyjścia
            stop_loss: Cena stop loss'u

        Returns:
            float: R-multiple
        """
        if entry_price == 0 or stop_loss == 0:
            return 0.0

        try:
            risk_per_share = abs(entry_price - stop_loss)
            if risk_per_share == 0:
                return 0.0

            profit_loss = exit_price - entry_price
            r_multiple = profit_loss / risk_per_share

            return round(r_multiple, 2)
        except Exception:
            return 0.0

    @staticmethod
    def calculate_win_rate(trades_list: list) -> dict:
        """
        Oblicza win rate i statystyki wygranych/przegranych.

        Args:
            trades_list: Lista dict'ów z polami: 'pnl', 'entry', 'exit', 'stop'

        Returns:
            dict: {
                'win_rate': float (0-1),
                'win_count': int,
                'loss_count': int,
                'breakeven_count': int,
                'total_trades': int
            }
        """
        result = {
            'win_rate': 0.0,
            'win_count': 0,
            'loss_count': 0,
            'breakeven_count': 0,
            'total_trades': 0
        }

        if not trades_list:
            return result

        win_count = 0
        loss_count = 0
        be_count = 0

        for trade in trades_list:
            if not isinstance(trade, dict):
                continue

            pnl = trade.get('pnl', 0)

            if pnl > 0.001:  # Margin dla floating point
                win_count += 1
            elif pnl < -0.001:
                loss_count += 1
            else:
                be_count += 1

        total = win_count + loss_count + be_count
        result['total_trades'] = total
        result['win_count'] = win_count
        result['loss_count'] = loss_count
        result['breakeven_count'] = be_count

        if total > 0:
            result['win_rate'] = round(win_count / total, 4)

        return result

    @staticmethod
    def calculate_avg_win_loss(trades_list: list) -> dict:
        """
        Oblicza średnią wygraną i stratę.

        Args:
            trades_list: Lista dict'ów z polem 'pnl'

        Returns:
            dict: {
                'avg_win': float,
                'avg_loss': float,
                'sum_wins': float,
                'sum_losses': float
            }
        """
        result = {
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'sum_wins': 0.0,
            'sum_losses': 0.0,
            'win_count': 0,
            'loss_count': 0
        }

        if not trades_list:
            return result

        wins = []
        losses = []

        for trade in trades_list:
            if not isinstance(trade, dict):
                continue

            pnl = trade.get('pnl', 0)

            if pnl > 0.001:
                wins.append(pnl)
            elif pnl < -0.001:
                losses.append(abs(pnl))

        result['win_count'] = len(wins)
        result['loss_count'] = len(losses)
        result['sum_wins'] = sum(wins)
        result['sum_losses'] = sum(losses)

        if wins:
            result['avg_win'] = round(sum(wins) / len(wins), 2)

        if losses:
            result['avg_loss'] = round(sum(losses) / len(losses), 2)

        return result

    @staticmethod
    def calculate_expectancy(win_rate: float, avg_win: float, avg_loss: float) -> float:
        """
        Oblicza expectancy (średni zysk/stratę per trade).

        Formula:
            Expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)

        Args:
            win_rate: Win rate (0-1)
            avg_win: Średnia wygrana ($)
            avg_loss: Średnia strata ($)

        Returns:
            float: Expectancy ($)
        """
        if not (0 <= win_rate <= 1):
            return 0.0

        try:
            expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
            return round(expectancy, 2)
        except Exception:
            return 0.0

    @staticmethod
    def calculate_profit_factor(trades_list: list) -> float:
        """
        Oblicza profit factor: sum of wins / sum of losses.
        > 1.5 jest uważane za dobre.

        Args:
            trades_list: Lista dict'ów z polem 'pnl'

        Returns:
            float: Profit factor
        """
        if not trades_list:
            return 0.0

        sum_wins = 0.0
        sum_losses = 0.0

        for trade in trades_list:
            if not isinstance(trade, dict):
                continue

            pnl = trade.get('pnl', 0)

            if pnl > 0:
                sum_wins += pnl
            elif pnl < 0:
                sum_losses += abs(pnl)

        if sum_losses == 0:
            return sum_wins  # Jeśli bez strat, return całego zysku

        profit_factor = sum_wins / sum_losses
        return round(profit_factor, 2)

    @staticmethod
    def calculate_mae_mfe(entry: float, exit: float, stop: float,
                         high_in_trade: float = None, low_in_trade: float = None) -> dict:
        """
        Oblicza MAE (Maximum Adverse Excursion) i MFE (Maximum Favorable Excursion).

        MAE: najgorsza cena jaka była vs entry (przed wyj ściem)
        MFE: najlepsza cena jaka była vs entry (przed wyjściem)

        Args:
            entry: Cena wejścia
            exit: Cena wyjścia
            stop: Cena stop loss'u
            high_in_trade: Najwyższa cena w trade (dla long)
            low_in_trade: Najniższa cena w trade (dla short)

        Returns:
            dict: {
                'mae': float (% od entry),
                'mfe': float (% od entry),
                'mae_to_stop': float (jaki % stop loss był osiągnięty)
            }
        """
        result = {
            'mae': 0.0,
            'mfe': 0.0,
            'mae_to_stop': 0.0,
            'mae_amount': 0.0,
            'mfe_amount': 0.0
        }

        if entry == 0:
            return result

        try:
            # Long trade: High > entry, Low < entry
            if exit > entry:
                # Long trade
                mae_amount = (entry - low_in_trade) if low_in_trade else 0
                mfe_amount = (high_in_trade - entry) if high_in_trade else 0
            else:
                # Short trade
                mae_amount = (high_in_trade - entry) if high_in_trade else 0
                mfe_amount = (entry - low_in_trade) if low_in_trade else 0

            mae_pct = (mae_amount / abs(entry)) * 100 if entry != 0 else 0
            mfe_pct = (mfe_amount / abs(entry)) * 100 if entry != 0 else 0

            result['mae_amount'] = round(mae_amount, 2)
            result['mfe_amount'] = round(mfe_amount, 2)
            result['mae'] = round(mae_pct, 2)
            result['mfe'] = round(mfe_pct, 2)

            # MAE to stop: jaki % stop loss'u było osiągnięte
            if entry != stop:
                stop_distance = abs(entry - stop)
                mae_to_stop = (mae_amount / stop_distance) * 100 if stop_distance > 0 else 0
                result['mae_to_stop'] = round(mae_to_stop, 2)

        except Exception as e:
            print(f"Error calculating MAE/MFE: {e}")

        return result

    @staticmethod
    def calculate_equity_curve(trades_list: list, starting_equity: float = 10000) -> pd.Series:
        """
        Oblicza equity curve (zmiana kapitału w miarę trade'ów).

        Args:
            trades_list: Lista dict'ów z polem 'pnl'
            starting_equity: Kapitał początkowy

        Returns:
            pd.Series: Equity curve z indeksem = numer trade'u
        """
        if not trades_list:
            return pd.Series()

        equity_values = [starting_equity]

        for trade in trades_list:
            if not isinstance(trade, dict):
                continue

            pnl = trade.get('pnl', 0)
            last_equity = equity_values[-1]
            new_equity = last_equity + pnl
            equity_values.append(new_equity)

        return pd.Series(equity_values[:-1], name='Equity')  # Exclude last (duplicate)

    @staticmethod
    def calculate_rolling_win_rate(trades_list: list, window: int = 20) -> pd.Series:
        """
        Oblicza rolling win rate (np. win rate ostatnich 20 trade'ów).

        Args:
            trades_list: Lista dict'ów z polem 'pnl'
            window: Rozmiar okna (domyślnie 20)

        Returns:
            pd.Series: Rolling win rate
        """
        if not trades_list or window <= 0:
            return pd.Series()

        pnls = []
        for trade in trades_list:
            if isinstance(trade, dict):
                pnl = trade.get('pnl', 0)
                pnls.append(1 if pnl > 0 else 0)

        if not pnls:
            return pd.Series()

        rolling_wins = pd.Series(pnls).rolling(window=window).sum()
        rolling_wr = rolling_wins / window

        return rolling_wr

    @staticmethod
    def calculate_max_drawdown(equity_curve: pd.Series) -> dict:
        """
        Oblicza maksymalną spadek z szczytu (Maximum Drawdown).

        Args:
            equity_curve: pd.Series z wartościami equity

        Returns:
            dict: {
                'max_drawdown': float (% z szczytu),
                'max_drawdown_amount': float ($),
                'peak_value': float,
                'trough_value': float
            }
        """
        result = {
            'max_drawdown': 0.0,
            'max_drawdown_amount': 0.0,
            'peak_value': 0.0,
            'trough_value': 0.0
        }

        if equity_curve.empty:
            return result

        try:
            # Oblicz running peak
            peak_value = equity_curve.expanding().max()
            drawdown = (equity_curve - peak_value) / peak_value

            max_dd_idx = drawdown.idxmin()
            max_dd_pct = drawdown.iloc[max_dd_idx] * 100

            peak = peak_value.iloc[max_dd_idx]
            trough = equity_curve.iloc[max_dd_idx]
            dd_amount = peak - trough

            result['max_drawdown'] = round(max_dd_pct, 2)
            result['max_drawdown_amount'] = round(dd_amount, 2)
            result['peak_value'] = round(peak, 2)
            result['trough_value'] = round(trough, 2)

        except Exception as e:
            print(f"Error calculating max drawdown: {e}")

        return result

    @staticmethod
    def calculate_recovery_factor(max_drawdown: float, total_return: float) -> float:
        """
        Oblicza recovery factor: total_return / max_drawdown.
        Wyższy = lepszy (system odrabia straty szybciej).

        Args:
            max_drawdown: Maksymalny drawdown ($)
            total_return: Całkowity return ($)

        Returns:
            float: Recovery factor
        """
        if max_drawdown == 0 or max_drawdown < 0:
            return 0.0

        try:
            recovery = total_return / max_drawdown
            return round(recovery, 2)
        except Exception:
            return 0.0

    @staticmethod
    def generate_performance_report(trades_list: list, starting_equity: float = 10000) -> dict:
        """
        Generuje kompletny raport performance'u.

        Args:
            trades_list: Lista dict'ów z trade'ami
            starting_equity: Kapitał początkowy

        Returns:
            dict: Kompletny raport metryk
        """
        report = {
            'total_trades': 0,
            'win_rate': 0.0,
            'win_count': 0,
            'loss_count': 0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'expectancy': 0.0,
            'profit_factor': 0.0,
            'total_pnl': 0.0,
            'total_return_pct': 0.0,
            'max_drawdown': 0.0,
            'recovery_factor': 0.0,
            'sharpe_ratio': 0.0
        }

        if not trades_list:
            return report

        try:
            # Win rate
            wr = PerformanceMetrics.calculate_win_rate(trades_list)
            report.update(wr)

            # Avg win/loss
            al = PerformanceMetrics.calculate_avg_win_loss(trades_list)
            report['avg_win'] = al['avg_win']
            report['avg_loss'] = al['avg_loss']

            # Expectancy
            report['expectancy'] = PerformanceMetrics.calculate_expectancy(
                wr['win_rate'], al['avg_win'], al['avg_loss']
            )

            # Profit factor
            report['profit_factor'] = PerformanceMetrics.calculate_profit_factor(trades_list)

            # Total PnL
            total_pnl = sum(t.get('pnl', 0) for t in trades_list if isinstance(t, dict))
            report['total_pnl'] = round(total_pnl, 2)
            report['total_return_pct'] = round((total_pnl / starting_equity) * 100, 2)

            # Equity curve
            ec = PerformanceMetrics.calculate_equity_curve(trades_list, starting_equity)
            if not ec.empty:
                dd = PerformanceMetrics.calculate_max_drawdown(ec)
                report['max_drawdown'] = dd['max_drawdown']
                report['recovery_factor'] = PerformanceMetrics.calculate_recovery_factor(
                    dd['max_drawdown_amount'], total_pnl
                )

        except Exception as e:
            print(f"Error generating performance report: {e}")

        return report


if __name__ == "__main__":
    print("PerformanceMetrics module loaded")
