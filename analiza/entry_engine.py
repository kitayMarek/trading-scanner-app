import pandas as pd
import numpy as np

class SilnikWejscia:
    @staticmethod
    def ocen_setup(df: pd.DataFrame) -> dict:
        """
        Ocenia czy występuje Setup A (Pullback) lub Setup B (Breakout).
        Zwraca: {'typ': 'A'/'B'/'BRAK', 'score': 0-100, 'detale': str}
        """
        if df.empty or len(df) < 50:
            return {'typ': 'BRAK', 'score': 0, 'detale': 'Brak danych'}
        
        ostatni = df.iloc[-1]
        cena = ostatni['close']
        sma50 = ostatni.get('SMA50', 0)
        
        # Ostatnie 3 dni dla Pullbacku
        ostatnie_3 = df.tail(3)
        low_3 = ostatnie_3['low'].min()
        
        # Setup A: Pullback to 50MA
        # Warunki:
        # 1. Cena blisko SMA50 (<= 3%) LUB Low <= SMA50 w ost 3 dniach (i Close > SMA50 dzisiaj)
        # 2. Odbicie (Return 5d > 0) - prompt mówi 5d return > 0, ale to przy odbiciu...
        #    Może "Short term momentum is positive"?
        
        dystans_do_sma50_pct = abs(cena - sma50) / sma50 * 100
        dotkniecie_sma50 = (low_3 <= sma50 * 1.01) and (cena > sma50) # Margines 1%
        blisko_sma50 = (dystans_do_sma50_pct <= 3.0) and (cena > sma50)
        
        if dotkniecie_sma50 or blisko_sma50:
            # Sprawdź czy to nie jest spadający nóż (Return 5d > -5%?)
            # Prompt: "5d return > 0"
            ret5d = df['close'].pct_change(5).iloc[-1]
            
            if ret5d > -0.05: # Lekko łagodzimy, bo pullback to spadek
                # Entry Score: Im bliżej średniej tym lepiej?
                # Albo im mocniejsze odbicie od średniej (świeca objęcia)?
                # Score bazowy 80, +10 za dotknięcie
                score = 80
                if dotkniecie_sma50: score += 10
                if ret5d > 0: score += 10
                
                return {
                    'typ': 'A (Pullback)',
                    'score': min(score, 100),
                    'detale': f"Blisko SMA50 ({dystans_do_sma50_pct:.1f}%), 5d={ret5d:.1%}"
                }

        # Setup B: Breakout
        # Warunki:
        # 1. Close > 20-day High (Donchian)
        # 2. RS Slope > 0 (siła relatywna rośnie)
        
        max20 = df['high'].rolling(20).max().shift(1).iloc[-1] # Shift by nie patrzeć na dzisiejszy high wczoraj
        # Ale breakout to dzisiejsze close > wczorajszy MAX20
        
        if cena > max20:
            rs_slope = ostatni.get('RS_Slope', 0)
            if rs_slope > 0:
                # Score za siłę wybicia (Volumen?)
                vol_avg = df['volume'].rolling(20).mean().iloc[-1]
                vol_curr = ostatni['volume']
                
                bs_score = 80
                if vol_curr > vol_avg * 1.5: bs_score += 10 # Mocny wolumen
                if rs_slope > 0.1: bs_score += 10 # Silne RS
                
                return {
                    'typ': 'B (Breakout)',
                    'score': min(bs_score, 100),
                    'detale': f"Wybicie > {max20:.2f}, Vol={vol_curr/vol_avg:.1f}x"
                }
                
        return {'typ': 'BRAK', 'score': 0, 'detale': ''}
