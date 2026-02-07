import asyncio
import certifi
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

async def test_connection():
    url = os.getenv("MONGODB_URL")
    safe_url = "mongodb+srv://***@" + url.split("@")[-1] if "@" in url else url
    print(f"Testing connection to: {safe_url}")
    
    # Attempt 1: Default
    print("\n--- Attempt 1: Default Client ---")
    try:
        client = AsyncIOMotorClient(url, serverSelectionTimeoutMS=5000)
        info = await client.server_info()
        print("Success! Server info:", info.get('version'))
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
