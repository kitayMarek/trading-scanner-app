import pandas as pd

class SilnikKar:
    @staticmethod
    def oblicz_kary(df: pd.DataFrame) -> dict:
        """
        Oblicza punkty karne za ryzykowne zachowanie ceny.
        Overextended: > SMA50 + 2ATR -> penalty
        Extreme: > SMA200 + 4ATR -> HARD REJECT (penalty > 100)
        """
        if df.empty: return {'penalty': 0, 'reason': ''}
        
        ostatni = df.iloc[-1]
        cena = ostatni['close']
        sma50 = ostatni.get('SMA50', 0)
        sma200 = ostatni.get('SMA200', 0)
        atr = ostatni.get('ATR14', 0)
        
        punkty_karne = 0
        powody = []
        
        # Extreme Check (Hard Reject)
        limit_extreme = sma200 + (4 * atr)
        if cena > limit_extreme:
            return {'penalty': 1000, 'reason': 'EXTREME EXTENSION (>200SMA+4ATR)'}
            
        # Overextended Check
        limit_extended = sma50 + (2 * atr)
        if cena > limit_extended:
            punkty_karne += 40
            powody.append("Extended (>50SMA+2ATR)")
            
        # High ATR% (Zmienność)
        atr_pct = ostatni.get('ATR_Pct', 0)
        if atr_pct > 5.0: # Bardzo zmienne
            punkty_karne += 20
            powody.append(f"High Volatility ({atr_pct:.1f}%)")
            
        return {
            'penalty': punkty_karne,
            'reason': ", ".join(powody)
        }
