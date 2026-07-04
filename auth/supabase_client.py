import os
import sys
from dotenv import load_dotenv
from supabase import create_client

# Detect if running as a PyInstaller bundled exe
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

env_path = os.path.join(base_path, ".env")
load_dotenv(env_path)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "Missing Supabase credentials. Please set SUPABASE_URL and SUPABASE_KEY in your environment."
    )

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
