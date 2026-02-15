import pandas as pd
import yfinance as yf
from typing import List
from .modele import Swieca
from datetime import datetime

class ImporterDanych:
    @staticmethod
    def importuj_z_pliku(sciezka_pliku: str, tyker: str) -> List[Swieca]:
        """Importuje dane z CSV."""
        df = pd.read_csv(sciezka_pliku)
        df.columns = [c.lower() for c in df.columns]

        # Mapowanie kolumn jeśli są inne
        mapa = {'date': 'data', 'open': 'otwarcie', 'high': 'najwyzszy', 'low': 'najnizszy', 'close': 'zamkniecie', 'volume': 'wolumen'}
        df = df.rename(columns=mapa)

        swiece = []
        for _, row in df.iterrows():
            # Pobierz datę z kolumny 'data' lub 'date'
            data_str = None
            if 'data' in row.index and pd.notna(row['data']):
                data_str = row['data']
            elif 'date' in row.index and pd.notna(row['date']):
                data_str = row['date']

            if data_str is None:
                continue  # Pomiń wiersze bez daty

            swiece.append(Swieca(
                tyker=tyker,
                data=pd.to_datetime(data_str).strftime('%Y-%m-%d'),
                otwarcie=float(row.get('otwarcie', row.get('open', 0))),
                najwyzszy=float(row.get('najwyzszy', row.get('high', 0))),
                najnizszy=float(row.get('najnizszy', row.get('low', 0))),
                zamkniecie=float(row.get('zamkniecie', row.get('close', 0))),
                wolumen=int(row.get('wolumen', row.get('volume', 0)))
            ))
        return swiece

    @staticmethod
    def pobierz_yfinance(tyker: str, okres="2y", interwal="1d") -> List[Swieca]:
        """Pobiera dane z Yahoo Finance."""
        try:
            df = yf.download(tyker, period=okres, interval=interwal, progress=False, auto_adjust=True)
            if df.empty:
                return []
            
            swiece = []
            for index, row in df.iterrows():
                # YFinance zwraca MultiIndex kolumn w nowych wersjach, trzeba uważać
                # .iloc lub .xs może być potrzebne, ale auto_adjust=True upraszcza
                open_val = row['Open'].iloc[0] if isinstance(row['Open'], pd.Series) else row['Open']
                high_val = row['High'].iloc[0] if isinstance(row['High'], pd.Series) else row['High']
                low_val = row['Low'].iloc[0] if isinstance(row['Low'], pd.Series) else row['Low']
                close_val = row['Close'].iloc[0] if isinstance(row['Close'], pd.Series) else row['Close']
                vol_val = row['Volume'].iloc[0] if isinstance(row['Volume'], pd.Series) else row['Volume']
                
                swiece.append(Swieca(
                    tyker=tyker,
                    data=index.strftime('%Y-%m-%d'),
                    otwarcie=float(open_val),
                    najwyzszy=float(high_val),
                    najnizszy=float(low_val),
                    zamkniecie=float(close_val),
                    wolumen=int(vol_val)
                ))
            return swiece
        except Exception as e:
            print(f"Błąd pobierania {tyker}: {e}")
            return []
