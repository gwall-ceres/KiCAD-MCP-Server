#!/usr/bin/env python3
"""
Analyze and explain KiCAD schematic design
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

PROJECT_PATH = r"C:\Users\geoff\Desktop\projects\kicad-astro-daughterboard2\Astro-DB_rev00005"

def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80 + "\n")

def main():
    print_section("ASTRO DAUGHTERBOARD REV00005 - SCHEMATIC ANALYSIS")

    # Get project index
    result = SchematicDSLManager.get_schematic_index(PROJECT_PATH)

    if result['success']:
        # Handle Unicode on Windows console
        output = result['index'].encode('ascii', 'replace').decode('ascii')
        print(output)
    else:
        print(f"Error: {result['error']}")
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())
