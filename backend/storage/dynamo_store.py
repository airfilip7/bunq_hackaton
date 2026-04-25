"""DynamoDB-backed storage — stub. Implement in Phase 11."""

from backend.models import BunqToken, PendingTool, Profile, Session, Turn


class DynamoStore:
    """Satisfies the Storage protocol. All methods raise NotImplementedError."""

    def get_profile(self, user_id: str) -> Profile | None:
        raise NotImplementedError

    def upsert_profile(self, profile: Profile) -> None:
        raise NotImplementedError

    def create_session(self, user_id: str) -> Session:
        raise NotImplementedError

    def get_latest_session(self, user_id: str) -> Session | None:
        raise NotImplementedError

    def touch_session(self, session_id: str) -> None:
        raise NotImplementedError

    def append_turn(self, session_id: str, turn: Turn) -> None:
        raise NotImplementedError

    def list_turns(self, session_id: str, include_hidden: bool = False) -> list[Turn]:
        raise NotImplementedError

    def put_pending_tool(self, session_id: str, pending: PendingTool) -> None:
        raise NotImplementedError

    def get_pending_tool(self, session_id: str, tool_use_id: str) -> PendingTool | None:
        raise NotImplementedError

    def clear_pending_tool(self, session_id: str, tool_use_id: str) -> None:
        raise NotImplementedError

    def get_bunq_token(self, user_id: str) -> BunqToken | None:
        raise NotImplementedError

    def put_bunq_token(self, user_id: str, token: BunqToken) -> None:
        raise NotImplementedError
