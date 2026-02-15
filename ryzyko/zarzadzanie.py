from dataclasses import dataclass
from konfiguracja import Konfiguracja
import pandas as pd

@dataclass
class WynikPozycji:
    liczba_akcji: int
    ryzykowana_kwota: float
    calkowity_koszt: float
    wspolczynnik_rr: float
    jest_poprawny_rr: bool
    sugerowany_stop: float
    typ_stopu: str

class ZarzadzanieRyzykiem:
    @staticmethod
    def oblicz_pozycje(
        wielkosc_portfela: float,
        cena_wejscia: float,
        stop_loss: float,
        cena_celowana: float,
        procent_ryzyka: float = Konfiguracja.DOMYSLNE_RYZYKO_PROCENT,
        min_rr: float = Konfiguracja.MIN_RR
    ) -> WynikPozycji:
        """
        Oblicza wielkość pozycji na podstawie ryzyka procentowego i odległości do stop lossa.
        """
        if cena_wejscia <= 0 or stop_loss <= 0 or cena_celowana <= 0:
            return WynikPozycji(0, 0, 0, 0, False, 0, "Błąd Danych")
            
        ryzyko_na_akcje = cena_wejscia - stop_loss
        if ryzyko_na_akcje <= 0:
            return WynikPozycji(0, 0, 0, 0, False, 0, "Błąd Stop Lossa (Long Only)")

        kwota_ryzyka = wielkosc_portfela * procent_ryzyka
        liczba_akcji = int(kwota_ryzyka // ryzyko_na_akcje)
        
        zysk_na_akcje = cena_celowana - cena_wejscia
        rr = zysk_na_akcje / ryzyko_na_akcje
        
        return WynikPozycji(
            liczba_akcji=liczba_akcji,
            ryzykowana_kwota=kwota_ryzyka,
            calkowity_koszt=liczba_akcji * cena_wejscia,
            wspolczynnik_rr=rr,
            jest_poprawny_rr=rr >= min_rr,
            sugerowany_stop=stop_loss,
            typ_stopu="Użytkownika"
        )
    
    @staticmethod
    def sugeruj_stop_loss(df: pd.DataFrame, metoda: str = "ATR_2X") -> float:
        """
        Sugeruje poziom stop loss na podstawie wybranej metody.
        Dostępne metody: ATR_2X, SMA50, SMA200, LOWEST_LOW
        """
        if df.empty: return 0.0
        
        ostatni = df.iloc[-1]
        cena = ostatni['close']
        
        if metoda == "ATR_2X":
            atr = ostatni.get('ATR14', 0)
            if atr == 0: return 0.0
            return cena - (2 * atr)
            
        elif metoda == "SMA50":
            sma = ostatni.get('SMA50', 0)
            return sma if sma < cena else 0.0
            
        elif metoda == "SMA200":
            sma = ostatni.get('SMA200', 0)
            return sma if sma < cena else 0.0
            
        elif metoda == "LOWEST_LOW":
            # Najniższy dołek z ostatnich 10 dni
            return df['low'].tail(10).min()
            
        return 0.0

    @staticmethod
    def oblicz_portfolio_heat(aktywne_transakcje: list, biezaca_wycena_portfela: float) -> float:
        """
        Oblicza sumaryczne ryzyko (Heat) otwartych pozycji jako % portfela.
        """
        if biezaca_wycena_portfela <= 0: return 0.0
        
        suma_ryzyka = 0.0
        for t in aktywne_transakcje:
            ryzyko_transakcji = (t.cena_wejscia - t.stop_loss) * t.wielkosc
            if ryzyko_transakcji > 0:
                suma_ryzyka += ryzyko_transakcji
                
        return (suma_ryzyka / biezaca_wycena_portfela) * 100
