"""
Strategie Backtrader - odzwierciedlają logikę skanera rynku.

Brak importów Qt - ten moduł jest czystą logiką handlową.
"""

import backtrader as bt
import backtrader.indicators as btind


class StrategiaTrendMomentum(bt.Strategy):
    """
    Strategia Trend-Following Momentum — odwzorowanie logiki skanera.

    Warunki wejścia (odzwierciedlają SilnikStatusu "TRADEABLE"):
      1. Close > SMA200
      2. SMA200 slope > 0 (SMA200 rośnie — SMA200[0] > SMA200[-slope_window])
      3. Close > SMA50
      4. Momentum 3M > 0 (zwrot z 63 dni > 0%)
      5. RS_Ratio > RS_SMA50 (relative strength powyżej swojej MA)

    Warunki wyjścia:
      - Close spada poniżej SMA200 (przełamanie trendu)
      - LUB trailing ATR stop: 2x ATR poniżej lokalnego szczytu

    Pozycjonowanie: risk fractional — ryzykujemy risk_pct kapitału na transakcję,
    stop = entry - atr_multiplier * ATR.
    """

    params = (
        ('sma_fast',        50),     # SMA50
        ('sma_slow',        200),    # SMA200
        ('atr_period',      14),     # ATR period
        ('atr_multiplier',  2.0),    # Trailing stop = atr_multiplier * ATR
        ('momentum_period', 63),     # 3-miesięczne momentum (63 sesje)
        ('slope_window',    20),     # Okno do pomiaru nachylenia SMA200
        ('risk_pct',        0.02),   # Ryzyko 2% kapitału na transakcję
        ('use_rs_filter',   True),   # Wymagaj RS > RS_SMA50 do wejścia
        ('rs_sma_period',   50),     # Okres MA na RS ratio
        ('printlog',        False),
    )

    def __init__(self):
        # Referencja do ceny zamknięcia
        self.data_close = self.data.close

        # Wskaźniki SMA
        self.sma_fast = btind.SMA(self.data.close, period=self.p.sma_fast)
        self.sma_slow = btind.SMA(self.data.close, period=self.p.sma_slow)

        # ATR — do pozycjonowania i trailing stop
        self.atr = btind.ATR(self.data, period=self.p.atr_period)

        # Momentum: procentowa zmiana ceny w ciągu 63 sesji
        self.momentum = btind.ROC100(self.data.close, period=self.p.momentum_period)

        # RS Ratio — tylko gdy dostępny feed SPY (datas[1])
        self.rs_ratio = None
        self.rs_sma   = None
        if len(self.datas) > 1:
            spy = self.datas[1]
            self.rs_ratio = self.data.close / spy.close
            self.rs_sma   = btind.SMA(self.rs_ratio, period=self.p.rs_sma_period)

        # Tracking transakcji
        self.order               = None
        self.entry_price         = None
        self.stop_price          = None
        self.highest_since_entry = None
        self.trade_log           = []   # [{date, pnl, price}]

    def log(self, txt, dt=None):
        if self.p.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()}: {txt}')

    # ── Helpery warunków ───────────────────────────────────────────────────

    def _sma200_slope_positive(self):
        """True jeśli SMA200 dziś > SMA200 sprzed slope_window sesji."""
        if len(self.sma_slow) <= self.p.slope_window:
            return False
        return float(self.sma_slow[0]) > float(self.sma_slow[-self.p.slope_window])

    def _rs_filter_ok(self):
        """True jeśli RS_Ratio > RS_SMA50 (lub filtr wyłączony / brak danych SPY)."""
        if not self.p.use_rs_filter or self.rs_ratio is None:
            return True
        if len(self.rs_sma) < self.p.rs_sma_period:
            return True     # za mało danych — przepuść
        return float(self.rs_ratio[0]) > float(self.rs_sma[0])

    def _entry_conditions_met(self):
        """Wszystkie warunki wejścia spełnione?"""
        if len(self.sma_slow) < self.p.sma_slow:
            return False
        above_200  = float(self.data_close[0]) > float(self.sma_slow[0])
        above_50   = float(self.data_close[0]) > float(self.sma_fast[0])
        slope_ok   = self._sma200_slope_positive()
        mom_ok     = float(self.momentum[0]) > 0
        rs_ok      = self._rs_filter_ok()
        return above_200 and above_50 and slope_ok and mom_ok and rs_ok

    def _exit_conditions_met(self):
        """Wyjdź gdy cena < SMA200 LUB trailing stop uderzony."""
        below_200  = float(self.data_close[0]) < float(self.sma_slow[0])
        stop_hit   = (self.stop_price is not None and
                      float(self.data_close[0]) < self.stop_price)
        return below_200 or stop_hit

    # ── Główna logika ──────────────────────────────────────────────────────

    def next(self):
        if self.order:
            return      # czekaj na realizację zlecenia

        if not self.position:
            if self._entry_conditions_met():
                atr_val = float(self.atr[0])
                if atr_val <= 0:
                    return
                stop_dist   = self.p.atr_multiplier * atr_val
                risk_amount = self.broker.getvalue() * self.p.risk_pct
                size        = int(risk_amount / stop_dist)
                if size <= 0:
                    return

                self.entry_price         = float(self.data_close[0])
                self.stop_price          = self.entry_price - stop_dist
                self.highest_since_entry = self.entry_price
                self.order               = self.buy(size=size)
                self.log(f'BUY {size} @ {self.entry_price:.2f}  stop={self.stop_price:.2f}')
        else:
            # Aktualizuj trailing stop
            current_close = float(self.data_close[0])
            if current_close > self.highest_since_entry:
                self.highest_since_entry = current_close
                self.stop_price = (self.highest_since_entry -
                                   self.p.atr_multiplier * float(self.atr[0]))

            if self._exit_conditions_met():
                self.order = self.close()
                self.log(f'SELL @ {current_close:.2f}')

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED  @ {order.executed.price:.2f}')
            elif order.issell():
                self.log(f'SELL EXECUTED @ {order.executed.price:.2f}  PnL={order.executed.pnl:.2f}')
                self.trade_log.append({
                    'date':  self.datas[0].datetime.date(0).isoformat(),
                    'pnl':   round(order.executed.pnl, 2),
                    'price': round(order.executed.price, 2),
                })
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')
        self.order = None

    def notify_trade(self, trade):
        if trade.isclosed:
            self.log(f'TRADE  Gross={trade.pnl:.2f}  Net={trade.pnlcomm:.2f}')


# ──────────────────────────────────────────────────────────────────────────────

class StrategiaSmaCrossover(bt.Strategy):
    """
    Prosta strategia SMA Crossover — punkt odniesienia (baseline).

    Wejście: SMA50 > SMA200 (golden cross).
    Wyjście: SMA50 < SMA200 (death cross).
    """

    params = (
        ('sma_fast',  50),
        ('sma_slow',  200),
        ('risk_pct',  0.95),    # 95% kapitału (pełna pozycja)
        ('printlog',  False),
    )

    def __init__(self):
        self.sma_fast  = btind.SMA(self.data.close, period=self.p.sma_fast)
        self.sma_slow  = btind.SMA(self.data.close, period=self.p.sma_slow)
        self.cross     = btind.CrossOver(self.sma_fast, self.sma_slow)
        self.order     = None
        self.trade_log = []

    def log(self, txt, dt=None):
        if self.p.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()}: {txt}')

    def next(self):
        if self.order:
            return

        if not self.position:
            if float(self.cross[0]) > 0:
                size = int((self.broker.getvalue() * self.p.risk_pct) /
                           float(self.data.close[0]))
                if size > 0:
                    self.order = self.buy(size=size)
                    self.log(f'BUY {size} @ {float(self.data.close[0]):.2f}')
        else:
            if float(self.cross[0]) < 0:
                self.order = self.close()
                self.log(f'SELL @ {float(self.data.close[0]):.2f}')

    def notify_order(self, order):
        if order.status == order.Completed:
            if order.issell():
                self.trade_log.append({
                    'date':  self.datas[0].datetime.date(0).isoformat(),
                    'pnl':   round(order.executed.pnl, 2),
                    'price': round(order.executed.price, 2),
                })
        self.order = None
