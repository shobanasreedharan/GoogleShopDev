from datetime import datetime, timezone
from backend.db.firestore_client import db
import time

# =====================================================
# CONFIG CACHE (avoid reading Firestore on every request)
# Re-reads config every 5 minutes
# =====================================================
_config_cache = {"data": None, "fetched_at": 0}
CONFIG_TTL_SECONDS = 300  # 5 minutes


def get_rate_limit_config() -> dict:
    """
    Reads rate limit config from Firestore config/rate_limits.
    Cached in memory for 5 minutes.
    Update the Firestore doc anytime from Firebase Console — 
    changes take effect within 5 minutes, no redeployment needed.
    """
    now = time.time()
    if _config_cache["data"] and (now - _config_cache["fetched_at"]) < CONFIG_TTL_SECONDS:
        return _config_cache["data"]

    try:
        doc = db.collection("config").document("rate_limits").get()
        if doc.exists:
            config = doc.to_dict()
        else:
            # Defaults if config doc doesn't exist yet
            config = _default_config()
            # Auto-create the doc so admin can see/edit it
            db.collection("config").document("rate_limits").set(config)
            print("[rate_limit] Created default config/rate_limits in Firestore")
    except Exception as e:
        print(f"[rate_limit] Failed to read config: {e} — using defaults")
        config = _default_config()

    _config_cache["data"] = config
    _config_cache["fetched_at"] = now
    return config


def _default_config() -> dict:
    return {
        "generate_per_day": 20,   # max /generate calls per user per day (covers Places API)
        "gemini_per_day":   10,   # max Gemini calls per user per day (subset of generate)
        "chat_per_day":     20,   # max /chat calls per user per day
        "updated_at":       datetime.now(timezone.utc),
    }


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _usage_doc(user_id: str):
    return (
        db.collection("users")
        .document(user_id)
        .collection("rate_limits")
        .document(_today())
    )


def get_usage(user_id: str) -> dict:
    """Returns today's usage counts for the user."""
    try:
        doc = _usage_doc(user_id).get()
        if doc.exists:
            return doc.to_dict()
    except Exception as e:
        print(f"[rate_limit] Failed to read usage for {user_id}: {e}")
    return {"generate": 0, "gemini": 0, "chat": 0}


def increment_usage(user_id: str, key: str) -> int:
    """
    Increments a usage counter for today. Returns new count.
    key: "generate" | "gemini" | "chat"
    """
    try:
        from google.cloud.firestore import Increment
        ref = _usage_doc(user_id)
        ref.set(
            {key: Increment(1), "date": _today()},
            merge=True
        )
        updated = ref.get().to_dict() or {}
        return updated.get(key, 1)
    except Exception as e:
        print(f"[rate_limit] Failed to increment {key} for {user_id}: {e}")
        return 0


# =====================================================
# CHECK HELPERS — called from main.py
# =====================================================

def check_generate_limit(user_id: str) -> dict:
    """
    Check if user can call /generate (Places API limit).
    Returns {"allowed": True/False, "used": N, "limit": N, "message": "..."}
    """
    config = get_rate_limit_config()
    limit  = config.get("generate_per_day", 20)
    usage  = get_usage(user_id)
    used   = usage.get("generate", 0)

    if used >= limit:
        return {
            "allowed": False,
            "used": used, "limit": limit,
            "message": f"Daily generate limit reached ({used}/{limit}). Try again tomorrow."
        }
    return {"allowed": True, "used": used, "limit": limit, "message": ""}


def check_gemini_limit(user_id: str) -> dict:
    """
    Check if user can call Gemini (cache miss path only).
    Returns {"allowed": True/False, "used": N, "limit": N, "message": "..."}
    """
    config = get_rate_limit_config()
    limit  = config.get("gemini_per_day", 10)
    usage  = get_usage(user_id)
    used   = usage.get("gemini", 0)

    if used >= limit:
        return {
            "allowed": False,
            "used": used, "limit": limit,
            "message": f"Daily AI generation limit reached ({used}/{limit}). Cached results will still load. Try again tomorrow."
        }
    return {"allowed": True, "used": used, "limit": limit, "message": ""}


def check_chat_limit(user_id: str) -> dict:
    """
    Check if user can call /chat.
    Returns {"allowed": True/False, "used": N, "limit": N, "message": "..."}
    """
    config = get_rate_limit_config()
    limit  = config.get("chat_per_day", 20)
    usage  = get_usage(user_id)
    used   = usage.get("chat", 0)

    if used >= limit:
        return {
            "allowed": False,
            "used": used, "limit": limit,
            "message": f"Daily chat limit reached ({used}/{limit}). Try again tomorrow."
        }
    return {"allowed": True, "used": used, "limit": limit, "message": ""}
