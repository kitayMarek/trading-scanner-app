from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QDoubleSpinBox, QLabel, QPushButton, QComboBox
)
from ryzyko.zarzadzanie import ZarzadzanieRyzykiem
from konfiguracja import Konfiguracja
from dane.repozytorium import RepozytoriumDanych
import pandas as pd # Import pandas wewnątrz funkcji jeśli potrzebny, ale tu raczej typy

class KalkulatorRyzykaWidok(QWidget):
    def __init__(self):
        super().__init__()
        self.repo = RepozytoriumDanych()
        self.inicjalizuj_ui()
        
    def inicjalizuj_ui(self):
        uklad = QVBoxLayout()
        formularz = QFormLayout()
        
        self.input_kapital = QDoubleSpinBox()
        self.input_kapital.setRange(1000, 10000000)
        self.input_kapital.setValue(100000)
        
        self.input_cena = QDoubleSpinBox()
        self.input_cena.setRange(0.01, 10000)
        
        self.input_stop = QDoubleSpinBox()
        self.input_stop.setRange(0.01, 10000)
        
        self.input_cel = QDoubleSpinBox()
        self.input_cel.setRange(0.01, 10000)
        
        self.input_procent = QDoubleSpinBox()
        self.input_procent.setRange(0.1, 5.0)
        self.input_procent.setValue(1.0)
        self.input_procent.setSuffix("%")
        
        # Sugestie Stop Loss
        self.btn_sugeruj_stop = QPushButton("Sugeruj Stop (2x ATR)")
        self.btn_sugeruj_stop.clicked.connect(self.pobierz_sugestie)
        
        formularz.addRow("Kapitał:", self.input_kapital)
        formularz.addRow("Cena Wejścia:", self.input_cena)
        formularz.addRow("Stop Loss:", self.input_stop)
        formularz.addRow("Cel (Target):", self.input_cel)
        formularz.addRow("Ryzyko Portfolio:", self.input_procent)
        
        uklad.addLayout(formularz)
        uklad.addWidget(self.btn_sugeruj_stop)
        
        btn_oblicz = QPushButton("Oblicz Pozycję")
        btn_oblicz.clicked.connect(self.oblicz)
        uklad.addWidget(btn_oblicz)
        
        self.lbl_wynik = QLabel("")
        self.lbl_wynik.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 10px;")
        uklad.addWidget(self.lbl_wynik)
        
        uklad.addStretch()
        self.setLayout(uklad)
        
    def pobierz_sugestie(self):
        # TODO: Pobranie aktywnego tykera z kontekstu aplikacji
        # Na razie to placeholder, w wersji 2.0 trzeba by przekazać tykera
        pass

    def oblicz(self):
        wynik = ZarzadzanieRyzykiem.oblicz_pozycje(
            wielkosc_portfela=self.input_kapital.value(),
            cena_wejscia=self.input_cena.value(),
            stop_loss=self.input_stop.value(),
            cena_celowana=self.input_cel.value(),
            procent_ryzyka=self.input_procent.value() / 100.0,
            min_rr=Konfiguracja.MIN_RR
        )
        
        kolor = "green" if wynik.jest_poprawny_rr else "red"
        tekst = f"""
        Liczba Akcji: {wynik.liczba_akcji}
        Wartość Pozycji: {wynik.calkowity_koszt:,.2f} USD
        Ryzykowana Kwota: {wynik.ryzykowana_kwota:.2f} USD
        R:R: {wynik.wspolczynnik_rr:.2f} ({'OK' if wynik.jest_poprawny_rr else 'ZA NISKI'})
        """
        self.lbl_wynik.setText(tekst)
        self.lbl_wynik.setStyleSheet(f"color: {kolor}; font-size: 14px; font-weight: bold;")
