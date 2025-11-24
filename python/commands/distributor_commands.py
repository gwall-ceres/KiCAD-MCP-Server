"""
Distributor API command implementations for KiCAD interface
Handles component availability checking and automotive alternative finding
"""

import os
import logging
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger('kicad_interface')


class DistributorCommands:
    """Handles distributor API operations for component availability and alternatives"""

    def __init__(self):
        """Initialize distributor commands"""
        # Load environment variables from .env file
        env_path = Path(__file__).parent.parent.parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)

        # Get API keys from environment
        self.mouser_api_key = os.environ.get('MOUSER_API_KEY')
        self.digikey_client_id = os.environ.get('DIGIKEY_CLIENT_ID')
        self.digikey_client_secret = os.environ.get('DIGIKEY_CLIENT_SECRET')

        # Determine if we should use mock mode (no API keys = mock mode)
        self.use_mock = not (self.mouser_api_key or (self.digikey_client_id and self.digikey_client_secret))

        if self.use_mock:
            logger.info("Distributor commands running in MOCK MODE (no API keys found)")
        else:
            logger.info("Distributor commands using REAL API calls")

    def find_automotive_alternative(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Find automotive/industrial alternative for a component

        Args:
            params: {
                "mpn": str - Manufacturer part number,
                "requirements": {
                    "temp_range": [min, max] - Optional temperature range,
                    "grades": [str] - Optional acceptable grades,
                    "min_stock": int - Optional minimum stock,
                    "same_footprint": bool - Optional footprint requirement,
                    "max_price_increase_pct": float - Optional max price increase
                }
            }

        Returns:
            Dict with success status and alternative component info
        """
        try:
            mpn = params.get('mpn')
            if not mpn:
                return {
                    "success": False,
                    "message": "Missing required parameter: mpn",
                    "errorDetails": "MPN (manufacturer part number) is required"
                }

            # Import async function (import directly to avoid pcbnew dependency)
            import sys
            import importlib.util
            from pathlib import Path

            parent_dir = Path(__file__).parent.parent
            if str(parent_dir) not in sys.path:
                sys.path.insert(0, str(parent_dir))

            # Import distributor module directly without triggering commands/__init__.py
            spec = importlib.util.spec_from_file_location(
                "distributor",
                Path(__file__).parent / "distributor.py"
            )
            distributor = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(distributor)

            find_automotive_alternative = distributor.find_automotive_alternative
            ComponentRequirements = distributor.ComponentRequirements

            from api_clients.types import ComponentGrade

            # Build requirements
            requirements_data = params.get('requirements', {})
            requirements = ComponentRequirements(
                temp_range=tuple(requirements_data.get('temp_range', [-40, 125])),
                grades=[
                    ComponentGrade(g.lower())
                    for g in requirements_data.get('grades', ['automotive', 'industrial'])
                ],
                min_stock=requirements_data.get('min_stock', 0),
                same_footprint=requirements_data.get('same_footprint', True),
                max_price_increase_pct=requirements_data.get('max_price_increase_pct', 50.0)
            )

            # Run async function
            logger.debug(f"Finding automotive alternative for {mpn}")
            result = asyncio.run(find_automotive_alternative(
                mpn=mpn,
                requirements=requirements,
                use_mock=self.use_mock,
                mouser_api_key=self.mouser_api_key,
                digikey_client_id=self.digikey_client_id,
                digikey_client_secret=self.digikey_client_secret
            ))

            return result

        except Exception as e:
            logger.error(f"Error finding automotive alternative: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Error finding automotive alternative: {str(e)}",
                "errorDetails": str(e)
            }

    def search_component(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search for component by MPN

        Args:
            params: {
                "mpn": str - Manufacturer part number,
                "distributors": [str] - Optional distributor list
            }

        Returns:
            Dict with component availability info
        """
        try:
            mpn = params.get('mpn')
            if not mpn:
                return {
                    "success": False,
                    "message": "Missing required parameter: mpn",
                    "errorDetails": "MPN is required"
                }

            # Import async function (import directly to avoid pcbnew dependency)
            import sys
            import importlib.util
            from pathlib import Path

            parent_dir = Path(__file__).parent.parent
            if str(parent_dir) not in sys.path:
                sys.path.insert(0, str(parent_dir))

            # Import distributor module directly
            spec = importlib.util.spec_from_file_location(
                "distributor",
                Path(__file__).parent / "distributor.py"
            )
            distributor = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(distributor)

            _get_component_info = distributor._get_component_info

            logger.debug(f"Searching for component: {mpn}")
            result = asyncio.run(_get_component_info(
                mpn=mpn,
                use_mock=self.use_mock,
                mouser_api_key=self.mouser_api_key,
                digikey_client_id=self.digikey_client_id,
                digikey_client_secret=self.digikey_client_secret
            ))

            if result:
                # Import directly to avoid pcbnew dependency
                import importlib.util
                spec = importlib.util.spec_from_file_location(
                    "distributor",
                    Path(__file__).parent / "distributor.py"
                )
                distributor = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(distributor)
                _component_to_dict = distributor._component_to_dict

                return {
                    "success": True,
                    "component": _component_to_dict(result)
                }
            else:
                return {
                    "success": False,
                    "message": f"Component {mpn} not found",
                    "errorDetails": "Component not found in Mouser or DigiKey"
                }

        except Exception as e:
            logger.error(f"Error searching component: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Error searching component: {str(e)}",
                "errorDetails": str(e)
            }

    def get_availability(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get component availability and pricing

        Alias for search_component
        """
        return self.search_component(params)

    def check_bom_compliance(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check BOM for automotive/aviation compliance

        Args:
            params: {
                "temp_range": [min, max] - Temperature requirements,
                "required_grades": [str] - Required component grades
            }

        Returns:
            Dict with compliance status for all components
        """
        try:
            # TODO: Implement BOM reading from KiCAD project
            # For now, return a placeholder
            return {
                "success": False,
                "message": "BOM compliance checking not yet implemented",
                "errorDetails": "This feature requires BOM export integration"
            }

        except Exception as e:
            logger.error(f"Error checking BOM compliance: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Error checking BOM compliance: {str(e)}",
                "errorDetails": str(e)
            }

    def find_bom_alternatives(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Find automotive alternatives for multiple BOM components

        Args:
            params: {
                "component_types": [str] - Component prefixes (e.g., ["U", "Q"]),
                "priority": str - Priority level,
                "requirements": {} - Component requirements
            }

        Returns:
            Dict with alternatives for each component
        """
        try:
            # TODO: Implement batch alternative finding
            return {
                "success": False,
                "message": "Batch BOM alternatives not yet implemented",
                "errorDetails": "This feature requires BOM export integration"
            }

        except Exception as e:
            logger.error(f"Error finding BOM alternatives: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Error finding BOM alternatives: {str(e)}",
                "errorDetails": str(e)
            }

    def compare_availability(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare availability for multiple components

        Args:
            params: {
                "components": [str] - List of MPNs to compare
            }

        Returns:
            Dict with availability comparison
        """
        try:
            components = params.get('components', [])
            if not components:
                return {
                    "success": False,
                    "message": "Missing required parameter: components",
                    "errorDetails": "List of component MPNs is required"
                }

            # Import async function (import directly to avoid pcbnew dependency)
            import sys
            import importlib.util
            from pathlib import Path

            parent_dir = Path(__file__).parent.parent
            if str(parent_dir) not in sys.path:
                sys.path.insert(0, str(parent_dir))

            # Import distributor module directly
            spec = importlib.util.spec_from_file_location(
                "distributor",
                Path(__file__).parent / "distributor.py"
            )
            distributor = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(distributor)

            _get_component_info = distributor._get_component_info
            _component_to_dict = distributor._component_to_dict

            results = []
            for mpn in components:
                logger.debug(f"Checking availability for: {mpn}")
                component = asyncio.run(_get_component_info(
                    mpn=mpn,
                    use_mock=self.use_mock,
                    mouser_api_key=self.mouser_api_key,
                    digikey_client_id=self.digikey_client_id,
                    digikey_client_secret=self.digikey_client_secret
                ))

                if component:
                    results.append(_component_to_dict(component))
                else:
                    results.append({
                        "mpn": mpn,
                        "found": False,
                        "message": "Component not found"
                    })

            return {
                "success": True,
                "components": results,
                "total": len(results)
            }

        except Exception as e:
            logger.error(f"Error comparing availability: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Error comparing availability: {str(e)}",
                "errorDetails": str(e)
            }

    def generate_substitution_report(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate component substitution report

        Args:
            params: {
                "from_revision": str - Source revision,
                "to_revision": str - Target revision,
                "substitutions": [{original_mpn, replacement_mpn, reference, reason}]
            }

        Returns:
            Dict with report generation status
        """
        try:
            # TODO: Implement substitution report generation
            return {
                "success": False,
                "message": "Substitution report generation not yet implemented",
                "errorDetails": "This feature will be implemented in a future update"
            }

        except Exception as e:
            logger.error(f"Error generating substitution report: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Error generating substitution report: {str(e)}",
                "errorDetails": str(e)
            }
