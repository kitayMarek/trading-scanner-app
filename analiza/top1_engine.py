import pandas as pd
from .entry_engine import SilnikWejscia
from .penalty_engine import SilnikKar
from .wskazniki import SilnikWskaznikow
from konfiguracja import Konfiguracja

class SilnikDecyzyjny:
    @staticmethod
    def analizuj_rynek(market_df: pd.DataFrame) -> str:
        """
        Market Gate: ALLOW, CAUTION, BLOCK.
        """
        if market_df.empty: return "BLOCK"
        
        ostatni = market_df.iloc[-1]
        cena = ostatni['close']
        sma200 = ostatni.get('SMA200', 0)
        sma50 = ostatni.get('SMA50', 0)
        slope200 = ostatni.get('SMA200_Slope', 0)
        
        if cena < sma200:
            return "BLOCK"
            
        # Cena > SMA200
        if slope200 > 0:
            return "ALLOW"
            
        # Slope <= 0 lub Cena < SMA50 -> CAUTION
        return "CAUTION"

    @staticmethod
    def wybierz_top1(dane_tykerow: dict, market_df: pd.DataFrame) -> dict:
        """
        Główna pętla decyzyjna.
        """
        # 1. Market Gate
        market_status = SilnikDecyzyjny.analizuj_rynek(market_df)
        if market_status == "BLOCK":
            return {
                'status': 'NO TRADE',
                'reason': 'Market is BLOCK (Bear Market)',
                'market_status': market_status
            }

        kandydaci = []
        
        for tyker, df in dane_tykerow.items():
            if df.empty or len(df) < 200: continue
            
            # Wskaźniki
            if 'SMA200_Slope' not in df.columns:
                 df = SilnikWskaznikow.oblicz_wskazniki(df, market_df)
            ostatni = df.iloc[-1]
            
            # 2. Trend Gate (Per Ticker)
            # - Close > SMA200 & Slope > 0
            if not (ostatni['close'] > ostatni['SMA200'] and ostatni.get('SMA200_Slope', 0) > 0):
                continue
                
            # - (SMA50 > SMA200) OR (Close > SMA50 & Slope50 > 0)
            cond_structure = (ostatni['SMA50'] > ostatni['SMA200']) or \
                             (ostatni['close'] > ostatni['SMA50'] and ostatni.get('SMA50_Slope', 0) > 0)
            if not cond_structure: continue
            
            # - RS ratio > RS_MA OR RS slope > 0
            rs_ok = (ostatni.get('RS_Ratio', 0) > ostatni.get('RS_SMA50', 0)) or (ostatni.get('RS_Slope', 0) > 0)
            if not rs_ok: continue
            
            # - 6M Drawdown < 35%
            max_6m = df['high'].rolling(126).max().iloc[-1]
            dd = (max_6m - ostatni['close']) / max_6m * 100
            if dd > 35: continue

            # 3. Entry & Penalty
            entry = SilnikWejscia.ocen_setup(df)
            if entry['typ'] == 'BRAK': continue
            
            penalty = SilnikKar.oblicz_kary(df)
            if penalty['penalty'] >= 100: continue # Hard Reject
            
            # 4. Trend Score (0-100)
            # RS Strength + Slope200 + Mom6M
            trend_score = 50 
            if ostatni.get('RS_Ratio', 0) > 1.0: trend_score += 20
            if ostatni.get('SMA200_Slope', 0) > 0.05: trend_score += 15
            if ostatni.get('Mom6M', 0) > 0.1: trend_score += 15
            trend_score = min(trend_score, 100)
            
            # 5. Final Score
            # Final = 0.35*Trend + 0.55*Entry - 0.25*Penalty
            final_score = (0.35 * trend_score) + (0.55 * entry['score']) - (0.25 * penalty['penalty'])
            
            # Setup suggestion
            stop_loss = 0
            atr = ostatni.get('ATR14', 0)
            if entry['typ'].startswith('A'): # Pullback
                # Stop poniżej SMA50 lub świecy
                stop_loss = min(ostatni['SMA50'], ostatni['low']) - atr
            else: # Breakout
                # Stop -2ATR
                stop_loss = ostatni['close'] - (2 * atr)
                
            # Target 5R
            risk = ostatni['close'] - stop_loss
            target = ostatni['close'] + (5 * risk)

            kandydaci.append({
                'tyker': tyker,
                'final_score': final_score,
                'setup_type': entry['typ'],
                'entry_score': entry['score'],
                'trend_score': trend_score,
                'penalty': penalty['penalty'],
                'penalty_reason': penalty['reason'],
                'close': ostatni['close'],
                'stop_loss': stop_loss,
                'target': target,
                'risk': risk
            })
            
        if not kandydaci:
            return {
                'status': 'NO TRADE',
                'reason': 'No valid setups found',
                'market_status': market_status
            }
            
        # Wybierz TOP 1
        kandydaci.sort(key=lambda x: x['final_score'], reverse=True)
        najlepszy = kandydaci[0]
        
        if najlepszy['final_score'] < 65:
            return {
                'status': 'NO TRADE',
                'reason': f"Best candidate {najlepszy['tyker']} score too low ({najlepszy['final_score']:.1f})",
                'candidate': najlepszy,
                'market_status': market_status
            }
            
        return {
            'status': 'TOP 1 FOUND',
            'top1': najlepszy,
            'market_status': market_status
        }
