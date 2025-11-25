#!/usr/bin/env python3
"""
Comprehensive test script for KiCAD MCP Server tools.

This script tests all KiCAD API functions directly (without MCP layer) to:
1. Verify each function works correctly
2. Document the correct parameters and return values
3. Serve as reference for LLM agents using the MCP tools

Run with KiCAD's Python:
    "C:\Program Files\KiCad\9.0\bin\python.exe" tests/test_all_kicad_tools.py

Each test runs in isolation with a timeout to prevent hangs from blocking dialogs.
"""

import os
import sys
import json
import tempfile
import shutil
import subprocess
import traceback
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
import threading

# Timeout for each individual test (seconds)
TEST_TIMEOUT = 10

# Add the python directory to path
script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir / "python"))

# Test results tracking
class TestResults:
    def __init__(self):
        self.passed = []
        self.failed = []
        self.skipped = []
        self.timeout = []

    def add_pass(self, name: str, details: str = ""):
        self.passed.append((name, details))
        print(f"  ✅ PASS: {name}")
        if details:
            print(f"          {details}")

    def add_fail(self, name: str, error: str):
        self.failed.append((name, error))
        print(f"  ❌ FAIL: {name}")
        print(f"          Error: {error}")

    def add_skip(self, name: str, reason: str):
        self.skipped.append((name, reason))
        print(f"  ⏭️  SKIP: {name}")
        print(f"          Reason: {reason}")

    def add_timeout(self, name: str):
        self.timeout.append(name)
        print(f"  ⏰ TIMEOUT: {name}")
        print(f"          Test exceeded {TEST_TIMEOUT}s - likely a blocking dialog")

    def summary(self):
        total = len(self.passed) + len(self.failed) + len(self.skipped) + len(self.timeout)
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"Total:   {total}")
        print(f"Passed:  {len(self.passed)}")
        print(f"Failed:  {len(self.failed)}")
        print(f"Timeout: {len(self.timeout)}")
        print(f"Skipped: {len(self.skipped)}")

        if self.failed:
            print("\nFailed Tests:")
            for name, error in self.failed:
                print(f"  - {name}: {error}")

        if self.timeout:
            print("\nTimeout Tests (likely KiCAD API bugs with modal dialogs):")
            for name in self.timeout:
                print(f"  - {name}")

        return len(self.failed) == 0 and len(self.timeout) == 0


results = TestResults()


def run_with_timeout(func, timeout=TEST_TIMEOUT):
    """Run a function with a timeout. Returns (success, result_or_error)"""
    result = [None]
    error = [None]
    completed = threading.Event()

    def wrapper():
        try:
            result[0] = func()
        except Exception as e:
            error[0] = str(e) + "\n" + traceback.format_exc()
        finally:
            completed.set()

    thread = threading.Thread(target=wrapper)
    thread.daemon = True
    thread.start()

    if completed.wait(timeout):
        if error[0]:
            return False, error[0]
        return True, result[0]
    else:
        return None, "TIMEOUT"


def safe_test(name: str, func):
    """Run a test function safely with timeout handling"""
    success, result = run_with_timeout(func)

    if success is None:
        results.add_timeout(name)
        return None
    elif success:
        return result
    else:
        results.add_fail(name, result)
        return None


# =============================================================================
# SETUP - Import KiCAD modules
# =============================================================================

def setup_kicad():
    """Import and setup KiCAD modules"""
    print("Setting up KiCAD environment...")

    # Import platform helper to set up KiCAD paths
    from utils.platform_helper import PlatformHelper
    PlatformHelper.add_kicad_to_python_path()

    import pcbnew
    print(f"KiCAD Version: {pcbnew.GetBuildVersion()}")
    return pcbnew


# =============================================================================
# TEST FUNCTIONS
# =============================================================================

def test_project_commands(pcbnew, test_dir: Path):
    """Test project management commands"""
    print("\n" + "-"*60)
    print("TESTING: Project Commands")
    print("-"*60)

    from commands.project import ProjectCommands
    project_commands = ProjectCommands(None)

    # Test: create_project
    def test_create():
        result = project_commands.create_project({
            "path": str(test_dir),
            "projectName": "TestProject",
            "template": "blank"
        })
        if result.get("success"):
            results.add_pass("create_project", f"Created: {result['project']['name']}")
            return result
        else:
            results.add_fail("create_project", result.get("errorDetails", "Unknown error"))
            return None

    create_result = safe_test("create_project", test_create)

    # Test: get_project_info
    def test_get_info():
        result = project_commands.get_project_info({})
        if result.get("success"):
            results.add_pass("get_project_info", f"Project: {result['project']['name']}")
        else:
            results.add_fail("get_project_info", result.get("errorDetails", "Unknown error"))

    safe_test("get_project_info", test_get_info)

    # Test: save_project
    def test_save():
        result = project_commands.save_project({})
        if result.get("success"):
            results.add_pass("save_project", "Project saved")
        else:
            results.add_fail("save_project", result.get("errorDetails", "Unknown error"))

    safe_test("save_project", test_save)

    return project_commands.board


def test_board_commands(pcbnew, board):
    """Test board-related commands"""
    print("\n" + "-"*60)
    print("TESTING: Board Commands")
    print("-"*60)

    from commands.board import BoardCommands
    board_commands = BoardCommands(board)

    # Test: set_board_size
    def test_set_size():
        result = board_commands.set_board_size({
            "width": 100,
            "height": 80,
            "unit": "mm"
        })
        if result.get("success"):
            results.add_pass("set_board_size", f"Size: {result['size']['width']}x{result['size']['height']} mm")
        else:
            results.add_fail("set_board_size", result.get("errorDetails", "Unknown error"))

    safe_test("set_board_size", test_set_size)

    # Test: get_board_info
    def test_get_info():
        result = board_commands.get_board_info({})
        if result.get("success"):
            results.add_pass("get_board_info", f"Layers: {len(result['board']['layers'])}")
        else:
            results.add_fail("get_board_info", result.get("errorDetails", "Unknown error"))

    safe_test("get_board_info", test_get_info)

    # Test: get_layer_list
    def test_get_layers():
        result = board_commands.get_layer_list({})
        if result.get("success"):
            layer_names = [l['name'] for l in result['layers'][:5]]
            results.add_pass("get_layer_list", f"Layers: {layer_names}...")
        else:
            results.add_fail("get_layer_list", result.get("errorDetails", "Unknown error"))

    safe_test("get_layer_list", test_get_layers)

    # Test: get_board_extents
    def test_get_extents():
        result = board_commands.get_board_extents({"unit": "mm"})
        if result.get("success"):
            ext = result['extents']
            results.add_pass("get_board_extents", f"Extents: {ext['width']}x{ext['height']} mm")
        else:
            results.add_fail("get_board_extents", result.get("errorDetails", "Unknown error"))

    safe_test("get_board_extents", test_get_extents)

    # Test: add_mounting_hole
    def test_add_hole():
        result = board_commands.add_mounting_hole({
            "position": {"x": 5, "y": 5, "unit": "mm"},
            "diameter": 3.2
        })
        if result.get("success"):
            results.add_pass("add_mounting_hole", f"Hole: {result['mountingHole']['diameter']}mm")
        else:
            results.add_fail("add_mounting_hole", result.get("errorDetails", "Unknown error"))

    safe_test("add_mounting_hole", test_add_hole)

    # Test: add_text
    def test_add_text():
        result = board_commands.add_text({
            "text": "Test Board v1.0",
            "position": {"x": 50, "y": 75, "unit": "mm"},
            "layer": "F.Silkscreen",
            "size": 2
        })
        if result.get("success"):
            results.add_pass("add_board_text", f"Text: '{result['text']['text']}'")
        else:
            results.add_fail("add_board_text", result.get("errorDetails", "Unknown error"))

    safe_test("add_board_text", test_add_text)

    # NOTE: set_active_layer and add_layer removed from MCP server
    # They require GUI and don't work headlessly in KiCad 9

    return board_commands


def test_routing_commands(pcbnew, board):
    """Test routing-related commands"""
    print("\n" + "-"*60)
    print("TESTING: Routing Commands")
    print("-"*60)

    from commands.routing import RoutingCommands
    routing_commands = RoutingCommands(board)

    # Test: add_net (GND)
    def test_add_gnd():
        result = routing_commands.add_net({"name": "GND"})
        if result.get("success"):
            results.add_pass("add_net (GND)", f"Netcode: {result['net']['netcode']}")
        else:
            results.add_fail("add_net (GND)", result.get("errorDetails", "Unknown error"))

    safe_test("add_net (GND)", test_add_gnd)

    # Test: add_net (VCC)
    def test_add_vcc():
        result = routing_commands.add_net({"name": "VCC"})
        if result.get("success"):
            results.add_pass("add_net (VCC)", f"Netcode: {result['net']['netcode']}")
        else:
            results.add_fail("add_net (VCC)", result.get("errorDetails", "Unknown error"))

    safe_test("add_net (VCC)", test_add_vcc)

    # Test: route_trace
    def test_route():
        result = routing_commands.route_trace({
            "start": {"x": 10, "y": 10, "unit": "mm"},
            "end": {"x": 50, "y": 10, "unit": "mm"},
            "layer": "F.Cu",
            "width": 0.25,
            "net": "VCC"
        })
        if result.get("success"):
            results.add_pass("route_trace", f"Width: {result['trace']['width']}mm")
        else:
            results.add_fail("route_trace", result.get("errorDetails", "Unknown error"))

    safe_test("route_trace", test_route)

    # Test: add_via (KNOWN BUG - GetWidth needs layer argument in KiCAD 9)
    def test_add_via():
        result = routing_commands.add_via({
            "position": {"x": 30, "y": 10, "unit": "mm"},
            "net": "VCC"
        })
        if result.get("success"):
            results.add_pass("add_via", f"Via added")
        else:
            results.add_fail("add_via", result.get("errorDetails", "Unknown error"))

    safe_test("add_via", test_add_via)

    # Test: add_copper_pour (zone)
    def test_add_pour():
        result = routing_commands.add_copper_pour({
            "layer": "F.Cu",
            "net": "GND",
            "points": [
                {"x": 60, "y": 20, "unit": "mm"},
                {"x": 90, "y": 20, "unit": "mm"},
                {"x": 90, "y": 60, "unit": "mm"},
                {"x": 60, "y": 60, "unit": "mm"}
            ],
            "clearance": 0.3,
            "minWidth": 0.2
        })
        if result.get("success"):
            results.add_pass("add_copper_pour", f"Points: {result['pour']['pointCount']}")
        else:
            results.add_fail("add_copper_pour", result.get("errorDetails", "Unknown error"))

    safe_test("add_copper_pour", test_add_pour)

    # Test: get_nets_list
    def test_get_nets():
        result = routing_commands.get_nets_list({})
        if result.get("success"):
            net_names = [n['name'] for n in result['nets'][:5]]
            results.add_pass("get_nets_list", f"Nets: {net_names}")
        else:
            results.add_fail("get_nets_list", result.get("errorDetails", "Unknown error"))

    safe_test("get_nets_list", test_get_nets)

    return routing_commands


def test_component_commands(pcbnew, board):
    """Test component-related commands"""
    print("\n" + "-"*60)
    print("TESTING: Component Commands")
    print("-"*60)

    from commands.component import ComponentCommands
    from commands.library import LibraryManager

    library_manager = LibraryManager()
    component_commands = ComponentCommands(board, library_manager)

    # Test: get_component_list (should start empty)
    def test_get_list():
        result = component_commands.get_component_list({})
        if result.get("success"):
            count = len(result.get("components", []))
            results.add_pass("get_component_list", f"Components: {count}")
        else:
            results.add_fail("get_component_list", result.get("errorDetails", "Unknown error"))

    safe_test("get_component_list", test_get_list)

    # Test: place_component (need to find a valid footprint first)
    def test_place():
        # First search for a simple footprint
        footprints = library_manager.search_footprints("*R_0603*", limit=1)
        if not footprints:
            results.add_skip("place_component", "No footprints found in library")
            return None

        footprint_name = footprints[0]['full_name']

        result = component_commands.place_component({
            "componentId": footprint_name,
            "position": {"x": 20, "y": 20, "unit": "mm"},
            "reference": "R1",
            "value": "10k",
            "rotation": 0,
            "layer": "F.Cu"
        })
        if result.get("success"):
            results.add_pass("place_component", f"Placed: {result['component']['reference']}")
            return result
        else:
            results.add_fail("place_component", result.get("errorDetails", "Unknown error"))
            return None

    place_result = safe_test("place_component", test_place)

    # Test: find_component
    def test_find():
        result = component_commands.find_component({"reference": "R1"})
        if result.get("success"):
            results.add_pass("find_component", f"Found: {result['count']} component(s)")
        else:
            # Expected if place_component failed
            if place_result:
                results.add_fail("find_component", result.get("errorDetails", "Unknown error"))
            else:
                results.add_skip("find_component", "No component to find (place_component failed)")

    if place_result:
        safe_test("find_component", test_find)
    else:
        results.add_skip("find_component", "No component to find (place_component skipped)")

    # Test: get_component_properties
    def test_get_props():
        result = component_commands.get_component_properties({"reference": "R1"})
        if result.get("success"):
            comp = result['component']
            results.add_pass("get_component_properties", f"Reference: {comp['reference']}, Value: {comp['value']}")
        else:
            results.add_fail("get_component_properties", result.get("errorDetails", "Unknown error"))

    if place_result:
        safe_test("get_component_properties", test_get_props)
    else:
        results.add_skip("get_component_properties", "No component to get properties (place_component skipped)")

    # Test: move_component
    def test_move():
        result = component_commands.move_component({
            "reference": "R1",
            "position": {"x": 30, "y": 30, "unit": "mm"}
        })
        if result.get("success"):
            pos = result['component']['position']
            results.add_pass("move_component", f"Moved to: ({pos['x']}, {pos['y']})")
        else:
            results.add_fail("move_component", result.get("errorDetails", "Unknown error"))

    if place_result:
        safe_test("move_component", test_move)
    else:
        results.add_skip("move_component", "No component to move (place_component skipped)")

    # Test: rotate_component
    def test_rotate():
        result = component_commands.rotate_component({
            "reference": "R1",
            "angle": 90
        })
        if result.get("success"):
            results.add_pass("rotate_component", f"Rotated to: {result['component']['rotation']}°")
        else:
            results.add_fail("rotate_component", result.get("errorDetails", "Unknown error"))

    if place_result:
        safe_test("rotate_component", test_rotate)
    else:
        results.add_skip("rotate_component", "No component to rotate (place_component skipped)")

    # Test: edit_component
    def test_edit():
        result = component_commands.edit_component({
            "reference": "R1",
            "value": "100k"
        })
        if result.get("success"):
            results.add_pass("edit_component", f"Updated value to: {result['component']['value']}")
        else:
            results.add_fail("edit_component", result.get("errorDetails", "Unknown error"))

    if place_result:
        safe_test("edit_component", test_edit)
    else:
        results.add_skip("edit_component", "No component to edit (place_component skipped)")

    # Test: duplicate_component
    def test_duplicate():
        result = component_commands.duplicate_component({
            "reference": "R1",
            "newReference": "R2",
            "position": {"x": 40, "y": 30, "unit": "mm"}
        })
        if result.get("success"):
            results.add_pass("duplicate_component", f"Duplicated to: {result['component']['reference']}")
        else:
            results.add_fail("duplicate_component", result.get("errorDetails", "Unknown error"))

    if place_result:
        safe_test("duplicate_component", test_duplicate)
    else:
        results.add_skip("duplicate_component", "No component to duplicate (place_component skipped)")

    # Test: delete_component (delete the duplicate)
    def test_delete():
        result = component_commands.delete_component({"reference": "R2"})
        if result.get("success"):
            results.add_pass("delete_component", "Deleted R2")
        else:
            results.add_fail("delete_component", result.get("errorDetails", "Unknown error"))

    if place_result:
        safe_test("delete_component", test_delete)
    else:
        results.add_skip("delete_component", "No component to delete (place_component skipped)")

    return component_commands


def test_library_commands(pcbnew):
    """Test library management commands"""
    print("\n" + "-"*60)
    print("TESTING: Library Commands")
    print("-"*60)

    from commands.library import LibraryCommands, LibraryManager

    library_manager = LibraryManager()
    library_commands = LibraryCommands(library_manager)

    # Test: list_libraries
    def test_list():
        result = library_commands.list_libraries({})
        if result.get("success"):
            results.add_pass("list_libraries", f"Found: {result['count']} libraries")
            return result
        else:
            results.add_fail("list_libraries", result.get("errorDetails", "Unknown error"))
            return None

    list_result = safe_test("list_libraries", test_list)

    # Test: search_footprints
    def test_search():
        result = library_commands.search_footprints({"pattern": "*0603*", "limit": 10})
        if result.get("success"):
            results.add_pass("search_footprints", f"Found: {result['count']} footprints matching *0603*")
        else:
            results.add_fail("search_footprints", result.get("errorDetails", "Unknown error"))

    safe_test("search_footprints", test_search)

    # Test: list_library_footprints
    def test_list_footprints():
        # Get a library name from the list
        if not list_result or not list_result.get("libraries"):
            results.add_skip("list_library_footprints", "No libraries available")
            return

        library_name = list_result['libraries'][0] if list_result['libraries'] else None
        if not library_name:
            results.add_skip("list_library_footprints", "No libraries available")
            return

        result = library_commands.list_library_footprints({"library": library_name})
        if result.get("success"):
            results.add_pass("list_library_footprints", f"Library '{library_name}': {result['count']} footprints")
        else:
            results.add_fail("list_library_footprints", result.get("errorDetails", "Unknown error"))

    safe_test("list_library_footprints", test_list_footprints)

    # Test: get_footprint_info
    def test_get_info():
        # Search for a footprint to get info about
        search_result = library_manager.search_footprints("*0603*", limit=1)
        if not search_result:
            results.add_skip("get_footprint_info", "No footprints found to get info")
            return

        footprint_spec = search_result[0]['full_name']
        result = library_commands.get_footprint_info({"footprint": footprint_spec})
        if result.get("success"):
            info = result['footprint_info']
            results.add_pass("get_footprint_info", f"Footprint: {info['full_name']}")
        else:
            results.add_fail("get_footprint_info", result.get("errorDetails", "Unknown error"))

    safe_test("get_footprint_info", test_get_info)

    return library_commands


def test_design_rule_commands(pcbnew, board):
    """Test design rule commands"""
    print("\n" + "-"*60)
    print("TESTING: Design Rule Commands")
    print("-"*60)

    from commands.design_rules import DesignRuleCommands
    dr_commands = DesignRuleCommands(board)

    # Test: get_design_rules
    def test_get_rules():
        result = dr_commands.get_design_rules({})
        if result.get("success"):
            rules = result['rules']
            results.add_pass("get_design_rules", f"Track width: {rules['trackWidth']}mm")
        else:
            results.add_fail("get_design_rules", result.get("errorDetails", "Unknown error"))

    safe_test("get_design_rules", test_get_rules)

    # Test: set_design_rules
    def test_set_rules():
        result = dr_commands.set_design_rules({
            "clearance": 0.2,
            "trackWidth": 0.25,
            "viaDiameter": 0.6,
            "viaDrill": 0.3
        })
        if result.get("success"):
            results.add_pass("set_design_rules", "Rules updated")
        else:
            results.add_fail("set_design_rules", result.get("errorDetails", "Unknown error"))

    safe_test("set_design_rules", test_set_rules)

    # Test: run_drc
    def test_run_drc():
        result = dr_commands.run_drc({})
        if result.get("success"):
            results.add_pass("run_drc", f"Violations: {result['summary']['total']}")
        else:
            results.add_fail("run_drc", result.get("errorDetails", "Unknown error"))

    safe_test("run_drc", test_run_drc)

    # Test: get_drc_violations
    def test_get_violations():
        result = dr_commands.get_drc_violations({"limit": 10})
        if result.get("success"):
            results.add_pass("get_drc_violations", f"Returned: {result['returned']} of {result['total']}")
        else:
            results.add_fail("get_drc_violations", result.get("errorDetails", "Unknown error"))

    safe_test("get_drc_violations", test_get_violations)

    return dr_commands


def test_export_commands(pcbnew, board, test_dir: Path):
    """Test export commands"""
    print("\n" + "-"*60)
    print("TESTING: Export Commands")
    print("-"*60)

    from commands.export import ExportCommands
    export_commands = ExportCommands(board)
    export_dir = test_dir / "exports"
    export_dir.mkdir(exist_ok=True)

    # Test: export_bom CSV
    def test_bom_csv():
        result = export_commands.export_bom({
            "outputPath": str(export_dir / "test_bom.csv"),
            "format": "CSV"
        })
        if result.get("success"):
            results.add_pass("export_bom (CSV)", f"Components: {result['file']['componentCount']}")
        else:
            results.add_fail("export_bom (CSV)", result.get("errorDetails", "Unknown error"))

    safe_test("export_bom (CSV)", test_bom_csv)

    # Test: export_gerber
    def test_gerber():
        gerber_dir = export_dir / "gerber"
        gerber_dir.mkdir(exist_ok=True)
        result = export_commands.export_gerber({
            "outputDir": str(gerber_dir)
        })
        if result.get("success"):
            results.add_pass("export_gerber", f"Files: {len(result['files']['gerber'])}")
        else:
            results.add_fail("export_gerber", result.get("errorDetails", "Unknown error"))

    safe_test("export_gerber", test_gerber)

    # Test: export_pdf
    def test_pdf():
        result = export_commands.export_pdf({
            "outputPath": str(export_dir / "test_board.pdf")
        })
        if result.get("success"):
            results.add_pass("export_pdf", "Exported")
        else:
            results.add_fail("export_pdf", result.get("errorDetails", "Unknown error"))

    safe_test("export_pdf", test_pdf)

    # Test: export_svg
    def test_svg():
        result = export_commands.export_svg({
            "outputPath": str(export_dir / "test_board.svg")
        })
        if result.get("success"):
            results.add_pass("export_svg", "Exported")
        else:
            results.add_fail("export_svg", result.get("errorDetails", "Unknown error"))

    safe_test("export_svg", test_svg)

    return export_commands


def test_schematic_dsl():
    """Test schematic DSL commands"""
    print("\n" + "-"*60)
    print("TESTING: Schematic DSL Commands")
    print("-"*60)

    from commands.schematic_dsl import SchematicDSLManager

    # Check if there's a test project with schematics
    test_project = Path(r"c:\Users\geoff\Desktop\projects\kicad-astro-daughterboard2\Astro-DB_rev00005")

    if not test_project.exists():
        results.add_skip("get_schematic_index", "No test project with schematics")
        results.add_skip("get_schematic_page", "No test project with schematics")
        results.add_skip("get_schematic_context", "No test project with schematics")
        return

    # Test: get_schematic_index
    def test_index():
        result = SchematicDSLManager.get_schematic_index(str(test_project))
        if result.get("success"):
            index = result.get("index", "")
            page_count = index.count("components,")
            results.add_pass("get_schematic_index", f"Found {page_count} pages")
        else:
            results.add_fail("get_schematic_index", result.get("errorDetails", "Unknown error"))

    safe_test("get_schematic_index", test_index)

    # Test: get_schematic_page
    def test_page():
        result = SchematicDSLManager.get_schematic_page(str(test_project), "Power_Supplies")
        if result.get("success"):
            dsl = result.get("dsl", "")
            comp_count = dsl.count("COMP ")
            results.add_pass("get_schematic_page", f"Page has {comp_count} components")
        else:
            results.add_fail("get_schematic_page", result.get("errorDetails", "Unknown error"))

    safe_test("get_schematic_page", test_page)

    # Test: get_schematic_context
    def test_context():
        result = SchematicDSLManager.get_schematic_context(str(test_project), component_ref="U501")
        if result.get("success"):
            results.add_pass("get_schematic_context", f"Context type: {result.get('context_type')}")
        else:
            results.add_fail("get_schematic_context", result.get("errorDetails", "Unknown error"))

    safe_test("get_schematic_context", test_context)


def test_distributor_commands():
    """Test distributor API commands (async)"""
    print("\n" + "-"*60)
    print("TESTING: Distributor Commands")
    print("-"*60)

    import asyncio
    from commands.distributor import DistributorCommands

    dist_commands = DistributorCommands(None)

    # Test: search_component
    def test_search():
        async def _search():
            return await dist_commands.search_component({"query": "STM32F407VGT6"})

        result = asyncio.run(_search())
        if result.get("success"):
            count = result.get("total", len(result.get("results", [])))
            results.add_pass("search_component", f"Found {count} results")
        else:
            results.add_fail("search_component", result.get("errorDetails", "Unknown error"))

    safe_test("search_component", test_search)

    # Test: get_component_availability
    def test_availability():
        async def _avail():
            return await dist_commands.get_component_availability({"mpn": "STM32F407VGT6"})

        result = asyncio.run(_avail())
        if result.get("success"):
            avail = result.get("availability", {})
            sources = list(avail.keys())
            results.add_pass("get_component_availability", f"Sources: {sources}")
        else:
            results.add_fail("get_component_availability", result.get("errorDetails", "Unknown error"))

    safe_test("get_component_availability", test_availability)


def main():
    print("="*60)
    print("KiCAD MCP Server - Comprehensive Tool Test")
    print("="*60)
    print(f"Python Version: {sys.version}")
    print(f"Test Timeout: {TEST_TIMEOUT}s per test")

    # Setup KiCAD
    try:
        pcbnew = setup_kicad()
    except Exception as e:
        print(f"❌ Failed to setup KiCAD: {e}")
        return 1

    # Create temporary test directory
    test_dir = Path(tempfile.mkdtemp(prefix="kicad_mcp_test_"))
    print(f"Test Directory: {test_dir}")

    try:
        # Run all tests
        board = test_project_commands(pcbnew, test_dir)

        if board:
            test_board_commands(pcbnew, board)
            test_routing_commands(pcbnew, board)
            test_component_commands(pcbnew, board)  # Component tests before design rules
            test_library_commands(pcbnew)  # Library tests (doesn't require board)
            test_design_rule_commands(pcbnew, board)
            test_export_commands(pcbnew, board, test_dir)
        else:
            print("\n⚠️  No board created, skipping board-dependent tests")

        test_schematic_dsl()
        test_distributor_commands()

        # Print summary
        success = results.summary()

        # Save results to file
        results_file = script_dir / "test_results.json"
        with open(results_file, "w") as f:
            json.dump({
                "passed": results.passed,
                "failed": results.failed,
                "skipped": results.skipped,
                "timeout": results.timeout
            }, f, indent=2)
        print(f"\nResults saved to: {results_file}")

        return 0 if success else 1

    finally:
        # Cleanup
        print(f"\nCleaning up test directory: {test_dir}")
        try:
            shutil.rmtree(test_dir)
        except Exception as e:
            print(f"Warning: Could not clean up: {e}")


if __name__ == "__main__":
    sys.exit(main())
