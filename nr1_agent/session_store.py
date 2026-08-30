from __future__ import annotations

from collections.abc import Callable
from threading import Lock
from uuid import uuid4

from nr1_agent.models import ChatMessage, Role, SessionState


class InMemorySessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}
        self._lock = Lock()

    def create(self) -> SessionState:
        session = SessionState(session_id=str(uuid4()))
        with self._lock:
            self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> SessionState:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise KeyError(session_id)
            return session

    def update(self, session: SessionState) -> SessionState:
        with self._lock:
            self._sessions[session.session_id] = session
        return session

    def append_message(self, session_id: str, role: Role, content: str) -> SessionState:
        session = self.get(session_id)
        session.messages.append(ChatMessage(role=role, content=content))
        return self.update(session)

    def reset(self, session_id: str) -> SessionState:
        session = SessionState(session_id=session_id)
        return self.update(session)

    def list(self) -> list[SessionState]:
        with self._lock:
            return list(self._sessions.values())

