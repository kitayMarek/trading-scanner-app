"""
Silnik backtestingu — czysta logika obliczeniowa, brak importów Qt.

Jedyna zależność zewnętrzna: backtrader, pandas, numpy.
Dane wejściowe: pd.DataFrame z repo.pobierz_swiece_df()
Wynik: słownik z equity_curve, trades, metryki, error.
"""

import backtrader as bt
import backtrader.feeds as btfeeds
import pandas as pd
import numpy as np
import itertools
from typing import Optional, Dict, Any, List

from .strategie import StrategiaTrendMomentum, StrategiaSmaCrossover

# Rejestr dostępnych strategii — klucz = nazwa wyświetlana w UI
DOSTEPNE_STRATEGIE: Dict[str, type] = {
    'Trend Momentum (logika skanera)': StrategiaTrendMomentum,
    'SMA Crossover (baseline)':        StrategiaSmaCrossover,
}


def _dataframe_do_feed(df: pd.DataFrame) -> btfeeds.PandasData:
    """
    Konwertuje DataFrame z repo.pobierz_swiece_df() do Backtrader PandasData.

    Oczekiwana struktura df:
      - indeks: DatetimeIndex (parsowany do datetime)
      - kolumny: open, high, low, close, volume
    """
    # Upewnij się że indeks to DatetimeIndex
    if not isinstance(df.index, pd.DatetimeIndex):
        df = df.copy()
        df.index = pd.to_datetime(df.index)

    return btfeeds.PandasData(
        dataname=df,
        datetime=None,      # używa indeksu
        open='open',
        high='high',
        low='low',
        close='close',
        volume='volume',
        openinterest=-1,    # brak danych OI
    )


class SilnikBacktestingu:
    """
    Fasada do uruchamiania pojedynczego backtestу lub optymalizacji grid-search.
    Brak zależności od Qt — wywoływany z wątku QThread.
    """

    @staticmethod
    def uruchom(
        df_ticker: pd.DataFrame,
        nazwa_strategii: str,
        parametry: dict,
        kapital_poczatkowy: float = 100_000.0,
        df_spy: Optional[pd.DataFrame] = None,
        prowizja: float = 0.001,
    ) -> Dict[str, Any]:
        """
        Uruchamia backtest i zwraca ustrukturyzowany słownik wyników.

        Args:
            df_ticker:         OHLCV DataFrame z repozytorium
            nazwa_strategii:   Klucz z DOSTEPNE_STRATEGIE
            parametry:         Parametry strategii (dict)
            kapital_poczatkowy: Startowy kapitał USD
            df_spy:            Opcjonalny DataFrame SPY do RS (może być None)
            prowizja:          Prowizja ułamkowa (0.001 = 0.1%)

        Returns:
            dict z kluczami:
              'equity_curve' : pd.Series  (DatetimeIndex → wartość portfela)
              'trades'       : list[dict] ({date, pnl, price})
              'metryki'      : dict       (total_return_pct, sharpe, drawdown, …)
              'error'        : str | None
        """
        wynik: Dict[str, Any] = {
            'equity_curve': pd.Series(dtype=float),
            'trades':       [],
            'metryki':      {},
            'error':        None,
        }

        if df_ticker is None or df_ticker.empty:
            wynik['error'] = 'Brak danych dla wybranego tykera.'
            return wynik

        if len(df_ticker) < 250:
            wynik['error'] = (
                f'Zbyt mało danych: {len(df_ticker)} świec. '
                'Wymagane minimum 250 (ok. 1 rok).'
            )
            return wynik

        klasa = DOSTEPNE_STRATEGIE.get(nazwa_strategii)
        if klasa is None:
            wynik['error'] = f'Nieznana strategia: {nazwa_strategii}'
            return wynik

        try:
            cerebro = bt.Cerebro(stdstats=False)
            cerebro.broker.setcash(kapital_poczatkowy)
            cerebro.broker.setcommission(commission=prowizja)

            # Główny feed danych
            cerebro.adddata(_dataframe_do_feed(df_ticker), name='ticker')

            # Opcjonalny feed SPY do RS ratio
            if df_spy is not None and not df_spy.empty:
                # Wyrównaj daty z tickerem
                wspolne = df_ticker.index.intersection(df_spy.index)
                if len(wspolne) >= 200:
                    cerebro.adddata(
                        _dataframe_do_feed(df_spy.loc[wspolne]),
                        name='spy'
                    )

            # Dodaj strategię
            cerebro.addstrategy(klasa, **parametry)

            # Analizatory
            cerebro.addanalyzer(
                bt.analyzers.SharpeRatio,
                _name='sharpe',
                riskfreerate=0.05,
                annualize=True,
                timeframe=bt.TimeFrame.Days,
            )
            cerebro.addanalyzer(bt.analyzers.DrawDown,    _name='drawdown')
            cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
            cerebro.addanalyzer(
                bt.analyzers.TimeReturn,
                _name='timereturn',
                timeframe=bt.TimeFrame.Days,
            )

            # Uruchom
            results  = cerebro.run(runonce=True, preload=True)
            strat    = results[0]

            # ── Equity curve ─────────────────────────────────────────────
            time_return = strat.analyzers.timereturn.get_analysis()
            if time_return:
                ret_series   = pd.Series(time_return)
                ret_series.index = pd.to_datetime(ret_series.index)
                equity_curve = (1 + ret_series).cumprod() * kapital_poczatkowy
            else:
                equity_curve = pd.Series([kapital_poczatkowy], dtype=float)

            wynik['equity_curve'] = equity_curve
            wynik['trades']       = getattr(strat, 'trade_log', [])

            # ── Metryki ───────────────────────────────────────────────────
            final_value  = cerebro.broker.getvalue()
            total_return = (final_value - kapital_poczatkowy) / kapital_poczatkowy * 100

            sharpe_ana  = strat.analyzers.sharpe.get_analysis()
            sharpe      = sharpe_ana.get('sharperatio') or 0.0

            dd_ana      = strat.analyzers.drawdown.get_analysis()
            max_dd      = dd_ana.get('max', {}).get('drawdown', 0.0)

            tr_ana      = strat.analyzers.trades.get_analysis()
            total_tr    = tr_ana.get('total',  {}).get('closed', 0)
            won         = tr_ana.get('won',    {}).get('total',  0)
            lost        = tr_ana.get('lost',   {}).get('total',  0)
            win_rate    = won / total_tr if total_tr > 0 else 0.0

            avg_win     = tr_ana.get('won',  {}).get('pnl', {}).get('average', 0.0) or 0.0
            avg_loss    = tr_ana.get('lost', {}).get('pnl', {}).get('average', 0.0) or 0.0

            sum_wins    = tr_ana.get('won',  {}).get('pnl', {}).get('total', 0.0) or 0.0
            sum_losses  = abs(tr_ana.get('lost', {}).get('pnl', {}).get('total', 0.0) or 0.0)
            profit_factor = sum_wins / sum_losses if sum_losses > 0 else float('inf')

            wynik['metryki'] = {
                'total_return_pct':  round(total_return, 2),
                'sharpe_ratio':      round(float(sharpe), 3),
                'max_drawdown_pct':  round(float(max_dd), 2),
                'win_rate':          round(win_rate, 4),
                'num_trades':        total_tr,
                'profit_factor':     round(float(profit_factor), 2) if profit_factor != float('inf') else 999.0,
                'avg_win':           round(avg_win, 2),
                'avg_loss':          round(avg_loss, 2),
                'final_value':       round(final_value, 2),
                'kapital_poczatkowy': kapital_poczatkowy,
            }

        except Exception as exc:
            wynik['error'] = str(exc)

        return wynik

    @staticmethod
    def uruchom_optymalizacje(
        df_ticker: pd.DataFrame,
        nazwa_strategii: str,
        siatka_parametrow: Dict[str, List],
        kapital_poczatkowy: float = 100_000.0,
        df_spy: Optional[pd.DataFrame] = None,
        callback=None,      # callable(current: int, total: int, params: dict)
    ) -> pd.DataFrame:
        """
        Grid-search optymalizacja parametrów.

        Args:
            siatka_parametrow: {param: [v1, v2, ...]} np. {'sma_fast': [20,50], 'sma_slow': [100,200]}
            callback: Wywoływany po każdej kombinacji dla raportowania postępu.

        Returns:
            pd.DataFrame posortowany po sharpe_ratio malejąco.
        """
        klucze     = list(siatka_parametrow.keys())
        wartosci   = [siatka_parametrow[k] for k in klucze]
        kombinacje = list(itertools.product(*wartosci))
        total      = len(kombinacje)
        wyniki     = []

        for i, combo in enumerate(kombinacje):
            params = dict(zip(klucze, combo))
            if callback:
                callback(i, total, params)

            result = SilnikBacktestingu.uruchom(
                df_ticker=df_ticker,
                nazwa_strategii=nazwa_strategii,
                parametry=params,
                kapital_poczatkowy=kapital_poczatkowy,
                df_spy=df_spy,
            )

            if result['error'] is None and result['metryki']:
                row = dict(params)
                row.update(result['metryki'])
                wyniki.append(row)

        if not wyniki:
            return pd.DataFrame()

        df_out = pd.DataFrame(wyniki)
        df_out = df_out.sort_values('sharpe_ratio', ascending=False)
        df_out = df_out.reset_index(drop=True)
        return df_out
