"""
Mock API responses for testing without actual API keys
Based on real Mouser/DigiKey response structures
"""
from .types import ComponentAvailability, PriceBreak, Distributor, ComponentGrade

# Mock database of components (based on your Astro board + common alternatives)
MOCK_COMPONENTS = {
    # Your current Rev0004 components
    "LM2596": {
        "mouser": {
            "mpn": "LM2596S-ADJ/NOPB",
            "manufacturer": "Texas Instruments",
            "description": "Switching Voltage Regulators SIMPLE SWITCHER 3A Step-Down Voltage Regulator",
            "stock": 2145,
            "price_breaks": [
                (1, 3.10),
                (10, 2.89),
                (100, 2.62),
                (1000, 2.38)
            ],
            "package": "TO-263",
            "grade": ComponentGrade.COMMERCIAL,
            "temp_min": 0,
            "temp_max": 70,
            "datasheet": "https://www.ti.com/lit/ds/symlink/lm2596.pdf"
        },
        "digikey": {
            "mpn": "LM2596S-ADJ/NOPB",
            "manufacturer": "Texas Instruments",
            "description": "IC REG BUCK ADJ 3A TO263-5",
            "stock": 1892,
            "price_breaks": [
                (1, 3.15),
                (10, 2.93),
                (100, 2.68)
            ],
            "package": "TO-263-5",
            "grade": ComponentGrade.COMMERCIAL,
            "temp_min": 0,
            "temp_max": 70
        }
    },

    # Automotive alternative for LM2596
    "TPS54360-Q1": {
        "mouser": {
            "mpn": "TPS54360-Q1DPWRQ1",
            "manufacturer": "Texas Instruments",
            "description": "Switching Voltage Regulators 3.5-V to 42-V input, 3.5-A, synchronous buck AEC-Q100",
            "stock": 3247,
            "price_breaks": [
                (1, 2.45),
                (10, 2.28),
                (100, 2.08),
                (1000, 1.89)
            ],
            "package": "TO-263",
            "grade": ComponentGrade.AUTOMOTIVE,
            "temp_min": -40,
            "temp_max": 125,
            "datasheet": "https://www.ti.com/lit/ds/symlink/tps54360-q1.pdf",
            "specs": {
                "AEC-Q100": "Qualified",
                "Input Voltage": "3.5V to 42V",
                "Output Current": "3.5A",
                "Efficiency": "95%"
            }
        },
        "digikey": {
            "mpn": "TPS54360-Q1DPWRQ1",
            "manufacturer": "Texas Instruments",
            "description": "IC REG BUCK ADJ 3.5A TO263-7 AEC-Q100",
            "stock": 5247,
            "price_breaks": [
                (1, 2.50),
                (10, 2.32),
                (100, 2.12)
            ],
            "package": "TO-263-7",
            "grade": ComponentGrade.AUTOMOTIVE,
            "temp_min": -40,
            "temp_max": 125
        }
    },

    # Your current Rev0004 FET
    "SI4459BDY": {
        "mouser": {
            "mpn": "SI4459BDY-T1-GE3",
            "manufacturer": "Vishay Siliconix",
            "description": "MOSFET 2P-CH -30V -7A PowerPAK SO-8",
            "stock": 1543,
            "price_breaks": [
                (1, 2.10),
                (10, 1.95),
                (100, 1.78)
            ],
            "package": "PowerPAK SO-8",
            "grade": ComponentGrade.COMMERCIAL,
            "temp_min": -55,
            "temp_max": 150,
            "specs": {
                "Voltage": "-30V",
                "Current (per channel)": "-7A",
                "Channels": "2 (Dual)",
                "Rds(on)": "0.017Ω @ -10V"
            }
        }
    },

    # Replacement FET from your Rev0005 plan
    "SI4435BDY": {
        "mouser": {
            "mpn": "Si4435BDY-T1-GE3",
            "manufacturer": "Vishay Siliconix",
            "description": "MOSFET P-CH -40V -14A PowerPAK SO-8",
            "stock": 1247,
            "price_breaks": [
                (1, 2.45),
                (10, 2.28),
                (100, 2.08)
            ],
            "package": "PowerPAK SO-8",
            "grade": ComponentGrade.COMMERCIAL,  # Note: -Q1 version available for automotive
            "temp_min": -55,
            "temp_max": 150,
            "datasheet": "https://www.vishay.com/docs/63734/si4435bdy.pdf",
            "specs": {
                "Voltage": "-40V",
                "Current": "-14A",
                "Channels": "1 (Single)",
                "Rds(on)": "0.0085Ω @ -10V"
            }
        },
        "digikey": {
            "mpn": "Si4435BDY-T1-GE3",
            "manufacturer": "Vishay Siliconix",
            "description": "MOSFET P-CH -40V -14A 8SO",
            "stock": 892,
            "price_breaks": [
                (1, 2.50),
                (10, 2.33),
                (100, 2.13)
            ],
            "package": "PowerPAK SO-8",
            "grade": ComponentGrade.COMMERCIAL,
            "temp_min": -55,
            "temp_max": 150
        }
    },

    # Example: STM32 MCU (if on your board)
    "STM32F407VGT6": {
        "mouser": {
            "mpn": "STM32F407VGT6",
            "manufacturer": "STMicroelectronics",
            "description": "ARM Microcontrollers - MCU High-performance 1MB Flash 168MHz CPU",
            "stock": 2845,
            "price_breaks": [
                (1, 10.50),
                (10, 9.80),
                (100, 8.95)
            ],
            "package": "LQFP-100",
            "grade": ComponentGrade.INDUSTRIAL,
            "temp_min": -40,
            "temp_max": 85
        },
        "digikey": {
            "mpn": "STM32F407VGT6",
            "manufacturer": "STMicroelectronics",
            "description": "IC MCU 32BIT 1MB FLASH 100LQFP",
            "stock": 1245,
            "price_breaks": [
                (1, 10.85),
                (10, 10.12),
                (100, 9.24)
            ],
            "package": "LQFP-100",
            "grade": ComponentGrade.INDUSTRIAL,
            "temp_min": -40,
            "temp_max": 85
        }
    },

    # Generic resistor (for testing passives)
    "RC0603FR-0710KL": {
        "mouser": {
            "mpn": "RC0603FR-0710KL",
            "manufacturer": "Yageo",
            "description": "Thick Film Resistors - SMD 10kOhm 1% 1/10W",
            "stock": 15420,
            "price_breaks": [
                (1, 0.10),
                (10, 0.012),
                (100, 0.004),
                (1000, 0.002)
            ],
            "package": "0603",
            "grade": ComponentGrade.COMMERCIAL,
            "temp_min": -55,
            "temp_max": 155
        }
    },

    # Generic capacitor
    "CL10B104KB8NNNC": {
        "mouser": {
            "mpn": "CL10B104KB8NNNC",
            "manufacturer": "Samsung Electro-Mechanics",
            "description": "Multilayer Ceramic Capacitors MLCC - SMD/SMT 0.1uF 50V X7R 0603",
            "stock": 8943,
            "price_breaks": [
                (1, 0.10),
                (10, 0.015),
                (100, 0.006),
                (1000, 0.003)
            ],
            "package": "0603",
            "grade": ComponentGrade.COMMERCIAL,
            "temp_min": -55,
            "temp_max": 125
        }
    }
}


def get_mock_component(mpn: str, distributor: str = "mouser") -> dict:
    """Get mock component data"""
    mpn_key = mpn.upper().split("-")[0]  # Handle part number variants

    # Try exact match first
    if mpn_key in MOCK_COMPONENTS:
        if distributor in MOCK_COMPONENTS[mpn_key]:
            return MOCK_COMPONENTS[mpn_key][distributor]

    # Search for partial matches
    for key, data in MOCK_COMPONENTS.items():
        if key in mpn.upper() or mpn.upper() in key:
            if distributor in data:
                return data[distributor]

    return None


def search_mock_alternatives(original_mpn: str, requirements: dict = None) -> list:
    """Search for alternatives based on requirements"""
    alternatives = []

    # Simple matching logic for demo
    if "LM2596" in original_mpn.upper():
        # Return automotive buck converter alternative
        alternatives.append("TPS54360-Q1")

    elif "SI4459" in original_mpn.upper():
        # Return higher-rated FET
        alternatives.append("Si4435BDY")

    # Filter by requirements if provided
    if requirements:
        required_grade = requirements.get("grade")
        temp_range = requirements.get("temp_range", [-40, 125])

        filtered = []
        for alt in alternatives:
            if alt in MOCK_COMPONENTS:
                data = MOCK_COMPONENTS[alt].get("mouser", {})
                grade = data.get("grade")
                temp_min = data.get("temp_min")
                temp_max = data.get("temp_max")

                # Check grade
                if required_grade:
                    if isinstance(required_grade, list):
                        if grade not in required_grade:
                            continue
                    elif grade != required_grade:
                        continue

                # Check temperature range
                if temp_min is not None and temp_max is not None:
                    if temp_min > temp_range[0] or temp_max < temp_range[1]:
                        continue

                filtered.append(alt)

        return filtered

    return alternatives


def convert_to_component_availability(mock_data: dict, mpn: str, distributor: Distributor) -> ComponentAvailability:
    """Convert mock data dict to ComponentAvailability object"""
    if not mock_data:
        return None

    price_breaks = [
        PriceBreak(quantity=qty, price=price)
        for qty, price in mock_data.get("price_breaks", [])
    ]

    return ComponentAvailability(
        mpn=mock_data.get("mpn", mpn),
        manufacturer=mock_data.get("manufacturer", "Unknown"),
        description=mock_data.get("description", ""),
        distributor=distributor,
        stock=mock_data.get("stock", 0),
        price_breaks=price_breaks,
        datasheet_url=mock_data.get("datasheet"),
        product_url=mock_data.get("product_url"),
        lead_time=mock_data.get("lead_time"),
        package=mock_data.get("package"),
        grade=mock_data.get("grade", ComponentGrade.UNKNOWN),
        temp_min=mock_data.get("temp_min"),
        temp_max=mock_data.get("temp_max"),
        specs=mock_data.get("specs", {})
    )
