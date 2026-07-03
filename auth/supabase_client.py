import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "Missing Supabase credentials. Please set SUPABASE_URL and SUPABASE_KEY in your environment."
    )

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
