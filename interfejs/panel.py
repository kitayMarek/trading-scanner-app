from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QFrame, QMessageBox, QInputDialog,
    QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from konfiguracja import Konfiguracja
from dane.repozytorium import RepozytoriumDanych
from analiza.rezim import SilnikRezimu, MarketRegime
from analiza.ranking import RankingEngine
from analiza.top1_engine import SilnikDecyzyjny
from dane.importer import ImporterDanych
from ryzyko.position_sizing import PositionSizing

class PanelStartowy(QWidget):
    def __init__(self):
        super().__init__()
        self.repo = RepozytoriumDanych()
        self.inicjalizuj_ui()
        self.odswiez_dane()
        
    def inicjalizuj_ui(self):
        uklad = QVBoxLayout()

        # Nagłówek
        tytul = QLabel("Pulpit Inwestora - Trend Following 2.0")
        tytul.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 10px;")
        uklad.addWidget(tytul)

        # ===== SEKCJA 1: Market Regime Badge (v2.0) =====
        ramka_regime = QFrame()
        ramka_regime.setFrameShape(QFrame.StyledPanel)
        ramka_regime.setStyleSheet("border: 2px solid #333; border-radius: 8px; padding: 10px; background-color: #f5f5f5;")
        uklad_regime = QHBoxLayout(ramka_regime)

        uklad_regime.addWidget(QLabel("<b>Market Regime:</b>"))
        self.badge_regime = QLabel("LOADING")
        self.badge_regime.setAlignment(Qt.AlignCenter)
        self.badge_regime.setStyleSheet("font-size: 18px; font-weight: bold; color: white; background-color: gray; padding: 5px; border-radius: 4px; min-width: 150px;")
        uklad_regime.addWidget(self.badge_regime)

        self.lbl_regime_desc = QLabel("Waiting for data...")
        uklad_regime.addWidget(self.lbl_regime_desc)
        uklad_regime.addStretch()

        uklad.addWidget(ramka_regime)

        # ===== SEKCJA 2: Top 5 Tier A Setup (v2.0) =====
        uklad.addWidget(QLabel("<b>Top 5 Tier A Candidates:</b>"))
        self.tabela_top5 = QTableWidget()
        self.tabela_top5.setColumnCount(7)
        self.tabela_top5.setHorizontalHeaderLabels(["Status", "Tier", "Tyker", "ChecklistScore", "Price", "SMA200 Slope", "RS"])
        self.tabela_top5.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabela_top5.setMaximumHeight(150)
        uklad.addWidget(self.tabela_top5)

        # ===== SEKCJA 3: Portfolio Heat (v2.0) =====
        ramka_heat = QFrame()
        ramka_heat.setFrameShape(QFrame.StyledPanel)
        ramka_heat.setStyleSheet("border: 2px solid #333; border-radius: 8px; padding: 10px; background-color: #f5f5f5;")
        uklad_heat = QVBoxLayout(ramka_heat)

        uklad_heat.addWidget(QLabel("<b>Portfolio Heat (Risk):</b>"))
        uklad_heat_bar = QHBoxLayout()
        self.progress_heat = QProgressBar()
        self.progress_heat.setMaximum(100)
        self.progress_heat.setTextVisible(True)
        self.lbl_heat_value = QLabel("0.0% (Limit: 6.0%)")
        uklad_heat_bar.addWidget(self.progress_heat)
        uklad_heat_bar.addWidget(self.lbl_heat_value)
        uklad_heat.addLayout(uklad_heat_bar)

        uklad.addWidget(ramka_heat)

        # ===== SEKCJA 4: Watchlist Statistics =====
        uklad.addWidget(QLabel("<b>Watchlist Statistics:</b>"))
        ramka_stats = QFrame()
        ramka_stats.setStyleSheet("background-color: #f0f0f0; border-radius: 5px; padding: 5px;")
        layout_stats = QHBoxLayout(ramka_stats)

        self.lbl_tradeable = QLabel("TRADEABLE: -")
        self.lbl_tradeable.setStyleSheet("color: green; font-weight: bold; font-size: 14px;")
        self.lbl_setup = QLabel("SETUP: -")
        self.lbl_setup.setStyleSheet("color: #aa8800; font-weight: bold; font-size: 14px;")
        self.lbl_out = QLabel("OUT: -")
        self.lbl_out.setStyleSheet("color: gray; font-size: 14px;")

        layout_stats.addWidget(self.lbl_tradeable)
        layout_stats.addWidget(self.lbl_setup)
        layout_stats.addWidget(self.lbl_out)
        layout_stats.addStretch()

        uklad.addWidget(ramka_stats)

        # ===== SEKCJA 5: Action Buttons =====
        uklad_przyciskow = QHBoxLayout()
        btn_odswiez = QPushButton("Refresh Analysis")
        btn_odswiez.clicked.connect(self.odswiez_dane)
        uklad_przyciskow.addWidget(btn_odswiez)

        btn_import_yf = QPushButton("Download Data (YFinance)")
        btn_import_yf.clicked.connect(self.pobierz_yf)
        uklad_przyciskow.addWidget(btn_import_yf)

        uklad.addLayout(uklad_przyciskow)
        uklad.addStretch()
        self.setLayout(uklad)
        
    def odswiez_dane(self):
        try:
            benchmark = Konfiguracja.TYKER_BENCHMARK
            df_bench = self.repo.pobierz_swiece_df(benchmark)

            # ===== FALLBACK: Jeśli benchmark (SPY) jest pusty, spróbuj użyć pierwszego dostępnego tykera =====
            if df_bench.empty:
                dostepne_tykery = self.repo.pobierz_wszystkie_tykery()
                if not dostepne_tykery:
                    self.badge_regime.setText("NO DATA")
                    self.badge_regime.setStyleSheet("font-size: 18px; font-weight: bold; color: white; background-color: gray; padding: 5px;")
                    self.lbl_regime_desc.setText("Brak danych w bazie. Pobierz dane dla co najmniej jednej spółki.")
                    return

                # Użyj pierwszego dostępnego tykera jako benchmark
                benchmark = dostepne_tykery[0]
                df_bench = self.repo.pobierz_swiece_df(benchmark)

                if df_bench.empty:
                    self.badge_regime.setText("NO DATA")
                    self.badge_regime.setStyleSheet("font-size: 18px; font-weight: bold; color: white; background-color: gray; padding: 5px;")
                    return

            # ===== 1. MARKET REGIME v2.0 (with badge) =====
            regime, desc = SilnikRezimu.detect_regime(df_bench)

            regime_text = regime.value
            kolor_badge = "#999999"  # Default gray

            if regime == MarketRegime.STRONG_BULL:
                kolor_badge = "#00aa00"  # Dark green
            elif regime == MarketRegime.BULL:
                kolor_badge = "#00cc00"  # Light green
            elif regime == MarketRegime.NEUTRAL:
                kolor_badge = "#ff9900"  # Orange
            elif regime == MarketRegime.BEAR:
                kolor_badge = "#ff6666"  # Light red
            elif regime == MarketRegime.STRONG_BEAR:
                kolor_badge = "#aa0000"  # Dark red

            self.badge_regime.setText(regime_text)
            self.badge_regime.setStyleSheet(f"font-size: 18px; font-weight: bold; color: white; background-color: {kolor_badge}; padding: 5px; border-radius: 4px;")
            self.lbl_regime_desc.setText(desc)

            # ===== 2. GET DATA FOR ALL TICKERS =====
            tykery = self.repo.pobierz_wszystkie_tykery()
            dane_map = {}
            for t in tykery:
                df = self.repo.pobierz_swiece_df(t)
                if not df.empty:
                    dane_map[t] = df

            if not dane_map:
                self.badge_regime.setText("WAITING")
                self.badge_regime.setStyleSheet("font-size: 18px; font-weight: bold; color: white; background-color: #ff9900; padding: 5px;")
                self.lbl_regime_desc.setText("Pobieranie danych w toku. Dodaj spółki i kliknij 'Download Data'.")
                return

            # ===== 3. GENERATE RANKING (v2.0 with Composite Score) =====
            ranking_df = RankingEngine.generuj_ranking(dane_map, df_bench)

            # ===== 4. POPULATE TOP 5 TIER A =====
            self.wypelnij_top5(ranking_df)

            # ===== 5. UPDATE STATISTICS =====
            if not ranking_df.empty:
                counts = ranking_df['Status'].value_counts()
                self.lbl_tradeable.setText(f"TRADEABLE: {counts.get('TRADEABLE', 0)}")
                self.lbl_setup.setText(f"SETUP: {counts.get('SETUP', 0)}")
                self.lbl_out.setText(f"OUT: {counts.get('OUT', 0)}")

                # Portfolio Heat (mock - na razie 0, ale struktura jest gotowa do integracji z serwisem dziennika)
                # W rzeczywistości trzeba by pobierać z journal serwisu otwarte pozycje
                self.progress_heat.setValue(0)
                self.lbl_heat_value.setText(f"0.0% (Limit: {Konfiguracja.MAX_PORTFOLIO_HEAT_PERCENT}%)")
                self.progress_heat.setStyleSheet("QProgressBar { background-color: #e0e0e0; } QProgressBar::chunk { background-color: #00aa00; }")
            else:
                self.lbl_tradeable.setText("TRADEABLE: 0")
                self.lbl_setup.setText("SETUP: 0")
                self.lbl_out.setText("OUT: 0")

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            import traceback
            traceback.print_exc()

    def wypelnij_top5(self, ranking_df):
        """Populuje tabelę Top 5 Tier A setupów z Status=TRADEABLE (v2.1)"""
        self.tabela_top5.setRowCount(0)

        if ranking_df.empty:
            return

        # ===== NOWE v2.1 =====
        # Filtruj: TRADEABLE + Tier A, posortuj po ChecklistScore DESC
        tradeable_a = ranking_df[
            (ranking_df['Status'] == 'TRADEABLE') &
            (ranking_df['Tier'] == 'A')
        ].sort_values('ChecklistScore', ascending=False).head(5)

        if tradeable_a.empty:
            # Jeśli brak Tier A, pokaż przynajmniej top 5 TRADEABLE z Tier B
            tradeable = ranking_df[ranking_df['Status'] == 'TRADEABLE'].sort_values('ChecklistScore', ascending=False).head(5)
            if tradeable.empty:
                return
            tradeable_a = tradeable

        self.tabela_top5.setRowCount(len(tradeable_a))

        for r, row in enumerate(tradeable_a.itertuples()):
            # Status
            item_status = QTableWidgetItem(str(row.Status))
            item_status.setBackground(QColor(200, 255, 200))  # Green for TRADEABLE
            self.tabela_top5.setItem(r, 0, item_status)

            # Tier
            item_tier = QTableWidgetItem(str(row.Tier))
            if row.Tier == 'A':
                item_tier.setBackground(QColor(200, 255, 200))  # Green
            else:
                item_tier.setBackground(QColor(255, 255, 200))  # Yellow
            self.tabela_top5.setItem(r, 1, item_tier)

            # Ticker
            item_ticker = QTableWidgetItem(str(row.Tyker))
            self.tabela_top5.setItem(r, 2, item_ticker)

            # ChecklistScore (0-10) - NOWE v2.1
            item_score = QTableWidgetItem(f"{row.ChecklistScore}/10")
            if row.ChecklistScore >= 8:
                item_score.setBackground(QColor(200, 255, 200))  # Green
            else:
                item_score.setBackground(QColor(255, 255, 200))  # Yellow
            self.tabela_top5.setItem(r, 3, item_score)

            # Price
            item_price = QTableWidgetItem(f"${row.Zamkniecie:.2f}")
            self.tabela_top5.setItem(r, 4, item_price)

            # SMA200 Slope (zielony jeśli dodatni, czerwony jeśli ujemny)
            slope = row.SMA200_Slope
            item_slope = QTableWidgetItem(f"{slope:.2f}%")
            if slope > 0:
                item_slope.setBackground(QColor(200, 255, 200))
            else:
                item_slope.setBackground(QColor(255, 200, 200))
            self.tabela_top5.setItem(r, 5, item_slope)

            # RS
            item_rs = QTableWidgetItem(f"{row.RS_Ratio:.2f}")
            self.tabela_top5.setItem(r, 6, item_rs)

    def pobierz_yf(self):
        tyker, ok = QInputDialog.getText(self, "Pobieranie Danych", "Podaj symbol tickera (np. SPY, AAPL):")
        if ok and tyker:
            try:
                tyker_clean = tyker.upper().strip()
                swiece = ImporterDanych.pobierz_yfinance(tyker_clean)
                if swiece:
                    self.repo.zapisz_swiece(swiece)
                    self.odswiez_dane()
                    QMessageBox.information(self, "Sukces", f"Pobrano {len(swiece)} świec dla {tyker_clean}. Panel został odświeżony.")
                else:
                    QMessageBox.warning(self, "Brak Danych", f"Nie udało się pobrać danych dla {tyker_clean}. Sprawdź symbol tickera.")
            except Exception as e:
                QMessageBox.critical(self, "Błąd", f"Błąd pobierania danych: {str(e)}")
