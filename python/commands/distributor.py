"""
Distributor integration for component search and availability checking
"""
import os
import pcbnew
import logging
import asyncio
from typing import Dict, Any, Optional, List
from api_clients import MouserClient, DigiKeyClient

logger = logging.getLogger('kicad_interface')


class DistributorCommands:
    """Handles distributor-related operations (Mouser, DigiKey)"""

    def __init__(self, board: Optional[pcbnew.BOARD] = None):
        """Initialize with optional board instance"""
        self.board = board

    def _create_mouser_client(self):
        """Create a new Mouser client instance"""
        api_key = os.getenv('MOUSER_API_KEY')
        logger.info(f"Creating Mouser client, API key present: {bool(api_key)}")
        if api_key:
            return MouserClient(api_key=api_key)
        else:
            logger.debug("No MOUSER_API_KEY found, using mock mode")
            return MouserClient(use_mock=True)

    def _create_digikey_client(self):
        """Create a new DigiKey client instance"""
        client_id = os.getenv('DIGIKEY_CLIENT_ID')
        client_secret = os.getenv('DIGIKEY_CLIENT_SECRET')
        if client_id and client_secret:
            return DigiKeyClient(
                client_id=client_id,
                client_secret=client_secret
            )
        else:
            logger.debug("No DigiKey credentials found, using mock mode")
            return DigiKeyClient(use_mock=True)

    async def _search_all_distributors(self, query: str, distributors: Optional[List[str]] = None) -> Dict[str, Any]:
        """Search across all specified distributors"""
        active_distributors = distributors or ["mouser", "digikey"]
        logger.info(f"Searching distributors: {active_distributors} for query: {query}")
        results = []
        errors = []

        # Search Mouser if requested
        if "mouser" in active_distributors:
            try:
                async with self._create_mouser_client() as client:
                    dist_results = await client.search(query)
                    if dist_results:
                        results.extend(dist_results)
            except Exception as e:
                logger.warning(f"Error searching mouser: {e}")
                errors.append({"distributor": "mouser", "error": str(e)})

        # Search DigiKey if requested
        if "digikey" in active_distributors:
            try:
                async with self._create_digikey_client() as client:
                    dist_results = await client.search(query)
                    if dist_results:
                        results.extend(dist_results)
            except Exception as e:
                logger.warning(f"Error searching digikey: {e}")
                errors.append({"distributor": "digikey", "error": str(e)})

        return {
            "success": True,
            "query": query,
            "results": results,
            "total": len(results),
            "errors": errors if errors else None
        }

    async def _get_availability_all(self, mpn: str, distributors: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get availability from all specified distributors"""
        active_distributors = distributors or ["mouser", "digikey"]
        availability = {}
        errors = []

        # Get Mouser availability if requested
        if "mouser" in active_distributors:
            try:
                async with self._create_mouser_client() as client:
                    dist_avail = await client.get_availability(mpn)
                    if dist_avail:
                        availability["mouser"] = dist_avail
            except Exception as e:
                logger.warning(f"Error getting availability from mouser: {e}")
                errors.append({"distributor": "mouser", "error": str(e)})

        # Get DigiKey availability if requested
        if "digikey" in active_distributors:
            try:
                async with self._create_digikey_client() as client:
                    dist_avail = await client.get_availability(mpn)
                    if dist_avail:
                        availability["digikey"] = dist_avail
            except Exception as e:
                logger.warning(f"Error getting availability from digikey: {e}")
                errors.append({"distributor": "digikey", "error": str(e)})

        return {
            "success": True,
            "mpn": mpn,
            "availability": availability,
            "errors": errors if errors else None
        }

    async def search_component(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search for components by MPN or keyword"""
        try:
            query = params.get("query")
            if not query:
                return {
                    "success": False,
                    "message": "Missing query parameter"
                }

            distributors = params.get("distributors")

            # Run async search
            result = await self._search_all_distributors(query, distributors)
            return result

        except Exception as e:
            logger.error(f"Error searching component: {e}")
            return {
                "success": False,
                "message": f"Search failed: {str(e)}"
            }

    async def get_component_availability(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed availability and pricing for a specific component"""
        try:
            mpn = params.get("mpn")
            if not mpn:
                return {
                    "success": False,
                    "message": "Missing mpn parameter"
                }

            distributors = params.get("distributors")

            # Run async availability check
            result = await self._get_availability_all(mpn, distributors)
            return result

        except Exception as e:
            logger.error(f"Error getting component availability: {e}")
            return {
                "success": False,
                "message": f"Availability check failed: {str(e)}"
            }

    async def check_bom_availability(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Check availability for all components in the BOM"""
        try:
            if not self.board:
                return {
                    "success": False,
                    "message": "No board is loaded"
                }

            # Extract components from board
            components = []
            for footprint in self.board.GetFootprints():
                ref = footprint.GetReference()
                value = footprint.GetValue()
                # Try to find MPN from component properties
                mpn = None
                for prop in footprint.GetProperties():
                    if prop.lower() in ["mpn", "manpartno", "mfr_part_num"]:
                        mpn = footprint.GetProperties()[prop]
                        break

                if mpn:
                    components.append({
                        "reference": ref,
                        "value": value,
                        "mpn": mpn
                    })

            if not components:
                return {
                    "success": False,
                    "message": "No components with MPN found in board"
                }

            # Check availability for each component
            results = []
            for comp in components:
                avail = await self.get_component_availability({"mpn": comp["mpn"]})
                results.append({
                    "reference": comp["reference"],
                    "value": comp["value"],
                    "mpn": comp["mpn"],
                    "availability": avail.get("availability", {})
                })

            return {
                "success": True,
                "components": results,
                "total": len(results)
            }

        except Exception as e:
            logger.error(f"Error checking BOM availability: {e}")
            return {
                "success": False,
                "message": f"BOM check failed: {str(e)}"
            }

    async def find_component_alternatives(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Find alternative components for a specific part"""
        try:
            mpn = params.get("mpn")
            reason = params.get("reason", "unknown")

            if not mpn:
                return {
                    "success": False,
                    "message": "Missing mpn parameter"
                }

            # Get original component info
            original = await self.get_component_availability({"mpn": mpn})

            # Search for similar components (simplified - just search by base part number)
            base_part = mpn.split("-")[0] if "-" in mpn else mpn[:8]
            alternatives = await self.search_component({"query": base_part})

            return {
                "success": True,
                "mpn": mpn,
                "reason": reason,
                "original": original,
                "alternatives": alternatives.get("results", [])
            }

        except Exception as e:
            logger.error(f"Error finding alternatives: {e}")
            return {
                "success": False,
                "message": f"Alternative search failed: {str(e)}"
            }

    async def validate_bom_lifecycle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate lifecycle status of components in the BOM"""
        try:
            bom_check = await self.check_bom_availability(params)

            if not bom_check.get("success"):
                return bom_check

            # Analyze lifecycle status from availability data
            lifecycle_issues = []
            for comp in bom_check.get("components", []):
                avail = comp.get("availability", {})
                for dist, info in avail.items():
                    lifecycle = info.get("lifecycle_status", "unknown")
                    if lifecycle.lower() in ["obsolete", "nrnd", "discontinued"]:
                        lifecycle_issues.append({
                            "reference": comp["reference"],
                            "mpn": comp["mpn"],
                            "status": lifecycle,
                            "distributor": dist
                        })

            return {
                "success": True,
                "total_components": len(bom_check.get("components", [])),
                "issues": lifecycle_issues,
                "issue_count": len(lifecycle_issues)
            }

        except Exception as e:
            logger.error(f"Error validating BOM lifecycle: {e}")
            return {
                "success": False,
                "message": f"Lifecycle validation failed: {str(e)}"
            }

    async def compare_distributor_pricing(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Compare pricing across distributors for a component"""
        try:
            mpn = params.get("mpn")
            if not mpn:
                return {
                    "success": False,
                    "message": "Missing mpn parameter"
                }

            # Get availability from all distributors
            avail = await self.get_component_availability({"mpn": mpn})

            if not avail.get("success"):
                return avail

            # Extract and compare pricing
            pricing_comparison = []
            for dist, info in avail.get("availability", {}).items():
                pricing = info.get("pricing", [])
                if pricing:
                    best_price = min(pricing, key=lambda x: x.get("price_per_unit", float('inf')))
                    pricing_comparison.append({
                        "distributor": dist,
                        "stock": info.get("stock", 0),
                        "best_price": best_price.get("price_per_unit"),
                        "moq": best_price.get("quantity"),
                        "all_pricing": pricing
                    })

            # Sort by best price
            pricing_comparison.sort(key=lambda x: x.get("best_price", float('inf')))

            return {
                "success": True,
                "mpn": mpn,
                "pricing": pricing_comparison,
                "recommended": pricing_comparison[0] if pricing_comparison else None
            }

        except Exception as e:
            logger.error(f"Error comparing pricing: {e}")
            return {
                "success": False,
                "message": f"Pricing comparison failed: {str(e)}"
            }
