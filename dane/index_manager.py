"""
Index Manager - Multi-index support for Market Screener
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional
import pandas as pd


@dataclass
class IndexDefinition:
    """Definition of a stock market index"""
    id: str
    name: str
    csv_filename: str
    stock_count: int
    estimated_time_min: int  # Estimated scan time in minutes
    description: str
    requires_download: bool = False   # True = CSV musi być pobrany z internetu


class IndexManager:
    """Manages loading and validation of multiple stock indices"""

    # Index definitions
    INDICES = {
        'russell_1000': IndexDefinition(
            id='russell_1000',
            name='Russell 1000',
            csv_filename='russell_1000_tickers.csv',
            stock_count=1341,
            estimated_time_min=4,
            description='Large-cap US stocks (top 1000 by market cap)'
        ),
        'sp_500': IndexDefinition(
            id='sp_500',
            name='S&P 500',
            csv_filename='sp_500_tickers.csv',
            stock_count=500,
            estimated_time_min=2,
            description='Top 500 US large-cap companies'
        ),
        'russell_2000': IndexDefinition(
            id='russell_2000',
            name='Russell 2000',
            csv_filename='russell_2000_tickers.csv',
            stock_count=2000,
            estimated_time_min=7,
            description='Small-cap US stocks (rank 1001-3000)'
        ),
        'nasdaq': IndexDefinition(
            id='nasdaq',
            name='NASDAQ (wszystkie)',
            csv_filename='nasdaq_tickers.csv',
            stock_count=3500,
            estimated_time_min=14,
            description='Wszystkie spółki notowane na giełdzie NASDAQ (~3500 spółek)',
            requires_download=True
        ),
        'nyse': IndexDefinition(
            id='nyse',
            name='NYSE / AMEX / ARCA',
            csv_filename='nyse_tickers.csv',
            stock_count=2800,
            estimated_time_min=11,
            description='Wszystkie spółki notowane na NYSE, AMEX i ARCA (~2800 spółek)',
            requires_download=True
        ),
        'all_exchanges': IndexDefinition(
            id='all_exchanges',
            name='Wszystkie Giełdy (NYSE + NASDAQ)',
            csv_filename='all_exchange_tickers.csv',
            stock_count=6000,
            estimated_time_min=24,
            description='Kompletna lista spółek z NYSE + NASDAQ (~6000 spółek)',
            requires_download=True
        ),
    }

    def __init__(self, data_dir: Path = None):
        if data_dir is None:
            data_dir = Path(__file__).parent
        self.data_dir = data_dir

    def get_index(self, index_id: str) -> Optional[IndexDefinition]:
        """Get index definition by ID"""
        return self.INDICES.get(index_id)

    def list_indices(self) -> List[IndexDefinition]:
        """Get list of all available indices"""
        return list(self.INDICES.values())

    def is_csv_available(self, index_id: str) -> bool:
        """Check if CSV file exists on disk (for requires_download indices)"""
        index_def = self.get_index(index_id)
        if not index_def:
            return False
        csv_path = self.data_dir / index_def.csv_filename
        return csv_path.exists()

    def load_tickers(self, index_id: str) -> List[str]:
        """
        Load ticker symbols from index CSV.

        For indices with requires_download=True:
          - If CSV exists: load from file
          - If CSV missing: raise FileNotFoundError with hint to use 'Pobierz listę'

        Args:
            index_id: Index identifier (e.g., 'russell_1000', 'nasdaq')

        Returns:
            List of ticker symbols

        Raises:
            ValueError: If index_id is unknown
            FileNotFoundError: If CSV file doesn't exist
        """
        index_def = self.get_index(index_id)
        if not index_def:
            raise ValueError(f"Unknown index: {index_id}")

        csv_path = self.data_dir / index_def.csv_filename
        if not csv_path.exists():
            if index_def.requires_download:
                raise FileNotFoundError(
                    f"Lista tykerów dla '{index_def.name}' nie została jeszcze pobrana.\n\n"
                    f"Kliknij przycisk '⬇ Pobierz listę tykerów' aby pobrać aktualną listę z internetu."
                )
            else:
                raise FileNotFoundError(
                    f"Index file not found: {csv_path}\n"
                    f"Please ensure {index_def.csv_filename} exists in {self.data_dir}"
                )

        try:
            df = pd.read_csv(csv_path, comment='#')
            tickers = df['Ticker'].dropna().str.strip().tolist()
            return tickers
        except Exception as e:
            raise IOError(f"Error loading {index_def.name}: {e}")

    def validate_index_files(self) -> Dict[str, Dict]:
        """
        Check which index CSV files exist and are valid

        Returns:
            Dictionary mapping index_id to validation status
        """
        validation = {}

        for index_id, index_def in self.INDICES.items():
            csv_path = self.data_dir / index_def.csv_filename

            if not csv_path.exists():
                validation[index_id] = {
                    'exists': False,
                    'valid': False,
                    'path': str(csv_path),
                    'requires_download': index_def.requires_download,
                }
            else:
                try:
                    df = pd.read_csv(csv_path, comment='#')
                    if 'Ticker' not in df.columns:
                        validation[index_id] = {
                            'exists': True,
                            'valid': False,
                            'error': "Missing 'Ticker' column",
                            'path': str(csv_path),
                            'requires_download': index_def.requires_download,
                        }
                    else:
                        ticker_count = len(df)
                        # Check file modification time for freshness info
                        import os
                        import datetime
                        mtime = os.path.getmtime(csv_path)
                        modified = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')
                        validation[index_id] = {
                            'exists': True,
                            'valid': True,
                            'ticker_count': ticker_count,
                            'path': str(csv_path),
                            'requires_download': index_def.requires_download,
                            'last_updated': modified,
                        }
                except Exception as e:
                    validation[index_id] = {
                        'exists': True,
                        'valid': False,
                        'error': str(e),
                        'path': str(csv_path),
                        'requires_download': index_def.requires_download,
                    }

        return validation
