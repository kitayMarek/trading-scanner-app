"""
Wątki QThread do uruchamiania backtestу i optymalizacji w tle.

Wzorzec identyczny jak Russell1000DownloadThread w market_screener.py:
  1. Utwórz instancję
  2. Ustaw atrybuty danych
  3. Podłącz sygnały
  4. Wywołaj .start()
"""

from PySide6.QtCore import QThread, Signal


class WatekBacktestingu(QThread):
    """
    Wątek do uruchamiania pojedynczego backtestу.

    Sygnały:
        postep(int, int, str)  — (bieżący, total, wiadomość)
        wynik_gotowy(dict)     — słownik wyników z SilnikBacktestingu.uruchom()
        blad(str)              — komunikat błędu
    """

    postep       = Signal(int, int, str)
    wynik_gotowy = Signal(dict)
    blad         = Signal(str)

    def __init__(self):
        super().__init__()
        # Atrybuty ustawiane przed .start()
        self.df_ticker       = None
        self.df_spy          = None
        self.nazwa_strategii = None
        self.parametry       = {}
        self.kapital         = 100_000.0
        self.prowizja        = 0.001

    def run(self):
        # Import tutaj, żeby nie spowalniać startu aplikacji
        from .silnik_backtestingu import SilnikBacktestingu

        try:
            self.postep.emit(0, 1, 'Uruchamianie backtestу…')

            wynik = SilnikBacktestingu.uruchom(
                df_ticker=self.df_ticker,
                nazwa_strategii=self.nazwa_strategii,
                parametry=self.parametry,
                kapital_poczatkowy=self.kapital,
                df_spy=self.df_spy,
                prowizja=self.prowizja,
            )

            if wynik.get('error'):
                self.blad.emit(wynik['error'])
            else:
                self.postep.emit(1, 1, 'Gotowe.')
                self.wynik_gotowy.emit(wynik)

        except Exception as exc:
            self.blad.emit(str(exc))


class WatekOptymalizacji(QThread):
    """
    Wątek do grid-search optymalizacji parametrów.

    Sygnały:
        postep(int, int, str)     — postęp przez kombinacje
        wynik_gotowy(object)      — pd.DataFrame posortowany po Sharpe
        blad(str)
    """

    postep       = Signal(int, int, str)
    wynik_gotowy = Signal(object)
    blad         = Signal(str)

    def __init__(self):
        super().__init__()
        self.df_ticker         = None
        self.df_spy            = None
        self.nazwa_strategii   = None
        self.siatka_parametrow = {}
        self.kapital           = 100_000.0

    def _callback(self, current: int, total: int, params: dict):
        msg = f'Kombinacja {current + 1}/{total}: {params}'
        self.postep.emit(current, total, msg)

    def run(self):
        from .silnik_backtestingu import SilnikBacktestingu

        try:
            wynik_df = SilnikBacktestingu.uruchom_optymalizacje(
                df_ticker=self.df_ticker,
                nazwa_strategii=self.nazwa_strategii,
                siatka_parametrow=self.siatka_parametrow,
                kapital_poczatkowy=self.kapital,
                df_spy=self.df_spy,
                callback=self._callback,
            )
            self.wynik_gotowy.emit(wynik_df)

        except Exception as exc:
            self.blad.emit(str(exc))
