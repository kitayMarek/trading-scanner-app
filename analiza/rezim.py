import pandas as pd
from enum import Enum
from .wskazniki import SilnikWskaznikow
from konfiguracja import Konfiguracja


class MarketRegime(Enum):
    """Klasyfikacja reżimu rynkowego"""
    STRONG_BULL = "STRONG_BULL"
    BULL = "BULL"
    NEUTRAL = "NEUTRAL"
    BEAR = "BEAR"
    STRONG_BEAR = "STRONG_BEAR"


class SilnikRezimu:
    """
    Silnik do detekcji reżimu rynkowego (bull/bear/neutral).
    Opiera się na:
    - Cena vs SMA200 (daily)
    - SMA200 slope (daily)
    - SPY weekly trend
    - Breadth proxy (% spółek >200MA w watchliście)
    """

    @staticmethod
    def _is_trend_up(close: float, sma200: float, slope: float) -> bool:
        """
        Sprawdza czy trend jest wzrostowy: Cena > SMA200 AND SMA200 slope > 0

        Args:
            close: Cena zamknięcia
            sma200: Wartość SMA200
            slope: Nachylenie SMA200 (%)

        Returns:
            bool: True jeśli trend UP
        """
        return close > sma200 and slope > Konfiguracja.SLOPE_RISING_THRESHOLD

    @staticmethod
    def _is_trend_down(close: float, sma200: float, slope: float) -> bool:
        """
        Sprawdza czy trend jest spadkowy: Cena < SMA200 OR SMA200 slope < 0

        Args:
            close: Cena zamknięcia
            sma200: Wartość SMA200
            slope: Nachylenie SMA200 (%)

        Returns:
            bool: True jeśli trend DOWN
        """
        return close < sma200 or slope < Konfiguracja.SLOPE_FALLING_THRESHOLD

    @staticmethod
    def calculate_breadth_proxy(ticker_list: list, all_tickers_data: dict) -> float:
        """
        Oblicza breadth proxy: % spółek w liście, które są >200MA.
        Używane jeśli brak dostępu do NYSE adv/dec data.

        Args:
            ticker_list: Lista symboli (np. z watchlisty)
            all_tickers_data: Dict {symbol: df} z danymi dla każdego tykera

        Returns:
            float: Procentaż spółek powyżej 200MA (0-100)
        """
        if not ticker_list or not all_tickers_data:
            return 50.0  # Domyślnie neutral

        above_sma200 = 0
        for ticker in ticker_list:
            if ticker in all_tickers_data:
                df = all_tickers_data[ticker]
                if not df.empty and 'close' in df.columns and 'SMA200' in df.columns:
                    last_close = df['close'].iloc[-1]
                    last_sma200 = df['SMA200'].iloc[-1]
                    if last_close > last_sma200:
                        above_sma200 += 1

        if not ticker_list:
            return 50.0

        breadth_pct = (above_sma200 / len(ticker_list)) * 100
        return breadth_pct

    @staticmethod
    def detect_regime(benchmark_df: pd.DataFrame, breadth_proxy: float = None) -> tuple[MarketRegime, str]:
        """
        Określa reżim rynkowy na podstawie daily i weekly trendu benchmarku (SPY).

        Logika:
        - STRONG_BULL: daily UP + weekly UP + breadth > 75%
        - BULL: daily UP + weekly UP
        - NEUTRAL: mieszane sygnały
        - BEAR: daily DOWN LUB weekly DOWN
        - STRONG_BEAR: daily DOWN + weekly DOWN + breadth < 25%

        Args:
            benchmark_df: DataFrame z danymi SPY (musi mieć SMA50, SMA200, SMA200_Slope)
            breadth_proxy: Procentaż spółek >200MA (opcjonalnie dla STRONG_BULL/BEAR)

        Returns:
            tuple: (MarketRegime, description_string)
        """
        if benchmark_df.empty or len(benchmark_df) < 200:
            return MarketRegime.NEUTRAL, "Brak wystarczających danych"

        # Upewnij się że mamy potrzebne wskaźniki
        if 'SMA200_Slope' not in benchmark_df.columns:
            benchmark_df = SilnikWskaznikow.oblicz_wskazniki(benchmark_df)

        # Daily data
        ostatni = benchmark_df.iloc[-1]
        daily_close = ostatni['close']
        daily_sma200 = ostatni['SMA200']
        daily_slope = ostatni.get('SMA200_Slope', 0)

        # Weekly data - resample
        try:
            df_weekly = benchmark_df.resample('W').agg({
                'close': 'last',
                'SMA200': 'last'
            }).dropna()

            if len(df_weekly) >= 20:
                weekly_last = df_weekly.iloc[-1]
                weekly_close = weekly_last['close']
                weekly_sma200 = weekly_last['SMA200']
                # Weekly slope (простой скатегор)
                if len(df_weekly) >= Konfiguracja.OKRES_NACHYLENIA:
                    from .slope import SlopeMetrics
                    weekly_slopes = SlopeMetrics.calculate_sma_slope(
                        df_weekly.reset_index()[['SMA200']],
                        'SMA200',
                        window=min(Konfiguracja.OKRES_NACHYLENIA, len(df_weekly) - 1)
                    )
                    weekly_slope = weekly_slopes.iloc[-1] if not weekly_slopes.empty else 0.0
                else:
                    weekly_slope = 0.0
            else:
                weekly_close = daily_close
                weekly_sma200 = daily_sma200
                weekly_slope = daily_slope
        except Exception as e:
            print(f"Error calculating weekly trend: {e}")
            weekly_close = daily_close
            weekly_sma200 = daily_sma200
            weekly_slope = daily_slope

        # Trend checks
        daily_trend_up = SilnikRezimu._is_trend_up(daily_close, daily_sma200, daily_slope)
        daily_trend_down = SilnikRezimu._is_trend_down(daily_close, daily_sma200, daily_slope)
        weekly_trend_up = SilnikRezimu._is_trend_up(weekly_close, weekly_sma200, weekly_slope)
        weekly_trend_down = SilnikRezimu._is_trend_down(weekly_close, weekly_sma200, weekly_slope)

        # Breadth default
        if breadth_proxy is None:
            breadth_proxy = 50.0

        # Regime determination
        if daily_trend_up and weekly_trend_up:
            if breadth_proxy > Konfiguracja.BREADTH_STRONG_BULL_THRESHOLD:
                regime = MarketRegime.STRONG_BULL
                desc = f"SILNA HOSSA - Daily & Weekly UP, Breadth {breadth_proxy:.0f}%"
            else:
                regime = MarketRegime.BULL
                desc = "HOSSA - Daily & Weekly trend wzrostowy"
        elif daily_trend_down or weekly_trend_down:
            if daily_trend_down and weekly_trend_down and breadth_proxy < Konfiguracja.BREADTH_STRONG_BEAR_THRESHOLD:
                regime = MarketRegime.STRONG_BEAR
                desc = f"SILNA BESSA - Daily & Weekly DOWN, Breadth {breadth_proxy:.0f}%"
            else:
                regime = MarketRegime.BEAR
                desc = "BESSA - Daily lub Weekly trend spadkowy"
        else:
            regime = MarketRegime.NEUTRAL
            desc = "NEUTRALNY - Rynek bez jasnego kierunku"

        return regime, desc

    @staticmethod
    def wykryj_rezim(benchmark_df: pd.DataFrame, breadth_proxy: float = None) -> tuple[str, str]:
        """
        Legacy wrapper - zwraca tuple (str, str) zamiast (MarketRegime, str).
        Dla backward compatibility.

        Args:
            benchmark_df: DataFrame z danymi SPY
            breadth_proxy: Procentaż spółek >200MA

        Returns:
            tuple: (regime_name_str, description_str)
        """
        regime, desc = SilnikRezimu.detect_regime(benchmark_df, breadth_proxy)
        return regime.value, desc
