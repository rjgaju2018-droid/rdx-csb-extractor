from typing import Tuple
from supabase_auth.errors import AuthApiError
from auth.supabase_client import supabase


def login_user(email: str, password: str) -> Tuple[bool, str, dict]:
    """Try to sign in a user and return (success, message, auth_data)."""
    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if response.session and response.user:
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
