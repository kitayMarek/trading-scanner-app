from typing import List, Dict
from dane.repozytorium import RepozytoriumDanych
from dane.modele import Transakcja
import pandas as pd
import numpy as np

class SerwisDziennika:
    def __init__(self):
        self.repo = RepozytoriumDanych()

    def dodaj_transakcje(self, t: Transakcja):
        self.repo.zapisz_transakcje(t)

    def pobierz_transakcje(self) -> List[Transakcja]:
        return self.repo.pobierz_transakcje()

    def pobierz_otwarte_transakcje(self) -> List[Transakcja]:
        wszystkie = self.repo.pobierz_transakcje()
        return [t for t in wszystkie if not t.jest_zamknieta]

    def zamknij_transakcje(self, transaction_id: int, exit_date: str, exit_price: float):
        """Close an open position by setting exit date and price"""
        t = self.repo.pobierz_transakcje_po_id(transaction_id)
        if not t:
            raise ValueError(f"Transaction {transaction_id} not found")
        if t.jest_zamknieta:
            raise ValueError(f"Transaction {transaction_id} is already closed")

        t.data_wyjscia = exit_date
        t.cena_wyjscia = exit_price
        self.repo.zapisz_transakcje(t)

    def usun_transakcje(self, transaction_id: int):
        """Delete a transaction permanently"""
        self.repo.usun_transakcje(transaction_id)

    def generuj_statystyki(self) -> Dict:
        transakcje = self.pobierz_transakcje()
        zamkniete = [t for t in transakcje if t.jest_zamknieta]
        
        statystyki = {
            "liczba_transakcji": len(transakcje),
            "zamkniete": len(zamkniete),
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "expectancy_r": 0.0,
            "sredni_zysk": 0.0,
            "srednia_strata": 0.0,
            "najwiekszy_drawdown": 0.0,
            "equity_curve": []
        }
        
        if not zamkniete:
            return statystyki
            
        zyski = [t.zysk_strata for t in zamkniete]
        wygrane = [z for z in zyski if z > 0]
        przegrane = [z for z in zyski if z <= 0]
        
        statystyki["win_rate"] = len(wygrane) / len(zamkniete)
        statystyki["sredni_zysk"] = np.mean(wygrane) if wygrane else 0.0
        statystyki["srednia_strata"] = np.mean(przegrane) if przegrane else 0.0
        
        total_win = sum(wygrane)
        total_loss = abs(sum(przegrane))
        statystyki["profit_factor"] = total_win / total_loss if total_loss > 0 else float('inf')
        
        # Obliczanie Expectancy w R
        rs = [t.r_multiple for t in zamkniete]
        statystyki["expectancy_r"] = np.mean(rs) if rs else 0.0
        
        # Equity Curve (symulacja od 0) & Drawdown
        equity = 0
        curve = []
        high_water_mark = 0
        max_dd = 0
        
        # Sortowanie chronologicznie do krzywej
        for t in sorted(zamkniete, key=lambda x: x.data_wyjscia):
            equity += t.zysk_strata
            curve.append((t.data_wyjscia, equity))
            
            if equity > high_water_mark:
                high_water_mark = equity
            
            dd = high_water_mark - equity
            if dd > max_dd:
                max_dd = dd
                
        statystyki["najwiekszy_drawdown"] = max_dd
        statystyki["equity_curve"] = curve
        
        return statystyki
