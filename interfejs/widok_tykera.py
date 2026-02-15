from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QFrame
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from dane.repozytorium import RepozytoriumDanych
from analiza.wskazniki import SilnikWskaznikow
from konfiguracja import Konfiguracja
import pandas as pd

class WidokTykera(QWidget):
    def __init__(self):
        super().__init__()
        self.repo = RepozytoriumDanych()
        self.biezacy_tyker = None
        self.inicjalizuj_ui()
        
    def inicjalizuj_ui(self):
        uklad = QHBoxLayout()
        
        # Lewa: Wykres
        uklad_wykresu = QVBoxLayout()
        self.rysunek = Figure()
        self.plotno = FigureCanvas(self.rysunek)
        uklad_wykresu.addWidget(self.plotno)
        uklad.addLayout(uklad_wykresu, stretch=2)
        
        # Prawa: Panel Boczny
        panel_boczny = QVBoxLayout()
        self.etykieta_tykera = QLabel("Wybierz Tykera")
        self.etykieta_tykera.setStyleSheet("font-size: 20px; font-weight: bold;")
        panel_boczny.addWidget(self.etykieta_tykera)
        
        # Metryki Trendu
        panel_boczny.addWidget(QLabel("<b>Struktura Trendu:</b>"))
        self.chk_trend = QCheckBox("Cena > SMA200 (Wzrostowy)")
        self.chk_slope = QCheckBox("SMA200 Rosnąca")
        self.chk_rs = QCheckBox("RS > RS_MA (Siła Względna)")
        
        for chk in [self.chk_trend, self.chk_slope, self.chk_rs]:
            chk.setEnabled(False)
            panel_boczny.addWidget(chk)
            
        # Szczegóły Liczbowe
        self.lbl_detale = QLabel("")
        panel_boczny.addWidget(self.lbl_detale)
        
        panel_boczny.addStretch()
        uklad.addLayout(panel_boczny, stretch=1)
        
        self.setLayout(uklad)
        
    def zaladuj_tykera(self, tyker: str):
        self.biezacy_tyker = tyker
        self.etykieta_tykera.setText(f"Analiza: {tyker}")
        
        df = self.repo.pobierz_swiece_df(tyker)
        bench_df = self.repo.pobierz_swiece_df(Konfiguracja.TYKER_BENCHMARK)
        
        if df.empty: return
        
        # Obliczanie wskaźników
        df = SilnikWskaznikow.oblicz_wskazniki(df, bench_df)
        
        self.rysuj_wykres(df)
        self.aktualizuj_panel(df)
        
    def rysuj_wykres(self, df):
        self.rysunek.clear()
        ax = self.rysunek.add_subplot(111)
        
        # Ostatni rok
        dane_plot = df.tail(252)
        
        ax.plot(dane_plot.index, dane_plot['close'], label='Cena', color='black')
        if 'SMA50' in dane_plot.columns:
            ax.plot(dane_plot.index, dane_plot['SMA50'], label='SMA50', color='#1f77b4')
        if 'SMA200' in dane_plot.columns:
            ax.plot(dane_plot.index, dane_plot['SMA200'], label='SMA200', color='#d62728')
            
        ax.legend()
        ax.set_title(f"{self.biezacy_tyker} Interwał Dzienny")
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        
        self.plotno.draw()

    def get_metric_color(self, metric_name, value, ostatni=None):
        """
        Determine color for metric based on value and thresholds.
        Returns tuple: (color_hex, threshold_text)

        Args:
            metric_name: Name of metric (e.g., 'SMA200_Slope')
            value: Current value of metric
            ostatni: Last row from dataframe (needed for RS_Ratio comparison)

        Returns:
            (color, threshold): e.g., ('#00aa00', 'min: >0.001%')
        """
        from konfiguracja import Konfiguracja

        GREEN = '#00aa00'
        YELLOW = '#aa8800'
        RED = '#cc0000'
        GRAY = '#777777'

        if metric_name == 'SMA200_Slope' or metric_name == 'SMA50_Slope':
            threshold_text = f'min: >{Konfiguracja.SLOPE_RISING_THRESHOLD:.3f}%'
            if value > Konfiguracja.SLOPE_RISING_THRESHOLD:
                return (GREEN, threshold_text)
            elif value < Konfiguracja.SLOPE_FALLING_THRESHOLD:
                return (RED, threshold_text)
            else:
                return (GRAY, threshold_text)

        elif metric_name == 'Dist_SMA200':
            threshold_text = f'range: {Konfiguracja.DISTANCE_MIN_PCT:.0f}% to {Konfiguracja.DISTANCE_MAX_PCT:.0f}%'
            if -5 <= value <= 15:  # Good zone
                return (GREEN, threshold_text)
            elif Konfiguracja.DISTANCE_MIN_PCT <= value <= Konfiguracja.DISTANCE_MAX_PCT:  # Neutral zone
                return (YELLOW, threshold_text)
            else:  # Extended
                return (RED, threshold_text)

        elif metric_name == 'ATR_Pct':
            threshold_text = f'max: <{Konfiguracja.ATR_MAX_PCT:.1f}%'
            if 1.0 <= value <= 3.0:  # Good zone
                return (GREEN, threshold_text)
            elif 3.0 < value < Konfiguracja.ATR_MAX_PCT:  # Neutral zone
                return (YELLOW, threshold_text)
            else:  # Too volatile or too low
                return (RED, threshold_text)

        elif metric_name in ['Mom3M', 'Mom6M']:
            threshold_text = 'min: >0%'
            if value > 0.01:  # > 1% positive
                return (GREEN, threshold_text)
            elif value < -0.01:  # < -1% negative
                return (RED, threshold_text)
            else:  # Near zero
                return (GRAY, threshold_text)

        elif metric_name == 'RS_Ratio':
            rs_sma50 = ostatni.get('RS_SMA50', 1.0) if ostatni is not None else 1.0
            threshold_text = f'min: >{rs_sma50:.3f}'
            if value > rs_sma50:
                return (GREEN, threshold_text)
            elif value < rs_sma50 * 0.98:  # 2% below SMA
                return (RED, threshold_text)
            else:
                return (GRAY, threshold_text)

        elif metric_name == 'RS_Slope':
            threshold_text = 'min: >0%'
            if value > 0.001:
                return (GREEN, threshold_text)
            elif value < -0.001:
                return (RED, threshold_text)
            else:
                return (GRAY, threshold_text)

        # Default fallback
        return (GRAY, '')

    def aktualizuj_panel(self, df):
        ostatni = df.iloc[-1]
        
        # Checkboxy (convert numpy.bool_ to Python bool)
        trend_ok = bool(ostatni['close'] > ostatni['SMA200'])
        slope_ok = bool(ostatni.get('SMA200_Slope', 0) > 0)
        rs_ok = bool(ostatni.get('RS_Ratio', 0) > ostatni.get('RS_SMA50', 0))

        self.chk_trend.setChecked(trend_ok)
        self.chk_slope.setChecked(slope_ok)
        self.chk_rs.setChecked(rs_ok)

        # Detale - Color-coded metrics with thresholds
        # Get metric values
        sma200_slope = ostatni.get('SMA200_Slope', 0)
        sma50_slope = ostatni.get('SMA50_Slope', 0)
        dist_sma200 = ostatni.get('Dist_SMA200', 0)
        atr_pct = ostatni.get('ATR_Pct', 0)
        mom3m = ostatni.get('Mom3M', 0)
        mom6m = ostatni.get('Mom6M', 0)
        rs_ratio = ostatni.get('RS_Ratio', 0)
        rs_slope = ostatni.get('RS_Slope', 0)

        # Get colors and thresholds
        color_sma200, thresh_sma200 = self.get_metric_color('SMA200_Slope', sma200_slope)
        color_sma50, thresh_sma50 = self.get_metric_color('SMA50_Slope', sma50_slope)
        color_dist, thresh_dist = self.get_metric_color('Dist_SMA200', dist_sma200)
        color_atr, thresh_atr = self.get_metric_color('ATR_Pct', atr_pct)
        color_mom3m, thresh_mom3m = self.get_metric_color('Mom3M', mom3m)
        color_mom6m, thresh_mom6m = self.get_metric_color('Mom6M', mom6m)
        color_rs_ratio, thresh_rs_ratio = self.get_metric_color('RS_Ratio', rs_ratio, ostatni)
        color_rs_slope, thresh_rs_slope = self.get_metric_color('RS_Slope', rs_slope)

        # Build HTML with inline color styling
        tekst = f"""
        <br><b>Metryki Wskaźniki:</b><br>
        <span style='color: {color_sma200}; font-weight: bold;'>SMA200 Slope: {sma200_slope:.2f}%</span> <span style='color: #666; font-size: 10px;'>({thresh_sma200})</span><br>
        <span style='color: {color_sma50}; font-weight: bold;'>SMA50 Slope: {sma50_slope:.2f}%</span> <span style='color: #666; font-size: 10px;'>({thresh_sma50})</span><br>
        <span style='color: {color_dist}; font-weight: bold;'>Distance from SMA200: {dist_sma200:.1f}%</span> <span style='color: #666; font-size: 10px;'>({thresh_dist})</span><br>
        <span style='color: {color_atr}; font-weight: bold;'>ATR % of Price: {atr_pct:.2f}%</span> <span style='color: #666; font-size: 10px;'>({thresh_atr})</span><br>
        <span style='color: {color_mom3m}; font-weight: bold;'>Momentum 3M: {mom3m:.2%}</span> <span style='color: #666; font-size: 10px;'>({thresh_mom3m})</span><br>
        <span style='color: {color_mom6m}; font-weight: bold;'>Momentum 6M: {mom6m:.2%}</span> <span style='color: #666; font-size: 10px;'>({thresh_mom6m})</span><br>
        <span style='color: {color_rs_ratio}; font-weight: bold;'>RS Ratio: {rs_ratio:.3f}</span> <span style='color: #666; font-size: 10px;'>({thresh_rs_ratio})</span><br>
        <span style='color: {color_rs_slope}; font-weight: bold;'>RS Slope: {rs_slope:.2f}%</span> <span style='color: #666; font-size: 10px;'>({thresh_rs_slope})</span><br>
        """
        self.lbl_detale.setText(tekst)
