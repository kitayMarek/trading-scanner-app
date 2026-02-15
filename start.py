import sys
from PySide6.QtWidgets import QApplication
from interfejs.glowne_okno import GlowneOkno
from dane.baza import BazaDanych

def start():
    app = QApplication(sys.argv)
    
    # Inicjalizacja bazy
    db = BazaDanych()
    db.inicjalizuj()
    
    okno = GlowneOkno()
    okno.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    start()
