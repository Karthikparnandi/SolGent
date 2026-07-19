from supabase import create_client, Client
from app.config import settings

class SupabaseMemoryManager:
    def __init__(self):
        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
            raise ValueError("CRITICAL FAILURE: Supabase configuration keys are missing in your environment.")
        self.supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

    def fetch_chat_session(self, session_id: str) -> list:
        """Extracts complete sequential chat history arrays to preserve conversational continuity."""
        try:
            response = self.supabase.table("chat_history")\
                .select("role", "content")\
                .eq("session_id", session_id)\
                .order("created_at", desc=False)\
                .execute()
            return response.data
        except Exception:
            return []  

    def log_message(self, session_id: str, role: str, content: str):
        """Persists text blocks instantly into your Supabase Postgres schema storage tier."""
        try:
            self.supabase.table("chat_history").insert({
                "session_id": session_id,
                "role": role,
                "content": content
            }).execute()
        except Exception:
            pass