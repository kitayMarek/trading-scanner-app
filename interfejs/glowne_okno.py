from PySide6.QtWidgets import QMainWindow, QTabWidget, QVBoxLayout, QWidget
from konfiguracja import Konfiguracja
from .panel import PanelStartowy
from .skaner import SkanerWidok
from .widok_tykera import WidokTykera
from .kalkulator_ryzyka import KalkulatorRyzykaWidok
from .dziennik_widok import DziennikWidok
from .market_screener import MarketScreenerWidget
from .backtest_widok import BacktestWidok

class GlowneOkno(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(Konfiguracja.TYTUL_APLIKACJI)
        self.resize(*Konfiguracja.ROZMIAR_OKNA)
        
        self.centralny_widget = QWidget()
        self.setCentralWidget(self.centralny_widget)
        
        self.uklad = QVBoxLayout(self.centralny_widget)
        
        self.zakladki = QTabWidget()
        self.uklad.addWidget(self.zakladki)
        
        self.utworz_zakladki()
        
    def utworz_zakladki(self):
        self.panel = PanelStartowy()
        self.zakladki.addTab(self.panel, "Pulpit")
        
        self.skaner = SkanerWidok()
        self.zakladki.addTab(self.skaner, "Skaner Rynku")
        
        self.widok_tykera = WidokTykera()
        self.zakladki.addTab(self.widok_tykera, "Analiza Tykera")
        
        self.kalkulator = KalkulatorRyzykaWidok()
        self.zakladki.addTab(self.kalkulator, "Kalkulator Ryzyka")
        
        self.dziennik = DziennikWidok()
        self.zakladki.addTab(self.dziennik, "Dziennik 2.0")

        # NEW: Market Screener tab
        self.market_screener = MarketScreenerWidget()
        self.zakladki.addTab(self.market_screener, "🔍 Market Screener")

        # NEW: Backtesting tab
        self.backtest = BacktestWidok()
        self.zakladki.addTab(self.backtest, "📊 Backtesting")

        # Połączenia sygnałów
        self.skaner.tyker_wybrany.connect(self.otworz_tykera)

        # NEW: Connect Market Screener results to Scanner tab
        self.market_screener.results_filtered.connect(
            self.skaner.receive_market_screener_results
        )

        # Podwójne kliknięcie w Skaner → wstępnie wypełnia pole tykera w Backtestingu
        self.skaner.tyker_wybrany.connect(self.backtest.ustaw_tyker)

        # Przycisk "Użyj ze Skanera" w BacktestWidok
        self.backtest.btn_ze_skanera.clicked.connect(self._skopiuj_tyker_ze_skanera)

    def otworz_tykera(self, tyker):
        self.zakladki.setCurrentWidget(self.widok_tykera)
        self.widok_tykera.zaladuj_tykera(tyker)

    def _skopiuj_tyker_ze_skanera(self):
        """
        Kopiuje aktualnie zaznaczony tyker ze Skanera do pola Backtestingu
        i przełącza na zakładkę Backtesting.
        """
        selected = self.skaner.tabela.selectedItems()
        if selected:
            row  = selected[0].row()
            item = self.skaner.tabela.item(row, 1)   # kolumna 1 = Tyker
            if item:
                self.backtest.ustaw_tyker(item.text())
        self.zakladki.setCurrentWidget(self.backtest)
