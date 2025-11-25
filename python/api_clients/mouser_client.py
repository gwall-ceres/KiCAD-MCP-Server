"""
Mouser Electronics API client
Based on sparkmicro/mouser-api patterns with mock support
"""
from typing import Dict, Any, Optional, List
from .base_client import BaseDistributorClient
from .types import ComponentAvailability, PriceBreak, Distributor, ComponentGrade
from .mock_data import get_mock_component, convert_to_component_availability


class MouserClient(BaseDistributorClient):
    """
    Mouser Electronics API client

    API Documentation: https://api.mouser.com/api/docs/ui/index
    Rate Limits: 1,000 requests/day, 30 requests/minute
    """

    BASE_URL = "https://api.mouser.com/api/v1"

    def __init__(self, api_key: Optional[str] = None, use_mock: bool = False):
        """
        Initialize Mouser client

        Args:
            api_key: Mouser API key (from https://www.mouser.com/api-hub/)
            use_mock: Use mock data instead of real API (for testing)
        """
        super().__init__(
            rate_limit=30,  # 30 requests/minute
            cache_ttl=3600,  # 1 hour cache
            use_mock=use_mock
        )
        self.api_key = api_key

        if not use_mock and not api_key:
            raise ValueError("API key required when not using mock mode")

    def _build_headers(self) -> Dict[str, str]:
        """Build request headers with API key"""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _build_search_request(self, mpn: str) -> Dict[str, Any]:
        """
        Build Mouser search request payload

        Args:
            mpn: Manufacturer part number

        Returns:
            Request payload dict
        """
        return {
            "SearchByPartRequest": {
                "mouserPartNumber": mpn,
                "partSearchOptions": ""
            }
        }

    async def search_by_mpn(self, mpn: str) -> ComponentAvailability:
        """
        Search for component by manufacturer part number

        Args:
            mpn: Manufacturer part number

        Returns:
            ComponentAvailability object or None if not found
        """
        # Use mock data if enabled
        if self.use_mock:
            mock_data = get_mock_component(mpn, "mouser")
            if mock_data:
                return convert_to_component_availability(
                    mock_data, mpn, Distributor.MOUSER
                )
            return None

        # Real API call
        url = f"{self.BASE_URL}/search/partnumber"
        params = {"apiKey": self.api_key}
        payload = self._build_search_request(mpn)

        try:
            response = await self._post(
                url,
                headers=self._build_headers(),
                params=params,
                json_data=payload,
                use_cache=True
            )

            # Parse Mouser response
            return self._parse_search_response(response, mpn)

        except Exception as e:
            print(f"Mouser API error searching for {mpn}: {e}")
            return None

    def _parse_search_response(
        self,
        response: Dict[str, Any],
        mpn: str
    ) -> Optional[ComponentAvailability]:
        """
        Parse Mouser API search response

        Mouser Response Structure:
        {
            "SearchResults": {
                "NumberOfResult": 1,
                "Parts": [
                    {
                        "MouserPartNumber": "...",
                        "Manufacturer": "...",
                        "Description": "...",
                        "DataSheetUrl": "...",
                        "ProductDetailUrl": "...",
                        "Availability": "1,234 In Stock",
                        "PriceBreaks": [
                            {"Quantity": 1, "Price": "$3.10", "Currency": "USD"}
                        ],
                        "LifecycleStatus": "Active",
                        "PackageType": "TO-263",
                        ...
                    }
                ]
            }
        }
        """
        try:
            search_results = response.get("SearchResults", {})
            parts = search_results.get("Parts", [])

            if not parts:
                return None

            # Find first part with stock available (skip restricted/unavailable parts)
            part = None
            for p in parts:
                availability = p.get("Availability")
                # Check if part has availability info and is not restricted
                if availability and "In Stock" in availability:
                    part = p
                    break

            # If no part with stock, take first result anyway
            if not part:
                part = parts[0]

            # Parse stock availability
            availability_str = part.get("Availability", "0 In Stock")
            stock = 0
            try:
                stock = int(availability_str.split()[0].replace(",", ""))
            except (ValueError, IndexError):
                stock = 0

            # Parse price breaks
            price_breaks = []
            for pb in part.get("PriceBreaks", []):
                try:
                    quantity = int(pb.get("Quantity", 0))
                    price_str = pb.get("Price", "$0.00").replace("$", "").replace(",", "")
                    price = float(price_str)
                    currency = pb.get("Currency", "USD")
                    price_breaks.append(PriceBreak(quantity, price, currency))
                except (ValueError, KeyError):
                    continue

            # Extract temperature rating from description/specs if available
            # This would require parsing product attributes
            temp_min = None
            temp_max = None
            grade = ComponentGrade.UNKNOWN

            # Check lifecycle status (can be None, so handle safely)
            lifecycle_status = part.get("LifecycleStatus")
            lifecycle = lifecycle_status.lower() if lifecycle_status else ""

            # Build ComponentAvailability object
            return ComponentAvailability(
                mpn=part.get("ManufacturerPartNumber", mpn),
                manufacturer=part.get("Manufacturer", "Unknown"),
                description=part.get("Description", ""),
                distributor=Distributor.MOUSER,
                stock=stock,
                price_breaks=price_breaks,
                datasheet_url=part.get("DataSheetUrl"),
                product_url=part.get("ProductDetailUrl"),
                lead_time=part.get("LeadTime"),
                package=part.get("PackageType"),
                grade=grade,
                temp_min=temp_min,
                temp_max=temp_max,
                specs={}
            )

        except Exception as e:
            print(f"Error parsing Mouser response: {e}")
            return None

    async def get_component_details(self, mouser_part_number: str) -> Dict[str, Any]:
        """
        Get detailed component information from Mouser

        Args:
            mouser_part_number: Mouser's part number

        Returns:
            Detailed component data
        """
        # For now, use the same search endpoint
        # Mouser doesn't have a separate "details" endpoint
        return await self.search_by_mpn(mouser_part_number)

    async def search_by_keyword(
        self,
        keyword: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ComponentAvailability]:
        """
        Search for components by keyword with optional filters

        Args:
            keyword: Search keyword (e.g., "buck converter automotive")
            filters: Optional search filters
                - manufacturer: str
                - category: str
                - min_stock: int
                - grade: ComponentGrade

        Returns:
            List of ComponentAvailability objects
        """
        # Use mock data if enabled
        if self.use_mock:
            # Simple mock implementation - just return empty list for now
            return []

        # Real API call
        url = f"{self.BASE_URL}/search/keyword"
        params = {"apiKey": self.api_key}

        payload = {
            "SearchByKeywordRequest": {
                "keyword": keyword,
                "records": 0,  # 0 = return all results
                "startingRecord": 0,
                "searchOptions": "",
                "searchWithYourSignUpLanguage": ""
            }
        }

        try:
            response = await self._post(
                url,
                headers=self._build_headers(),
                params=params,
                json_data=payload,
                use_cache=True
            )

            # Parse results
            results = []
            parts = response.get("SearchResults", {}).get("Parts", [])

            for part in parts:
                component = self._parse_search_response(
                    {"SearchResults": {"Parts": [part]}},
                    part.get("ManufacturerPartNumber", "")
                )

                if component:
                    # Apply filters if provided
                    if filters:
                        if not self._apply_filters(component, filters):
                            continue
                    results.append(component)

            return results

        except Exception as e:
            print(f"Mouser API error searching keyword '{keyword}': {e}")
            return []

    def _apply_filters(
        self,
        component: ComponentAvailability,
        filters: Dict[str, Any]
    ) -> bool:
        """
        Apply filters to a component

        Returns:
            True if component passes all filters, False otherwise
        """
        # Manufacturer filter
        if "manufacturer" in filters:
            if component.manufacturer.lower() != filters["manufacturer"].lower():
                return False

        # Minimum stock filter
        if "min_stock" in filters:
            if component.stock < filters["min_stock"]:
                return False

        # Grade filter
        if "grade" in filters:
            required_grade = filters["grade"]
            if isinstance(required_grade, ComponentGrade):
                if component.grade != required_grade:
                    return False

        # Temperature range filter
        if "temp_range" in filters:
            temp_min, temp_max = filters["temp_range"]
            if component.temp_min is None or component.temp_max is None:
                return False
            if component.temp_min > temp_min or component.temp_max < temp_max:
                return False

        return True
