#!/usr/bin/env python3
"""
Test getting a specific page's DSL output
"""
import sys
import os

# Add python directory to path
python_dir = os.path.join(os.path.dirname(__file__), 'python')
sys.path.insert(0, python_dir)

import importlib.util
spec = importlib.util.spec_from_file_location(
    "schematic_dsl",
    os.path.join(python_dir, "commands", "schematic_dsl.py")
)
schematic_dsl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(schematic_dsl)
SchematicDSLManager = schematic_dsl.SchematicDSLManager

PROJECT_PATH = r"C:\Users\geoff\Desktop\projects\kicad-astro-daughterboard2\Astro-DB_rev00005"

def main():
    print("=" * 80)
    print("Testing get_schematic_page() for battery_charger")
    print("=" * 80 + "\n")

    result = SchematicDSLManager.get_schematic_page(PROJECT_PATH, "battery_charger")

    if result['success']:
        output = result['dsl'].encode('ascii', 'replace').decode('ascii')
        print(output)
    else:
        print(f"Error: {result['error']}")
        if 'details' in result:
            print(f"\nDetails:\n{result['details']}")
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())
