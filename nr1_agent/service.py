from __future__ import annotations

from dataclasses import dataclass

from nr1_agent.graph import ConversationGraph
from nr1_agent.llm import LLMClient
from nr1_agent.log_store import SQLiteLogStore
from nr1_agent.models import ChatMessage, ChatResponse, Role, SessionSnapshot, SessionStatus
from nr1_agent.report_store import SQLiteReportStore
from nr1_agent.session_store import InMemorySessionStore


@dataclass(slots=True)
class ConversationStep:
    session_id: str
    assistant_message: str
    status: SessionStatus


class ConversationService:
    def __init__(
        self,
        store: InMemorySessionStore | None = None,
        llm: LLMClient | None = None,
        report_store: SQLiteReportStore | None = None,
        log_store: SQLiteLogStore | None = None,
    ) -> None:
        self.store = store or InMemorySessionStore()
        self.llm = llm or LLMClient()
        self.report_store = report_store or SQLiteReportStore()
        self.log_store = log_store or SQLiteLogStore(self.report_store.database_path)
        self.graph = ConversationGraph(self.store, self.llm, self.log_store)

    def start(self) -> ConversationStep:
        session = self.store.create()
        assistant_message = self.llm.fixed_response("ask_name")
        session.messages.append(ChatMessage(role=Role.assistant, content=assistant_message))
        self.store.update(session)
        return ConversationStep(
            session_id=session.session_id,
            assistant_message=assistant_message,
            status=session.status,
        )

    def handle_message(self, session_id: str, message: str) -> ChatResponse:
        result = self.graph.invoke(session_id, message)
        session = self.store.get(session_id)
        report = result.get("report")
        if session.status == SessionStatus.complete and report:
            self.report_store.save(
                session.session_id,
                session.user_name,
                session.sector,
                report,
                result["classification"],
            )
        return ChatResponse(
            session_id=session.session_id,
            status=session.status,
            assistant_message=result["assistant_message"],
            question_count=session.question_count,
            user_name=session.user_name,
            sector=session.sector,
        )

    def snapshot(self, session_id: str) -> SessionSnapshot:
        session = self.store.get(session_id)
        return SessionSnapshot(**session.model_dump())

    def list_reports(self) -> list[dict[str, object]]:
        return self.report_store.list_reports()

    def report(self, session_id: str) -> dict[str, object] | None:
        return self.report_store.get_report(session_id)

    def list_logs(self) -> list[dict[str, object]]:
        return self.log_store.list_logs()
