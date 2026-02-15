from dataclasses import dataclass
from typing import Optional

@dataclass
class Swieca:
    tyker: str
    data: str  # ISO Format YYYY-MM-DD
    otwarcie: float
    najwyzszy: float
    najnizszy: float
    zamkniecie: float
    wolumen: int

@dataclass
class Transakcja:
    id: Optional[int]
    tyker: str
    data_wejscia: str
    cena_wejscia: float
    data_wyjscia: Optional[str]
    cena_wyjscia: Optional[float]
    wielkosc: int
    stop_loss: float
    cel_cenowy: float
    prowizje: float
    notatki: str
    tag_setupu: str
    
    @property
    def jest_zamknieta(self):
        return self.cena_wyjscia is not None and self.data_wyjscia is not None

    @property
    def zysk_strata(self):
        # P/L = (Exit - Entry) * Size - Fees
        if not self.jest_zamknieta:
            return 0.0
        return (self.cena_wyjscia - self.cena_wejscia) * self.wielkosc - self.prowizje
    
    @property
    def r_multiple(self):
        if not self.jest_zamknieta:
            return 0.0
        ryzyko = self.cena_wejscia - self.stop_loss
        if ryzyko <= 0: return 0.0
        zysk = self.cena_wyjscia - self.cena_wejscia
        return zysk / ryzyko
