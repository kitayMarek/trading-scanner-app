from PySide6.QtWidgets import QMainWindow, QTabWidget, QVBoxLayout, QWidget
from konfiguracja import Konfiguracja
from .panel import PanelStartowy
from .skaner import SkanerWidok
from .widok_tykera import WidokTykera
from .kalkulator_ryzyka import KalkulatorRyzykaWidok
from .dziennik_widok import DziennikWidok

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
        
        # Połączenia sygnałów
        self.skaner.tyker_wybrany.connect(self.otworz_tykera)

    def otworz_tykera(self, tyker):
        self.zakladki.setCurrentWidget(self.widok_tykera)
        self.widok_tykera.zaladuj_tykera(tyker)
