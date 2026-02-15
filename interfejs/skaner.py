from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHBoxLayout, QPushButton, QHeaderView, QLabel,
    QComboBox, QGroupBox, QTabWidget, QMessageBox, QSplitter
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor, QBrush
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from dane.repozytorium import RepozytoriumDanych
from analiza.ranking import RankingEngine
from analiza.wskazniki import SilnikWskaznikow
from konfiguracja import Konfiguracja

class SkanerWidok(QWidget):
    tyker_wybrany = Signal(str)

    def __init__(self):
        super().__init__()
        self.repo = RepozytoriumDanych()
        self.ranking_df = None

        # Chart components (will be initialized in inicjalizuj_ui)
        self.rysunek = None
        self.plotno = None
        self.lbl_detale = None

        self.inicjalizuj_ui()
        
    def inicjalizuj_ui(self):
        uklad = QVBoxLayout()

        # ===== TAB WIDGET =====
        self.tabs = QTabWidget()

        # ===== TAB 1: SCANNER =====
        scanner_tab = QWidget()
        scanner_layout = QVBoxLayout(scanner_tab)

        # Tip label for scanner tab
        tip_label = QLabel("💡 <b>Tip:</b> Double-click any row to view stock details. See 'Help' tab for column interpretation guide.")
        tip_label.setStyleSheet("color: #0066cc; padding: 5px; font-size: 11px;")
        scanner_layout.addWidget(tip_label)

        # Controls
        uklad_btn = QHBoxLayout()
        btn_skanuj = QPushButton("Run Scanner (v2.1)")
        btn_skanuj.clicked.connect(self.uruchom_skaner)
        uklad_btn.addWidget(btn_skanuj)

        # NEW: Remove stock button
        btn_remove = QPushButton("Remove Stock")
        btn_remove.clicked.connect(self.usun_spolke)
        btn_remove.setStyleSheet("background-color: #cc4444; color: white;")  # Red button
        uklad_btn.addWidget(btn_remove)

        # Filter by Status
        uklad_btn.addWidget(QLabel("Filter by Status:"))
        self.combo_status = QComboBox()
        self.combo_status.addItems(["All", "TRADEABLE", "SETUP", "OUT"])
        self.combo_status.currentIndexChanged.connect(self.on_status_changed)
        uklad_btn.addWidget(self.combo_status)

        uklad_btn.addStretch()
        scanner_layout.addLayout(uklad_btn)

        # Table
        self.tabela = QTableWidget()
        kolumny = [
            "Status", "Tyker", "ChecklistScore", "Tier", "Price",
            "SMA200 Slope %", "RS Slope %", "Distance %", "ATR %"
        ]
        self.tabela.setColumnCount(len(kolumny))
        self.tabela.setHorizontalHeaderLabels(kolumny)
        self.tabela.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tabela.cellDoubleClicked.connect(self.on_dwuklik)
        self.tabela.cellClicked.connect(self.on_pojedyncze_klikniecie)  # Single click updates chart

        # Enable row selection for removing stocks
        self.tabela.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela.setSelectionMode(QTableWidget.SingleSelection)

        # Create horizontal splitter for table + chart
        splitter = QSplitter(Qt.Horizontal)

        # Left side: Table
        splitter.addWidget(self.tabela)

        # Right side: Chart + Metrics panel
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Chart canvas
        self.rysunek = Figure(figsize=(8, 6))
        self.plotno = FigureCanvas(self.rysunek)
        right_layout.addWidget(self.plotno, stretch=3)

        # Metrics panel
        self.lbl_detale = QLabel("Select a stock to view chart and metrics")
        self.lbl_detale.setWordWrap(True)
        self.lbl_detale.setStyleSheet("padding: 10px; background-color: #f5f5f5; border-radius: 5px;")
        self.lbl_detale.setAlignment(Qt.AlignTop)
        right_layout.addWidget(self.lbl_detale, stretch=1)

        right_panel.setLayout(right_layout)
        splitter.addWidget(right_panel)

        # Set initial sizes (60% table, 40% chart)
        splitter.setSizes([600, 400])

        scanner_layout.addWidget(splitter)

        # Store full ranking for filtering
        self.ranking_df = None

        # ===== TAB 2: HELP/LEGEND =====
        help_tab = QWidget()
        help_layout = QVBoxLayout(help_tab)

        # Legend HTML content
        legend_html = """
<style>
    table { border-collapse: collapse; width: 100%; font-size: 12px; }
    th { background-color: #e0e0e0; padding: 6px; text-align: left; font-weight: bold; }
    td { padding: 5px; border-bottom: 1px solid #ddd; }
    .good { color: green; font-weight: bold; }
    .neutral { color: #aa8800; }
    .bad { color: red; }
    .header { font-weight: bold; margin-top: 10px; margin-bottom: 5px; }
</style>

<div class='header'>📊 Column Interpretation Guide</div>

<table>
<tr>
    <th>Column</th>
    <th>Good Value</th>
    <th>Neutral</th>
    <th>Poor Value</th>
    <th>Meaning & Thresholds</th>
</tr>

<tr>
    <td><b>Status</b></td>
    <td class='good'>TRADEABLE</td>
    <td class='neutral'>SETUP</td>
    <td class='bad'>OUT</td>
    <td>Trading readiness based on 4 strict criteria (Close>SMA200, SMA200↑, Close>SMA50, RS strong)</td>
</tr>

<tr>
    <td><b>ChecklistScore</b></td>
    <td class='good'>8-10</td>
    <td class='neutral'>6-7</td>
    <td class='bad'>0-5</td>
    <td>Count of 10 binary conditions met. Each condition = +1 point. Higher = better setup quality.</td>
</tr>

<tr>
    <td><b>Tier</b></td>
    <td class='good'>A</td>
    <td class='neutral'>B, C</td>
    <td class='bad'>D</td>
    <td>Quality grade: A=8-10 score (excellent), B=6-7 (good), C=4-5 (fair), D=0-3 (poor)</td>
</tr>

<tr>
    <td><b>SMA200 Slope %</b></td>
    <td class='good'>+0.3% or higher</td>
    <td class='neutral'>+0.001% to +0.2%</td>
    <td class='bad'>Negative or 0</td>
    <td>200-day trend direction. Example: +0.35% = strong upward trend. Passes condition if >0.001%</td>
</tr>

<tr>
    <td><b>RS Slope %</b></td>
    <td class='good'>+0.2% or higher</td>
    <td class='neutral'>0% to +0.1%</td>
    <td class='bad'>Negative</td>
    <td>Relative strength trend vs SPY benchmark. Example: +0.35% = strong outperformance. Passes if >0%</td>
</tr>

<tr>
    <td><b>Distance %</b></td>
    <td class='good'>-5% to +15%</td>
    <td class='neutral'>±15% to ±20%</td>
    <td class='bad'>Beyond ±20%</td>
    <td>Price gap from SMA200. Example: +1.9% = 1.9% above SMA200 (healthy). Range -20% to +20% passes condition.</td>
</tr>

<tr>
    <td><b>ATR %</b></td>
    <td class='good'>1.0% to 3.0%</td>
    <td class='neutral'>3.0% to 3.9%</td>
    <td class='bad'>4.0% or higher</td>
    <td>Volatility as % of price. Example: 2.5% = moderate volatility, good for tight stops. Must be <4.0% to pass condition.</td>
</tr>
</table>

<div class='header'>✅ 10 ChecklistScore Conditions (each = +1 point)</div>

<table>
<tr><th>#</th><th>Condition</th><th>Threshold</th></tr>
<tr><td>1</td><td>Close > SMA200</td><td>Price above 200-day MA</td></tr>
<tr><td>2</td><td>SMA200 Slope Rising</td><td>>0.001%</td></tr>
<tr><td>3</td><td>Close > SMA50</td><td>Price above 50-day MA</td></tr>
<tr><td>4</td><td>SMA50 Slope Rising</td><td>>0.001%</td></tr>
<tr><td>5</td><td>RS Slope Positive</td><td>>0%</td></tr>
<tr><td>6</td><td>RS Ratio Strong</td><td>RS > RS_SMA50</td></tr>
<tr><td>7</td><td>6M Momentum Positive</td><td>>0%</td></tr>
<tr><td>8</td><td>3M Momentum Positive</td><td>>0%</td></tr>
<tr><td>9</td><td>Distance Within Range</td><td>-20% to +20%</td></tr>
<tr><td>10</td><td>ATR Below Threshold</td><td><4.0%</td></tr>
</table>

<div class='header'>🎨 Color Coding</div>
<p>
<span style='background-color: #c8ffc8; padding: 3px;'>TRADEABLE = Green background</span> |
<span style='background-color: #ffffc8; padding: 3px;'>SETUP = Yellow background</span> |
<span style='background-color: #f0f0f0; padding: 3px;'>OUT = Gray background</span>
</p>
<p>
<b>SMA200/RS Slope cells:</b> <span class='good'>Green = Positive (rising)</span> | <span class='bad'>Red = Negative (falling)</span>
</p>
"""

        # Legend label
        legend_label = QLabel()
        legend_label.setTextFormat(Qt.RichText)
        legend_label.setWordWrap(True)
        legend_label.setText(legend_html)
        legend_label.setStyleSheet("padding: 10px; background-color: white;")
        help_layout.addWidget(legend_label)

        # ===== ADD TABS TO WIDGET =====
        self.tabs.addTab(scanner_tab, "📊 Scanner")
        self.tabs.addTab(help_tab, "📖 Help / Legend")

        uklad.addWidget(self.tabs)
        self.setLayout(uklad)
        
    def uruchom_skaner(self):
        """Run scanner with v2.0 RankingEngine"""
        tykery = self.repo.pobierz_wszystkie_tykery()
        benchmark = Konfiguracja.TYKER_BENCHMARK
        df_bench = self.repo.pobierz_swiece_df(benchmark)

        # Validate benchmark loading
        if df_bench is None or df_bench.empty:
            print(f"⚠️ WARNING: Benchmark {benchmark} failed to load or is empty!")
            print("RS metrics will use default values (RS_Ratio=1.0, RS_Slope=0.0)")

        dane_map = {}
        for t in tykery:
            df = self.repo.pobierz_swiece_df(t)
            if not df.empty:
                dane_map[t] = df

        # Use new RankingEngine v2.0
        ranking_df = RankingEngine.generuj_ranking(dane_map, df_bench)
        self.ranking_df = ranking_df  # Store for filtering
        self.combo_status.setCurrentIndex(0)  # Reset filter to "All"
        self.wypelnij_tabele(ranking_df)

    def usun_spolke(self):
        """Remove selected stock from database and scanner"""
        # Check if a row is selected
        selected_items = self.tabela.selectedItems()
        if not selected_items:
            QMessageBox.warning(
                self,
                "Błąd",
                "Wybierz spółkę do usunięcia z listy!"
            )
            return

        # Get the ticker from the selected row (column 1 = Tyker)
        row = selected_items[0].row()
        ticker_item = self.tabela.item(row, 1)  # Column 1 is "Tyker"

        if not ticker_item:
            QMessageBox.warning(self, "Błąd", "Nie można odczytać tykera!")
            return

        ticker = ticker_item.text()

        # Confirmation dialog
        reply = QMessageBox.question(
            self,
            "Potwierdzenie usunięcia",
            f"Czy na pewno usunąć wszystkie dane dla {ticker}?\n\n"
            f"Spowoduje to:\n"
            f"• Usunięcie wszystkich danych cenowych (świece)\n"
            f"• Usunięcie spółki z listy analizowanych\n"
            f"• Ta operacja jest nieodwracalna!\n\n"
            f"Kontynuować?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No  # Default to No for safety
        )

        if reply == QMessageBox.No:
            return

        # Delete from database
        try:
            deleted_count = self.repo.usun_dane_tykera(ticker)

            # Show success message
            QMessageBox.information(
                self,
                "Sukces",
                f"Usunięto {ticker} z listy.\n"
                f"Usuniętych wierszy: {deleted_count}"
            )

            # Refresh the scanner table
            self.uruchom_skaner()

        except Exception as e:
            QMessageBox.critical(
                self,
                "Błąd",
                f"Nie udało się usunąć {ticker}:\n{str(e)}"
            )

    def rysuj_wykres(self, df, tyker):
        """Draw price chart with SMA50 and SMA200"""
        self.rysunek.clear()

        if df is None or df.empty:
            ax = self.rysunek.add_subplot(111)
            ax.text(0.5, 0.5, 'No data available',
                    ha='center', va='center', fontsize=14, color='gray')
            ax.axis('off')
            self.plotno.draw()
            return

        ax = self.rysunek.add_subplot(111)

        # Last 252 trading days (1 year)
        dane_plot = df.tail(252)

        # Plot price
        ax.plot(dane_plot.index, dane_plot['close'], label='Close Price', color='black', linewidth=1.5)

        # Plot SMA50
        if 'SMA50' in dane_plot.columns:
            ax.plot(dane_plot.index, dane_plot['SMA50'], label='SMA50', color='#1f77b4', linewidth=1.2)

        # Plot SMA200
        if 'SMA200' in dane_plot.columns:
            ax.plot(dane_plot.index, dane_plot['SMA200'], label='SMA200', color='#d62728', linewidth=1.2)

        # Formatting
        ax.legend(loc='upper left', fontsize=9)
        ax.set_title(f"{tyker} - Daily Chart", fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.tick_params(axis='both', which='major', labelsize=8)

        # Tight layout to maximize chart space
        self.rysunek.tight_layout()
        self.plotno.draw()

    def aktualizuj_panel(self, df, tyker):
        """Update metrics panel with indicator values"""
        if df is None or df.empty:
            self.lbl_detale.setText("<b>Select a stock to view metrics</b>")
            return

        ostatni = df.iloc[-1]  # Last row (most recent data)

        # Status indicator
        status = ostatni.get('Status', 'N/A')
        status_color = {
            'TRADEABLE': '#00aa00',
            'SETUP': '#aa8800',
            'OUT': '#cc0000'
        }.get(status, '#777777')

        # Trend structure checkboxes (using symbols)
        trend_ok = bool(ostatni.get('close', 0) > ostatni.get('SMA200', 0))
        slope_ok = bool(ostatni.get('SMA200_Slope', 0) > 0)
        rs_ok = bool(ostatni.get('RS_Ratio', 0) > ostatni.get('RS_SMA50', 0))

        check_trend = "✅" if trend_ok else "❌"
        check_slope = "✅" if slope_ok else "❌"
        check_rs = "✅" if rs_ok else "❌"

        # Format metrics text
        tekst = f"""
        <div style='padding: 10px;'>
        <h3 style='margin: 0 0 10px 0; color: #333;'>{tyker} - Metrics</h3>

        <p style='margin: 5px 0;'><b>Status:</b> <span style='color: {status_color}; font-weight: bold;'>{status}</span></p>

        <p style='margin: 10px 0 5px 0;'><b>Trend Structure:</b></p>
        <ul style='margin: 0; padding-left: 20px; line-height: 1.8;'>
            <li>{check_trend} Price &gt; SMA200</li>
            <li>{check_slope} SMA200 Rising</li>
            <li>{check_rs} RS &gt; RS_MA</li>
        </ul>

        <p style='margin: 15px 0 5px 0;'><b>Key Indicators:</b></p>
        <table style='width: 100%; border-collapse: collapse; font-size: 11px;'>
            <tr><td style='padding: 3px;'>SMA200 Slope:</td><td style='padding: 3px; text-align: right;'><b>{ostatni.get('SMA200_Slope', 0):.2f}%</b></td></tr>
            <tr><td style='padding: 3px;'>Distance to SMA200:</td><td style='padding: 3px; text-align: right;'><b>{ostatni.get('Dist_SMA200', 0):.2f}%</b></td></tr>
            <tr><td style='padding: 3px;'>ATR (% of price):</td><td style='padding: 3px; text-align: right;'><b>{ostatni.get('ATR_Pct', 0):.2f}%</b></td></tr>
            <tr><td style='padding: 3px;'>Momentum 3M:</td><td style='padding: 3px; text-align: right;'><b>{ostatni.get('Mom3M', 0):.2%}</b></td></tr>
            <tr><td style='padding: 3px;'>Momentum 6M:</td><td style='padding: 3px; text-align: right;'><b>{ostatni.get('Mom6M', 0):.2%}</b></td></tr>
            <tr><td style='padding: 3px;'>RS Ratio:</td><td style='padding: 3px; text-align: right;'><b>{ostatni.get('RS_Ratio', 0):.3f}</b></td></tr>
            <tr><td style='padding: 3px;'>RS Slope:</td><td style='padding: 3px; text-align: right;'><b>{ostatni.get('RS_Slope', 0):.2f}%</b></td></tr>
        </table>
        </div>
        """

        self.lbl_detale.setText(tekst)

    def on_pojedyncze_klikniecie(self, row, col):
        """Handle single click - update chart and metrics in scanner"""
        item = self.tabela.item(row, 1)  # Column 1 = Tyker
        if not item:
            return

        ticker = item.text()

        # Load data
        df = self.repo.pobierz_swiece_df(ticker)
        bench_df = self.repo.pobierz_swiece_df(Konfiguracja.TYKER_BENCHMARK)

        if df.empty:
            self.lbl_detale.setText(f"<b>No data available for {ticker}</b>")
            self.rysunek.clear()
            self.plotno.draw()
            return

        # Calculate indicators
        df = SilnikWskaznikow.oblicz_wskazniki(df, bench_df)

        # Update chart and metrics
        self.rysuj_wykres(df, ticker)
        self.aktualizuj_panel(df, ticker)

    def wypelnij_tabele(self, df, filter_status=None):
        """Populate table with ranking data (v2.1 ChecklistScore 0-10)"""
        self.tabela.setRowCount(0)
        if df.empty:
            return

        # ===== FILTER BY STATUS (NOWE v2.1) =====
        if filter_status and filter_status != "All":
            df = df[df['Status'] == filter_status]

        if df.empty:
            return

        self.tabela.setRowCount(len(df))

        for r, row in enumerate(df.itertuples()):
            # ===== STATUS COLORING (TRADEABLE=Green, SETUP=Yellow, OUT=Gray) =====
            item_status = QTableWidgetItem(str(row.Status))

            bg_color = QColor(255, 255, 255)
            fg_color = QColor(0, 0, 0)

            if row.Status == "TRADEABLE":
                bg_color = QColor(200, 255, 200)  # Light green
                fg_color = QColor(0, 100, 0)
            elif row.Status == "SETUP":
                bg_color = QColor(255, 255, 200)  # Light yellow
                fg_color = QColor(100, 100, 0)
            else:  # OUT
                bg_color = QColor(240, 240, 240)  # Gray
                fg_color = QColor(150, 150, 150)

            item_status.setBackground(QBrush(bg_color))
            item_status.setForeground(QBrush(fg_color))
            self.tabela.setItem(r, 0, item_status)

            # Ticker
            self.tabela.setItem(r, 1, QTableWidgetItem(str(row.Tyker)))

            # ChecklistScore (0-10) - NOWE v2.1
            item_score = QTableWidgetItem(f"{row.ChecklistScore}/10")
            # Color code: 8-10=Green, 6-7=Yellow, 4-5=Orange, 0-3=Red
            score = row.ChecklistScore
            if score >= 8:
                item_score.setBackground(QBrush(QColor(200, 255, 200)))  # Green
                item_score.setForeground(QBrush(QColor(0, 100, 0)))
            elif score >= 6:
                item_score.setBackground(QBrush(QColor(255, 255, 200)))  # Yellow
                item_score.setForeground(QBrush(QColor(100, 100, 0)))
            elif score >= 4:
                item_score.setBackground(QBrush(QColor(255, 230, 200)))  # Orange
                item_score.setForeground(QBrush(QColor(150, 100, 0)))
            else:
                item_score.setBackground(QBrush(QColor(255, 200, 200)))  # Red
                item_score.setForeground(QBrush(QColor(100, 0, 0)))
            self.tabela.setItem(r, 2, item_score)

            # Tier (A/B/C/D) - NOWE v2.1
            item_tier = QTableWidgetItem(str(row.Tier))
            if row.Tier == 'A':
                item_tier.setBackground(QBrush(QColor(200, 255, 200)))  # Green
            elif row.Tier == 'B':
                item_tier.setBackground(QBrush(QColor(255, 255, 200)))  # Yellow
            elif row.Tier == 'C':
                item_tier.setBackground(QBrush(QColor(255, 230, 200)))  # Orange
            else:  # D
                item_tier.setBackground(QBrush(QColor(255, 200, 200)))  # Red
            self.tabela.setItem(r, 3, item_tier)

            # Price
            self.tabela.setItem(r, 4, QTableWidgetItem(f"${row.Zamkniecie:.2f}"))

            # SMA200 Slope (zielony >0, czerwony <0)
            slope_val = row.SMA200_Slope
            item_slope = QTableWidgetItem(f"{slope_val:.2f}%")
            if slope_val > 0:
                item_slope.setBackground(QBrush(QColor(200, 255, 200)))
                item_slope.setForeground(QBrush(QColor(0, 100, 0)))
            elif slope_val < 0:
                item_slope.setBackground(QBrush(QColor(255, 200, 200)))
                item_slope.setForeground(QBrush(QColor(100, 0, 0)))
            self.tabela.setItem(r, 5, item_slope)

            # RS Slope (zielony >0, czerwony <0)
            slope_rs = row.RS_Slope
            item_rs_slope = QTableWidgetItem(f"{slope_rs:.2f}%")
            if slope_rs > 0:
                item_rs_slope.setBackground(QBrush(QColor(200, 255, 200)))
                item_rs_slope.setForeground(QBrush(QColor(0, 100, 0)))
            elif slope_rs < 0:
                item_rs_slope.setBackground(QBrush(QColor(255, 200, 200)))
                item_rs_slope.setForeground(QBrush(QColor(100, 0, 0)))
            self.tabela.setItem(r, 6, item_rs_slope)

            # Distance %
            dist = row.Distance_200
            item_dist = QTableWidgetItem(f"{dist:.1f}%")
            self.tabela.setItem(r, 7, item_dist)

            # ATR %
            item_atr = QTableWidgetItem(f"{row.ATR_Pct:.2f}%")
            self.tabela.setItem(r, 8, item_atr)

            # Apply row background color to remaining cells
            for c in range(1, self.tabela.columnCount()):
                item = self.tabela.item(r, c)
                if item and c not in [5, 6]:  # Skip slope cells (already colored)
                    item.setBackground(QBrush(bg_color))
                    if row.Status == "OUT":
                        item.setForeground(QBrush(fg_color))

    def on_status_changed(self, index):
        """Handle status filter change (NOWE v2.1)"""
        if self.ranking_df is None or self.ranking_df.empty:
            return

        status_filter = self.combo_status.currentText()
        self.wypelnij_tabele(self.ranking_df, filter_status=status_filter)

    def on_dwuklik(self, row, col):
        """Handle double-click to open ticker detail"""
        item = self.tabela.item(row, 1)  # Ticker column
        if item:
            self.tyker_wybrany.emit(item.text())

