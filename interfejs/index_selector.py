"""
Index Selector Widget - Choose which market index to scan
Supports downloading fresh ticker lists from NYSE/NASDAQ FTP for dynamic indices.
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QComboBox,
    QPushButton, QMessageBox, QProgressBar
)
from PySide6.QtCore import Signal, QThread, Qt

from dane.index_manager import IndexManager


# ─────────────────────────────────────────────
#   Wątek pobierający listę tykerów z FTP
# ─────────────────────────────────────────────

class TickerListDownloadThread(QThread):
    """Background thread - pobiera listę tykerów z Nasdaq FTP"""

    progress_update = Signal(str)           # (message)
    download_complete = Signal(str, int)    # (index_id, ticker_count)
    download_failed = Signal(str, str)      # (index_id, error_message)

    def __init__(self, index_id: str):
        super().__init__()
        self.index_id = index_id

    def run(self):
        try:
            from dane.exchange_loader import ExchangeLoader

            def cb(msg):
                self.progress_update.emit(msg)

            if self.index_id == 'nasdaq':
                self.progress_update.emit("Łączenie z ftp.nasdaqtrader.com ...")
                count = ExchangeLoader.update_nasdaq(cb)
                self.download_complete.emit(self.index_id, count)

            elif self.index_id == 'nyse':
                self.progress_update.emit("Łączenie z ftp.nasdaqtrader.com ...")
                count = ExchangeLoader.update_nyse(cb)
                self.download_complete.emit(self.index_id, count)

            elif self.index_id == 'all_exchanges':
                self.progress_update.emit("Pobieranie Nasdaq + NYSE ...")
                result = ExchangeLoader.update_all(cb)
                self.download_complete.emit(self.index_id, result['all'])

            else:
                self.download_failed.emit(
                    self.index_id,
                    f"Indeks '{self.index_id}' nie wymaga pobierania."
                )

        except Exception as e:
            self.download_failed.emit(self.index_id, str(e))


# ─────────────────────────────────────────────
#   Widget
# ─────────────────────────────────────────────

class IndexSelector(QWidget):
    """
    Widget wyboru indeksu giełdowego do skanowania.

    Dla indeksów requires_download=True pokazuje:
      - status CSV (czy plik istnieje, kiedy ostatnio aktualizowany)
      - przycisk ⬇ Pobierz listę tykerów
      - pasek postępu podczas pobierania
    """

    index_changed = Signal(str)   # emituje index_id przy zmianie

    def __init__(self, index_manager: IndexManager, parent=None):
        super().__init__(parent)
        self.index_manager = index_manager
        self._download_thread = None
        self.setup_ui()

    # ── UI ──────────────────────────────────

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)

        # Wiersz 1: etykieta + combo + info
        row1 = QHBoxLayout()
        row1.setContentsMargins(0, 0, 0, 0)

        row1.addWidget(QLabel("Indeks:"))

        self.index_combo = QComboBox()
        self._populate_combo()
        self.index_combo.currentIndexChanged.connect(self._on_combo_changed)
        row1.addWidget(self.index_combo, 1)

        self.btn_info = QPushButton("ℹ")
        self.btn_info.setMaximumWidth(30)
        self.btn_info.setToolTip("Informacje o indeksie")
        self.btn_info.clicked.connect(self.show_index_info)
        row1.addWidget(self.btn_info)

        row1.addStretch()
        root.addLayout(row1)

        # Wiersz 2: status CSV + przycisk pobierania (widoczny tylko dla requires_download)
        row2 = QHBoxLayout()
        row2.setContentsMargins(0, 0, 0, 0)

        self.lbl_csv_status = QLabel("")
        self.lbl_csv_status.setStyleSheet("font-size: 11px; color: #555;")
        row2.addWidget(self.lbl_csv_status)

        self.btn_download = QPushButton("⬇ Pobierz listę tykerów")
        self.btn_download.setStyleSheet(
            "font-size: 11px; padding: 3px 8px; "
            "background-color: #2196F3; color: white; border-radius: 3px;"
        )
        self.btn_download.setToolTip(
            "Pobierz aktualną listę spółek z Nasdaq FTP (ftp.nasdaqtrader.com).\n"
            "Wymagane jednorazowo, dane są zapisywane lokalnie."
        )
        self.btn_download.clicked.connect(self._start_download)
        self.btn_download.setVisible(False)
        row2.addWidget(self.btn_download)

        row2.addStretch()
        root.addLayout(row2)

        # Wiersz 3: pasek postępu pobierania
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)   # Indeterminate
        self.progress_bar.setMaximumHeight(12)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(False)
        root.addWidget(self.progress_bar)

        self.lbl_dl_status = QLabel("")
        self.lbl_dl_status.setStyleSheet("font-size: 10px; color: #1565C0;")
        self.lbl_dl_status.setVisible(False)
        root.addWidget(self.lbl_dl_status)

        # Inicjalne odświeżenie statusu
        self._refresh_status()

    def _populate_combo(self):
        """Wypełnij combo box indeksami"""
        self.index_combo.clear()
        validation = self.index_manager.validate_index_files()

        for index_def in self.index_manager.list_indices():
            v = validation.get(index_def.id, {})
            available = v.get('valid', False)

            if index_def.requires_download:
                if available:
                    count = v.get('ticker_count', index_def.stock_count)
                    label = f"{index_def.name} ({count:,} spółek, ~{index_def.estimated_time_min}min) ✅"
                else:
                    label = f"{index_def.name} (~{index_def.stock_count:,} spółek) ⬇ wymaga pobrania"
            else:
                count = v.get('ticker_count', index_def.stock_count) if available else index_def.stock_count
                label = f"{index_def.name} ({count:,} spółek, ~{index_def.estimated_time_min}min)"

            self.index_combo.addItem(label, index_def.id)

    def _on_combo_changed(self, _index):
        self._refresh_status()
        index_id = self.get_selected_index_id()
        if index_id:
            self.index_changed.emit(index_id)

    def _refresh_status(self):
        """Odśwież etykietę statusu CSV i widoczność przycisku pobierania"""
        index_id = self.get_selected_index_id()
        if not index_id:
            return

        index_def = self.index_manager.get_index(index_id)
        if not index_def:
            return

        if not index_def.requires_download:
            self.lbl_csv_status.setText("")
            self.btn_download.setVisible(False)
            return

        # requires_download=True
        validation = self.index_manager.validate_index_files()
        v = validation.get(index_id, {})

        if v.get('valid'):
            count = v.get('ticker_count', '?')
            updated = v.get('last_updated', '?')
            self.lbl_csv_status.setText(
                f"✅ Lista dostępna: {count:,} spółek | ostatnia aktualizacja: {updated}"
            )
            self.btn_download.setText("🔄 Aktualizuj listę")
            self.btn_download.setStyleSheet(
                "font-size: 11px; padding: 3px 8px; "
                "background-color: #43A047; color: white; border-radius: 3px;"
            )
        elif v.get('exists'):
            self.lbl_csv_status.setText(
                f"⚠️ Plik istnieje, ale jest uszkodzony: {v.get('error', '')}"
            )
            self.btn_download.setText("⬇ Pobierz listę ponownie")
            self.btn_download.setStyleSheet(
                "font-size: 11px; padding: 3px 8px; "
                "background-color: #FB8C00; color: white; border-radius: 3px;"
            )
        else:
            self.lbl_csv_status.setText(
                "❌ Lista nie pobrana — wymagane jednorazowe pobranie z internetu"
            )
            self.btn_download.setText("⬇ Pobierz listę tykerów")
            self.btn_download.setStyleSheet(
                "font-size: 11px; padding: 3px 8px; "
                "background-color: #2196F3; color: white; border-radius: 3px;"
            )

        self.btn_download.setVisible(True)

    # ── Pobieranie ───────────────────────────

    def _start_download(self):
        """Uruchom wątek pobierający listę tykerów z FTP"""
        index_id = self.get_selected_index_id()
        index_def = self.index_manager.get_index(index_id)

        if not index_def or not index_def.requires_download:
            return

        # Zablokuj UI
        self.btn_download.setEnabled(False)
        self.index_combo.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.lbl_dl_status.setText("Łączenie z ftp.nasdaqtrader.com ...")
        self.lbl_dl_status.setVisible(True)

        # Uruchom wątek
        self._download_thread = TickerListDownloadThread(index_id)
        self._download_thread.progress_update.connect(self._on_dl_progress)
        self._download_thread.download_complete.connect(self._on_dl_complete)
        self._download_thread.download_failed.connect(self._on_dl_failed)
        self._download_thread.start()

    def _on_dl_progress(self, message: str):
        self.lbl_dl_status.setText(message)

    def _on_dl_complete(self, index_id: str, ticker_count: int):
        """Obsłuż zakończenie pobierania"""
        # Przywróć UI
        self.progress_bar.setVisible(False)
        self.lbl_dl_status.setVisible(False)
        self.btn_download.setEnabled(True)
        self.index_combo.setEnabled(True)

        # Odśwież combo i status
        current_id = self.get_selected_index_id()
        self._populate_combo()
        # Przywróć zaznaczenie
        for i in range(self.index_combo.count()):
            if self.index_combo.itemData(i) == current_id:
                self.index_combo.setCurrentIndex(i)
                break
        self._refresh_status()

        index_def = self.index_manager.get_index(index_id)
        name = index_def.name if index_def else index_id
        QMessageBox.information(
            self,
            "Pobieranie zakończone",
            f"✅ Lista tykerów dla '{name}' została pobrana.\n\n"
            f"Pobrano {ticker_count:,} spółek.\n"
            f"Możesz teraz uruchomić skan."
        )

    def _on_dl_failed(self, index_id: str, error: str):
        """Obsłuż błąd pobierania"""
        self.progress_bar.setVisible(False)
        self.lbl_dl_status.setVisible(False)
        self.btn_download.setEnabled(True)
        self.index_combo.setEnabled(True)

        QMessageBox.critical(
            self,
            "Błąd pobierania",
            f"❌ Nie udało się pobrać listy tykerów.\n\n"
            f"Błąd: {error}\n\n"
            f"Sprawdź połączenie z internetem i spróbuj ponownie."
        )

    # ── Publiczne API ────────────────────────

    def get_selected_index_id(self) -> str:
        """Zwróć ID aktualnie wybranego indeksu"""
        return self.index_combo.currentData()

    def show_index_info(self):
        """Pokaż szczegóły wybranego indeksu"""
        index_id = self.get_selected_index_id()
        index_def = self.index_manager.get_index(index_id)

        if not index_def:
            return

        validation = self.index_manager.validate_index_files()
        status = validation.get(index_id, {})

        info = f"Indeks: {index_def.name}\n"
        info += f"Opis: {index_def.description}\n"
        info += f"Szacowana liczba spółek: ~{index_def.stock_count:,}\n"
        info += f"Szacowany czas skanowania: ~{index_def.estimated_time_min} minut\n"
        info += f"Plik CSV: {index_def.csv_filename}\n"

        if index_def.requires_download:
            info += f"\n⬇ Ten indeks wymaga jednorazowego pobrania listy tykerów z internetu.\n"
            info += f"Źródło: ftp.nasdaqtrader.com/symboldirectory\n"

        info += "\n--- Status pliku ---\n"

        if status.get('valid'):
            info += f"✅ Plik istnieje i jest poprawny\n"
            info += f"Liczba tykerów: {status.get('ticker_count', '?'):,}\n"
            info += f"Ostatnia aktualizacja: {status.get('last_updated', '?')}"
        elif status.get('exists'):
            info += f"⚠️ Plik istnieje, ale zawiera błędy\n"
            info += f"Błąd: {status.get('error', 'Nieznany')}"
        else:
            info += f"❌ Plik nie istnieje\n"
            info += f"Oczekiwana ścieżka: {status.get('path', '?')}"

        QMessageBox.information(self, "Informacje o indeksie", info)
