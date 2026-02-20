from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHBoxLayout, QPushButton, QHeaderView, QLabel,
    QComboBox, QGroupBox, QTabWidget, QMessageBox, QSplitter,
    QLineEdit, QFileDialog, QMenu, QFrame, QApplication, QProgressBar, QSpinBox,
    QStyledItemDelegate
)
from PySide6.QtCore import Signal, Qt, QTimer, QRect
from PySide6.QtGui import QColor, QBrush, QAction, QKeySequence


class _WrappedHeaderDelegate(QStyledItemDelegate):
    """Delegat rysujący tekst nagłówka z zawijaniem wierszy (obsługa \\n)."""

    def paint(self, painter, option, index):
        painter.save()
        text = index.data(Qt.DisplayRole) or ""
        painter.drawText(
            QRect(option.rect),
            Qt.AlignCenter | Qt.TextWordWrap,
            text
        )
        painter.restore()

    def sizeHint(self, option, index):
        from PySide6.QtCore import QSize
        text = index.data(Qt.DisplayRole) or ""
        lines = text.count("\n") + 1
        fm = option.fontMetrics
        return QSize(fm.horizontalAdvance("MMMM"), fm.height() * lines + 8)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from datetime import datetime
from dane.repozytorium import RepozytoriumDanych
from analiza.ranking import RankingEngine
from analiza.wskazniki import SilnikWskaznikow
from konfiguracja import Konfiguracja

class SkanerWidok(QWidget):
    tyker_wybrany = Signal(str)

    # ── Mapowanie kolumn tabeli ────────────────────────────────────────────
    # Indeks → (nazwa_df, nagłówek_wyświetlany)
    # Kolumna 12 (Uwagi) jest specjalna — SpinBox, nie QTableWidgetItem
    KOLUMNY = [
        (None,            "Status"),          # 0  — tylko tekst, brak kolumny df
        ('Tyker',         "Tyker"),            # 1
        ('ChecklistScore',"Score\n(0-10)"),   # 2  — zawijany nagłówek
        ('Tier',          "Tier"),             # 3
        ('Zamkniecie',    "Price"),            # 4
        ('SMA200_Slope',  "SMA200\nSlope %"), # 5  — zawijany
        ('RS_Slope',      "RS\nSlope %"),     # 6  — zawijany
        ('Distance_200',  "Dist\nSMA200 %"), # 7  — zawijany
        ('ATR_Pct',       "ATR %"),           # 8
        ('Momentum_3M',   "Mom\n3M %"),       # 9  — NOWE, zawijany
        ('Momentum_6M',   "Mom\n6M %"),       # 10 — NOWE, zawijany
        ('RS_Ratio',      "RS\nRatio"),       # 11 — NOWE, zawijany
        (None,            "Uwagi\n(0-9)"),    # 12 — SpinBox, zawijany
    ]

    def __init__(self):
        super().__init__()
        self.repo = RepozytoriumDanych()
        self.ranking_df = None
        self.full_ranking_df = None

        # Search and sort state
        self.search_text = ""
        self.sort_column = None
        self.sort_ascending = True

        # Notatki skanera: {tyker: priorytet (0-9)}
        self._notatki: dict = {}

        # Chart components (initialized in inicjalizuj_ui)
        self.rysunek = None
        self.plotno = None
        self.lbl_detale = None

        self._zaladuj_notatki()
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

        # NEW: Search box
        uklad_btn.addWidget(QLabel("  |  Search:"))
        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("Filter ticker/values...")
        self.input_search.setMaximumWidth(180)
        self.input_search.setClearButtonEnabled(True)
        self.input_search.textChanged.connect(self.on_search_changed)
        uklad_btn.addWidget(self.input_search)

        # Filter by Status
        uklad_btn.addWidget(QLabel("Status:"))
        self.combo_status = QComboBox()
        self.combo_status.addItems(["All", "TRADEABLE", "SETUP", "OUT"])
        self.combo_status.currentIndexChanged.connect(self.on_status_changed)
        uklad_btn.addWidget(self.combo_status)

        # NEW: Copy and Export buttons
        uklad_btn.addWidget(QLabel("|"))
        btn_copy = QPushButton("Copy")
        btn_copy.setToolTip("Copy selected rows (Ctrl+C)")
        btn_copy.clicked.connect(self.copy_selected_rows)
        uklad_btn.addWidget(btn_copy)

        btn_export = QPushButton("Export CSV")
        btn_export.setToolTip("Export table to CSV file")
        btn_export.clicked.connect(self.export_to_csv)
        uklad_btn.addWidget(btn_export)

        uklad_btn.addStretch()
        scanner_layout.addLayout(uklad_btn)

        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(16)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setVisible(False)
        scanner_layout.addWidget(self.progress_bar)

        self.lbl_progress = QLabel("")
        self.lbl_progress.setStyleSheet("color: #666; font-size: 11px; padding: 1px 0px;")
        self.lbl_progress.setVisible(False)
        scanner_layout.addWidget(self.lbl_progress)

        # Table
        self.tabela = QTableWidget()
        self.tabela.setColumnCount(len(self.KOLUMNY))
        self.tabela.setHorizontalHeaderLabels([h for _, h in self.KOLUMNY])

        # Nagłówki wieloliniowe — delegat rysujący tekst z \n
        hdr = self.tabela.horizontalHeader()
        hdr.setDefaultAlignment(Qt.AlignCenter)
        hdr.setMinimumSectionSize(44)
        hdr.setDefaultSectionSize(62)          # domyślna szerokość kolumny
        hdr.setMinimumHeight(36)               # 2 linie tekstu mieszczą się
        self._header_delegate = _WrappedHeaderDelegate(self.tabela)
        hdr.setItemDelegate(self._header_delegate)

        # Większość kolumn — ResizeToContents; wyjątki poniżej
        hdr.setSectionResizeMode(QHeaderView.ResizeToContents)

        # Kolumna 12 (Uwagi) — stała szerokość, żeby SpinBox się zmieścił
        hdr.setSectionResizeMode(12, QHeaderView.Fixed)
        self.tabela.setColumnWidth(12, 58)

        self.tabela.cellDoubleClicked.connect(self.on_dwuklik)
        # cellClicked zastąpiony przez currentRowChanged — obsługuje klik i strzałki
        self.tabela.selectionModel().currentRowChanged.connect(self.on_row_changed)

        self.tabela.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela.setSelectionMode(QTableWidget.ExtendedSelection)

        hdr.sectionClicked.connect(self.on_header_clicked)

        self.tabela.installEventFilter(self)
        self.tabela.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tabela.customContextMenuRequested.connect(self.show_context_menu)

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
    <td>Volatility as % of price. Example: 2.5% = moderate volatility, good for tight stops. Must be &lt;4.0% to pass condition.</td>
</tr>

<tr>
    <td><b>Mom 3M %</b></td>
    <td class='good'>&gt;+5%</td>
    <td class='neutral'>0% to +5%</td>
    <td class='bad'>Negative</td>
    <td>3-month price return (63 days). Green = positive momentum. One of the 10 checklist conditions.</td>
</tr>

<tr>
    <td><b>Mom 6M %</b></td>
    <td class='good'>&gt;+10%</td>
    <td class='neutral'>0% to +10%</td>
    <td class='bad'>Negative</td>
    <td>6-month price return (126 days). Confirms longer-term trend. One of the 10 checklist conditions.</td>
</tr>

<tr>
    <td><b>RS Ratio</b></td>
    <td class='good'>&gt;1.00</td>
    <td class='neutral'>~1.00</td>
    <td class='bad'>&lt;1.00</td>
    <td>Price / SPY price. &gt;1.0 = outperforming market. Green = stronger than SPY. One of the 10 checklist conditions.</td>
</tr>

<tr>
    <td><b>Uwagi (0-9)</b></td>
    <td class='good'>7-9 priority</td>
    <td class='neutral'>4-6</td>
    <td class='bad'>0 = no priority</td>
    <td>Your personal priority score. 0=lowest, 9=highest. Click arrows or type to set. Saved to database. Click column header to sort.</td>
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
        
    # ── Notatki / priorytety ────────────────────────────────────────────────

    def _zaladuj_notatki(self):
        """Wczytaj priorytety z bazy do słownika _notatki."""
        try:
            dane = self.repo.pobierz_notatki_skanera()
            self._notatki = {t: v['priorytet'] for t, v in dane.items()}
        except Exception:
            self._notatki = {}

    def _zapisz_notatke(self, tyker: str, wartosc: int):
        """Zapisz zmianę priorytetu do bazy i do lokalnego cache."""
        self._notatki[tyker] = wartosc
        try:
            self.repo.zapisz_notatke_skanera(tyker, wartosc)
        except Exception as e:
            print(f"Błąd zapisu notatki dla {tyker}: {e}")

    def _wstaw_spinbox(self, row: int, tyker: str):
        """Utwórz i wstaw QSpinBox (0-9) do kolumny 12 w podanym wierszu."""
        sb = QSpinBox()
        sb.setRange(0, 9)
        sb.setValue(self._notatki.get(tyker, 0))
        sb.setAlignment(Qt.AlignCenter)
        sb.setStyleSheet(
            "QSpinBox { border: 1px solid #bbb; border-radius: 3px; "
            "background: white; font-weight: bold; font-size: 12px; }"
            "QSpinBox::up-button { width: 14px; } "
            "QSpinBox::down-button { width: 14px; }"
        )
        # Zapisz zmianę natychmiast (lambda + default arg unika closure-trap)
        sb.valueChanged.connect(lambda v, t=tyker: self._zapisz_notatke(t, v))
        self.tabela.setCellWidget(row, 12, sb)

    def uruchom_skaner(self):
        """Run scanner with v2.0 RankingEngine"""
        tykery = self.repo.pobierz_wszystkie_tykery()
        total = len(tykery)

        # Show progress bar
        self.progress_bar.setMaximum(total + 1)  # +1 for ranking step
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.lbl_progress.setVisible(True)
        self.lbl_progress.setText("Ładowanie benchmarku...")
        QApplication.processEvents()

        benchmark = Konfiguracja.TYKER_BENCHMARK
        df_bench = self.repo.pobierz_swiece_df(benchmark)

        # Validate benchmark loading
        if df_bench is None or df_bench.empty:
            print(f"⚠️ WARNING: Benchmark {benchmark} failed to load or is empty!")
            print("RS metrics will use default values (RS_Ratio=1.0, RS_Slope=0.0)")

        dane_map = {}
        for i, t in enumerate(tykery):
            self.progress_bar.setValue(i + 1)
            self.lbl_progress.setText(f"Ładowanie danych ({i+1}/{total}): {t}")
            QApplication.processEvents()
            df = self.repo.pobierz_swiece_df(t)
            if not df.empty:
                dane_map[t] = df

        # Ranking step
        self.progress_bar.setValue(total)
        self.lbl_progress.setText(f"Obliczanie rankingu dla {len(dane_map)} spółek...")
        QApplication.processEvents()

        # Use new RankingEngine v2.0
        ranking_df = RankingEngine.generuj_ranking(dane_map, df_bench)

        # Hide progress bar
        self.progress_bar.setValue(total + 1)
        self.progress_bar.setVisible(False)
        self.lbl_progress.setVisible(False)

        self.full_ranking_df = ranking_df  # NEW: Store unfiltered
        self.ranking_df = ranking_df  # Store for filtering
        self.combo_status.setCurrentIndex(0)  # Reset filter to "All"
        self.input_search.clear()  # NEW: Reset search
        self.sort_column = None  # NEW: Reset sort
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
            # Usuń też notatkę i wyczyść cache
            self.repo.usun_notatke_skanera(ticker)
            self._notatki.pop(ticker, None)

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

    def on_header_clicked(self, logical_index):
        """Handle column header click for sorting"""
        if self.ranking_df is None or self.ranking_df.empty:
            return

        # Map column index to DataFrame column name
        # Kolumna 12 (Uwagi) sortuje wg słownika _notatki — obsługa niżej
        column_map = {
            0: 'Status',
            1: 'Tyker',
            2: 'ChecklistScore',
            3: 'Tier',
            4: 'Zamkniecie',
            5: 'SMA200_Slope',
            6: 'RS_Slope',
            7: 'Distance_200',
            8: 'ATR_Pct',
            9: 'Momentum_3M',
            10: 'Momentum_6M',
            11: 'RS_Ratio',
            12: '_Uwagi',   # wirtualna kolumna — obsłużona w apply_sort
        }

        df_column = column_map.get(logical_index)
        if not df_column:
            return

        # Toggle sort direction if same column clicked
        if self.sort_column == logical_index:
            self.sort_ascending = not self.sort_ascending
        else:
            self.sort_column = logical_index
            self.sort_ascending = True

        # Apply sort based on column type
        sorted_df = self.apply_sort_to_dataframe(self.ranking_df, df_column, self.sort_ascending)

        # Update table display (preserve status filter)
        current_filter = self.combo_status.currentText()
        if current_filter == "All":
            self.wypelnij_tabele(sorted_df)
        else:
            self.wypelnij_tabele(sorted_df, filter_status=current_filter)

        # Update header to show sort indicator
        self.update_header_indicators()

    def apply_sort_to_dataframe(self, df, column_name, ascending):
        """Apply sorting with special handling for Status, Tier and Uwagi columns"""
        if df.empty:
            return df

        # Special handling for Status (TRADEABLE > SETUP > OUT priority)
        if column_name == 'Status':
            status_order = {"TRADEABLE": 0, "SETUP": 1, "OUT": 2}
            sorted_df = df.copy()
            sorted_df['_status_order'] = sorted_df['Status'].map(status_order).fillna(3)
            sorted_df = sorted_df.sort_values(by='_status_order', ascending=ascending)
            return sorted_df.drop(columns=['_status_order'])

        # Special handling for Tier (A > B > C > D)
        elif column_name == 'Tier':
            tier_order = {"A": 0, "B": 1, "C": 2, "D": 3}
            sorted_df = df.copy()
            sorted_df['_tier_order'] = sorted_df['Tier'].map(tier_order).fillna(4)
            sorted_df = sorted_df.sort_values(by='_tier_order', ascending=ascending)
            return sorted_df.drop(columns=['_tier_order'])

        # Wirtualna kolumna Uwagi — wartości z _notatki
        elif column_name == '_Uwagi':
            sorted_df = df.copy()
            col = 'Tyker' if 'Tyker' in sorted_df.columns else 'Ticker'
            sorted_df['_uwagi_order'] = sorted_df[col].map(
                lambda t: self._notatki.get(t, 0)
            )
            sorted_df = sorted_df.sort_values(by='_uwagi_order', ascending=ascending)
            return sorted_df.drop(columns=['_uwagi_order'])

        # Standard numeric/text sorting
        else:
            return df.sort_values(by=column_name, ascending=ascending)

    def update_header_indicators(self):
        """Update column headers to show sort direction"""
        for i, (_, header) in enumerate(self.KOLUMNY):
            if i == self.sort_column:
                arrow = " ▲" if self.sort_ascending else " ▼"
                item = QTableWidgetItem(header + arrow)
            else:
                item = QTableWidgetItem(header)
            item.setTextAlignment(Qt.AlignCenter)
            self.tabela.setHorizontalHeaderItem(i, item)

    def receive_market_screener_results(self, df, filter_config):
        """
        Receive filtered results from Market Screener and display in scanner table

        Args:
            df: Filtered DataFrame from Market Screener (pandas DataFrame)
            filter_config: Filter configuration used (FilterConfig object)
        """
        if df.empty:
            # Empty results - clear table and show message in tip label
            self.tabela.setRowCount(0)
            self.ranking_df = None
            # Find the tip label to update it
            for i in range(self.tabs.widget(0).layout().count()):
                widget = self.tabs.widget(0).layout().itemAt(i).widget()
                if isinstance(widget, QLabel) and "Tip" in widget.text():
                    widget.setText(f"💡 <b>Info:</b> No stocks match filter: {filter_config.name}")
                    break
            return

        # Store the DataFrame for filtering
        self.full_ranking_df = df  # NEW: Store unfiltered
        self.ranking_df = df

        # Update tip label to show filter info
        for i in range(self.tabs.widget(0).layout().count()):
            widget = self.tabs.widget(0).layout().itemAt(i).widget()
            if isinstance(widget, QLabel) and "💡" in widget.text():
                widget.setText(
                    f"💡 <b>Market Screener:</b> Showing {len(df)} stocks from filter: {filter_config.name}"
                )
                break

        # Reset status filter to "All"
        self.combo_status.setCurrentIndex(0)
        self.input_search.clear()  # NEW: Reset search
        self.sort_column = None  # NEW: Reset sort

        # Populate table with Market Screener results
        self.wypelnij_tabele(df)

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

        # Show indeterminate progress while loading chart data
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.setVisible(True)
        self.lbl_progress.setText(f"Ładowanie wykresu: {ticker}...")
        self.lbl_progress.setVisible(True)
        QApplication.processEvents()

        # Load data
        df = self.repo.pobierz_swiece_df(ticker)
        bench_df = self.repo.pobierz_swiece_df(Konfiguracja.TYKER_BENCHMARK)

        if df.empty:
            self.progress_bar.setVisible(False)
            self.lbl_progress.setVisible(False)
            self.lbl_detale.setText(f"<b>No data available for {ticker}</b>")
            self.rysunek.clear()
            self.plotno.draw()
            return

        # Calculate indicators
        df = SilnikWskaznikow.oblicz_wskazniki(df, bench_df)

        self.progress_bar.setRange(0, 1)  # Back to determinate
        self.progress_bar.setValue(1)
        self.progress_bar.setVisible(False)
        self.lbl_progress.setVisible(False)

        # Update chart and metrics
        self.rysuj_wykres(df, ticker)
        self.aktualizuj_panel(df, ticker)

    def on_row_changed(self, current, previous):
        """Handle row change (mouse click OR keyboard arrows) - update chart and metrics.
        currentRowChanged fires only when the row actually changes, so no double-load risk."""
        if not current.isValid():
            return
        self.on_pojedyncze_klikniecie(current.row(), current.column())

    def wypelnij_tabele(self, df, filter_status=None):
        """Populate table with ranking data (v2.2: 13 kolumn + SpinBox Uwagi)"""
        self.tabela.setRowCount(0)
        if df.empty:
            return

        if filter_status and filter_status != "All":
            df = df[df['Status'] == filter_status]
        if df.empty:
            return

        self.tabela.setRowCount(len(df))

        for r, row in enumerate(df.itertuples()):

            # ── kolory tła zależne od statusu ────────────────
            if row.Status == "TRADEABLE":
                bg_color = QColor(200, 255, 200)
                fg_color = QColor(0, 100, 0)
            elif row.Status == "SETUP":
                bg_color = QColor(255, 255, 200)
                fg_color = QColor(100, 100, 0)
            else:  # OUT
                bg_color = QColor(240, 240, 240)
                fg_color = QColor(150, 150, 150)

            def item(tekst, bg=bg_color, fg=fg_color, center=True):
                it = QTableWidgetItem(str(tekst))
                it.setBackground(QBrush(bg))
                it.setForeground(QBrush(fg))
                if center:
                    it.setTextAlignment(Qt.AlignCenter)
                return it

            def slope_item(val, fmt="{:.2f}%"):
                if val > 0:
                    b, f = QColor(200, 255, 200), QColor(0, 100, 0)
                elif val < 0:
                    b, f = QColor(255, 200, 200), QColor(100, 0, 0)
                else:
                    b, f = bg_color, fg_color
                it = QTableWidgetItem(fmt.format(val))
                it.setBackground(QBrush(b))
                it.setForeground(QBrush(f))
                it.setTextAlignment(Qt.AlignCenter)
                return it

            # 0 — Status (skrót dla oszczędności miejsca)
            status_short = {"TRADEABLE": "TRADE", "SETUP": "SETUP", "OUT": "OUT"}.get(row.Status, row.Status)
            self.tabela.setItem(r, 0, item(status_short))

            # 1 — Tyker
            self.tabela.setItem(r, 1, item(str(row.Tyker)))

            # 2 — ChecklistScore  (kolor wg wartości)
            score = row.ChecklistScore
            if score >= 8:
                sc_bg, sc_fg = QColor(200, 255, 200), QColor(0, 100, 0)
            elif score >= 6:
                sc_bg, sc_fg = QColor(255, 255, 200), QColor(100, 100, 0)
            elif score >= 4:
                sc_bg, sc_fg = QColor(255, 230, 200), QColor(150, 100, 0)
            else:
                sc_bg, sc_fg = QColor(255, 200, 200), QColor(100, 0, 0)
            self.tabela.setItem(r, 2, item(f"{score}/10", sc_bg, sc_fg))

            # 3 — Tier  (kolor wg wartości)
            tier_colors = {
                'A': (QColor(200, 255, 200), QColor(0, 100, 0)),
                'B': (QColor(255, 255, 200), QColor(100, 100, 0)),
                'C': (QColor(255, 230, 200), QColor(150, 100, 0)),
                'D': (QColor(255, 200, 200), QColor(100, 0, 0)),
            }
            tb, tf = tier_colors.get(row.Tier, (bg_color, fg_color))
            self.tabela.setItem(r, 3, item(str(row.Tier), tb, tf))

            # 4 — Price
            self.tabela.setItem(r, 4, item(f"${row.Zamkniecie:.2f}"))

            # 5 — SMA200 Slope
            self.tabela.setItem(r, 5, slope_item(row.SMA200_Slope))

            # 6 — RS Slope
            self.tabela.setItem(r, 6, slope_item(row.RS_Slope))

            # 7 — Distance SMA200 %  (zielony blisko 0, pomarańczowy daleko)
            dist = row.Distance_200
            if -10 <= dist <= 20:
                d_bg, d_fg = bg_color, fg_color
            else:
                d_bg, d_fg = QColor(255, 230, 200), QColor(150, 100, 0)
            self.tabela.setItem(r, 7, item(f"{dist:.1f}%", d_bg, d_fg))

            # 8 — ATR %
            self.tabela.setItem(r, 8, item(f"{row.ATR_Pct:.2f}%"))

            # 9 — Momentum 3M  (NOWE)
            mom3 = getattr(row, 'Momentum_3M', 0) or 0
            self.tabela.setItem(r, 9, slope_item(mom3 * 100, "{:.1f}%"))

            # 10 — Momentum 6M  (NOWE)
            mom6 = getattr(row, 'Momentum_6M', 0) or 0
            self.tabela.setItem(r, 10, slope_item(mom6 * 100, "{:.1f}%"))

            # 11 — RS Ratio  (NOWE)
            rs_r = getattr(row, 'RS_Ratio', 1.0) or 1.0
            rs_bg = QColor(200, 255, 200) if rs_r >= 1.0 else QColor(255, 200, 200)
            rs_fg = QColor(0, 100, 0)     if rs_r >= 1.0 else QColor(100, 0, 0)
            self.tabela.setItem(r, 11, item(f"{rs_r:.3f}", rs_bg, rs_fg))

            # 12 — Uwagi SpinBox  (NOWE, nie QTableWidgetItem)
            self._wstaw_spinbox(r, str(row.Tyker))

    def on_search_changed(self, text):
        """Handle search text change - filter table in real-time"""
        self.search_text = text.strip().upper()

        if self.full_ranking_df is None or self.full_ranking_df.empty:
            return

        # Start with full unfiltered data
        filtered_df = self.full_ranking_df.copy()

        # Apply search filter (if not empty)
        if self.search_text:
            # Search across Tyker and numeric values
            mask = (
                filtered_df['Tyker'].str.upper().str.contains(self.search_text, regex=False) |
                filtered_df['Zamkniecie'].astype(str).str.contains(self.search_text, regex=False) |
                filtered_df['SMA200_Slope'].astype(str).str.contains(self.search_text, regex=False) |
                filtered_df['RS_Slope'].astype(str).str.contains(self.search_text, regex=False)
            )
            filtered_df = filtered_df[mask]

        # Apply status filter (if not "All")
        current_status = self.combo_status.currentText()
        if current_status != "All":
            filtered_df = filtered_df[filtered_df['Status'] == current_status]

        # Apply current sort (if active)
        if self.sort_column is not None:
            column_map = {
                0: 'Status', 1: 'Tyker', 2: 'ChecklistScore', 3: 'Tier',
                4: 'Zamkniecie', 5: 'SMA200_Slope', 6: 'RS_Slope',
                7: 'Distance_200', 8: 'ATR_Pct',
                9: 'Momentum_3M', 10: 'Momentum_6M', 11: 'RS_Ratio', 12: '_Uwagi',
            }
            df_column = column_map.get(self.sort_column)
            if df_column:
                filtered_df = self.apply_sort_to_dataframe(filtered_df, df_column, self.sort_ascending)

        # Update table
        self.ranking_df = filtered_df
        self.wypelnij_tabele(filtered_df)

    def on_status_changed(self, index):
        """Handle status filter change - works with search filter"""
        if self.full_ranking_df is None or self.full_ranking_df.empty:
            return

        # Start with full data
        filtered_df = self.full_ranking_df.copy()

        # Apply search filter (if active)
        if self.search_text:
            mask = (
                filtered_df['Tyker'].str.upper().str.contains(self.search_text, regex=False) |
                filtered_df['Zamkniecie'].astype(str).str.contains(self.search_text, regex=False)
            )
            filtered_df = filtered_df[mask]

        # Apply status filter
        status_filter = self.combo_status.currentText()
        if status_filter != "All":
            filtered_df = filtered_df[filtered_df['Status'] == status_filter]

        # Apply current sort
        if self.sort_column is not None:
            column_map = {
                0: 'Status', 1: 'Tyker', 2: 'ChecklistScore', 3: 'Tier',
                4: 'Zamkniecie', 5: 'SMA200_Slope', 6: 'RS_Slope',
                7: 'Distance_200', 8: 'ATR_Pct',
                9: 'Momentum_3M', 10: 'Momentum_6M', 11: 'RS_Ratio', 12: '_Uwagi',
            }
            df_column = column_map.get(self.sort_column)
            if df_column:
                filtered_df = self.apply_sort_to_dataframe(filtered_df, df_column, self.sort_ascending)

        self.ranking_df = filtered_df
        self.wypelnij_tabele(filtered_df)

    def on_dwuklik(self, row, col):
        """Handle double-click to open ticker detail"""
        item = self.tabela.item(row, 1)  # Ticker column
        if item:
            self.tyker_wybrany.emit(item.text())

    def eventFilter(self, source, event):
        """Intercept Ctrl+C keyboard shortcut"""
        if (event.type() == event.Type.KeyPress and
            source is self.tabela and
            event.matches(QKeySequence.Copy)):
            self.copy_selected_rows()
            return True
        return super().eventFilter(source, event)

    def show_context_menu(self, position):
        """Show right-click context menu"""
        menu = QMenu()

        copy_action = QAction("Copy Selected Rows", self)
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(self.copy_selected_rows)
        menu.addAction(copy_action)

        menu.exec_(self.tabela.viewport().mapToGlobal(position))

    def copy_selected_rows(self):
        """Copy selected table rows to clipboard (tab-separated format)"""
        selected_ranges = self.tabela.selectedRanges()

        if not selected_ranges:
            QMessageBox.information(self, "No Selection", "Please select rows to copy.")
            return

        # Build tab-separated text
        lines = []

        # Add header row
        headers = []
        for col in range(self.tabela.columnCount()):
            headers.append(self.tabela.horizontalHeaderItem(col).text())
        lines.append("\t".join(headers))

        # Collect unique selected rows
        selected_rows = set()
        for selected_range in selected_ranges:
            for row in range(selected_range.topRow(), selected_range.bottomRow() + 1):
                selected_rows.add(row)

        # Sort rows to maintain order
        for row in sorted(selected_rows):
            row_data = []
            for col in range(self.tabela.columnCount()):
                item = self.tabela.item(row, col)
                row_data.append(item.text() if item else "")
            lines.append("\t".join(row_data))

        # Copy to clipboard
        clipboard = QApplication.clipboard()
        clipboard.setText("\n".join(lines))

        # Show confirmation in tip label
        for i in range(self.tabs.widget(0).layout().count()):
            widget = self.tabs.widget(0).layout().itemAt(i).widget()
            if isinstance(widget, QLabel) and "💡" in widget.text():
                original_text = widget.text()
                widget.setText(f"💡 Copied {len(selected_rows)} rows to clipboard")
                # Restore original text after 3 seconds
                QTimer.singleShot(3000, lambda: widget.setText(original_text))
                break

    def export_to_csv(self):
        """Export current table data to CSV file"""
        if self.ranking_df is None or self.ranking_df.empty:
            QMessageBox.information(self, "No Data", "No data to export. Run scanner first.")
            return

        # Generate default filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"scanner_results_{timestamp}.csv"

        # Show file save dialog
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Scanner Results to CSV",
            default_filename,
            "CSV Files (*.csv);;All Files (*)"
        )

        if not file_path:
            return  # User cancelled

        try:
            # Prepare DataFrame for export
            export_df = self.ranking_df.copy()

            # Dodaj kolumnę Uwagi z cache
            col = 'Tyker' if 'Tyker' in export_df.columns else 'Ticker'
            export_df['Uwagi'] = export_df[col].map(lambda t: self._notatki.get(t, 0))

            # Rename columns to match table headers
            export_df = export_df.rename(columns={
                'Tyker': 'Ticker',
                'Zamkniecie': 'Price',
                'Distance_200': 'Distance_SMA200_pct',
                'ATR_Pct': 'ATR_pct',
                'Momentum_3M': 'Mom3M_pct',
                'Momentum_6M': 'Mom6M_pct',
            })

            # Select and reorder columns to match table
            available = export_df.columns.tolist()
            preferred = [
                'Status', 'Ticker', 'ChecklistScore', 'Tier', 'Price',
                'SMA200_Slope', 'RS_Slope', 'Distance_SMA200_pct', 'ATR_pct',
                'Mom3M_pct', 'Mom6M_pct', 'RS_Ratio', 'Uwagi',
            ]
            columns_to_export = [c for c in preferred if c in available]
            export_df = export_df[columns_to_export]

            # Export to CSV
            export_df.to_csv(file_path, index=False, encoding='utf-8')

            QMessageBox.information(
                self,
                "Export Success",
                f"Exported {len(export_df)} rows to:\n{file_path}"
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Failed",
                f"Failed to export CSV:\n{str(e)}"
            )

