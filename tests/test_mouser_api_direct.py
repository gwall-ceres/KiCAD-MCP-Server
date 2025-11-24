"""
Direct test of Mouser API to debug 404 error
"""
import asyncio
import aiohttp
import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

API_KEY = os.environ.get('MOUSER_API_KEY')

async def test_mouser_api():
    """Test Mouser API with different endpoint formats"""

    print(f"API Key: {API_KEY[:10]}..." if API_KEY else "No API key found")
    print()

    if not API_KEY:
        print("ERROR: No MOUSER_API_KEY found in environment")
        return

    # Test data
    mpn = "LM2596"

    # According to Mouser API docs, the endpoint should be:
    # POST https://api.mouser.com/api/v1/search/partnumber
    # with apiKey as URL parameter

    url = f"https://api.mouser.com/api/v1/search/partnumber"
    params = {"apiKey": API_KEY}
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    payload = {
        "SearchByPartRequest": {
            "mouserPartNumber": mpn,
            "partSearchOptions": ""
        }
    }

    print(f"Testing Mouser API:")
    print(f"URL: {url}")
    print(f"Params: apiKey={API_KEY[:10]}...")
    print(f"Payload: {payload}")
    print()

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                url,
                params=params,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                print(f"Response Status: {response.status}")
                print(f"Response Headers: {dict(response.headers)}")

                text = await response.text()
                print(f"Response Body: {text[:500]}")

                if response.status == 200:
                    data = await response.json()
                    print("\n[OK] Mouser API call successful!")
                    print(f"Data: {data}")
                else:
                    print(f"\n[ERROR] API returned status {response.status}")

        except Exception as e:
            print(f"\n[ERROR] Exception: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mouser_api())
