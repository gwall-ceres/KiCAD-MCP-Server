"""
DigiKey API V4 client with OAuth2 authentication
"""
from typing import Dict, Any, Optional, List
import json
from pathlib import Path
from .base_client import BaseDistributorClient
from .types import ComponentAvailability, PriceBreak, Distributor, ComponentGrade
from .mock_data import get_mock_component, convert_to_component_availability


class DigiKeyClient(BaseDistributorClient):
    """
    DigiKey API V4 client

    API Documentation: https://developer.digikey.com/products/product-information-v4
    Rate Limits: 1,000 requests/day (free tier)
    Authentication: OAuth2 Client Credentials
    """

    BASE_URL = "https://api.digikey.com/v1/api/v4"
    TOKEN_URL = "https://api.digikey.com/v1/oauth2/token"

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        use_mock: bool = False,
        token_cache_path: Optional[str] = None
    ):
        """
        Initialize DigiKey client

        Args:
            client_id: DigiKey OAuth2 client ID
            client_secret: DigiKey OAuth2 client secret
            use_mock: Use mock data instead of real API (for testing)
            token_cache_path: Path to cache OAuth2 tokens (default: .digikey_tokens.json)
        """
        super().__init__(
            rate_limit=30,  # Conservative rate limit
            cache_ttl=3600,  # 1 hour cache
            use_mock=use_mock
        )

        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token: Optional[str] = None
        self.token_cache_path = token_cache_path or ".digikey_tokens.json"

        if not use_mock and (not client_id or not client_secret):
            raise ValueError("Client ID and secret required when not using mock mode")

    async def _get_access_token(self) -> str:
        """
        Get OAuth2 access token (with caching)

        Returns:
            Access token string

        Raises:
            Exception if authentication fails
        """
        # Check if we have a cached valid token
        if self.access_token:
            return self.access_token

        # Try to load from file cache
        cached_token = self._load_cached_token()
        if cached_token:
            self.access_token = cached_token
            return cached_token

        # Request new token using client credentials flow
        if not self.session:
            raise RuntimeError("Client not initialized. Use async with context manager.")

        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials"
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        try:
            async with self.session.post(
                self.TOKEN_URL,
                data=payload,
                headers=headers
            ) as response:
                response.raise_for_status()
                token_data = await response.json()

                self.access_token = token_data["access_token"]
                self._save_cached_token(token_data)

                return self.access_token

        except Exception as e:
            raise Exception(f"DigiKey OAuth2 authentication failed: {e}")

    def _load_cached_token(self) -> Optional[str]:
        """Load access token from file cache"""
        try:
            cache_path = Path(self.token_cache_path)
            if cache_path.exists():
                with open(cache_path, 'r') as f:
                    token_data = json.load(f)
                    # TODO: Check expiration time
                    return token_data.get("access_token")
        except Exception:
            pass
        return None

    def _save_cached_token(self, token_data: Dict[str, Any]):
        """Save access token to file cache"""
        try:
            with open(self.token_cache_path, 'w') as f:
                json.dump(token_data, f)
        except Exception as e:
            print(f"Warning: Failed to cache DigiKey token: {e}")

    async def _build_headers(self) -> Dict[str, str]:
        """Build request headers with OAuth2 token"""
        token = await self._get_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "X-DIGIKEY-Client-Id": self.client_id,
            "Content-Type": "application/json",
            "Accept": "application/json"
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
            mock_data = get_mock_component(mpn, "digikey")
            if mock_data:
                return convert_to_component_availability(
                    mock_data, mpn, Distributor.DIGIKEY
                )
            return None

        # Real API call - use keyword search with exact MPN
        url = f"{self.BASE_URL}/Search/Keyword"
        headers = await self._build_headers()

        payload = {
            "Keywords": mpn,
            "RecordCount": 1,
            "RecordStartPosition": 0,
            "Filters": {
                "ManufacturerPartNumber": {
                    "FilterType": "Exact",
                    "Values": [mpn]
                }
            }
        }

        try:
            response = await self._post(
                url,
                headers=headers,
                json_data=payload,
                use_cache=True
            )

            # Parse DigiKey response
            return self._parse_search_response(response, mpn)

        except Exception as e:
            print(f"DigiKey API error searching for {mpn}: {e}")
            return None

    def _parse_search_response(
        self,
        response: Dict[str, Any],
        mpn: str
    ) -> Optional[ComponentAvailability]:
        """
        Parse DigiKey V4 API search response

        DigiKey V4 Response Structure:
        {
            "ProductsCount": 1,
            "Products": [
                {
                    "ManufacturerPartNumber": "...",
                    "Manufacturer": {"Name": "..."},
                    "ProductDescription": "...",
                    "PrimaryDatasheet": "...",
                    "ProductUrl": "...",
                    "QuantityAvailable": 1234,
                    "StandardPricing": [
                        {"BreakQuantity": 1, "UnitPrice": 3.10}
                    ],
                    "ManufacturerProductStatus": "Active",
                    "Packaging": {"Name": "..."},
                    ...
                }
            ]
        }
        """
        try:
            products = response.get("Products", [])

            if not products:
                return None

            # Take first result
            product = products[0]

            # Parse stock
            stock = product.get("QuantityAvailable", 0)

            # Parse price breaks
            price_breaks = []
            for pb in product.get("StandardPricing", []):
                try:
                    quantity = int(pb.get("BreakQuantity", 0))
                    price = float(pb.get("UnitPrice", 0.0))
                    price_breaks.append(PriceBreak(quantity, price, "USD"))
                except (ValueError, KeyError):
                    continue

            # Extract manufacturer info
            manufacturer_data = product.get("Manufacturer", {})
            manufacturer = manufacturer_data.get("Name", "Unknown")

            # Extract packaging info
            packaging_data = product.get("Packaging", {})
            package = packaging_data.get("Name")

            # Extract temperature rating and grade from parameters
            temp_min = None
            temp_max = None
            grade = ComponentGrade.UNKNOWN

            parameters = product.get("Parameters", [])
            for param in parameters:
                param_name = param.get("Parameter", "").lower()

                # Operating temperature
                if "operating temperature" in param_name:
                    value = param.get("Value", "")
                    temp_min, temp_max = self._parse_temperature_range(value)

                # Automotive qualification
                if "automotive" in value.lower() or "aec-q" in value.lower():
                    grade = ComponentGrade.AUTOMOTIVE
                elif "industrial" in value.lower():
                    grade = ComponentGrade.INDUSTRIAL

            # Build ComponentAvailability object
            return ComponentAvailability(
                mpn=product.get("ManufacturerPartNumber", mpn),
                manufacturer=manufacturer,
                description=product.get("ProductDescription", ""),
                distributor=Distributor.DIGIKEY,
                stock=stock,
                price_breaks=price_breaks,
                datasheet_url=product.get("PrimaryDatasheet"),
                product_url=product.get("ProductUrl"),
                lead_time=product.get("StandardLeadTime"),
                package=package,
                grade=grade,
                temp_min=temp_min,
                temp_max=temp_max,
                specs={}
            )

        except Exception as e:
            print(f"Error parsing DigiKey response: {e}")
            return None

    def _parse_temperature_range(self, temp_str: str) -> tuple[Optional[float], Optional[float]]:
        """
        Parse temperature range string like "-40°C to 125°C"

        Returns:
            Tuple of (min_temp, max_temp) or (None, None) if parsing fails
        """
        try:
            # Common formats:
            # "-40°C to 125°C"
            # "-40 to 125 °C"
            # "-40°C ~ 125°C"
            import re

            # Extract numbers
            matches = re.findall(r'-?\d+', temp_str)
            if len(matches) >= 2:
                return (float(matches[0]), float(matches[1]))

        except Exception:
            pass

        return (None, None)

    async def get_component_details(self, digikey_part_number: str) -> Dict[str, Any]:
        """
        Get detailed component information

        Args:
            digikey_part_number: DigiKey's part number

        Returns:
            Detailed component data
        """
        if self.use_mock:
            return await self.search_by_mpn(digikey_part_number)

        # Use ProductDetails endpoint for more detailed info
        url = f"{self.BASE_URL}/ProductDetails/{digikey_part_number}"
        headers = await self._build_headers()

        try:
            response = await self._get(url, headers=headers, use_cache=True)
            return response
        except Exception as e:
            print(f"DigiKey API error getting details for {digikey_part_number}: {e}")
            return None

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
            return []

        # Real API call
        url = f"{self.BASE_URL}/Search/Keyword"
        headers = await self._build_headers()

        payload = {
            "Keywords": keyword,
            "RecordCount": 50,  # Max results to return
            "RecordStartPosition": 0,
            "Filters": {}
        }

        # Add filters if provided
        if filters:
            if "manufacturer" in filters:
                payload["Filters"]["Manufacturer"] = {
                    "FilterType": "Exact",
                    "Values": [filters["manufacturer"]]
                }

        try:
            response = await self._post(
                url,
                headers=headers,
                json_data=payload,
                use_cache=True
            )

            # Parse results
            results = []
            products = response.get("Products", [])

            for product in products:
                component = self._parse_search_response(
                    {"Products": [product]},
                    product.get("ManufacturerPartNumber", "")
                )

                if component:
                    # Apply additional filters
                    if filters:
                        if not self._apply_filters(component, filters):
                            continue
                    results.append(component)

            return results

        except Exception as e:
            print(f"DigiKey API error searching keyword '{keyword}': {e}")
            return []

    def _apply_filters(
        self,
        component: ComponentAvailability,
        filters: Dict[str, Any]
    ) -> bool:
        """Apply filters to a component (same as Mouser)"""
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
