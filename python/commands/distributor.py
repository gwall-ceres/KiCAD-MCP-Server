"""
Component matching and automotive alternative finder
Core logic for finding automotive/industrial replacements
"""
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import asyncio

from api_clients import MouserClient, DigiKeyClient
from api_clients.types import (
    ComponentAvailability,
    ComponentGrade,
    AlternativeComponent,
    Distributor
)
from api_clients.mock_data import search_mock_alternatives


@dataclass
class ComponentRequirements:
    """Requirements for component replacement"""
    temp_range: Tuple[float, float] = (-40, 125)  # Default: aviation requirements
    grades: List[ComponentGrade] = None  # Acceptable grades
    min_stock: int = 0
    same_footprint: bool = True
    max_price_increase_pct: float = 50.0  # Max 50% price increase acceptable


async def find_automotive_alternative(
    mpn: str,
    requirements: Optional[ComponentRequirements] = None,
    use_mock: bool = False,
    mouser_api_key: Optional[str] = None,
    digikey_client_id: Optional[str] = None,
    digikey_client_secret: Optional[str] = None
) -> Dict[str, Any]:
    """
    Find automotive/industrial alternative for a component

    Args:
        mpn: Manufacturer part number of original component
        requirements: ComponentRequirements object (default: aviation grade)
        use_mock: Use mock data (for testing without API keys)
        mouser_api_key: Mouser API key
        digikey_client_id: DigiKey client ID
        digikey_client_secret: DigiKey client secret

    Returns:
        Dictionary with:
        - original: Original component info
        - alternatives: List of alternative components
        - best_alternative: Recommended replacement
        - analysis: Detailed comparison
    """
    if requirements is None:
        requirements = ComponentRequirements(
            temp_range=(-40, 125),
            grades=[ComponentGrade.AUTOMOTIVE, ComponentGrade.INDUSTRIAL]
        )

    # Step 1: Get original component info
    original = await _get_component_info(
        mpn,
        use_mock,
        mouser_api_key,
        digikey_client_id,
        digikey_client_secret
    )

    if not original:
        return {
            "success": False,
            "error": f"Original component '{mpn}' not found",
            "mpn": mpn
        }

    # Step 2: Check if original already meets requirements
    if _meets_requirements(original, requirements):
        return {
            "success": True,
            "mpn": mpn,
            "original": _component_to_dict(original),
            "already_compliant": True,
            "message": f"{mpn} already meets aviation requirements"
        }

    # Step 3: Search for alternatives
    alternatives = await _search_alternatives(
        mpn,
        original,
        requirements,
        use_mock,
        mouser_api_key,
        digikey_client_id,
        digikey_client_secret
    )

    if not alternatives:
        return {
            "success": True,
            "mpn": mpn,
            "original": _component_to_dict(original),
            "alternatives": [],
            "message": f"No suitable alternatives found for {mpn}"
        }

    # Step 4: Score and rank alternatives
    scored_alternatives = []
    for alt in alternatives:
        score = _score_alternative(original, alt, requirements)
        scored_alternatives.append({
            "component": alt,
            "score": score,
            "comparison": _compare_components(original, alt)
        })

    # Sort by score (highest first)
    scored_alternatives.sort(key=lambda x: x["score"], reverse=True)

    # Best alternative is highest scored
    best = scored_alternatives[0] if scored_alternatives else None

    return {
        "success": True,
        "mpn": mpn,
        "original": _component_to_dict(original),
        "alternatives": [
            {
                "mpn": a["component"].mpn,
                "manufacturer": a["component"].manufacturer,
                "distributor": a["component"].distributor.value,
                "stock": a["component"].stock,
                "price": a["component"].unit_price,
                "grade": a["component"].grade.value,
                "temp_range": [a["component"].temp_min, a["component"].temp_max],
                "aviation_suitable": a["component"].is_aviation_suitable,
                "score": a["score"],
                "comparison": a["comparison"]
            }
            for a in scored_alternatives[:5]  # Top 5 alternatives
        ],
        "best_alternative": {
            "mpn": best["component"].mpn,
            "manufacturer": best["component"].manufacturer,
            "reason": _generate_recommendation_reason(original, best["component"]),
            "price_difference": best["component"].unit_price - original.unit_price,
            "price_difference_pct": (
                (best["component"].unit_price - original.unit_price) / original.unit_price * 100
                if original.unit_price > 0 else 0
            )
        } if best else None
    }


async def _get_component_info(
    mpn: str,
    use_mock: bool,
    mouser_api_key: Optional[str],
    digikey_client_id: Optional[str],
    digikey_client_secret: Optional[str]
) -> Optional[ComponentAvailability]:
    """Get component info from both Mouser and DigiKey, return best match"""

    results = []

    # Try Mouser
    try:
        async with MouserClient(api_key=mouser_api_key, use_mock=use_mock) as mouser:
            mouser_result = await mouser.search_by_mpn(mpn)
            if mouser_result:
                results.append(mouser_result)
    except Exception as e:
        print(f"Mouser search error: {e}")

    # Try DigiKey
    try:
        async with DigiKeyClient(
            client_id=digikey_client_id,
            client_secret=digikey_client_secret,
            use_mock=use_mock
        ) as digikey:
            digikey_result = await digikey.search_by_mpn(mpn)
            if digikey_result:
                results.append(digikey_result)
    except Exception as e:
        print(f"DigiKey search error: {e}")

    # Return result with best stock availability
    if not results:
        return None

    return max(results, key=lambda x: x.stock)


async def _search_alternatives(
    original_mpn: str,
    original: ComponentAvailability,
    requirements: ComponentRequirements,
    use_mock: bool,
    mouser_api_key: Optional[str],
    digikey_client_id: Optional[str],
    digikey_client_secret: Optional[str]
) -> List[ComponentAvailability]:
    """
    Search for alternative components

    Strategy:
    1. Use mock search (if enabled) to get known alternatives
    2. Extract component type from original (e.g., "buck converter", "MOSFET")
    3. Search by keyword with filters
    4. Filter results by requirements
    """
    alternatives = []

    # For mock mode, use predefined alternatives
    if use_mock:
        mock_alternatives = search_mock_alternatives(original_mpn, {
            "grade": requirements.grades,
            "temp_range": requirements.temp_range
        })

        for alt_mpn in mock_alternatives:
            alt_component = await _get_component_info(
                alt_mpn,
                use_mock,
                mouser_api_key,
                digikey_client_id,
                digikey_client_secret
            )
            if alt_component and _meets_requirements(alt_component, requirements):
                alternatives.append(alt_component)

        return alternatives

    # Real API search would go here
    # TODO: Implement intelligent keyword search based on original component
    # For now, return empty list (will be implemented with real APIs)

    return alternatives


def _meets_requirements(
    component: ComponentAvailability,
    requirements: ComponentRequirements
) -> bool:
    """Check if component meets requirements"""

    # Check temperature range
    if component.temp_min is None or component.temp_max is None:
        return False

    temp_min, temp_max = requirements.temp_range
    if component.temp_min > temp_min or component.temp_max < temp_max:
        return False

    # Check grade if specified
    if requirements.grades:
        if component.grade not in requirements.grades:
            return False

    # Check minimum stock
    if component.stock < requirements.min_stock:
        return False

    return True


def _score_alternative(
    original: ComponentAvailability,
    alternative: ComponentAvailability,
    requirements: ComponentRequirements
) -> float:
    """
    Score an alternative component (0-100, higher is better)

    Scoring factors:
    - Grade quality (automotive > industrial > commercial)
    - Temperature margin
    - Stock availability
    - Price (prefer cheaper or similar)
    - Same manufacturer (bonus)
    """
    score = 0.0

    # Grade score (30 points max)
    grade_scores = {
        ComponentGrade.AUTOMOTIVE: 30,
        ComponentGrade.INDUSTRIAL: 25,
        ComponentGrade.MILITARY: 20,
        ComponentGrade.COMMERCIAL: 10,
        ComponentGrade.UNKNOWN: 0
    }
    score += grade_scores.get(alternative.grade, 0)

    # Temperature margin score (20 points max)
    if alternative.temp_min is not None and alternative.temp_max is not None:
        required_min, required_max = requirements.temp_range
        temp_margin_low = required_min - alternative.temp_min  # Extra margin below
        temp_margin_high = alternative.temp_max - required_max  # Extra margin above

        # Give points for exceeding requirements
        if temp_margin_low >= 0 and temp_margin_high >= 0:
            score += 20
        elif temp_margin_low >= -10 and temp_margin_high >= -10:
            score += 10

    # Stock availability score (20 points max)
    if alternative.stock >= 1000:
        score += 20
    elif alternative.stock >= 100:
        score += 15
    elif alternative.stock >= 10:
        score += 10
    elif alternative.stock > 0:
        score += 5

    # Price score (20 points max)
    if original.unit_price > 0 and alternative.unit_price > 0:
        price_ratio = alternative.unit_price / original.unit_price

        if price_ratio <= 0.9:  # Cheaper
            score += 20
        elif price_ratio <= 1.0:  # Same price
            score += 18
        elif price_ratio <= 1.2:  # Up to 20% more expensive
            score += 15
        elif price_ratio <= 1.5:  # Up to 50% more expensive
            score += 10

    # Same manufacturer bonus (10 points)
    if original.manufacturer.lower() == alternative.manufacturer.lower():
        score += 10

    return score


def _compare_components(
    original: ComponentAvailability,
    alternative: ComponentAvailability
) -> Dict[str, Any]:
    """Generate side-by-side comparison"""

    return {
        "manufacturer": {
            "original": original.manufacturer,
            "alternative": alternative.manufacturer,
            "same": original.manufacturer.lower() == alternative.manufacturer.lower()
        },
        "grade": {
            "original": original.grade.value,
            "alternative": alternative.grade.value,
            "better": _is_grade_better(alternative.grade, original.grade)
        },
        "temperature": {
            "original": [original.temp_min, original.temp_max],
            "alternative": [alternative.temp_min, alternative.temp_max],
            "better": (
                alternative.temp_min is not None and
                alternative.temp_max is not None and
                original.temp_min is not None and
                original.temp_max is not None and
                alternative.temp_min <= original.temp_min and
                alternative.temp_max >= original.temp_max
            )
        },
        "price": {
            "original": original.unit_price,
            "alternative": alternative.unit_price,
            "difference": alternative.unit_price - original.unit_price,
            "difference_pct": (
                (alternative.unit_price - original.unit_price) / original.unit_price * 100
                if original.unit_price > 0 else 0
            ),
            "cheaper": alternative.unit_price < original.unit_price
        },
        "stock": {
            "original": original.stock,
            "alternative": alternative.stock,
            "better": alternative.stock > original.stock
        }
    }


def _is_grade_better(grade1: ComponentGrade, grade2: ComponentGrade) -> bool:
    """Check if grade1 is better than grade2"""
    grade_hierarchy = {
        ComponentGrade.MILITARY: 4,
        ComponentGrade.AUTOMOTIVE: 3,
        ComponentGrade.INDUSTRIAL: 2,
        ComponentGrade.COMMERCIAL: 1,
        ComponentGrade.UNKNOWN: 0
    }
    return grade_hierarchy.get(grade1, 0) > grade_hierarchy.get(grade2, 0)


def _generate_recommendation_reason(
    original: ComponentAvailability,
    alternative: ComponentAvailability
) -> str:
    """Generate human-readable recommendation reason"""

    reasons = []

    # Grade improvement
    if _is_grade_better(alternative.grade, original.grade):
        reasons.append(f"Upgraded to {alternative.grade.value} grade")

    # Temperature range improvement
    if (alternative.temp_min is not None and alternative.temp_max is not None and
        original.temp_min is not None and original.temp_max is not None):
        if alternative.temp_min < original.temp_min or alternative.temp_max > original.temp_max:
            reasons.append(
                f"Better temperature range ({alternative.temp_min}C to {alternative.temp_max}C "
                f"vs {original.temp_min}C to {original.temp_max}C)"
            )

    # Aviation suitable
    if alternative.is_aviation_suitable and not original.is_aviation_suitable:
        reasons.append("Meets aviation requirements (-40C to 125C)")

    # Price
    if alternative.unit_price < original.unit_price:
        savings = original.unit_price - alternative.unit_price
        reasons.append(f"Costs less (save ${savings:.2f} per unit)")
    elif alternative.unit_price > original.unit_price:
        increase = alternative.unit_price - original.unit_price
        reasons.append(f"Costs ${increase:.2f} more per unit for higher grade")

    # Stock
    if alternative.stock > original.stock:
        reasons.append(f"Better availability ({alternative.stock:,} in stock)")

    return "; ".join(reasons) if reasons else "Meets requirements"


def _component_to_dict(component: ComponentAvailability) -> Dict[str, Any]:
    """Convert ComponentAvailability to dictionary"""
    return {
        "mpn": component.mpn,
        "manufacturer": component.manufacturer,
        "description": component.description,
        "distributor": component.distributor.value,
        "stock": component.stock,
        "price": component.unit_price,
        "grade": component.grade.value,
        "temp_range": [component.temp_min, component.temp_max],
        "package": component.package,
        "aviation_suitable": component.is_aviation_suitable,
        "datasheet_url": component.datasheet_url,
        "product_url": component.product_url
    }


def check_aviation_compliance(component: ComponentAvailability) -> Dict[str, Any]:
    """
    Check if component meets aviation requirements

    Aviation requirements:
    - Temperature range: -40°C to +125°C minimum
    - Preferably automotive (AEC-Q) or industrial grade
    """
    compliant = component.is_aviation_suitable

    issues = []
    if component.temp_min is None or component.temp_max is None:
        issues.append("Temperature range not specified")
    elif component.temp_min > -40:
        issues.append(f"Min temperature {component.temp_min}C > -40C requirement")
    elif component.temp_max < 125:
        issues.append(f"Max temperature {component.temp_max}C < 125C requirement")

    if component.grade == ComponentGrade.COMMERCIAL:
        issues.append("Commercial grade (prefer automotive/industrial)")

    return {
        "mpn": component.mpn,
        "compliant": compliant,
        "grade": component.grade.value,
        "temp_range": [component.temp_min, component.temp_max],
        "issues": issues,
        "recommendation": (
            "Component meets aviation requirements" if compliant
            else f"Upgrade needed: {'; '.join(issues)}"
        )
    }
