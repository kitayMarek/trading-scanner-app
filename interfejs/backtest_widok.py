"""
BacktestWidok — zakładka backtestingu z Backtraderem.

Układ UI (góra → dół):
  [QGroupBox: Konfiguracja]
    Rząd 1: Ticker | "Użyj ze Skanera" | Strategia | Run | Cancel
    Rząd 2: Kapitał | Prowizja | SMA Fast | SMA Slow | ATR | Mult | Momentum | RS checkbox
    [QGroupBox checkable: Optymalizacja grid-search]
      Fast range | Slow range | Run Opt

  [QProgressBar + QLabel status]

  [QTabWidget: "Wyniki Backtestу" | "Wyniki Optymalizacji"]
    Tab A: QSplitter(Horizontal)
              lewa: metryki HTML (QLabel)
              prawa: equity curve (FigureCanvas)
           QTableWidget: lista transakcji
    Tab B: QTableWidget: wyniki optymalizacji + przycisk "Zastosuj"
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QDoubleSpinBox, QSpinBox, QGroupBox, QSplitter,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
    QMessageBox, QCheckBox, QTabWidget, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.ticker as mticker
import matplotlib.dates as mdates
import pandas as pd

from dane.repozytorium import RepozytoriumDanych
from konfiguracja import Konfiguracja
from backtesting.silnik_backtestingu import DOSTEPNE_STRATEGIE
from backtesting.watek_backtestingu import WatekBacktestingu, WatekOptymalizacji


class BacktestWidok(QWidget):
    """Główny widget zakładki Backtesting."""

    def __init__(self):
        super().__init__()
        self.repo         = RepozytoriumDanych()
        self.watek        = None    # WatekBacktestingu
        self.watek_opt    = None    # WatekOptymalizacji
        self.ostatni_wynik = None   # ostatni słownik wyników
        self._inicjalizuj_ui()

    # =========================================================================
    # Publiczne API — wywoływane z GlowneOkno
    # =========================================================================

    def ustaw_tyker(self, tyker: str):
        """Wypełnij pole tykera (np. z podwójnego kliknięcia w Skaner)."""
        self.input_tyker.setText(tyker.upper())

    # =========================================================================
    # Budowa UI
    # =========================================================================

    def _inicjalizuj_ui(self):
        root = QVBoxLayout()

        # ── Panel konfiguracji ─────────────────────────────────────────────
        panel = QGroupBox("Konfiguracja Backtestу")
        panel_lay = QVBoxLayout()

        # Rząd 1: ticker + strategia + przyciski
        r1 = QHBoxLayout()
        r1.addWidget(QLabel("Ticker:"))
        self.input_tyker = QLineEdit()
        self.input_tyker.setPlaceholderText("np. AAPL")
        self.input_tyker.setMinimumWidth(120)
        self.input_tyker.setMaximumWidth(180)
        r1.addWidget(self.input_tyker)

        self.btn_ze_skanera = QPushButton("⟵ Użyj ze Skanera")
        self.btn_ze_skanera.setToolTip(
            "Kopiuje zaznaczony tyker z zakładki Skaner Rynku"
        )
        r1.addWidget(self.btn_ze_skanera)

        r1.addWidget(QLabel("  Strategia:"))
        self.combo_strategia = QComboBox()
        for name in DOSTEPNE_STRATEGIE:
            self.combo_strategia.addItem(name)
        self.combo_strategia.setMinimumWidth(240)
        r1.addWidget(self.combo_strategia)

        self.btn_uruchom = QPushButton("▶  Uruchom Backtest")
        self.btn_uruchom.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold; padding: 6px 16px;"
        )
        self.btn_uruchom.clicked.connect(self._uruchom_backtest)
        r1.addWidget(self.btn_uruchom)

        self.btn_anuluj = QPushButton("✖ Anuluj")
        self.btn_anuluj.setEnabled(False)
        self.btn_anuluj.setStyleSheet("padding: 6px 10px;")
        self.btn_anuluj.clicked.connect(self._anuluj)
        r1.addWidget(self.btn_anuluj)
        r1.addStretch()
        panel_lay.addLayout(r1)

        # Rząd 2: parametry liczbowe
        r2 = QHBoxLayout()

        r2.addWidget(QLabel("Kapitał:"))
        self.spin_kapital = QDoubleSpinBox()
        self.spin_kapital.setRange(1_000, 10_000_000)
        self.spin_kapital.setSingleStep(10_000)
        self.spin_kapital.setValue(Konfiguracja.BACKTEST_KAPITAL)
        self.spin_kapital.setPrefix("$")
        self.spin_kapital.setGroupSeparatorShown(True)
        self.spin_kapital.setMaximumWidth(130)
        r2.addWidget(self.spin_kapital)

        r2.addWidget(QLabel("  Prowizja %:"))
        self.spin_prowizja = QDoubleSpinBox()
        self.spin_prowizja.setRange(0.0, 2.0)
        self.spin_prowizja.setSingleStep(0.05)
        self.spin_prowizja.setValue(Konfiguracja.BACKTEST_PROWIZJA * 100)
        self.spin_prowizja.setSuffix(" %")
        self.spin_prowizja.setDecimals(3)
        self.spin_prowizja.setMaximumWidth(90)
        r2.addWidget(self.spin_prowizja)

        r2.addWidget(QLabel("  SMA Szybka:"))
        self.spin_sma_fast = QSpinBox()
        self.spin_sma_fast.setRange(5, 200)
        self.spin_sma_fast.setValue(Konfiguracja.SMA_SZYBKA)
        self.spin_sma_fast.setMaximumWidth(68)
        r2.addWidget(self.spin_sma_fast)

        r2.addWidget(QLabel("  SMA Wolna:"))
        self.spin_sma_slow = QSpinBox()
        self.spin_sma_slow.setRange(50, 500)
        self.spin_sma_slow.setValue(Konfiguracja.SMA_WOLNA)
        self.spin_sma_slow.setMaximumWidth(68)
        r2.addWidget(self.spin_sma_slow)

        r2.addWidget(QLabel("  ATR:"))
        self.spin_atr = QSpinBox()
        self.spin_atr.setRange(5, 50)
        self.spin_atr.setValue(Konfiguracja.OKRES_ATR)
        self.spin_atr.setMaximumWidth(58)
        r2.addWidget(self.spin_atr)

        r2.addWidget(QLabel("  Mult:"))
        self.spin_atr_mult = QDoubleSpinBox()
        self.spin_atr_mult.setRange(0.5, 5.0)
        self.spin_atr_mult.setSingleStep(0.5)
        self.spin_atr_mult.setValue(Konfiguracja.MULTIPLE_ATR_FOR_STOP)
        self.spin_atr_mult.setMaximumWidth(64)
        r2.addWidget(self.spin_atr_mult)

        r2.addWidget(QLabel("  Momentum:"))
        self.spin_momentum = QSpinBox()
        self.spin_momentum.setRange(10, 252)
        self.spin_momentum.setValue(Konfiguracja.MOMENTUM_KROTKIE)
        self.spin_momentum.setMaximumWidth(64)
        r2.addWidget(self.spin_momentum)

        self.chk_rs = QCheckBox("Filtr RS")
        self.chk_rs.setChecked(True)
        self.chk_rs.setToolTip(
            "Wymagaj RS_Ratio > RS_SMA50 przy wejściu (odzwierciedla logikę skanera)"
        )
        r2.addWidget(self.chk_rs)
        r2.addStretch()
        panel_lay.addLayout(r2)

        # Rząd 3: optymalizacja (zwijana)
        self.grp_opt = QGroupBox("Optymalizacja Parametrów (Grid Search)")
        self.grp_opt.setCheckable(True)
        self.grp_opt.setChecked(False)
        opt_lay = QHBoxLayout()

        opt_lay.addWidget(QLabel("SMA Fast od:"))
        self.spin_of_min = QSpinBox(); self.spin_of_min.setRange(5, 100);   self.spin_of_min.setValue(20);  self.spin_of_min.setMaximumWidth(60)
        opt_lay.addWidget(self.spin_of_min)
        opt_lay.addWidget(QLabel("do:"))
        self.spin_of_max = QSpinBox(); self.spin_of_max.setRange(5, 200);   self.spin_of_max.setValue(60);  self.spin_of_max.setMaximumWidth(60)
        opt_lay.addWidget(self.spin_of_max)
        opt_lay.addWidget(QLabel("krok:"))
        self.spin_of_step = QSpinBox(); self.spin_of_step.setRange(1, 50);  self.spin_of_step.setValue(10); self.spin_of_step.setMaximumWidth(55)
        opt_lay.addWidget(self.spin_of_step)

        opt_lay.addWidget(QLabel("   SMA Slow od:"))
        self.spin_os_min = QSpinBox(); self.spin_os_min.setRange(50, 400);  self.spin_os_min.setValue(100); self.spin_os_min.setMaximumWidth(68)
        opt_lay.addWidget(self.spin_os_min)
        opt_lay.addWidget(QLabel("do:"))
        self.spin_os_max = QSpinBox(); self.spin_os_max.setRange(50, 500);  self.spin_os_max.setValue(250); self.spin_os_max.setMaximumWidth(68)
        opt_lay.addWidget(self.spin_os_max)
        opt_lay.addWidget(QLabel("krok:"))
        self.spin_os_step = QSpinBox(); self.spin_os_step.setRange(10, 100); self.spin_os_step.setValue(50); self.spin_os_step.setMaximumWidth(60)
        opt_lay.addWidget(self.spin_os_step)

        self.btn_optymalizuj = QPushButton("🔍 Uruchom Optymalizację")
        self.btn_optymalizuj.setStyleSheet(
            "background-color: #2196F3; color: white; padding: 5px 12px;"
        )
        self.btn_optymalizuj.clicked.connect(self._uruchom_optymalizacje)
        opt_lay.addWidget(self.btn_optymalizuj)
        opt_lay.addStretch()
        self.grp_opt.setLayout(opt_lay)
        panel_lay.addWidget(self.grp_opt)

        panel.setLayout(panel_lay)
        root.addWidget(panel)

        # ── Pasek postępu + status ─────────────────────────────────────────
        self.progress = QProgressBar()
        self.progress.setMaximumHeight(14)
        self.progress.setVisible(False)
        root.addWidget(self.progress)

        self.lbl_status = QLabel(
            "Gotowy. Wpisz ticker i kliknij 'Uruchom Backtest'."
        )
        self.lbl_status.setStyleSheet("color: #555; font-size: 11px; padding: 2px 0;")
        root.addWidget(self.lbl_status)

        # ── Zakładki wyników ───────────────────────────────────────────────
        self.tabs_wyniki = QTabWidget()

        # Tab A: wyniki backtestу
        tab_bt = QWidget()
        bt_lay = QVBoxLayout(tab_bt)

        splitter = QSplitter(Qt.Horizontal)

        # Lewo: metryki HTML
        self.lbl_metryki = QLabel("Uruchom backtest, aby zobaczyć wyniki.")
        self.lbl_metryki.setWordWrap(True)
        self.lbl_metryki.setAlignment(Qt.AlignTop)
        self.lbl_metryki.setStyleSheet(
            "padding: 12px; background: #f8f8f8; border-radius: 4px;"
        )
        self.lbl_metryki.setMinimumWidth(230)
        self.lbl_metryki.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        splitter.addWidget(self.lbl_metryki)

        # Prawo: equity curve
        self.fig_eq = Figure(figsize=(8, 4))
        self.canvas_eq = FigureCanvas(self.fig_eq)
        splitter.addWidget(self.canvas_eq)
        splitter.setSizes([260, 740])

        bt_lay.addWidget(splitter, stretch=2)

        # Tabela transakcji
        self.tabela_tr = QTableWidget()
        self.tabela_tr.setColumnCount(5)
        self.tabela_tr.setHorizontalHeaderLabels(
            ['#', 'Data', 'PnL ($)', 'Skumulowany PnL', 'Wynik']
        )
        self.tabela_tr.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabela_tr.setMaximumHeight(170)
        self.tabela_tr.setSelectionBehavior(QTableWidget.SelectRows)
        bt_lay.addWidget(self.tabela_tr, stretch=1)

        self.tabs_wyniki.addTab(tab_bt, "📈 Wyniki Backtestу")

        # Tab B: wyniki optymalizacji
        tab_opt = QWidget()
        opt_res_lay = QVBoxLayout(tab_opt)

        self.tabela_opt = QTableWidget()
        self.tabela_opt.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela_opt.setSelectionMode(QTableWidget.SingleSelection)
        opt_res_lay.addWidget(self.tabela_opt)

        self.btn_zastosuj = QPushButton(
            "✔ Zastosuj zaznaczone parametry i uruchom backtest"
        )
        self.btn_zastosuj.setStyleSheet(
            "background-color: #4CAF50; color: white; padding: 5px 12px;"
        )
        self.btn_zastosuj.clicked.connect(self._zastosuj_i_uruchom)
        opt_res_lay.addWidget(self.btn_zastosuj)

        self.tabs_wyniki.addTab(tab_opt, "🔍 Wyniki Optymalizacji")

        root.addWidget(self.tabs_wyniki, stretch=1)
        self.setLayout(root)

    # =========================================================================
    # Uruchamianie backtestу
    # =========================================================================

    def _pobierz_parametry(self) -> dict:
        """Odczytaj wartości spinboxów do słownika parametrów strategii."""
        return {
            'sma_fast':        self.spin_sma_fast.value(),
            'sma_slow':        self.spin_sma_slow.value(),
            'atr_period':      self.spin_atr.value(),
            'atr_multiplier':  self.spin_atr_mult.value(),
            'momentum_period': self.spin_momentum.value(),
            'use_rs_filter':   self.chk_rs.isChecked(),
        }

    def _uruchom_backtest(self):
        tyker = self.input_tyker.text().strip().upper()
        if not tyker:
            QMessageBox.warning(self, "Brak tykera", "Wpisz ticker spółki.")
            return

        df_ticker = self.repo.pobierz_swiece_df(tyker)
        if df_ticker.empty:
            QMessageBox.warning(
                self, "Brak danych",
                f"Brak danych dla {tyker}.\n"
                "Pobierz dane przez Market Screener lub importer.",
            )
            return

        df_spy = self.repo.pobierz_swiece_df(Konfiguracja.TYKER_BENCHMARK)

        self._ustaw_stan(True)
        self.lbl_status.setText(f"Uruchamianie backtestу dla {tyker}…")

        self.watek = WatekBacktestingu()
        self.watek.df_ticker       = df_ticker
        self.watek.df_spy          = df_spy if not df_spy.empty else None
        self.watek.nazwa_strategii = self.combo_strategia.currentText()
        self.watek.parametry       = self._pobierz_parametry()
        self.watek.kapital         = self.spin_kapital.value()
        self.watek.prowizja        = self.spin_prowizja.value() / 100.0

        self.watek.postep.connect(self._on_postep)
        self.watek.wynik_gotowy.connect(lambda w: self._on_wynik(w, tyker))
        self.watek.blad.connect(self._on_blad)
        self.watek.finished.connect(lambda: self._ustaw_stan(False))
        self.watek.start()

    def _uruchom_optymalizacje(self):
        tyker = self.input_tyker.text().strip().upper()
        if not tyker:
            QMessageBox.warning(self, "Brak tykera", "Wpisz ticker spółki.")
            return

        df_ticker = self.repo.pobierz_swiece_df(tyker)
        if df_ticker.empty:
            QMessageBox.warning(self, "Brak danych", f"Brak danych dla {tyker}.")
            return

        df_spy = self.repo.pobierz_swiece_df(Konfiguracja.TYKER_BENCHMARK)

        # Buduj siatkę parametrów
        fast_vals = list(range(
            self.spin_of_min.value(), self.spin_of_max.value() + 1, self.spin_of_step.value()
        ))
        slow_vals = list(range(
            self.spin_os_min.value(), self.spin_os_max.value() + 1, self.spin_os_step.value()
        ))

        if not fast_vals or not slow_vals:
            QMessageBox.warning(self, "Błąd siatki", "Nieprawidłowy zakres optymalizacji.")
            return

        # Filtruj kombinacje gdzie fast < slow
        siatka = {
            'sma_fast': [v for v in fast_vals if v < min(slow_vals)],
            'sma_slow': slow_vals,
        }
        if not siatka['sma_fast']:
            QMessageBox.warning(
                self, "Błąd siatki",
                "Wszystkie wartości SMA Fast ≥ SMA Slow min.\nPopraw zakresy."
            )
            return

        total_combos = len(siatka['sma_fast']) * len(siatka['sma_slow'])
        self._ustaw_stan(True)
        self.progress.setMaximum(total_combos)
        self.lbl_status.setText(
            f"Optymalizacja {total_combos} kombinacji dla {tyker}…"
        )

        self.watek_opt = WatekOptymalizacji()
        self.watek_opt.df_ticker         = df_ticker
        self.watek_opt.df_spy            = df_spy if not df_spy.empty else None
        self.watek_opt.nazwa_strategii   = self.combo_strategia.currentText()
        self.watek_opt.siatka_parametrow = siatka
        self.watek_opt.kapital           = self.spin_kapital.value()

        self.watek_opt.postep.connect(self._on_postep)
        self.watek_opt.wynik_gotowy.connect(self._on_wynik_opt)
        self.watek_opt.blad.connect(self._on_blad)
        self.watek_opt.finished.connect(lambda: self._ustaw_stan(False))
        self.watek_opt.start()

    def _anuluj(self):
        for w in (self.watek, self.watek_opt):
            if w and w.isRunning():
                w.terminate()
        self.lbl_status.setText("Anulowano.")
        self._ustaw_stan(False)

    # =========================================================================
    # Sloty sygnałów QThread
    # =========================================================================

    def _on_postep(self, current: int, total: int, msg: str):
        self.progress.setMaximum(max(total, 1))
        self.progress.setValue(current)
        self.lbl_status.setText(msg)

    def _on_wynik(self, wynik: dict, tyker: str):
        self.ostatni_wynik = wynik
        self.tabs_wyniki.setCurrentIndex(0)
        m = wynik['metryki']
        self._pokaz_metryki(m, tyker)
        self._rysuj_equity_curve(wynik['equity_curve'], tyker)
        self._wypelnij_tabele_transakcji(wynik['trades'])
        self.lbl_status.setText(
            f"✔ Backtest zakończony — {tyker}  |  "
            f"Return: {m.get('total_return_pct', 0):+.1f}%  "
            f"Sharpe: {m.get('sharpe_ratio', 0):.2f}  "
            f"Transakcji: {m.get('num_trades', 0)}"
        )

    def _on_wynik_opt(self, df):
        self.tabs_wyniki.setCurrentIndex(1)
        self._wypelnij_tabele_opt(df)
        if not df.empty:
            best = df.iloc[0]['sharpe_ratio'] if 'sharpe_ratio' in df.columns else '?'
            self.lbl_status.setText(
                f"✔ Optymalizacja zakończona — {len(df)} kombinacji  |  "
                f"Najlepszy Sharpe: {best:.3f}"
            )
        else:
            self.lbl_status.setText("Optymalizacja zakończona — brak wyników.")

    def _on_blad(self, msg: str):
        QMessageBox.critical(self, "Błąd backtestу", msg)
        self.lbl_status.setText(f"❌ Błąd: {msg}")

    def _ustaw_stan(self, running: bool):
        self.btn_uruchom.setEnabled(not running)
        self.btn_optymalizuj.setEnabled(not running)
        self.btn_anuluj.setEnabled(running)
        self.progress.setVisible(running)
        if not running:
            self.progress.setValue(0)

    # =========================================================================
    # Wyświetlanie wyników
    # =========================================================================

    def _pokaz_metryki(self, m: dict, tyker: str):
        tr      = m.get('total_return_pct', 0)
        sharpe  = m.get('sharpe_ratio', 0)
        max_dd  = m.get('max_drawdown_pct', 0)
        wr      = m.get('win_rate', 0) * 100
        nt      = m.get('num_trades', 0)
        pf      = m.get('profit_factor', 0)
        aw      = m.get('avg_win', 0)
        al      = m.get('avg_loss', 0)
        fv      = m.get('final_value', 0)
        kap     = m.get('kapital_poczatkowy', Konfiguracja.BACKTEST_KAPITAL)

        rc = '#008800' if tr >= 0 else '#cc0000'
        sc = '#008800' if sharpe >= 1.0 else ('#aa7700' if sharpe >= 0 else '#cc0000')

        html = f"""
<div style='font-size:12px;'>
<h3 style='margin:0 0 8px 0; color:#333;'>{tyker}</h3>
<table style='border-collapse:collapse; width:100%;'>
<tr><td style='padding:3px'><b>Zwrot całkowity:</b></td>
    <td style='padding:3px; color:{rc}; font-weight:bold;'>{tr:+.2f}%</td></tr>
<tr><td style='padding:3px'><b>Wartość końcowa:</b></td>
    <td style='padding:3px'>${fv:,.0f}</td></tr>
<tr><td style='padding:3px'><b>Sharpe Ratio:</b></td>
    <td style='padding:3px; color:{sc}; font-weight:bold;'>{sharpe:.3f}</td></tr>
<tr><td style='padding:3px'><b>Max Drawdown:</b></td>
    <td style='padding:3px; color:#cc0000;'>{max_dd:.2f}%</td></tr>
<tr><td style='padding:3px'><b>Win Rate:</b></td>
    <td style='padding:3px'>{wr:.1f}%</td></tr>
<tr><td style='padding:3px'><b>Liczba transakcji:</b></td>
    <td style='padding:3px'>{nt}</td></tr>
<tr><td style='padding:3px'><b>Profit Factor:</b></td>
    <td style='padding:3px'>{pf:.2f}</td></tr>
<tr><td style='padding:3px'><b>Śr. zysk:</b></td>
    <td style='padding:3px; color:#008800;'>${aw:+.2f}</td></tr>
<tr><td style='padding:3px'><b>Śr. strata:</b></td>
    <td style='padding:3px; color:#cc0000;'>${al:.2f}</td></tr>
<tr><td style='padding:3px'><b>Kapitał startowy:</b></td>
    <td style='padding:3px'>${kap:,.0f}</td></tr>
</table>
</div>
"""
        self.lbl_metryki.setText(html)

    def _rysuj_equity_curve(self, equity: pd.Series, tyker: str):
        self.fig_eq.clear()
        ax = self.fig_eq.add_subplot(111)

        if equity.empty:
            ax.text(0.5, 0.5, 'Brak danych equity', ha='center', va='center',
                    color='gray', fontsize=13)
            ax.axis('off')
            self.canvas_eq.draw()
            return

        # Equity curve
        ax.plot(equity.index, equity.values,
                color='#1565C0', linewidth=1.6, label='Wartość portfela')

        # Linia startowa
        ax.axhline(
            y=equity.iloc[0], color='gray', linestyle='--',
            linewidth=1, alpha=0.6, label='Kapitał startowy'
        )

        # Zaciemnij obszary obsunięcia (peak − equity)
        peak = equity.expanding().max()
        ax.fill_between(
            equity.index, equity.values, peak.values,
            alpha=0.15, color='#E53935', label='Drawdown'
        )

        ax.set_title(f"{tyker} — Krzywa kapitału", fontsize=11, fontweight='bold')
        ax.set_ylabel("Wartość portfela ($)")
        ax.legend(loc='upper left', fontsize=9)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.yaxis.set_major_formatter(
            mticker.FuncFormatter(lambda x, _: f'${x:,.0f}')
        )
        try:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            self.fig_eq.autofmt_xdate()
        except Exception:
            pass

        self.fig_eq.tight_layout()
        self.canvas_eq.draw()

    def _wypelnij_tabele_transakcji(self, trades: list):
        self.tabela_tr.setRowCount(len(trades))
        cumulative = 0.0
        for i, t in enumerate(trades):
            pnl  = t.get('pnl', 0)
            cumulative += pnl
            dt   = t.get('date', '')
            res  = 'Zysk' if pnl > 0 else ('Strata' if pnl < 0 else 'BE')
            col  = QColor(200, 255, 200) if pnl > 0 else QColor(255, 200, 200)

            for c, txt in enumerate([
                str(i + 1), dt, f'${pnl:+.2f}', f'${cumulative:+.2f}', res
            ]):
                it = QTableWidgetItem(txt)
                it.setBackground(QBrush(col))
                it.setTextAlignment(Qt.AlignCenter)
                self.tabela_tr.setItem(i, c, it)

    def _wypelnij_tabele_opt(self, df):
        if df is None or df.empty:
            self.tabela_opt.setRowCount(0)
            return

        self.tabela_opt.setRowCount(len(df))
        self.tabela_opt.setColumnCount(len(df.columns))
        self.tabela_opt.setHorizontalHeaderLabels(list(df.columns))
        self.tabela_opt.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )

        # Kolumny Sharpe, Return, Drawdown — zabarwienie
        col_idx = {c: i for i, c in enumerate(df.columns)}

        for ri, (_, row) in enumerate(df.iterrows()):
            for ci, val in enumerate(row):
                txt = f'{val:.4f}' if isinstance(val, float) else str(val)
                it  = QTableWidgetItem(txt)
                it.setTextAlignment(Qt.AlignCenter)
                self.tabela_opt.setItem(ri, ci, it)

            # Podświetl najlepszy wiersz (pierwszy po sortowaniu)
            if ri == 0:
                for ci in range(len(df.columns)):
                    item = self.tabela_opt.item(ri, ci)
                    if item:
                        item.setBackground(QBrush(QColor(200, 255, 200)))

    def _zastosuj_i_uruchom(self):
        """Zastosuj zaznaczone parametry z tabeli optymalizacji → uruchom backtest."""
        selected = self.tabela_opt.selectedItems()
        if not selected:
            QMessageBox.information(
                self, "Brak wyboru",
                "Zaznacz wiersz z wynikami optymalizacji."
            )
            return

        row_idx = selected[0].row()
        headers = [
            self.tabela_opt.horizontalHeaderItem(c).text()
            for c in range(self.tabela_opt.columnCount())
        ]
        values = {
            h: self.tabela_opt.item(row_idx, ci).text()
            for ci, h in enumerate(headers)
            if self.tabela_opt.item(row_idx, ci)
        }

        try:
            if 'sma_fast' in values:
                self.spin_sma_fast.setValue(int(float(values['sma_fast'])))
            if 'sma_slow' in values:
                self.spin_sma_slow.setValue(int(float(values['sma_slow'])))
        except (ValueError, KeyError):
            pass

        self.tabs_wyniki.setCurrentIndex(0)
        self._uruchom_backtest()
