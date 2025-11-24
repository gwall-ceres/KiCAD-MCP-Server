"""
Direct test of DigiKey OAuth2 authentication
"""
import requests
import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

CLIENT_ID = os.environ.get('DIGIKEY_CLIENT_ID')
CLIENT_SECRET = os.environ.get('DIGIKEY_CLIENT_SECRET')

print("DigiKey OAuth2 Test")
print("=" * 70)
print(f"Client ID: {CLIENT_ID[:20]}..." if CLIENT_ID else "No Client ID")
print(f"Client Secret: {CLIENT_SECRET[:20]}..." if CLIENT_SECRET else "No Client Secret")
print()

if not CLIENT_ID or not CLIENT_SECRET:
    print("ERROR: Missing DigiKey credentials")
    exit(1)

# DigiKey OAuth2 token endpoint
TOKEN_URL = "https://api.digikey.com/v1/oauth2/token"

print(f"Testing OAuth2 endpoint: {TOKEN_URL}")
print()

# Prepare OAuth2 client credentials request
payload = {
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "grant_type": "client_credentials"
}

try:
    print("Attempting OAuth2 authentication...")
    response = requests.post(
        TOKEN_URL,
        data=payload,
        headers={
            "Content-Type": "application/x-www-form-urlencoded"
        },
        timeout=30
    )

    print(f"Response Status: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print()

    if response.status_code == 200:
        data = response.json()
        print("[OK] OAuth2 authentication successful!")
        print(f"Access Token: {data.get('access_token', '')[:30]}...")
        print(f"Token Type: {data.get('token_type')}")
        print(f"Expires In: {data.get('expires_in')} seconds")
    else:
        print(f"[ERROR] Authentication failed")
        print(f"Response: {response.text}")

except requests.exceptions.SSLError as e:
    print(f"[ERROR] SSL/TLS Error: {e}")
    print("\nTrying without SSL verification (not recommended for production)...")
    try:
        response = requests.post(
            TOKEN_URL,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
            verify=False
        )
        print(f"Response Status (no SSL verify): {response.status_code}")
    except Exception as e2:
        print(f"Still failed: {e2}")

except requests.exceptions.ConnectionError as e:
    print(f"[ERROR] Connection Error: {e}")
    print("\nPossible causes:")
    print("1. Firewall blocking api.digikey.com")
    print("2. Network connectivity issue")
    print("3. Proxy settings needed")

except Exception as e:
    print(f"[ERROR] Unexpected error: {e}")
    import traceback
    traceback.print_exc()
