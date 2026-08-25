from __future__ import annotations
from typing import Literal, TypedDict
from langgraph.graph import END, START, StateGraph
from langchain_core.messages import AIMessage, ToolMessage
from app.alerts import send_admin_report_alert
from app.llm import LLMClient
from app.log_store import SQLiteLogStore
from app.models import ChatMessage, GeneratedReport, Role, SessionState, SessionStatus
from app.risk_classifier import classify, format_assessment
from app.session_store import InMemorySessionStore
from app.tools.retriever import create_retriever
from app.tools.specialist_tools import (
    agendar_inspecao_interna,
    agendar_servico_externo,
)

MAX_QUESTIONS = 5
MIN_RESPONSE_LENGTH = 3
QUESTION_BANK = [
    "Conte como é o trabalho que você realiza e em que local ele acontece.",
    "Como é o local onde você trabalha e o que você utiliza para realizar suas atividades?",
    "Conte como é um dia típico de trabalho, do início ao fim da jornada.",
    "O que costuma acontecer quando algo sai do esperado durante o trabalho?",
    "Que orientações, treinamentos ou formas de proteção existem para essa atividade? Como você avalia o funcionamento delas?",
]

class ConversationGraphState(TypedDict, total=False):
    session_id: str
    message: str
    session: SessionState
    previous_status: SessionStatus
    assistant_message: str
    report: str
    classification: str
    alert_message: str
    messages: list # Campo para o ToolNode

class ConversationGraph:
    def __init__(self, store: InMemorySessionStore, llm: LLMClient, log_store: SQLiteLogStore) -> None:
        self.store = store
        self.llm = llm
        self.log_store = log_store
        self.retriever = create_retriever()
        self.tools = [agendar_inspecao_interna, agendar_servico_externo]
        self.graph = self._build_graph()

    def invoke(self, session_id: str, message: str) -> ConversationGraphState:
        return self.graph.invoke({"session_id": session_id, "message": message, "messages": []})

    def _build_graph(self):
        builder = StateGraph(ConversationGraphState)

        builder.add_node("load_session", self._load_session)
        builder.add_node("record_user_message", self._record_user_message)
        builder.add_node("handle_name", self._handle_name)
        builder.add_node("handle_sector", self._handle_sector)
        builder.add_node("handle_collecting", self._handle_collecting)
        builder.add_node("handle_complete", self._handle_complete)
        builder.add_node("specialist_agent", self._run_specialist_agent)
        builder.add_node("await_human_approval", self._await_human_approval)
        builder.add_node("handle_approval", self._handle_approval)
        builder.add_node("execute_tools", self._execute_tools)
        builder.add_node("process_tool_result", self._process_tool_result)
        builder.add_node("send_admin_report_alert", self._send_admin_report_alert)
        builder.add_node("persist_session", self._persist_session)

        builder.add_edge(START, "load_session")
        builder.add_edge("load_session", "record_user_message")
        builder.add_conditional_edges("record_user_message", self._route_turn, {
            "handle_name": "handle_name", "handle_sector": "handle_sector",
            "handle_collecting": "handle_collecting", "handle_complete": "handle_complete",
            "handle_approval": "handle_approval",
        })
        for handler in ("handle_name", "handle_sector", "handle_collecting", "handle_complete"):
            builder.add_conditional_edges(handler, self._route_after_turn, {
                "specialist_agent": "specialist_agent", "send_admin_report_alert": "send_admin_report_alert",
                "persist_session": "persist_session",
            })
        builder.add_conditional_edges("specialist_agent", self._route_after_specialist, {
            "await_human_approval": "await_human_approval", "send_admin_report_alert": "send_admin_report_alert",
        })
        builder.add_conditional_edges("handle_approval", self._route_after_approval, {
            "execute_tools": "execute_tools", "send_admin_report_alert": "send_admin_report_alert",
        })
        builder.add_edge("await_human_approval", "persist_session")
        builder.add_edge("execute_tools", "process_tool_result")
        builder.add_edge("process_tool_result", "send_admin_report_alert")
        builder.add_edge("send_admin_report_alert", "persist_session")
        builder.add_edge("persist_session", END)

        return builder.compile()

    def _load_session(self, state: ConversationGraphState) -> ConversationGraphState:
        session = self.store.get(state["session_id"])
        return {"session": session, "previous_status": session.status}

    def _record_user_message(self, state: ConversationGraphState) -> ConversationGraphState:
        session = state["session"]
        message = state["message"].strip()
        session.messages.append(ChatMessage(role=Role.user, content=message))
        return {"session": session}

    def _route_turn(self, state: ConversationGraphState):
        previous_status = state["previous_status"]
        if previous_status == SessionStatus.awaiting_name: return "handle_name"
        if previous_status == SessionStatus.awaiting_sector: return "handle_sector"
        if previous_status == SessionStatus.collecting: return "handle_collecting"
        if previous_status == SessionStatus.awaiting_approval: return "handle_approval"
        return "handle_complete"

    def _handle_name(self, state: ConversationGraphState):
        session, message = state["session"], self._validate_response(state["message"], "nome")
        session.user_name = message
        session.status = SessionStatus.awaiting_sector
        assistant_message = self.llm.fixed_response("ask_sector")
        session.messages.append(ChatMessage(role=Role.assistant, content=assistant_message))
        return {"session": session, "assistant_message": assistant_message}

    def _handle_sector(self, state: ConversationGraphState):
        session, message = state["session"], self._validate_response(state["message"], "setor")
        session.sector = message
        session.status = SessionStatus.collecting
        session.question_count = 0
        assistant_message = self.llm.fixed_response("ask_question", self._current_question(session))
        session.asked_questions.append(assistant_message)
        session.messages.append(ChatMessage(role=Role.assistant, content=assistant_message))
        return {"session": session, "assistant_message": assistant_message}

    def _handle_collecting(self, state: ConversationGraphState):
        session, message = state["session"], self._validate_response(state["message"], "resposta")
        session.question_count += 1
        session.answers.append(message)
        if session.question_count >= MAX_QUESTIONS:
            session.status = SessionStatus.complete
            session.summary = self._build_summary(session)
            report = self._build_report(session)
            assessment = classify(session)
            report = GeneratedReport(content=report + format_assessment(assessment)).content
            assistant_message = "Sessão de triagem concluída. Analisando o risco para determinar os próximos passos..."
            classification = assessment.classification
            session.classification = classification
            session.report = report
        else:
            assistant_message = self.llm.fixed_response("ask_question", self._current_question(session))
            session.asked_questions.append(assistant_message)
            report, classification = "", ""
        session.messages.append(ChatMessage(role=Role.assistant, content=assistant_message))
        return {"session": session, "assistant_message": assistant_message, "report": report, "classification": classification}

    def _handle_complete(self, state: ConversationGraphState):
        session = state["session"]
        report = self._build_report(session)
        assessment = classify(session)
        report = GeneratedReport(content=report + format_assessment(assessment)).content
        session.classification = assessment.classification
        return {"assistant_message": "Esta sessão já foi concluída.", "report": report, "classification": assessment.classification}

    def _route_after_turn(self, state: ConversationGraphState):
        classification = state.get("classification")
        if classification in {"Médio / Alerta", "Alto / Crítico"}: return "specialist_agent"
        return "persist_session" if not classification else "send_admin_report_alert"

    def _run_specialist_agent(self, state: ConversationGraphState):
        session = state["session"]
        last_user_message = next((msg.content for msg in reversed(session.messages) if msg.role == Role.user), "")
        docs = self.retriever.invoke(last_user_message)
        context = "\n\n".join([doc.page_content for doc in docs])
        context_msg = ChatMessage(role=Role.system, content=f"Contexto: {context}")
        response = self.llm.respond_with_tools(session.messages + [context_msg], "specialist_agent_v2", self.tools)
        session.pending_tool_calls = response.tool_calls
        session.messages.append(response)
        return {"session": session, "messages": session.messages, "classification": session.classification, "report": session.report}

    def _route_after_specialist(self, state: ConversationGraphState):
        return "await_human_approval" if state["session"].pending_tool_calls else "send_admin_report_alert"

    def _await_human_approval(self, state: ConversationGraphState):
        session = state["session"]
        session.status = SessionStatus.awaiting_approval
        tool_call = session.pending_tool_calls[0]
        assistant_message = (f"O especialista sugeriu a ação: **{tool_call['name']}** com os parâmetros: `{tool_call['args']}`. "
                           "Para aprovar, digite **'sim'**. Para cancelar, digite **'não'**.")
        session.messages.append(ChatMessage(role=Role.assistant, content=assistant_message))
        return {"session": session, "assistant_message": assistant_message, "classification": session.classification, "report": session.report}

    def _handle_approval(self, state: ConversationGraphState):
        session = state["session"]
        approved = state["message"].strip().lower() == "sim"
        if approved:
            last_tool_call_message = None
            for msg in reversed(session.messages):
                if msg.tool_calls:
                    last_tool_call_message = msg
                    break
            if last_tool_call_message:
                tool_calls = []
                for tc in last_tool_call_message.tool_calls:
                    tool_calls.append({
                        "name": tc["name"],
                        "args": tc["args"],
                        "id": tc["id"],
                        "type": "tool_call",
                    })
                ai_message = AIMessage(content=last_tool_call_message.content or "", tool_calls=tool_calls)
                return {"session": session, "messages": [ai_message], "classification": session.classification, "report": session.report}
            else:
                return {"session": session, "messages": [], "classification": session.classification, "report": session.report}
        else:
            assistant_message = "Ação cancelada pelo usuário."
            session.pending_tool_calls = []
            session.status = SessionStatus.complete
            session.messages.append(ChatMessage(role=Role.assistant, content=assistant_message))
            return {"session": session, "assistant_message": assistant_message, "classification": session.classification, "report": session.report}

    def _route_after_approval(self, state: ConversationGraphState):
        has_pending = bool(state["session"].pending_tool_calls)
        return "execute_tools" if has_pending else "send_admin_report_alert"

    def _send_admin_report_alert(self, state: ConversationGraphState):
        classification = state["classification"]
        if not classification: return state
        message = "O relatório gerado necessita de ação de verificação de risco."
        send_admin_report_alert(state["session"].session_id, classification, message, self.log_store)
        return {
            "alert_message": message,
            "report": state["session"].report,
            "classification": state["classification"],
            "assistant_message": state.get("assistant_message", ""),
        }

    def _execute_tools(self, state: ConversationGraphState):
        session = state["session"]
        messages = state.get("messages", [])
        tool_messages = []
        for msg in messages:
            if isinstance(msg, AIMessage) and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    tool_id = tool_call["id"]
                    tool_func = None
                    for t in self.tools:
                        if t.name == tool_name:
                            tool_func = t
                            break
                    if tool_func:
                        result = tool_func.invoke(tool_args)
                        tool_messages.append(ToolMessage(content=str(result), tool_call_id=tool_id))
        return {"messages": tool_messages, "session": session, "classification": session.classification, "report": session.report}

    def _process_tool_result(self, state: ConversationGraphState):
        session = state["session"]
        messages = state.get("messages", [])
        tool_result = None
        for msg in reversed(messages):
            if isinstance(msg, ToolMessage):
                tool_result = msg.content
                break
        if tool_result:
            assistant_message = f"Ação executada com sucesso. {tool_result}"
        else:
            assistant_message = "Ação executada com sucesso."
        session.messages.append(ChatMessage(role=Role.assistant, content=assistant_message))
        session.status = SessionStatus.complete
        session.pending_tool_calls = []
        return {"session": session, "assistant_message": assistant_message, "classification": session.classification, "report": session.report}

    def _persist_session(self, state: ConversationGraphState):
        self.store.update(state["session"])
        return state

    def _build_summary(self, s: SessionState):
        return f"Nome: {s.user_name or 'N/A'} | Setor: {s.sector or 'N/A'} | Perguntas: {s.question_count}"

    def _build_report(self, s: SessionState):
        report = self.llm.respond(s.messages, "summarize").text.strip()
        if not report: raise ValueError("A LLM não gerou conteúdo para o relatório")
        return report

    @staticmethod
    def _validate_response(v: str, f: str):
        if len(v.strip()) < MIN_RESPONSE_LENGTH: raise ValueError(f"{f} muito curto")
        return v.strip()

    def _current_question(self, s: SessionState):
        return QUESTION_BANK[min(s.question_count, len(QUESTION_BANK) - 1)]

