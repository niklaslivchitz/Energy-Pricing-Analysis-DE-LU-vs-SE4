import os
from dotenv import load_dotenv

load_dotenv()
token = os.getenv('ENTSOE_API_KEY')

if token:
    print(f"✅ Token loaded! Length: {len(token)} chars")
    print(f"   First 8 chars: {token[:8]}...")
else:
    print("❌ Token not found. Check .env file.")
    print("   Files in current directory:")
    for f in os.listdir('.'):
        print(f"     - {f}")
