import pandas as pd
from .baza import BazaDanych
from .modele import Swieca, Transakcja
from typing import List

class RepozytoriumDanych:
    def __init__(self):
        self.db = BazaDanych()

    def zapisz_swiece(self, swiece: List[Swieca]):
        conn = self.db.pobierz_polaczenie()
        
        dane = [(s.tyker, s.data, s.otwarcie, s.najwyzszy, s.najnizszy, s.zamkniecie, s.wolumen) for s in swiece]
        
        c = conn.cursor()
        c.executemany('''
        INSERT OR IGNORE INTO swiece (tyker, data, otwarcie, najwyzszy, najnizszy, zamkniecie, wolumen)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', dane)
        conn.commit()

    def pobierz_swiece_df(self, tyker: str) -> pd.DataFrame:
        conn = self.db.pobierz_polaczenie()
        query = "SELECT data, otwarcie, najwyzszy, najnizszy, zamkniecie, wolumen FROM swiece WHERE tyker = ? ORDER BY data ASC"
        df = pd.read_sql_query(query, conn, params=(tyker,))
        if not df.empty:
            df['data'] = pd.to_datetime(df['data'])
            df.set_index('data', inplace=True)
            # Zmiana nazw kolumn na angielskie dla pandasa (ułatwia obliczenia wskaźników, które często polegają na 'close', 'high' itp.)
            # Lub możemy używać polskich nazw, ale trzeba konsekwentnie.
            # Decyzja: Użyjemy angielskich nazw kolumn w DataFrame dla zgodności ze standardami (biblioteki ta-lib, pandas-ta itp.), 
            # ale interfejs repozytorium przyjmuje polskie obiekty.
            df.columns = ['open', 'high', 'low', 'close', 'volume']
        return df
    
    def pobierz_wszystkie_tykery(self) -> List[str]:
        conn = self.db.pobierz_polaczenie()
        c = conn.cursor()
        c.execute("SELECT DISTINCT tyker FROM swiece ORDER BY tyker")
        return [row[0] for row in c.fetchall()]

    def pobierz_ostatnia_data(self, tyker: str) -> str:
        """Get the most recent date for a ticker in the database

        Args:
            tyker: Stock symbol

        Returns:
            Latest date as string (YYYY-MM-DD format) or None if ticker not found
        """
        conn = self.db.pobierz_polaczenie()
        c = conn.cursor()
        c.execute("SELECT MAX(data) FROM swiece WHERE tyker = ?", (tyker,))
        result = c.fetchone()
        return result[0] if result and result[0] else None

    def czy_ticker_istnieje(self, tyker: str) -> bool:
        """Check if ticker exists in database

        Args:
            tyker: Stock symbol

        Returns:
            True if ticker has any data in database
        """
        conn = self.db.pobierz_polaczenie()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM swiece WHERE tyker = ?", (tyker,))
        count = c.fetchone()[0]
        return count > 0

    def usun_dane_tykera(self, tyker: str):
        """Delete all candle data for a specific ticker from database"""
        conn = self.db.pobierz_polaczenie()
        c = conn.cursor()
        c.execute("DELETE FROM swiece WHERE tyker = ?", (tyker,))
        conn.commit()

        # Return number of rows deleted for confirmation
        deleted_count = c.rowcount
        return deleted_count

    def zapisz_transakcje(self, t: Transakcja):
        conn = self.db.pobierz_polaczenie()
        c = conn.cursor()
        
        if t.id:
            c.execute('''
            UPDATE transakcje SET 
                data_wyjscia=?, cena_wyjscia=?, prowizje=?, notatki=?
            WHERE id=?
            ''', (t.data_wyjscia, t.cena_wyjscia, t.prowizje, t.notatki, t.id))
        else:
            c.execute('''
            INSERT INTO transakcje (tyker, data_wejscia, cena_wejscia, wielkosc, stop_loss, cel_cenowy, prowizje, notatki, tag_setupu)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (t.tyker, t.data_wejscia, t.cena_wejscia, t.wielkosc, t.stop_loss, t.cel_cenowy, t.prowizje, t.notatki, t.tag_setupu))
        
        conn.commit()

    def _map_row_to_transaction(self, row) -> Transakcja:
        """Helper to map database row to Transakcja object"""
        return Transakcja(
            id=row[0],
            tyker=row[1],
            data_wejscia=row[2],
            cena_wejscia=row[3],
            data_wyjscia=row[4],
            cena_wyjscia=row[5],
            wielkosc=row[6],
            stop_loss=row[7],
            cel_cenowy=row[8],
            prowizje=row[9],
            notatki=row[10],
            tag_setupu=row[11]
        )

    def pobierz_transakcje(self) -> List[Transakcja]:
        conn = self.db.pobierz_polaczenie()
        c = conn.cursor()
        c.execute("SELECT * FROM transakcje ORDER BY data_wejscia DESC")
        rows = c.fetchall()

        return [self._map_row_to_transaction(r) for r in rows]

    def pobierz_transakcje_po_id(self, transaction_id: int) -> Transakcja:
        """Retrieve single transaction by ID"""
        conn = self.db.pobierz_polaczenie()
        cursor = conn.execute(
            "SELECT * FROM transakcje WHERE id = ?", (transaction_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        return self._map_row_to_transaction(row)

    def usun_transakcje(self, transaction_id: int):
        """Delete transaction from database"""
        conn = self.db.pobierz_polaczenie()
        conn.execute("DELETE FROM transakcje WHERE id = ?", (transaction_id,))
        conn.commit()

    # ───────────────────────────────────────────────────
    #   Notatki skanera (priorytet 0-9 + opcjonalna notatka)
    # ───────────────────────────────────────────────────

    def pobierz_notatki_skanera(self) -> dict:
        """
        Pobierz wszystkie notatki skanera.

        Returns:
            dict {tyker: {'priorytet': int, 'notatka': str}}
        """
        conn = self.db.pobierz_polaczenie()
        c = conn.cursor()
        c.execute("SELECT tyker, priorytet, notatka FROM notatki_skanera")
        rows = c.fetchall()
        return {row[0]: {'priorytet': row[1], 'notatka': row[2] or ''} for row in rows}

    def zapisz_notatke_skanera(self, tyker: str, priorytet: int, notatka: str = ''):
        """
        Zapisz lub zaktualizuj priorytet i notatkę dla tykera.

        Args:
            tyker: Symbol akcji
            priorytet: Wartość 0-9
            notatka: Opcjonalny tekst (domyślnie pusty)
        """
        conn = self.db.pobierz_polaczenie()
        c = conn.cursor()
        c.execute('''
            INSERT INTO notatki_skanera (tyker, priorytet, notatka)
            VALUES (?, ?, ?)
            ON CONFLICT(tyker) DO UPDATE SET
                priorytet = excluded.priorytet,
                notatka   = excluded.notatka
        ''', (tyker, max(0, min(9, priorytet)), notatka))
        conn.commit()

    def usun_notatke_skanera(self, tyker: str):
        """Usuń notatkę dla tykera (np. przy usuwaniu spółki)."""
        conn = self.db.pobierz_polaczenie()
        conn.execute("DELETE FROM notatki_skanera WHERE tyker = ?", (tyker,))
        conn.commit()
