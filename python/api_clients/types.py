"""
Data types for distributor API responses
"""
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class Distributor(Enum):
    """Distributor names"""
    MOUSER = "mouser"
    DIGIKEY = "digikey"


class ComponentGrade(Enum):
    """Component qualification grade"""
    COMMERCIAL = "commercial"          # 0°C to 70°C
    INDUSTRIAL = "industrial"          # -40°C to 85°C
    AUTOMOTIVE = "automotive"          # -40°C to 125/150°C (AEC-Q qualified)
    MILITARY = "military"              # -55°C to 125°C (MIL-spec)
    UNKNOWN = "unknown"


@dataclass
class PriceBreak:
    """Price at specific quantity"""
    quantity: int
    price: float
    currency: str = "USD"

    def __repr__(self):
        return f"{self.quantity}+ @ ${self.price:.2f}"


@dataclass
class ComponentAvailability:
    """Component availability and pricing info from a distributor"""
    mpn: str
    manufacturer: str
    description: str
    distributor: Distributor
    stock: int
    price_breaks: List[PriceBreak] = field(default_factory=list)

    # Optional fields
    datasheet_url: Optional[str] = None
    product_url: Optional[str] = None
    lead_time: Optional[str] = None
    package: Optional[str] = None
    grade: ComponentGrade = ComponentGrade.UNKNOWN
    temp_min: Optional[float] = None  # °C
    temp_max: Optional[float] = None  # °C

    # Specifications
    specs: dict = field(default_factory=dict)

    @property
    def in_stock(self) -> bool:
        """Check if component is in stock"""
        return self.stock > 0

    @property
    def unit_price(self) -> float:
        """Price for quantity 1"""
        if self.price_breaks:
            return self.price_breaks[0].price
        return 0.0

    @property
    def is_automotive_grade(self) -> bool:
        """Check if component is automotive grade"""
        return self.grade == ComponentGrade.AUTOMOTIVE

    @property
    def is_aviation_suitable(self) -> bool:
        """Check if suitable for aviation (-40°C to +125°C minimum)"""
        if self.temp_min is None or self.temp_max is None:
            return False
        return self.temp_min <= -40 and self.temp_max >= 125

    def __repr__(self):
        stock_str = f"{self.stock:,} in stock" if self.in_stock else "Out of stock"
        price_str = f"${self.unit_price:.2f}" if self.price_breaks else "N/A"
        return f"{self.mpn} ({self.manufacturer}) - {stock_str}, {price_str} @ {self.distributor.value}"


@dataclass
class AlternativeComponent:
    """Alternative/replacement component with comparison"""
    mpn: str
    manufacturer: str
    description: str
    availability: List[ComponentAvailability]

    # Comparison to original
    same_footprint: bool = False
    footprint_notes: str = ""
    price_difference_pct: float = 0.0  # % cheaper (positive) or more expensive (negative)
    grade: ComponentGrade = ComponentGrade.UNKNOWN
    temp_min: Optional[float] = None
    temp_max: Optional[float] = None

    # Recommendation
    compatibility_score: float = 0.0  # 0-100, higher is better
    compatibility_notes: List[str] = field(default_factory=list)
    recommended: bool = False

    @property
    def best_price(self) -> float:
        """Lowest price across all distributors"""
        if not self.availability:
            return 0.0
        return min(a.unit_price for a in self.availability if a.price_breaks)

    @property
    def total_stock(self) -> int:
        """Total stock across all distributors"""
        return sum(a.stock for a in self.availability)

    @property
    def is_aviation_suitable(self) -> bool:
        """Check if suitable for aviation"""
        if self.temp_min is None or self.temp_max is None:
            return False
        return self.temp_min <= -40 and self.temp_max >= 125

    def __repr__(self):
        price_change = f"{self.price_difference_pct:+.1f}%" if self.price_difference_pct != 0 else "same price"
        footprint = "✓ same footprint" if self.same_footprint else "⚠ different footprint"
        rec = " [RECOMMENDED]" if self.recommended else ""
        return f"{self.mpn} ({self.manufacturer}) - {price_change}, {footprint}{rec}"


@dataclass
class ComponentSearchResult:
    """Result from searching for a component"""
    query: str
    results: List[ComponentAvailability]
    search_time: float = 0.0

    @property
    def found(self) -> bool:
        return len(self.results) > 0

    @property
    def best_availability(self) -> Optional[ComponentAvailability]:
        """Component with best availability (highest stock)"""
        if not self.results:
            return None
        return max(self.results, key=lambda x: x.stock)


@dataclass
class BOMComplianceCheck:
    """Aviation/automotive compliance check result"""
    total_components: int
    compliant_components: int
    non_compliant_components: int
    unknown_components: int

    # Detailed breakdown
    compliant_refs: List[str] = field(default_factory=list)
    non_compliant_refs: List[str] = field(default_factory=list)
    unknown_refs: List[str] = field(default_factory=list)

    # Cost impact
    total_cost_impact: float = 0.0  # $ per board

    # Recommendations
    components_to_upgrade: List[dict] = field(default_factory=list)

    @property
    def compliance_percentage(self) -> float:
        if self.total_components == 0:
            return 0.0
        return (self.compliant_components / self.total_components) * 100

    @property
    def needs_attention(self) -> bool:
        return self.non_compliant_components > 0
