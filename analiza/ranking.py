import pandas as pd
import numpy as np
from .wskazniki import SilnikWskaznikow
from .status import SilnikStatusu
from .slope import SlopeMetrics
from .volatility import VolatilityMetrics
from konfiguracja import Konfiguracja


class RankingEngine:
    """
    Zaawansowany silnik rankingu z Composite Score (0-100).
    Integruje slope metrics, volatility, multi-timeframe alignment, i relative strength.
    """

    @staticmethod
    def calculate_checklist_score(ticker: str, df: pd.DataFrame, benchmark_df: pd.DataFrame = None) -> dict:
        """
        Oblicza ChecklistScore (0-10) dla tickera z 10 binarnych warunków.

        **NOWY SYSTEM v2.1**: Zamiast Composite Score (0-100) z wagami,
        używamy prostego checklist (10 punktów za 10 warunków).

        Checklist (każdy warunek = +1 punkt):
        1. Close > SMA200
        2. SMA200_slope > SLOPE_RISING_THRESHOLD
        3. Close > SMA50
        4. SMA50_slope > SLOPE_RISING_THRESHOLD
        5. RS_slope > 0
        6. RS_ratio > RS_SMA50
        7. Momentum_6M > 0
        8. Momentum_3M > 0
        9. Distance_SMA200 within ±20% (between -20 and +20)
        10. ATR_pct < ATR_MAX_PCT (default 4%)

        Tier Classification:
        - A: 8-10 points
        - B: 6-7 points
        - C: 4-5 points
        - D: 0-3 points

        Args:
            ticker: Symbol tykera (str)
            df: DataFrame z danymi tykera (musi mieć wszystkie wskaźniki)
            benchmark_df: DataFrame z danymi benchmarku (opcjonalnie)

        Returns:
            dict: {
                'checklist_score': int (0-10),
                'tier': str ('A', 'B', 'C', 'D'),
                'checklist_details': dict (punkt po punkcie)
            }
        """
        result = {
            'checklist_score': 0,
            'tier': 'D',
            'checklist_details': {}
        }

        if df.empty or len(df) < 50:
            return result

        try:
            last_row = df.iloc[-1]
            close = last_row.get('close', 0)
            sma200 = last_row.get('SMA200', close)
            sma50 = last_row.get('SMA50', close)
            sma200_slope = last_row.get('SMA200_Slope', 0)
            sma50_slope = last_row.get('SMA50_Slope', 0)
            rs_slope = last_row.get('RS_Slope', 0)
            rs_ratio = last_row.get('RS_Ratio', 1.0)
            rs_sma50 = last_row.get('RS_SMA50', 0)
            mom3m = last_row.get('Mom3M', 0)
            mom6m = last_row.get('Mom6M', 0)
            atr_pct = last_row.get('ATR_Pct', 0)
            dist_sma200 = last_row.get('Dist_SMA200', 0)  # Already in %

            score = 0
            details = {}

            # 1. Close > SMA200
            cond_1 = close > sma200
            if cond_1:
                score += 1
            details['1_close_above_sma200'] = cond_1

            # 2. SMA200_slope > SLOPE_RISING_THRESHOLD
            cond_2 = sma200_slope > Konfiguracja.SLOPE_RISING_THRESHOLD
            if cond_2:
                score += 1
            details['2_sma200_slope_rising'] = cond_2

            # 3. Close > SMA50
            cond_3 = close > sma50
            if cond_3:
                score += 1
            details['3_close_above_sma50'] = cond_3

            # 4. SMA50_slope > SLOPE_RISING_THRESHOLD
            cond_4 = sma50_slope > Konfiguracja.SLOPE_RISING_THRESHOLD
            if cond_4:
                score += 1
            details['4_sma50_slope_rising'] = cond_4

            # 5. RS_slope > 0
            cond_5 = rs_slope > 0
            if cond_5:
                score += 1
            details['5_rs_slope_positive'] = cond_5

            # 6. RS_ratio > RS_SMA50
            cond_6 = rs_ratio > rs_sma50 if rs_sma50 > 0 else rs_ratio > 1.0
            if cond_6:
                score += 1
            details['6_rs_ratio_strong'] = cond_6

            # 7. Momentum_6M > 0
            cond_7 = mom6m > 0
            if cond_7:
                score += 1
            details['7_momentum_6m_positive'] = cond_7

            # 8. Momentum_3M > 0
            cond_8 = mom3m > 0
            if cond_8:
                score += 1
            details['8_momentum_3m_positive'] = cond_8

            # 9. Distance_SMA200 within ±20%
            # Pobierz progi z konfiguracji
            dist_min = getattr(Konfiguracja, 'DISTANCE_MIN_PCT', -20.0)
            dist_max = getattr(Konfiguracja, 'DISTANCE_MAX_PCT', 20.0)
            cond_9 = (dist_min <= dist_sma200 <= dist_max)
            if cond_9:
                score += 1
            details['9_distance_within_range'] = cond_9

            # 10. ATR_pct < ATR_MAX_PCT
            atr_max = getattr(Konfiguracja, 'ATR_MAX_PCT', 4.0)
            cond_10 = atr_pct < atr_max
            if cond_10:
                score += 1
            details['10_atr_below_threshold'] = cond_10

            result['checklist_score'] = score
            result['checklist_details'] = details

            # === TIER CLASSIFICATION ===
            if score >= 8:
                result['tier'] = 'A'
            elif score >= 6:
                result['tier'] = 'B'
            elif score >= 4:
                result['tier'] = 'C'
            else:
                result['tier'] = 'D'

        except Exception as e:
            print(f"Error in calculate_checklist_score for {ticker}: {e}")

        return result

    @staticmethod
    def calculate_percentile_rank(values: pd.Series, current_value: float) -> float:
        """
        Oblicza percentyl rankowy wartości w stosunku do serii.

        Args:
            values: pd.Series z wartościami do porównania
            current_value: Aktualna wartość do oceny

        Returns:
            float: Percentyl (0-100)
        """
        if values.empty or len(values) == 0:
            return 50.0

        try:
            # Percentyl: ile % wartości jest <= current_value
            percentile = (values <= current_value).sum() / len(values) * 100
            return max(0.0, min(100.0, percentile))  # Clamp do 0-100
        except Exception:
            return 50.0

    @staticmethod
    def calculate_composite_score(ticker: str, df: pd.DataFrame, benchmark_df: pd.DataFrame,
                                  all_tickers_data: dict = None) -> dict:
        """
        Oblicza Composite Score (0-100) dla tickera z 5 komponentów.

        Komponenty z wagami:
        - RS Percentile (30%): Rank względnej siły vs inne akcje
        - Momentum 3M/6M (20%): Percentyl momentum'u
        - SMA200 Slope (20%): Nachylenie trendu
        - Multi-Timeframe Alignment (20%): D/W/M alignment score (0-3)
        - Distance Penalty (10%): Kara jeśli cena >30% od SMA200

        Args:
            ticker: Symbol tykera (str)
            df: DataFrame z danymi tykera (musi mieć wszystkie wskaźniki)
            benchmark_df: DataFrame z danymi benchmarku (SPY)
            all_tickers_data: Dict {symbol: df} dla całej watchlisty (do obliczeń percentyli)

        Returns:
            dict: {
                'composite_score': float (0-100),
                'rs_percentile': float,
                'momentum_score': float,
                'slope_score': float,
                'alignment_score': float (0-3),
                'distance_penalty': float,
                'tier': str ('A', 'B', 'C')
            }
        """
        result = {
            'composite_score': 0.0,
            'rs_percentile': 50.0,
            'momentum_score': 50.0,
            'slope_score': 50.0,
            'alignment_score': 0.0,
            'distance_penalty': 0.0,
            'tier': 'C'
        }

        if df.empty or len(df) < 50:
            return result

        try:
            # Weź ostatni wiersz danych tykera
            last_row = df.iloc[-1]
            close = last_row['close']
            sma200 = last_row.get('SMA200', close)
            sma50 = last_row.get('SMA50', close)

            # === 1. RS PERCENTILE (30%) ===
            rs_percentile = 50.0
            if 'RS_Ratio' in last_row and all_tickers_data:
                # Oblicz percentyl RS tego tykera vs inne tykery w watchliście
                rs_values = []
                for other_ticker, other_df in all_tickers_data.items():
                    if not other_df.empty:
                        rs_val = other_df.iloc[-1].get('RS_Ratio', 1.0)
                        if rs_val > 0:
                            rs_values.append(rs_val)

                if rs_values:
                    rs_series = pd.Series(rs_values)
                    rs_percentile = RankingEngine.calculate_percentile_rank(rs_series, last_row['RS_Ratio'])
                    result['rs_percentile'] = rs_percentile

            # === 2. MOMENTUM 3M/6M (20%) ===
            momentum_score = 50.0
            mom3m = last_row.get('Mom3M', 0)
            mom6m = last_row.get('Mom6M', 0)

            if all_tickers_data:
                # Oblicz percentyl momentum tego tykera
                mom_values = []
                for other_ticker, other_df in all_tickers_data.items():
                    if not other_df.empty:
                        m3 = other_df.iloc[-1].get('Mom3M', 0)
                        if m3 is not None:
                            mom_values.append(m3)

                if mom_values:
                    # Średnia momentum (3M + 6M)
                    avg_momentum = (mom3m + mom6m) / 2 if (mom3m + mom6m) != 0 else 0
                    mom_series = pd.Series(mom_values)
                    momentum_score = RankingEngine.calculate_percentile_rank(mom_series, avg_momentum)
                    result['momentum_score'] = momentum_score
            else:
                # Fallback: simple check
                avg_momentum = (mom3m + mom6m) / 2 if (mom3m + mom6m) != 0 else 0
                momentum_score = 75.0 if avg_momentum > 0 else 25.0
                result['momentum_score'] = momentum_score

            # === 3. SMA200 SLOPE (20%) ===
            slope_score = 50.0
            sma200_slope = last_row.get('SMA200_Slope', 0)

            if all_tickers_data:
                # Percentyl slope
                slope_values = []
                for other_ticker, other_df in all_tickers_data.items():
                    if not other_df.empty:
                        sl = other_df.iloc[-1].get('SMA200_Slope', 0)
                        if sl is not None:
                            slope_values.append(sl)

                if slope_values:
                    slope_series = pd.Series(slope_values)
                    slope_score = RankingEngine.calculate_percentile_rank(slope_series, sma200_slope)
                    result['slope_score'] = slope_score
            else:
                # Fallback: simple check
                slope_score = 75.0 if sma200_slope > Konfiguracja.SLOPE_RISING_THRESHOLD else 25.0
                result['slope_score'] = slope_score

            # === 4. MULTI-TIMEFRAME ALIGNMENT (20%) ===
            alignment_score = 0.0

            # Daily: Trend OK (Close > 200MA AND slope > 0)
            daily_ok = close > sma200 and sma200_slope > Konfiguracja.SLOPE_RISING_THRESHOLD
            if daily_ok:
                alignment_score += 1.0

            # Check RS Alignment
            rs_ratio = last_row.get('RS_Ratio', 1.0)
            rs_sma50 = last_row.get('RS_SMA50', 0) if 'RS_SMA50' in df.columns else 0
            rs_trend_ok = rs_ratio > rs_sma50 if rs_sma50 > 0 else rs_ratio > 1.0
            if rs_trend_ok:
                alignment_score += 1.0

            # Weekly check (simplified: resample i oblicz)
            if len(df) >= Konfiguracja.OKRES_NACHYLENIA:
                try:
                    df_weekly = df.resample('W').agg({'close': 'last', 'SMA200': 'last'}).dropna()
                    if len(df_weekly) >= 10:
                        weekly_close = df_weekly.iloc[-1]['close']
                        weekly_sma200 = df_weekly.iloc[-1]['SMA200']
                        if weekly_close > weekly_sma200:
                            alignment_score += 1.0
                except Exception:
                    pass

            # Max 3.0 alignment score
            alignment_score = min(3.0, alignment_score)
            # Konwertuj na percentyl (0-3 -> 0-100)
            alignment_percentile = (alignment_score / 3.0) * 100
            result['alignment_score'] = alignment_score

            # === 5. DISTANCE PENALTY (10%) ===
            # Penalty jeśli cena >30% od SMA200
            distance_pct = ((close - sma200) / sma200) * 100 if sma200 > 0 else 0
            distance_penalty = 0.0

            if distance_pct > Konfiguracja.DISTANCE_PENALTY_THRESHOLD:
                # Penalty: każdy 1% powyżej 30% to -1 punkt
                excess_pct = distance_pct - Konfiguracja.DISTANCE_PENALTY_THRESHOLD
                distance_penalty = min(100.0, excess_pct * 1.0)  # Cap na 100
            elif distance_pct < -Konfiguracja.DISTANCE_PENALTY_THRESHOLD:
                # Penalty jeśli pod 30%
                excess_pct = abs(distance_pct) - Konfiguracja.DISTANCE_PENALTY_THRESHOLD
                distance_penalty = min(100.0, excess_pct * 0.5)  # Mniejsza penaltzy dla cen pod SMA200

            result['distance_penalty'] = distance_penalty
            distance_score = max(0.0, 100.0 - distance_penalty)

            # === COMPOSITE SCORE ===
            weights = Konfiguracja.WAGI_RANKINGU
            composite = (
                rs_percentile * weights['rs_percentile'] +
                momentum_score * weights['momentum'] +
                slope_score * weights['sma200_slope'] +
                alignment_percentile * weights['mtf_alignment'] +
                distance_score * weights['distance_penalty']
            )

            composite = round(composite, 2)
            result['composite_score'] = composite

            # === TIER CLASSIFICATION ===
            if composite > Konfiguracja.TIER_A_THRESHOLD:
                result['tier'] = 'A'
            elif composite >= Konfiguracja.TIER_B_THRESHOLD:
                result['tier'] = 'B'
            else:
                result['tier'] = 'C'

        except Exception as e:
            print(f"Error in calculate_composite_score for {ticker}: {e}")

        return result

    @staticmethod
    def generuj_ranking(dane_tykerow: dict[str, pd.DataFrame], benchmark_df: pd.DataFrame) -> pd.DataFrame:
        """
        Generuje ranking wszystkich tykerów z Composite Score i nowymi kolumnami.
        Trzyma backward compatibility ze starym SilnikRankingu.

        Args:
            dane_tykerow: Dict {symbol: DataFrame}
            benchmark_df: DataFrame z danymi SPY

        Returns:
            pd.DataFrame: Ranking z kolumnami: Tyker, Status, CompositeScore, Tier, Cena, SMA200_Slope, RS_Slope, Distance_200%, ATR_pct, AlignmentScore
        """
        wyniki = []

        for tyker, df in dane_tykerow.items():
            if df.empty or len(df) < 50:
                continue

            # Oblicz wszystkie wskaźniki
            df = SilnikWskaznikow.oblicz_wskazniki(df, benchmark_df)
            ostatni = df.iloc[-1]

            # Status (gating layer) - FIRST
            status = SilnikStatusu.okresl_status(ostatni)

            # ChecklistScore (NOVI SISTEM v2.1) - DRUGI
            # Samo za TRADEABLE spółki będą rankowane
            score_dict = RankingEngine.calculate_checklist_score(tyker, df, benchmark_df)

            # Przygotuj wiersz wynika
            wynik = {
                'Tyker': tyker,
                'Status': status,
                'ChecklistScore': score_dict['checklist_score'],  # 0-10
                'Tier': score_dict['tier'],  # A/B/C/D
                'Zamkniecie': ostatni['close'],
                'SMA200': ostatni.get('SMA200', 0),
                'SMA200_Slope': ostatni.get('SMA200_Slope', 0),
                'SMA50_Slope': ostatni.get('SMA50_Slope', 0),
                'RS_Ratio': ostatni.get('RS_Ratio', 0),
                'RS_Slope': ostatni.get('RS_Slope', 0),
                'Distance_200': ostatni.get('Dist_SMA200', 0),
                'ATR_Pct': ostatni.get('ATR_Pct', 0),
                'Momentum_3M': ostatni.get('Mom3M', 0),
                'Momentum_6M': ostatni.get('Mom6M', 0),
            }

            wyniki.append(wynik)

        if not wyniki:
            return pd.DataFrame()

        df_wynik = pd.DataFrame(wyniki)

        # ===== SORTOWANIE (NOVE) =====
        # Logika:
        # 1. Status: TRADEABLE -> SETUP -> OUT
        # 2. Dla TRADEABLE: ChecklistScore DESC (highest first)
        # 3. Dla SETUP/OUT: Bez rankingu numerycznego (domyślnie alfabetycznie)
        status_map = {"TRADEABLE": 0, "SETUP": 1, "OUT": 2}
        tier_map = {"A": 0, "B": 1, "C": 2, "D": 3}

        df_wynik['Status_Order'] = df_wynik['Status'].map(status_map).fillna(3)
        df_wynik['Tier_Order'] = df_wynik['Tier'].map(tier_map).fillna(4)

        # Sortuj: Status -> ChecklistScore DESC -> Tier (A->B->C->D)
        df_wynik = df_wynik.sort_values(
            by=['Status_Order', 'ChecklistScore', 'Tier_Order'],
            ascending=[True, False, True]
        )

        # Usuń kolumny pomocnicze
        df_wynik = df_wynik.drop(columns=['Status_Order', 'Tier_Order'], errors='ignore')

        return df_wynik


# Backward compatibility - alias
SilnikRankingu = RankingEngine
