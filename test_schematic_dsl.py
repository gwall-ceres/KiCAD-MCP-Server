#!/usr/bin/env python3
"""
Test script for KiCAD Schematic DSL tools
Tests the three new MCP tools:
1. get_schematic_index
2. get_schematic_page
3. get_schematic_context
"""
import sys
import os

# Add python directory to path
python_dir = os.path.join(os.path.dirname(__file__), 'python')
sys.path.insert(0, python_dir)

# Import directly to avoid pcbnew dependency
import importlib.util
spec = importlib.util.spec_from_file_location(
    "schematic_dsl",
    os.path.join(python_dir, "commands", "schematic_dsl.py")
)
schematic_dsl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(schematic_dsl)
SchematicDSLManager = schematic_dsl.SchematicDSLManager

# Test project path
PROJECT_PATH = r"C:\Users\geoff\Desktop\projects\kicad-astro-daughterboard2\Astro-DB_rev00005"

def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80 + "\n")

def test_get_schematic_index():
    """Test get_schematic_index command"""
    print_section("[1/3] Testing get_schematic_index")

    print(f"Project: {PROJECT_PATH}")

    result = SchematicDSLManager.get_schematic_index(PROJECT_PATH)

    if result['success']:
        print("\n[OK] get_schematic_index succeeded\n")
        # Handle Unicode on Windows console
        output = result['index'][:1000].encode('ascii', 'replace').decode('ascii')
        print(output)  # Print first 1000 chars
        print("\n... (output truncated)")
    else:
        print(f"\n[ERROR] get_schematic_index failed: {result['error']}")
        if 'details' in result:
            print(f"\nDetails:\n{result['details']}")

    return result['success']

def test_get_schematic_page():
    """Test get_schematic_page command"""
    print_section("[2/3] Testing get_schematic_page")

    page_name = "battery_charger"
    print(f"Project: {PROJECT_PATH}")
    print(f"Page: {page_name}")

    result = SchematicDSLManager.get_schematic_page(PROJECT_PATH, page_name)

    if result['success']:
        print(f"\n[OK] get_schematic_page succeeded for page '{result['page_name']}'\n")
        # Show first few lines of DSL (handle Unicode)
        lines = result['dsl'].split('\n')
        for line in lines[:30]:  # First 30 lines
            safe_line = line.encode('ascii', 'replace').decode('ascii')
            print(safe_line)
        print(f"\n... ({len(lines)} total lines)")
    else:
        print(f"\n[ERROR] get_schematic_page failed: {result['error']}")
        if 'hint' in result:
            print(f"\nHint: {result['hint']}")
        if 'details' in result:
            print(f"\nDetails:\n{result['details']}")

    return result['success']

def test_get_schematic_context():
    """Test get_schematic_context command"""
    print_section("[3/3] Testing get_schematic_context")

    # Test with a component
    component_ref = "Q200"
    print(f"Project: {PROJECT_PATH}")
    print(f"Component: {component_ref}")

    result = SchematicDSLManager.get_schematic_context(
        PROJECT_PATH,
        component_ref=component_ref
    )

    if result['success']:
        print(f"\n[OK] get_schematic_context succeeded for {result['context_id']}\n")
        # Handle Unicode on Windows console
        output = result['context'][:800].encode('ascii', 'replace').decode('ascii')
        print(output)  # First 800 chars
        print("\n... (output truncated)")
    else:
        print(f"\n[ERROR] get_schematic_context failed: {result['error']}")
        if 'details' in result:
            print(f"\nDetails:\n{result['details']}")

    return result['success']

def main():
    """Run all tests"""
    print_section("TESTING KICAD SCHEMATIC DSL SYSTEM")

    print(f"Python version: {sys.version}")
    print(f"Working directory: {os.getcwd()}")

    # Check if project exists
    if not os.path.exists(PROJECT_PATH):
        print(f"\n[ERROR] Test project not found: {PROJECT_PATH}")
        return 1

    # Run tests
    results = []
    results.append(("get_schematic_index", test_get_schematic_index()))
    results.append(("get_schematic_page", test_get_schematic_page()))
    results.append(("get_schematic_context", test_get_schematic_context()))

    # Print summary
    print_section("TEST SUMMARY")

    for test_name, success in results:
        status = "[OK]" if success else "[FAIL]"
        print(f"{status} {test_name}")

    passed = sum(1 for _, success in results if success)
    total = len(results)

    print(f"\nPassed: {passed}/{total}")

    return 0 if passed == total else 1

if __name__ == '__main__':
    sys.exit(main())
