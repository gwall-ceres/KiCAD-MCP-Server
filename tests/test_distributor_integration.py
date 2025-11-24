"""
Test distributor command integration with kicad_interface
Simulates how the TypeScript MCP server calls the Python commands
"""
import json
import sys
from pathlib import Path

# Add to path
sys.path.insert(0, str(Path(__file__).parent))

# Import the command handler directly to avoid pcbnew dependency
import importlib.util
spec = importlib.util.spec_from_file_location(
    "distributor_commands",
    Path(__file__).parent / "commands" / "distributor_commands.py"
)
distributor_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(distributor_module)

DistributorCommands = distributor_module.DistributorCommands


def test_find_automotive_alternative():
    """Test finding automotive alternative"""
    print("\n" + "="*70)
    print("Test 1: Find Automotive Alternative Command")
    print("="*70)

    commands = DistributorCommands()

    # Simulate MCP command call
    params = {
        "mpn": "LM2596",
        "requirements": {
            "temp_range": [-40, 125],
            "grades": ["automotive", "industrial"]
        }
    }

    print(f"\nCalling find_automotive_alternative with params:")
    print(json.dumps(params, indent=2))

    result = commands.find_automotive_alternative(params)

    print(f"\nResult:")
    print(json.dumps(result, indent=2))

    if result.get("success"):
        print("\n[OK] Command succeeded")
        if result.get("best_alternative"):
            best = result["best_alternative"]
            print(f"Best alternative: {best['mpn']}")
            print(f"Price impact: ${best['price_difference']:+.2f} ({best['price_difference_pct']:+.1f}%)")
    else:
        print(f"\n[FAIL] Command failed: {result.get('message')}")


def test_search_component():
    """Test searching for component"""
    print("\n" + "="*70)
    print("Test 2: Search Component Command")
    print("="*70)

    commands = DistributorCommands()

    params = {"mpn": "TPS54360-Q1"}

    print(f"\nCalling search_component with params:")
    print(json.dumps(params, indent=2))

    result = commands.search_component(params)

    print(f"\nResult:")
    print(json.dumps(result, indent=2))

    if result.get("success"):
        print("\n[OK] Command succeeded")
        component = result.get("component", {})
        print(f"Found: {component.get('mpn')} ({component.get('manufacturer')})")
        print(f"Grade: {component.get('grade')}")
        print(f"Stock: {component.get('stock'):,}")
        print(f"Price: ${component.get('price'):.2f}")
    else:
        print(f"\n[FAIL] Command failed: {result.get('message')}")


def test_compare_availability():
    """Test comparing availability for multiple components"""
    print("\n" + "="*70)
    print("Test 3: Compare Availability Command")
    print("="*70)

    commands = DistributorCommands()

    params = {
        "components": ["LM2596", "TPS54360-Q1", "SI4435BDY"]
    }

    print(f"\nCalling compare_availability with params:")
    print(json.dumps(params, indent=2))

    result = commands.compare_availability(params)

    print(f"\nResult:")
    if result.get("success"):
        print(f"[OK] Found {result.get('total')} components")
        for comp in result.get("components", []):
            if comp.get("found", True):
                print(f"\n  {comp['mpn']}: {comp['stock']:,} in stock @ ${comp['price']:.2f}")
            else:
                print(f"\n  {comp['mpn']}: Not found")
    else:
        print(f"[FAIL] Command failed: {result.get('message')}")


def test_missing_mpn():
    """Test error handling when MPN is missing"""
    print("\n" + "="*70)
    print("Test 4: Error Handling (Missing MPN)")
    print("="*70)

    commands = DistributorCommands()

    params = {}  # No MPN

    print(f"\nCalling search_component with empty params (should fail)")

    result = commands.search_component(params)

    if not result.get("success"):
        print(f"\n[OK] Correctly returned error: {result.get('message')}")
    else:
        print(f"\n[FAIL] Should have failed but succeeded")


def test_mode_detection():
    """Test mock vs real API mode detection"""
    print("\n" + "="*70)
    print("Test 5: Mock/Real Mode Detection")
    print("="*70)

    import os

    # Check environment
    has_mouser = bool(os.environ.get('MOUSER_API_KEY'))
    has_digikey = bool(os.environ.get('DIGIKEY_CLIENT_ID') and os.environ.get('DIGIKEY_CLIENT_SECRET'))

    commands = DistributorCommands()

    print(f"\nEnvironment:")
    print(f"  MOUSER_API_KEY: {'Set' if has_mouser else 'Not set'}")
    print(f"  DIGIKEY_CLIENT_ID: {'Set' if has_digikey else 'Not set'}")
    print(f"  DIGIKEY_CLIENT_SECRET: {'Set' if has_digikey else 'Not set'}")

    print(f"\nMode detected: {'REAL API' if not commands.use_mock else 'MOCK MODE'}")

    if commands.use_mock:
        print("[INFO] Using mock data (no API keys found)")
    else:
        print("[INFO] Will use real API calls")


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("Distributor Command Integration Tests")
    print("="*70)

    try:
        test_mode_detection()
        test_find_automotive_alternative()
        test_search_component()
        test_compare_availability()
        test_missing_mpn()

        print("\n" + "="*70)
        print("[OK] All distributor command tests completed!")
        print("="*70)
        print("\nNext steps:")
        print("1. Rebuild TypeScript: npm run build")
        print("2. Test through Claude Code MCP tools")
        print("3. Get API keys for real testing")
        print("="*70 + "\n")

    except Exception as e:
        print(f"\n[FAIL] Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
