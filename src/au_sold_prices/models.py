from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Sale:
    address: str
    suburb: str
    state: str
    postcode: str
    sold_price: int
    sold_date: date
    property_type: str = "house"
