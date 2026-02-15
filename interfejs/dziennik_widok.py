from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHBoxLayout, QPushButton,
    QFormLayout, QLineEdit, QDoubleSpinBox, QDateEdit, QLabel, QHeaderView, QTextEdit,
    QComboBox, QMessageBox, QDialog
)
from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor, QBrush
from dziennik.serwis import SerwisDziennika
from dane.modele import Transakcja
import pandas as pd

class DziennikWidok(QWidget):
    def __init__(self):
        super().__init__()
        self.serwis = SerwisDziennika()
        self.inicjalizuj_ui()
        self.odswiez_tabele()
        
    def inicjalizuj_ui(self):
        uklad = QVBoxLayout()
        
        # Formularz
        form_w = QWidget()
        form_l = QFormLayout()
        
        self.input_tyker = QLineEdit()
        self.input_cena = QDoubleSpinBox()
        self.input_cena.setRange(0, 99999)
        self.input_cena.setSuffix(" $")
        self.input_wielkosc = QDoubleSpinBox()
        self.input_wielkosc.setRange(1, 999999)
        self.input_wielkosc.setDecimals(0)
        self.input_data = QDateEdit()
        self.input_data.setDate(QDate.currentDate())

        # New fields
        self.input_stop_loss = QDoubleSpinBox()
        self.input_stop_loss.setRange(0, 99999)
        self.input_stop_loss.setSuffix(" $")

        self.input_cel = QDoubleSpinBox()
        self.input_cel.setRange(0, 99999)
        self.input_cel.setSuffix(" $")

        self.input_prowizje = QDoubleSpinBox()
        self.input_prowizje.setRange(0, 999)
        self.input_prowizje.setValue(0)
        self.input_prowizje.setSuffix(" $")

        self.input_tag = QComboBox()
        self.input_tag.addItems(["", "Tier A", "Tier B", "Tier C", "Pullback", "Breakout"])

        self.input_notatki = QTextEdit()
        self.input_notatki.setMaximumHeight(60)
        self.input_notatki.setPlaceholderText("Notatki o transakcji...")

        form_l.addRow("Tyker:", self.input_tyker)
        form_l.addRow("Data:", self.input_data)
        form_l.addRow("Cena wejścia:", self.input_cena)
        form_l.addRow("Wielkość:", self.input_wielkosc)
        form_l.addRow("Stop Loss:", self.input_stop_loss)
        form_l.addRow("Cel cenowy:", self.input_cel)
        form_l.addRow("Prowizje:", self.input_prowizje)
        form_l.addRow("Tag setupu:", self.input_tag)
        form_l.addRow("Notatki:", self.input_notatki)
        
        btn_dodaj = QPushButton("Dodaj Transakcję")
        btn_dodaj.clicked.connect(self.dodaj_transakcje)
        form_l.addRow(btn_dodaj)
        
        form_w.setLayout(form_l)
        uklad.addWidget(form_w)
        
        # Statystyki
        self.lbl_stats = QLabel("Statystyki...")
        uklad.addWidget(self.lbl_stats)
        
        # Tabela
        self.tabela = QTableWidget()
        kolumny = ["Tyker", "Data", "Cena", "Ilość", "Wyjście", "P/L", "R-Mutiple"]
        self.tabela.setColumnCount(len(kolumny))
        self.tabela.setHorizontalHeaderLabels(kolumny)
        self.tabela.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Enable row selection
        self.tabela.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela.setSelectionMode(QTableWidget.SingleSelection)

        uklad.addWidget(self.tabela)

        # Action buttons for selected transaction
        uklad_przyciskow = QHBoxLayout()
        btn_close = QPushButton("Close Trade")
        btn_close.clicked.connect(self.zamknij_pozycje)
        btn_edit = QPushButton("Edit")
        btn_edit.clicked.connect(self.edytuj_transakcje)
        btn_delete = QPushButton("Delete")
        btn_delete.clicked.connect(self.usun_transakcje)
        uklad_przyciskow.addWidget(btn_close)
        uklad_przyciskow.addWidget(btn_edit)
        uklad_przyciskow.addWidget(btn_delete)
        uklad_przyciskow.addStretch()
        uklad.addLayout(uklad_przyciskow)

        self.setLayout(uklad)
        
    def dodaj_transakcje(self):
        # Validation
        if not self.input_tyker.text().strip():
            QMessageBox.warning(self, "Błąd", "Wprowadź ticker!")
            return
        if self.input_cena.value() <= 0:
            QMessageBox.warning(self, "Błąd", "Cena musi być > 0!")
            return
        if self.input_stop_loss.value() <= 0:
            QMessageBox.warning(self, "Błąd", "Stop loss jest wymagany dla obliczenia R-multiple!")
            return

        t = Transakcja(
            id=None,
            tyker=self.input_tyker.text().upper().strip(),
            data_wejscia=self.input_data.text(),
            cena_wejscia=self.input_cena.value(),
            wielkosc=int(self.input_wielkosc.value()),
            stop_loss=self.input_stop_loss.value(),
            cel_cenowy=self.input_cel.value(),
            prowizje=self.input_prowizje.value(),
            notatki=self.input_notatki.toPlainText(),
            tag_setupu=self.input_tag.currentText(),
            data_wyjscia=None,
            cena_wyjscia=None
        )
        self.serwis.dodaj_transakcje(t)
        self.wyczysc_formularz()
        self.odswiez_tabele()

    def wyczysc_formularz(self):
        """Clear all form inputs after submission"""
        self.input_tyker.clear()
        self.input_cena.setValue(0)
        self.input_wielkosc.setValue(1)
        self.input_stop_loss.setValue(0)
        self.input_cel.setValue(0)
        self.input_prowizje.setValue(0)
        self.input_tag.setCurrentIndex(0)
        self.input_notatki.clear()
        self.input_data.setDate(QDate.currentDate())

    def zamknij_pozycje(self):
        """Close selected open position"""
        selected = self.tabela.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Błąd", "Wybierz transakcję!")
            return

        row = selected[0].row()
        ticker = self.tabela.item(row, 0).text()

        # Get transaction ID (stored in UserRole)
        transaction_id = self.tabela.item(row, 0).data(Qt.UserRole)

        if not transaction_id:
            QMessageBox.warning(self, "Błąd", "Nie można znaleźć ID transakcji!")
            return

        # Check if already closed
        exit_date_item = self.tabela.item(row, 4)
        if exit_date_item and exit_date_item.text() != "-":
            QMessageBox.warning(self, "Błąd", "Transakcja jest już zamknięta!")
            return

        # Show dialog to enter exit price and date
        dialog = CloseTradeDialog(ticker, self)
        if dialog.exec():
            exit_price = dialog.exit_price
            exit_date = dialog.exit_date

            try:
                self.serwis.zamknij_transakcje(transaction_id, exit_date, exit_price)
                self.odswiez_tabele()
                QMessageBox.information(self, "Sukces", f"Zamknięto pozycję {ticker}")
            except Exception as e:
                QMessageBox.critical(self, "Błąd", str(e))

    def edytuj_transakcje(self):
        """Edit selected transaction"""
        selected = self.tabela.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Błąd", "Wybierz transakcję!")
            return

        row = selected[0].row()
        transaction_id = self.tabela.item(row, 0).data(Qt.UserRole)

        # Retrieve full transaction
        t = self.serwis.repo.pobierz_transakcje_po_id(transaction_id)
        if not t:
            QMessageBox.warning(self, "Błąd", "Nie można załadować transakcji!")
            return

        # Show edit dialog
        dialog = EditTradeDialog(t, self)
        if dialog.exec():
            # Update transaction with new values
            updated_t = dialog.get_transaction()
            updated_t.id = transaction_id  # Preserve ID

            try:
                self.serwis.repo.zapisz_transakcje(updated_t)
                self.odswiez_tabele()
                QMessageBox.information(self, "Sukces", "Transakcja zaktualizowana")
            except Exception as e:
                QMessageBox.critical(self, "Błąd", str(e))

    def usun_transakcje(self):
        """Delete selected transaction"""
        selected = self.tabela.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Błąd", "Wybierz transakcję!")
            return

        row = selected[0].row()
        ticker = self.tabela.item(row, 0).text()
        transaction_id = self.tabela.item(row, 0).data(Qt.UserRole)

        # Confirmation dialog
        reply = QMessageBox.question(
            self, "Potwierdzenie",
            f"Czy na pewno usunąć transakcję {ticker}?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                self.serwis.usun_transakcje(transaction_id)
                self.odswiez_tabele()
                QMessageBox.information(self, "Sukces", "Transakcja usunięta")
            except Exception as e:
                QMessageBox.critical(self, "Błąd", str(e))

    def odswiez_tabele(self):
        transakcje = self.serwis.pobierz_transakcje()
        self.tabela.setRowCount(len(transakcje))

        for r, t in enumerate(transakcje):
            # Column 0: Ticker (store ID in UserRole)
            item_ticker = QTableWidgetItem(t.tyker)
            item_ticker.setData(Qt.UserRole, t.id)  # Store transaction ID
            self.tabela.setItem(r, 0, item_ticker)

            # Column 1: Entry Date
            self.tabela.setItem(r, 1, QTableWidgetItem(t.data_wejscia))

            # Column 2: Entry Price
            self.tabela.setItem(r, 2, QTableWidgetItem(f"${t.cena_wejscia:.2f}"))

            # Column 3: Quantity
            self.tabela.setItem(r, 3, QTableWidgetItem(str(t.wielkosc)))

            # Column 4: Exit Date
            exit_date_text = t.data_wyjscia if t.data_wyjscia else "-"
            self.tabela.setItem(r, 4, QTableWidgetItem(exit_date_text))

            # Column 5: P/L (with color coding)
            if t.jest_zamknieta:
                pl = t.zysk_strata
                pl_text = f"${pl:+.2f}"
                item_pl = QTableWidgetItem(pl_text)
                if pl > 0:
                    item_pl.setForeground(QBrush(QColor(0, 150, 0)))  # Green
                elif pl < 0:
                    item_pl.setForeground(QBrush(QColor(150, 0, 0)))  # Red
                self.tabela.setItem(r, 5, item_pl)
            else:
                self.tabela.setItem(r, 5, QTableWidgetItem("-"))

            # Column 6: R-Multiple (with color coding)
            if t.jest_zamknieta and t.r_multiple != 0:
                r_mult_text = f"{t.r_multiple:+.2f}R"
                item_r = QTableWidgetItem(r_mult_text)
                if t.r_multiple > 0:
                    item_r.setForeground(QBrush(QColor(0, 150, 0)))  # Green
                elif t.r_multiple < 0:
                    item_r.setForeground(QBrush(QColor(150, 0, 0)))  # Red
                self.tabela.setItem(r, 6, item_r)
            else:
                self.tabela.setItem(r, 6, QTableWidgetItem("-"))

        # Refresh statistics
        stats = self.serwis.generuj_statystyki()
        self.lbl_stats.setText(
            f"Transakcje: {stats['liczba_transakcji']} | Win Rate: {stats['win_rate']:.2%} | "
            f"Profit Factor: {stats['profit_factor']:.2f} | Expectancy: {stats['expectancy_r']:.2f}R"
        )


class CloseTradeDialog(QDialog):
    """Dialog for closing an open position"""
    def __init__(self, ticker, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Close Trade - {ticker}")

        layout = QFormLayout()

        self.exit_date_input = QDateEdit()
        self.exit_date_input.setDate(QDate.currentDate())
        layout.addRow("Exit Date:", self.exit_date_input)

        self.exit_price_input = QDoubleSpinBox()
        self.exit_price_input.setRange(0, 99999)
        self.exit_price_input.setSuffix(" $")
        layout.addRow("Exit Price:", self.exit_price_input)

        buttons = QHBoxLayout()
        btn_ok = QPushButton("OK")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        buttons.addWidget(btn_ok)
        buttons.addWidget(btn_cancel)
        layout.addRow(buttons)

        self.setLayout(layout)

    @property
    def exit_price(self):
        return self.exit_price_input.value()

    @property
    def exit_date(self):
        return self.exit_date_input.text()


class EditTradeDialog(QDialog):
    """Dialog for editing an existing transaction"""
    def __init__(self, transaction, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Edit Trade - {transaction.tyker}")
        self.transaction = transaction

        layout = QFormLayout()

        # All editable fields
        self.ticker_input = QLineEdit(transaction.tyker)
        layout.addRow("Ticker:", self.ticker_input)

        self.entry_date_input = QDateEdit()
        self.entry_date_input.setDate(QDate.fromString(transaction.data_wejscia, "yyyy-MM-dd"))
        layout.addRow("Entry Date:", self.entry_date_input)

        self.entry_price_input = QDoubleSpinBox()
        self.entry_price_input.setRange(0, 99999)
        self.entry_price_input.setValue(transaction.cena_wejscia)
        self.entry_price_input.setSuffix(" $")
        layout.addRow("Entry Price:", self.entry_price_input)

        self.size_input = QDoubleSpinBox()
        self.size_input.setRange(1, 999999)
        self.size_input.setDecimals(0)
        self.size_input.setValue(transaction.wielkosc)
        layout.addRow("Size:", self.size_input)

        self.stop_loss_input = QDoubleSpinBox()
        self.stop_loss_input.setRange(0, 99999)
        self.stop_loss_input.setValue(transaction.stop_loss or 0)
        self.stop_loss_input.setSuffix(" $")
        layout.addRow("Stop Loss:", self.stop_loss_input)

        # Exit fields (if closed)
        if transaction.jest_zamknieta:
            self.exit_date_input = QDateEdit()
            self.exit_date_input.setDate(QDate.fromString(transaction.data_wyjscia, "yyyy-MM-dd"))
            layout.addRow("Exit Date:", self.exit_date_input)

            self.exit_price_input = QDoubleSpinBox()
            self.exit_price_input.setRange(0, 99999)
            self.exit_price_input.setValue(transaction.cena_wyjscia)
            self.exit_price_input.setSuffix(" $")
            layout.addRow("Exit Price:", self.exit_price_input)
        else:
            self.exit_date_input = None
            self.exit_price_input = None

        buttons = QHBoxLayout()
        btn_save = QPushButton("Save")
        btn_save.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        buttons.addWidget(btn_save)
        buttons.addWidget(btn_cancel)
        layout.addRow(buttons)

        self.setLayout(layout)

    def get_transaction(self):
        """Return updated transaction object"""
        return Transakcja(
            id=self.transaction.id,
            tyker=self.ticker_input.text().upper().strip(),
            data_wejscia=self.entry_date_input.text(),
            cena_wejscia=self.entry_price_input.value(),
            wielkosc=int(self.size_input.value()),
            stop_loss=self.stop_loss_input.value(),
            cel_cenowy=self.transaction.cel_cenowy,  # Keep existing
            prowizje=self.transaction.prowizje,      # Keep existing
            notatki=self.transaction.notatki,        # Keep existing
            tag_setupu=self.transaction.tag_setupu,  # Keep existing
            data_wyjscia=self.exit_date_input.text() if self.exit_date_input else None,
            cena_wyjscia=self.exit_price_input.value() if self.exit_price_input else None
        )
