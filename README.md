# Trading Scanner App - Antigravity Strategy v2.0



🚀 Professional trend-foll<img width="1575" height="931" alt="Skaner tradera" src="https://github.com/user-attachments/assets/92d4f8ea-e96f-4f8f-866d-108e1c5925ca" />
owing trading strategy analyzer with technical indicators, market regime detection, and risk management tools.

![Version](https://img.shields.io/badge/version-2.0.1-blue)
![Tests](https://img.shields.io/badge/tests-76%20passing-success)
![Python](https://img.shields.io/badge/python-3.10+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## ✨ Features

### Core Functionality
- 📊 **Stock Screener** - ChecklistScore (0-10) binary ranking system
- 📈 **Technical Analysis** - SMA50, SMA200, RS metrics, momentum indicators
- 🎯 **Market Regime Detection** - 5-level classification (STRONG_BULL to STRONG_BEAR)
- 💼 **Risk Management** - Position sizing, dynamic stops, portfolio heat tracking
- 📝 **Trading Journal** - Complete transaction lifecycle with P/L tracking
- 🔍 **Multi-timeframe Analysis** - Daily/Weekly/Monthly alignment
- 📉 **Real-time Charts** - Matplotlib integration with interactive displays

### Advanced Features
- Status Gating Layer (TRADEABLE/SETUP/OUT classification)
- Relative Strength vs SPY benchmark
- ATR-based volatility analysis
- Distance from moving averages
- Tier classification (A/B/C/D grades)

## 🚀 Quick Start

### Prerequisites
- Python 3.10 or higher
- Internet connection (for Yahoo Finance data downloads)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/trading-scanner-app.git
   cd trading-scanner-app
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python start.py
   ```

### First-Time Setup

1. **Download benchmark data (required):**
   - Click "Download Data (YFinance)"
   - Enter: `SPY`
   - Wait 20-30 seconds

2. **Download stock data (5+ recommended):**
   - Click "Download Data (YFinance)" again
   - Enter tickers: `AAPL`, `MSFT`, `GOOGL`, `NVDA`, `META`
   - Repeat for each stock

3. **Run the scanner:**
   - Click "Refresh Analysis"
   - Wait 10-15 seconds
   - View results in Dashboard and Scanner tabs

## 📂 Project Structure

```
app_v2/
├── start.py                  # Application entry point
├── konfiguracja.py           # Global configuration (SMA periods, thresholds)
├── dane/                     # Data layer
│   ├── baza.py               # SQLite database manager
│   ├── modele.py             # Data models (Swieca dataclass)
│   ├── importer.py           # Yahoo Finance importer
│   └── repozytorium.py       # Repository pattern (CRUD operations)
├── analiza/                  # Analysis engine
│   ├── wskazniki.py          # Technical indicators (SMA, RS, ATR, Momentum)
│   ├── ranking.py            # ChecklistScore system (0-10 binary scoring)
│   ├── status.py             # Status gating (TRADEABLE/SETUP/OUT)
│   ├── rezim.py              # Market regime detection
│   ├── slope.py              # Slope calculations
│   └── volatility.py         # ATR volatility metrics
├── interfejs/                # PySide6 GUI
│   ├── glowne_okno.py        # Main application window
│   ├── panel.py              # Dashboard (Top 5 setups, regime badge)
│   ├── skaner.py             # Stock screener table with filters
│   ├── widok_tykera.py       # Individual ticker analysis view
│   ├── dziennik_widok.py     # Trading journal UI
│   └── kalkulator_ryzyka.py  # Risk calculator widget
├── ryzyko/                   # Risk management
│   ├── zarzadzanie.py        # Portfolio heat, position sizing
│   ├── dynamic_stop.py       # ATR-based stop losses
│   └── position_sizing.py    # Kelly criterion, fixed fractional
├── dziennik/                 # Trading journal
│   ├── serwis.py             # Journal service (add/edit/delete trades)
│   └── performance_metrics.py # Win rate, R-multiple calculations
└── testy/                    # Test suite (76 tests, 100% pass rate)
    ├── test_v2.py
    ├── test_ranking.py
    ├── test_status_gating.py
    └── ... (7 test files total)
```

## 📊 How It Works

### ChecklistScore System (0-10 Points)

Each stock is scored on **10 binary conditions** (pass = 1 point, fail = 0 points):

1. ✅ Close > SMA200
2. ✅ SMA200 Slope > 0.001%
3. ✅ Close > SMA50
4. ✅ SMA50 Slope > 0.001%
5. ✅ RS Slope > 0%
6. ✅ RS Ratio > RS_SMA50
7. ✅ Momentum 6M > 0%
8. ✅ Momentum 3M > 0%
9. ✅ Distance from SMA200 within ±20%
10. ✅ ATR < 4% (volatility threshold)

**Tier Classification:**
- **A**: 8-10 points (excellent setups)
- **B**: 6-7 points (good setups)
- **C**: 4-5 points (fair setups)
- **D**: 0-3 points (poor setups)

### Status Gating Logic

**TRADEABLE** (all 4 required):
- Close > SMA200
- SMA200 Slope > 0.001%
- Close > SMA50
- RS Slope > 0 OR RS Ratio > RS_SMA50

**SETUP** (partial strength):
- Close > SMA200
- SMA200 Slope ≥ 0
- Missing one strength criterion

**OUT**: Everything else (default)

## 🧪 Testing

Run the full test suite:

```bash
python -m pytest testy -v
```

**Expected output**: `76 passed` (100% success rate)

## 📖 Documentation

- [Quick Start Guide](QUICK_START.md) - Detailed setup instructions
- [Sprint 5.1 Summary](SPRINT_5_1_SUMMARY.md) - Latest version changes
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues and solutions
- [Bug Fix Log](BUG_FIX_LOG.md) - Debugging history

## 🛠️ Tech Stack

- **Language**: Python 3.14.0
- **GUI Framework**: PySide6 (Qt 6)
- **Data Processing**: pandas, numpy
- **Charting**: matplotlib
- **Data Source**: yfinance (Yahoo Finance API)
- **Database**: SQLite
- **Testing**: pytest

## 📈 Usage Examples

### Adding Stocks to Scanner

```python
# Via GUI: Dashboard → "Download Data (YFinance)" → Enter ticker
# Via code:
from dane.importer import ImporterDanych
from dane.repozytorium import RepozytoriumDanych

repo = RepozytoriumDanych()
swiece = ImporterDanych.pobierz_yfinance("AAPL")
if swiece:
    repo.zapisz_swiece(swiece)
```

### Analyzing a Stock

```python
from analiza.wskazniki import SilnikWskaznikow
from dane.repozytorium import RepozytoriumDanych

repo = RepozytoriumDanych()
df = repo.pobierz_swiece_df("AAPL")
bench_df = repo.pobierz_swiece_df("SPY")

df = SilnikWskaznikow.oblicz_wskazniki(df, bench_df)
print(df[['close', 'SMA50', 'SMA200', 'RS_Ratio', 'Status']].tail())
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This software is for educational and research purposes only. It is not financial advice. Trading stocks involves risk of loss. Always do your own research and consult a licensed financial advisor before making investment decisions.

## 📧 Contact

For questions or issues, please open an issue on GitHub.

---

**Version**: 2.0.1
**Last Updated**: February 2025
**Status**: Production Ready ✅

Built with ❤️ using Python, PySide6, and pandas
