"""
Schematic DSL Commands for KiCAD MCP Server

Provides high-level schematic analysis using the schematic_core library.
Generates LLM-optimized DSL representations of KiCAD schematics.
"""
from pathlib import Path
import sys
import traceback

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from schematic_core.adapters.kicad_sch import KiCADSchematicAdapter
from schematic_core.librarian import Librarian


class SchematicDSLManager:
    """Manages schematic DSL extraction and analysis"""

    @staticmethod
    def get_schematic_index(project_path: str) -> dict:
        """
        Get a high-level index/overview of all schematic pages

        Args:
            project_path: Path to directory containing .kicad_sch files

        Returns:
            dict with 'success', 'index' or 'error'
        """
        try:
            adapter = KiCADSchematicAdapter(project_path)
            librarian = Librarian(adapter)
            index = librarian.get_index()

            return {
                "success": True,
                "index": index
            }

        except Exception as e:
            error_msg = f"Error generating schematic index: {str(e)}"
            traceback.print_exc()
            return {
                "success": False,
                "error": error_msg,
                "details": traceback.format_exc()
            }

    @staticmethod
    def get_schematic_page(project_path: str, page_name: str) -> dict:
        """
        Get detailed DSL representation of a specific schematic page

        Args:
            project_path: Path to directory containing .kicad_sch files
            page_name: Name of the schematic page (without .kicad_sch extension)

        Returns:
            dict with 'success', 'dsl' or 'error'
        """
        try:
            adapter = KiCADSchematicAdapter(project_path)
            librarian = Librarian(adapter)
            page_dsl = librarian.get_page(page_name)

            return {
                "success": True,
                "dsl": page_dsl,
                "page_name": page_name
            }

        except Exception as e:
            error_msg = f"Error generating schematic page DSL: {str(e)}"
            traceback.print_exc()
            return {
                "success": False,
                "error": error_msg,
                "details": traceback.format_exc(),
                "hint": "Use get_schematic_index to see all available pages"
            }

    @staticmethod
    def get_schematic_context(project_path: str, component_ref: str = None, net_name: str = None) -> dict:
        """
        Get contextual information about a component or net

        Args:
            project_path: Path to directory containing .kicad_sch files
            component_ref: Component designator (e.g., "Q1", "U200") - optional
            net_name: Net name to trace (e.g., "GND", "VBUS") - optional

        Returns:
            dict with 'success', 'context' or 'error'
        """
        try:
            if not component_ref and not net_name:
                return {
                    "success": False,
                    "error": "Please specify either component_ref or net_name"
                }

            adapter = KiCADSchematicAdapter(project_path)
            librarian = Librarian(adapter)

            if component_ref:
                context = librarian.get_context([component_ref])
                context_type = "component"
                context_id = component_ref
            elif net_name:
                # For net context, find all components connected to the net
                librarian.refresh()

                # Find the net
                net = librarian.get_net(net_name)
                if not net:
                    return {
                        "success": False,
                        "error": f"Net '{net_name}' not found in schematic"
                    }

                # Get all component refdes connected to this net
                connected_components = list(set(refdes for refdes, pin in net.members))

                # Generate context for all connected components
                context = librarian.get_context(connected_components)
                context_type = "net"
                context_id = net_name

            return {
                "success": True,
                "context": context,
                "context_type": context_type,
                "context_id": context_id
            }

        except Exception as e:
            error_msg = f"Error generating schematic context: {str(e)}"
            traceback.print_exc()
            return {
                "success": False,
                "error": error_msg,
                "details": traceback.format_exc()
            }


if __name__ == '__main__':
    # Test the DSL manager
    import json

    # Example project path - adjust as needed
    test_project = r"C:\Users\geoff\Desktop\projects\kicad-astro-daughterboard2\Astro-DB_rev00005"

    print("Testing Schematic DSL Manager")
    print("=" * 80)

    # Test 1: Index
    print("\n[TEST 1] get_schematic_index()")
    result = SchematicDSLManager.get_schematic_index(test_project)
    if result["success"]:
        print("SUCCESS - Index generated")
        print(result["index"][:500] + "...")
    else:
        print(f"FAILED - {result['error']}")

    # Test 2: Page
    print("\n[TEST 2] get_schematic_page('battery_charger')")
    result = SchematicDSLManager.get_schematic_page(test_project, "battery_charger")
    if result["success"]:
        print("SUCCESS - Page DSL generated")
        print(f"Page: {result['page_name']}")
        print(result["dsl"][:500] + "...")
    else:
        print(f"FAILED - {result['error']}")

    # Test 3: Component context
    print("\n[TEST 3] get_schematic_context(component_ref='Q200')")
    result = SchematicDSLManager.get_schematic_context(test_project, component_ref="Q200")
    if result["success"]:
        print("SUCCESS - Context generated")
        print(f"Type: {result['context_type']}, ID: {result['context_id']}")
        print(result["context"][:500] + "...")
    else:
        print(f"FAILED - {result['error']}")
