import os
from pathlib import Path

from dotenv import load_dotenv

# 1. Force Python to find the .env file relative to this script's position
BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)


class Settings:
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    ALLOWED_ORIGINS: list = os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000"
    ).split(",")


settings = Settings()

# 2. Print instant startup diagnostics directly into your terminal window
print("\n🔍 --- SOLGENT ENGINE DIAGNOSTICS ---")
print(f"📍 Checking path: {env_path}")
print(f"📂 File physically exists: {env_path.exists()}")
print(f"🔑 GROQ_API_KEY found:  {'✅ YES' if settings.GROQ_API_KEY else '❌ NO'}")
print(f"🌐 SUPABASE_URL found:   {'✅ YES' if settings.SUPABASE_URL else '❌ NO'}")
print(f"🔒 SUPABASE_KEY found:   {'✅ YES' if settings.SUPABASE_KEY else '❌ NO'}")
print("---------------------------------------\n")
