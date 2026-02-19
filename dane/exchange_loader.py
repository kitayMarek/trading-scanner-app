"""
Exchange Loader - Pobieranie kompletnych list tykerów NYSE i Nasdaq
Źródła:
  - Nasdaq FTP: ftp.nasdaqtrader.com/symboldirectory (nasdaqlisted.txt, otherlisted.txt)
  - Wikipedia (S&P500, fallback)
  - yfinance (screener fallback)

Strategie:
  1. Nasdaq FTP  → najdokładniejsze źródło (oficjalne)
  2. Fallback: requests + pandas_datareader
"""

import ftplib
import io
import time
import pandas as pd
from typing import List, Callable, Optional
from pathlib import Path


DATA_DIR = Path(__file__).parent

# ─────────────────────────────────────────────
#   Stałe
# ─────────────────────────────────────────────
NASDAQ_FTP_HOST   = "ftp.nasdaqtrader.com"
NASDAQ_FTP_DIR    = "/symboldirectory"
NASDAQLISTED_FILE = "nasdaqlisted.txt"
OTHERLISTED_FILE  = "otherlisted.txt"   # NYSE, AMEX, ARCA …

# Znaki specjalne w symbolach do pominięcia
EXCLUDE_SUFFIXES = [
    '$', '+', '-', '.', '/', '^',   # warranty, testy, ETNy
    'W', 'R', 'U', 'Q',             # warranty, prawa, jednostki, bankructwa
]
EXCLUDE_KEYWORDS = ['TEST', 'ATEST']


# ─────────────────────────────────────────────
#   Helpers
# ─────────────────────────────────────────────

def _ftp_download(host: str, path: str, filename: str,
                  progress_cb: Optional[Callable[[str], None]] = None) -> str:
    """Pobierz plik z FTP i zwróć jako string."""
    if progress_cb:
        progress_cb(f"Łączenie z {host}{path}/{filename} ...")

    buf = io.BytesIO()
    with ftplib.FTP(host, timeout=30) as ftp:
        ftp.login()                        # anonymous
        ftp.cwd(path)
        ftp.retrbinary(f"RETR {filename}", buf.write)

    text = buf.getvalue().decode("utf-8", errors="replace")
    return text


def _parse_nasdaqlisted(text: str) -> pd.DataFrame:
    """
    Parsuj nasdaqlisted.txt → kolumny: Ticker, Name, Sector
    Format: Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares
    Ostatnia linia: File Creation Time: ...
    """
    lines = [l for l in text.splitlines() if l and not l.startswith("File Creation")]
    if not lines:
        return pd.DataFrame(columns=["Ticker", "Name", "Sector"])

    rows = []
    for line in lines[1:]:            # skip header
        parts = line.split("|")
        if len(parts) < 7:
            continue
        symbol      = parts[0].strip()
        name        = parts[1].strip()
        etf         = parts[6].strip()
        test_issue  = parts[3].strip()

        # Filtruj ETFy, testy, symbole specjalne
        if test_issue == "Y":
            continue
        if etf == "Y":
            continue
        if any(symbol.endswith(sfx) for sfx in EXCLUDE_SUFFIXES):
            continue
        if any(kw in symbol.upper() for kw in EXCLUDE_KEYWORDS):
            continue
        if not symbol or not symbol.replace(".", "").isalpha():
            continue

        rows.append({"Ticker": symbol, "Name": name, "Sector": ""})

    return pd.DataFrame(rows)


def _parse_otherlisted(text: str) -> pd.DataFrame:
    """
    Parsuj otherlisted.txt → kolumny: Ticker, Name, Sector, Exchange
    Format: ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot Size|Test Issue|NASDAQ Symbol
    Ostatnia linia: File Creation Time: ...
    """
    lines = [l for l in text.splitlines() if l and not l.startswith("File Creation")]
    if not lines:
        return pd.DataFrame(columns=["Ticker", "Name", "Sector", "Exchange"])

    rows = []
    for line in lines[1:]:            # skip header
        parts = line.split("|")
        if len(parts) < 7:
            continue
        symbol     = parts[0].strip()
        name       = parts[1].strip()
        exchange   = parts[2].strip()   # N=NYSE, A=AMEX, P=ARCA, Z=BATS …
        etf        = parts[4].strip()
        test_issue = parts[6].strip()

        if test_issue == "Y":
            continue
        if etf == "Y":
            continue
        if any(symbol.endswith(sfx) for sfx in EXCLUDE_SUFFIXES):
            continue
        if any(kw in symbol.upper() for kw in EXCLUDE_KEYWORDS):
            continue
        if not symbol or not symbol.replace(".", "").isalpha():
            continue

        rows.append({
            "Ticker": symbol,
            "Name": name,
            "Sector": "",
            "Exchange": exchange
        })

    return pd.DataFrame(rows)


# ─────────────────────────────────────────────
#   Główne API
# ─────────────────────────────────────────────

class ExchangeLoader:
    """
    Pobiera i buforuje kompleksowe listy tykerów NYSE i Nasdaq.
    Korzysta z oficjalnego FTP Nasdaq TraderInfo.
    """

    NASDAQ_CSV = DATA_DIR / "nasdaq_tickers.csv"
    NYSE_CSV   = DATA_DIR / "nyse_tickers.csv"
    ALL_CSV    = DATA_DIR / "all_exchange_tickers.csv"

    # ── Metody pobierające surowe dane ──────────

    @staticmethod
    def fetch_nasdaq_tickers(
        progress_cb: Optional[Callable[[str], None]] = None
    ) -> pd.DataFrame:
        """
        Pobiera spółki z giełdy Nasdaq (nasdaqlisted.txt).
        Zwraca DataFrame: Ticker, Name, Sector
        """
        text = _ftp_download(
            NASDAQ_FTP_HOST, NASDAQ_FTP_DIR, NASDAQLISTED_FILE, progress_cb
        )
        df = _parse_nasdaqlisted(text)
        df = df.drop_duplicates("Ticker").reset_index(drop=True)
        return df

    @staticmethod
    def fetch_nyse_tickers(
        progress_cb: Optional[Callable[[str], None]] = None
    ) -> pd.DataFrame:
        """
        Pobiera spółki z giełd NYSE, AMEX, ARCA (otherlisted.txt).
        Filtruje tylko Exchange == 'N' (NYSE) lub 'A' (AMEX) lub 'P' (ARCA).
        Zwraca DataFrame: Ticker, Name, Sector
        """
        text = _ftp_download(
            NASDAQ_FTP_HOST, NASDAQ_FTP_DIR, OTHERLISTED_FILE, progress_cb
        )
        df = _parse_otherlisted(text)

        # Zachowaj tylko NYSE / AMEX / ARCA (usuń BATS itp.)
        nyse_exchanges = {"N", "A", "P", "Q"}
        df = df[df["Exchange"].isin(nyse_exchanges)].copy()
        df = df.drop(columns=["Exchange"], errors="ignore")
        df = df.drop_duplicates("Ticker").reset_index(drop=True)
        return df

    @staticmethod
    def fetch_all_tickers(
        progress_cb: Optional[Callable[[str], None]] = None
    ) -> pd.DataFrame:
        """
        Pobiera wszystkie spółki z Nasdaq + NYSE (połączone, bez duplikatów).
        Zwraca DataFrame: Ticker, Name, Sector, Exchange
        """
        if progress_cb:
            progress_cb("Pobieranie listy Nasdaq ...")
        nasdaq_text = _ftp_download(
            NASDAQ_FTP_HOST, NASDAQ_FTP_DIR, NASDAQLISTED_FILE, None
        )
        nasdaq_df = _parse_nasdaqlisted(nasdaq_text)
        nasdaq_df["Exchange"] = "NASDAQ"

        if progress_cb:
            progress_cb("Pobieranie listy NYSE / AMEX / ARCA ...")
        other_text = _ftp_download(
            NASDAQ_FTP_HOST, NASDAQ_FTP_DIR, OTHERLISTED_FILE, None
        )
        other_df = _parse_otherlisted(other_text)
        nyse_exchanges = {"N", "A", "P", "Q"}
        other_df = other_df[other_df["Exchange"].isin(nyse_exchanges)].copy()
        other_df["Exchange"] = other_df["Exchange"].map(
            {"N": "NYSE", "A": "AMEX", "P": "ARCA", "Q": "NASDAQ"}
        ).fillna("OTHER")

        combined = pd.concat([nasdaq_df, other_df], ignore_index=True)
        combined = combined.drop_duplicates("Ticker").reset_index(drop=True)
        return combined

    # ── Zapis / odczyt CSV ───────────────────

    @staticmethod
    def save_nasdaq_csv(df: pd.DataFrame) -> Path:
        """Zapisz listę Nasdaq do CSV i zwróć ścieżkę."""
        out = df[["Ticker", "Name", "Sector"]].copy()
        out.to_csv(ExchangeLoader.NASDAQ_CSV, index=False)
        return ExchangeLoader.NASDAQ_CSV

    @staticmethod
    def save_nyse_csv(df: pd.DataFrame) -> Path:
        """Zapisz listę NYSE do CSV i zwróć ścieżkę."""
        out = df[["Ticker", "Name", "Sector"]].copy()
        out.to_csv(ExchangeLoader.NYSE_CSV, index=False)
        return ExchangeLoader.NYSE_CSV

    @staticmethod
    def save_all_csv(df: pd.DataFrame) -> Path:
        """Zapisz połączoną listę do CSV i zwróć ścieżkę."""
        df.to_csv(ExchangeLoader.ALL_CSV, index=False)
        return ExchangeLoader.ALL_CSV

    # ── Zintegrowane pobieranie + zapis ─────

    @staticmethod
    def update_nasdaq(
        progress_cb: Optional[Callable[[str], None]] = None
    ) -> int:
        """
        Pobierz i zapisz listę Nasdaq. Zwróć liczbę tykerów.
        Wywoływane z wątku pobierania w IndexSelector.
        """
        df = ExchangeLoader.fetch_nasdaq_tickers(progress_cb)
        ExchangeLoader.save_nasdaq_csv(df)
        return len(df)

    @staticmethod
    def update_nyse(
        progress_cb: Optional[Callable[[str], None]] = None
    ) -> int:
        """
        Pobierz i zapisz listę NYSE. Zwróć liczbę tykerów.
        """
        df = ExchangeLoader.fetch_nyse_tickers(progress_cb)
        ExchangeLoader.save_nyse_csv(df)
        return len(df)

    @staticmethod
    def update_all(
        progress_cb: Optional[Callable[[str], None]] = None
    ) -> dict:
        """
        Pobierz i zapisz Nasdaq + NYSE (osobno + razem).
        Zwraca słownik: {'nasdaq': n, 'nyse': n, 'all': n}
        """
        if progress_cb:
            progress_cb("Pobieranie Nasdaq ...")
        nasdaq_df = ExchangeLoader.fetch_nasdaq_tickers(None)
        ExchangeLoader.save_nasdaq_csv(nasdaq_df)

        if progress_cb:
            progress_cb("Pobieranie NYSE / AMEX / ARCA ...")
        nyse_df = ExchangeLoader.fetch_nyse_tickers(None)
        ExchangeLoader.save_nyse_csv(nyse_df)

        # Połącz
        nasdaq_df["Exchange"] = "NASDAQ"
        nyse_df_ex = nyse_df.copy()
        nyse_df_ex["Exchange"] = "NYSE"
        combined = pd.concat([nasdaq_df, nyse_df_ex], ignore_index=True)
        combined = combined.drop_duplicates("Ticker").reset_index(drop=True)
        ExchangeLoader.save_all_csv(combined)

        return {
            "nasdaq": len(nasdaq_df),
            "nyse": len(nyse_df),
            "all": len(combined),
        }

    # ── Odczyt z pliku (bez pobierania) ─────

    @staticmethod
    def load_nasdaq_from_csv() -> List[str]:
        """Wczytaj tykery Nasdaq z lokalnego CSV (bez pobierania)."""
        if not ExchangeLoader.NASDAQ_CSV.exists():
            return []
        df = pd.read_csv(ExchangeLoader.NASDAQ_CSV, comment="#")
        return df["Ticker"].dropna().str.strip().tolist()

    @staticmethod
    def load_nyse_from_csv() -> List[str]:
        """Wczytaj tykery NYSE z lokalnego CSV (bez pobierania)."""
        if not ExchangeLoader.NYSE_CSV.exists():
            return []
        df = pd.read_csv(ExchangeLoader.NYSE_CSV, comment="#")
        return df["Ticker"].dropna().str.strip().tolist()

    @staticmethod
    def load_all_from_csv() -> List[str]:
        """Wczytaj wszystkie tykery z lokalnego CSV (bez pobierania)."""
        if not ExchangeLoader.ALL_CSV.exists():
            return []
        df = pd.read_csv(ExchangeLoader.ALL_CSV, comment="#")
        return df["Ticker"].dropna().str.strip().tolist()
