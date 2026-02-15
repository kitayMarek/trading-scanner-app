import sqlite3
import os
from konfiguracja import Konfiguracja

class BazaDanych:
    _instancja = None

    def __new__(cls):
        if cls._instancja is None:
            cls._instancja = super(BazaDanych, cls).__new__(cls)
            cls._instancja.polaczenie = None
        return cls._instancja

    def inicjalizuj(self):
        """Inicjalizacja połączenia i tabel."""
        sciezka_bazy = os.path.join(os.getcwd(), Konfiguracja.NAZWA_BAZY)
        self.polaczenie = sqlite3.connect(sciezka_bazy, check_same_thread=False)
        self.utworz_tabele()

    def pobierz_polaczenie(self):
        if self.polaczenie is None:
            self.inicjalizuj()
        return self.polaczenie

    def utworz_tabele(self):
        kursor = self.polaczenie.cursor()
        
        # Tabela świec
        kursor.execute('''
        CREATE TABLE IF NOT EXISTS swiece (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tyker TEXT NOT NULL,
            data TEXT NOT NULL,
            otwarcie REAL,
            najwyzszy REAL,
            najnizszy REAL,
            zamkniecie REAL,
            wolumen INTEGER,
            UNIQUE(tyker, data)
        )
        ''')

        # Tabela transakcji
        kursor.execute('''
        CREATE TABLE IF NOT EXISTS transakcje (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tyker TEXT NOT NULL,
            data_wejscia TEXT NOT NULL,
            cena_wejscia REAL NOT NULL,
            data_wyjscia TEXT,
            cena_wyjscia REAL,
            wielkosc INTEGER NOT NULL,
            stop_loss REAL,
            cel_cenowy REAL,
            prowizje REAL DEFAULT 0,
            notatki TEXT,
            tag_setupu TEXT
        )
        ''')
        
        self.polaczenie.commit()
