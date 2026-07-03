from typing import Tuple
from datetime import datetime, timezone
from supabase_auth.errors import AuthApiError
from auth.supabase_client import supabase


def login_user(email: str, password: str) -> Tuple[bool, str, dict]:
    """Try to sign in a user and return (success, message, auth_data)."""
    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if response.session and response.user:
            try:
                # Update last_sign_in_at with current UTC timestamp
                # Note: This requires RLS policy to allow users to update their own profile
                now_utc = datetime.now(timezone.utc).isoformat()
                supabase.table("profiles").update(
                    {"last_sign_in_at": now_utc}
                ).eq("id", response.user.id).execute()
            except Exception:
                pass  # timestamp update fail ho toh bhi login block na ho
            return True, "Login successful", {"user": response.user, "session": response.session}
        if getattr(response, "error", None):
            return False, str(response.error), {}
        return False, "Login failed", {}
    except AuthApiError as exc:
        return False, str(exc), {}
    except Exception as exc:
        return False, f"Login error: {exc}", {}


def signup_user(email: str, password: str) -> Tuple[bool, str, dict]:
    """Create a new Supabase user account."""
    try:
        response = supabase.auth.sign_up({"email": email, "password": password})
        if response.user:
            return True, "Signup successful", {"user": response.user, "session": response.session}
        if getattr(response, "error", None):
            return False, str(response.error), {}
        return False, "Signup failed", {}
    except AuthApiError as exc:
        return False, str(exc), {}
    except Exception as exc:
        return False, f"Signup error: {exc}", {}
