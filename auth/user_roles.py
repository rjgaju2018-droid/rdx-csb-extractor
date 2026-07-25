from typing import Optional
from auth.supabase_client import supabase


def check_is_admin(user_id: str) -> bool:
    """Return True if the user is an admin in the profiles table."""
    if not user_id:
        return False

    query = supabase.from_("profiles").select("role").eq("id", user_id).maybe_single()
    result = query.execute()
    if not result or not getattr(result, "data", None):
        return False
    profile = result.data
    return profile.get("role") == "admin"


def get_user_profile(user_id: str) -> Optional[dict]:
    query = supabase.from_("profiles").select("id, email, role, created_at, last_sign_in_at").eq("id", user_id).maybe_single()
    result = query.execute()
    if not result or not getattr(result, "data", None):
        return None
    return result.data


def log_usage(user_id: str, action: str) -> None:
    if not user_id or not action:
        return
    try:
        supabase.from_("usage_logs").insert({"user_id": user_id, "action": action}).execute()
    except Exception:
        pass


def set_admin_status(user_id: str, is_admin: bool) -> tuple[bool, Optional[str]]:
    """Updates the admin status for a user in the 'profiles' table.
    Also updates the 'role' column based on the is_admin status.
    """
    try:
        # Supabase expects a dictionary for update operations
        data = {"is_admin": is_admin, "role": "admin" if is_admin else "user"}
        
        # Perform the update
        res = supabase.table("profiles").update(data).eq("id", user_id).execute()
        
        return True, None if res.data else f"User with ID {user_id} not found or no change applied."
    except Exception as e:
        return False, f"Database error: {e}"
