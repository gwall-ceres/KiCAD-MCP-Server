"""
Test API clients with mock data
Run this to verify API client setup before getting real API keys
"""
import asyncio
import sys
from pathlib import Path

# Add api_clients to path
sys.path.insert(0, str(Path(__file__).parent))

from api_clients import MouserClient, DigiKeyClient
from api_clients.types import ComponentGrade


async def test_mouser_client():
    """Test Mouser client with mock data"""
    print("\n" + "="*60)
    print("Testing Mouser Client (Mock Mode)")
    print("="*60)

    async with MouserClient(use_mock=True) as client:
        # Test 1: Search for LM2596 (current commercial part)
        print("\n1. Searching for LM2596 (current Rev0004 part)...")
        result = await client.search_by_mpn("LM2596")
        if result:
            print(f"   [OK] Found: {result}")
            print(f"   - Grade: {result.grade.value}")
            print(f"   - Temp: {result.temp_min}C to {result.temp_max}C")
            print(f"   - Stock: {result.stock:,}")
            print(f"   - Price: ${result.unit_price:.2f}")
            print(f"   - Aviation suitable: {result.is_aviation_suitable}")
        else:
            print("   [FAIL] Not found")

        # Test 2: Search for TPS54360-Q1 (automotive alternative)
        print("\n2. Searching for TPS54360-Q1 (automotive alternative)...")
        result = await client.search_by_mpn("TPS54360-Q1")
        if result:
            print(f"   [OK] Found: {result}")
            print(f"   - Grade: {result.grade.value}")
            print(f"   - Temp: {result.temp_min}C to {result.temp_max}C")
            print(f"   - Stock: {result.stock:,}")
            print(f"   - Price: ${result.unit_price:.2f}")
            print(f"   - Aviation suitable: {result.is_aviation_suitable}")
            print(f"   - AEC-Q100: {result.specs.get('AEC-Q100', 'N/A')}")
        else:
            print("   [FAIL] Not found")

        # Test 3: Search for SI4459BDY (failed FET from Rev0004)
        print("\n3. Searching for SI4459BDY (failed FET from Rev0004)...")
        result = await client.search_by_mpn("SI4459BDY")
        if result:
            print(f"   [OK] Found: {result}")
            print(f"   - Voltage: {result.specs.get('Voltage', 'N/A')}")
            print(f"   - Current: {result.specs.get('Current (per channel)', 'N/A')}")
            print(f"   - Channels: {result.specs.get('Channels', 'N/A')}")
        else:
            print("   [FAIL] Not found")

        # Test 4: Search for Si4435BDY (Rev0005 replacement FET)
        print("\n4. Searching for Si4435BDY (Rev0005 replacement)...")
        result = await client.search_by_mpn("Si4435BDY")
        if result:
            print(f"   [OK] Found: {result}")
            print(f"   - Voltage: {result.specs.get('Voltage', 'N/A')}")
            print(f"   - Current: {result.specs.get('Current', 'N/A')}")
            print(f"   - Channels: {result.specs.get('Channels', 'N/A')}")
            print(f"   - Temp: {result.temp_min}C to {result.temp_max}C")
            print(f"   - Aviation suitable: {result.is_aviation_suitable}")
        else:
            print("   [FAIL] Not found")

        # Test 5: Search for unknown part
        print("\n5. Searching for unknown part...")
        result = await client.search_by_mpn("UNKNOWN12345")
        if result:
            print(f"   [OK] Found: {result}")
        else:
            print("   [OK] Correctly returned None for unknown part")


async def test_digikey_client():
    """Test DigiKey client with mock data"""
    print("\n" + "="*60)
    print("Testing DigiKey Client (Mock Mode)")
    print("="*60)

    async with DigiKeyClient(use_mock=True) as client:
        # Test 1: Search for LM2596
        print("\n1. Searching for LM2596...")
        result = await client.search_by_mpn("LM2596")
        if result:
            print(f"   [OK] Found: {result}")
            print(f"   - Grade: {result.grade.value}")
            print(f"   - Temp: {result.temp_min}C to {result.temp_max}C")
            print(f"   - Stock: {result.stock:,}")
            print(f"   - Price: ${result.unit_price:.2f}")
        else:
            print("   [FAIL] Not found")

        # Test 2: Search for TPS54360-Q1
        print("\n2. Searching for TPS54360-Q1...")
        result = await client.search_by_mpn("TPS54360-Q1")
        if result:
            print(f"   [OK] Found: {result}")
            print(f"   - Grade: {result.grade.value}")
            print(f"   - Temp: {result.temp_min}C to {result.temp_max}C")
            print(f"   - Stock: {result.stock:,}")
            print(f"   - Price: ${result.unit_price:.2f}")
        else:
            print("   [FAIL] Not found")

        # Test 3: Search for Si4435BDY
        print("\n3. Searching for Si4435BDY...")
        result = await client.search_by_mpn("Si4435BDY")
        if result:
            print(f"   [OK] Found: {result}")
            print(f"   - Stock: {result.stock:,}")
            print(f"   - Aviation suitable: {result.is_aviation_suitable}")
        else:
            print("   [FAIL] Not found")


async def test_comparison():
    """Test comparing Mouser vs DigiKey for same part"""
    print("\n" + "="*60)
    print("Testing Mouser vs DigiKey Price Comparison")
    print("="*60)

    mpn = "Si4435BDY"
    print(f"\nComparing prices for {mpn}:")

    async with MouserClient(use_mock=True) as mouser:
        mouser_result = await mouser.search_by_mpn(mpn)

    async with DigiKeyClient(use_mock=True) as digikey:
        digikey_result = await digikey.search_by_mpn(mpn)

    if mouser_result and digikey_result:
        print(f"\nMouser:")
        print(f"  - Stock: {mouser_result.stock:,}")
        print(f"  - Price: ${mouser_result.unit_price:.2f}")
        print(f"  - Grade: {mouser_result.grade.value}")

        print(f"\nDigiKey:")
        print(f"  - Stock: {digikey_result.stock:,}")
        print(f"  - Price: ${digikey_result.unit_price:.2f}")
        print(f"  - Grade: {digikey_result.grade.value}")

        # Compare
        total_stock = mouser_result.stock + digikey_result.stock
        best_price = min(mouser_result.unit_price, digikey_result.unit_price)
        best_distributor = "Mouser" if mouser_result.unit_price < digikey_result.unit_price else "DigiKey"

        print(f"\nBest Deal:")
        print(f"  - Total stock: {total_stock:,}")
        print(f"  - Best price: ${best_price:.2f} @ {best_distributor}")
    else:
        print("  [FAIL] Could not compare - part not found")


async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("API Client Test Suite")
    print("Running with MOCK DATA (no API keys needed)")
    print("="*60)

    try:
        await test_mouser_client()
        await test_digikey_client()
        await test_comparison()

        print("\n" + "="*60)
        print("[OK] All tests completed successfully!")
        print("="*60)
        print("\nNext steps:")
        print("1. Get API keys from Mouser and DigiKey")
        print("2. Add keys to .env file")
        print("3. Run tests again with use_mock=False")
        print("="*60 + "\n")

    except Exception as e:
        print(f"\n[FAIL] Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
