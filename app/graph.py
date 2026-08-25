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
from app.tools.specialist_tools import agendar_servico_externo
from app.tools.cal_tools import get_cal_tools

MAX_QUESTIONS = 5
MIN_RESPONSE_LENGTH = 3
QUESTION_BANK = [
    "Conte como é o trabalho que você realiza e em que local ele acontece.",
    "Como é o local onde você trabalha e o que você utiliza para realizar suas atividades?",
    "Conte como é um dia típico de trabalho, do início ao fim da jornada.",
    "O que costuma acontecer quando algo sai do esperado durante o trabalho?",
    "Que orientações, treinamentos ou formas de proteção existem para essa atividade? Como você avalia o funcionamento delas?",
]

SPECIALIST_MAX_QUESTIONS = 5
SPECIALIST_QUESTION_BANK = [
    "Considerando os procedimentos de segurança, há quanto tempo você realiza esta atividade específica?",
    "Você já presenciou ou sofreu algum incidente ou quase-acidente relacionado a este risco?",
    "Os equipamentos de proteção (EPIs) fornecidos são adequados e estão em bom estado de conservação?",
    "Você se sente capacitado para identificar situações de perigo iminente e sabe como agir?",
    "Existe alguma condição do ambiente ou da tarefa que você acredita que não está coberta pelos procedimentos atuais?",
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
    messages: list

class ConversationGraph:
    def __init__(self, store: InMemorySessionStore, llm: LLMClient, log_store: SQLiteLogStore) -> None:
        self.store = store
        self.llm = llm
        self.log_store = log_store
        self.retriever = create_retriever()
        self.tools = [agendar_servico_externo] + get_cal_tools()
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
        builder.add_node("handle_processing", self._handle_processing)
        builder.add_node("handle_specialist_consent", self._handle_specialist_consent)
        builder.add_node("handle_specialist_collecting", self._handle_specialist_collecting)
        builder.add_node("handle_schedule_consent", self._handle_schedule_consent)
        builder.add_node("handle_complete", self._handle_complete)
        builder.add_node("handle_approval", self._handle_approval)
        builder.add_node("execute_tools", self._execute_tools)
        builder.add_node("process_tool_result", self._process_tool_result)
        builder.add_node("send_admin_report_alert", self._send_admin_report_alert)
        builder.add_node("persist_session", self._persist_session)

        builder.add_edge(START, "load_session")
        builder.add_edge("load_session", "record_user_message")
        builder.add_conditional_edges("record_user_message", self._route_turn, {
            "handle_name": "handle_name",
            "handle_sector": "handle_sector",
            "handle_collecting": "handle_collecting",
            "handle_processing": "handle_processing",
            "handle_specialist_consent": "handle_specialist_consent",
            "handle_specialist_collecting": "handle_specialist_collecting",
            "handle_schedule_consent": "handle_schedule_consent",
            "handle_complete": "handle_complete",
            "handle_approval": "handle_approval",
        })
        builder.add_conditional_edges("handle_name", self._route_after_turn, {
            "persist_session": "persist_session",
        })
        builder.add_conditional_edges("handle_sector", self._route_after_turn, {
            "persist_session": "persist_session",
        })
        builder.add_conditional_edges("handle_collecting", self._route_after_collecting, {
            "handle_processing": "handle_processing",
            "persist_session": "persist_session",
        })
        builder.add_conditional_edges("handle_processing", self._route_after_processing, {
            "persist_session": "persist_session",
        })
        builder.add_conditional_edges("handle_specialist_consent", self._route_after_specialist_consent, {
            "persist_session": "persist_session",
        })
        builder.add_conditional_edges("handle_specialist_collecting", self._route_after_specialist_collecting, {
            "persist_session": "persist_session",
        })
        builder.add_conditional_edges("handle_schedule_consent", self._route_after_schedule_consent, {
            "persist_session": "persist_session",
        })
        builder.add_conditional_edges("handle_complete", self._route_after_turn, {
            "persist_session": "persist_session",
            "send_admin_report_alert": "send_admin_report_alert",
        })
        builder.add_conditional_edges("handle_approval", self._route_after_approval, {
            "execute_tools": "execute_tools",
            "send_admin_report_alert": "send_admin_report_alert",
        })
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
        if previous_status == SessionStatus.processing: return "handle_processing"
        if previous_status == SessionStatus.awaiting_specialist_consent: return "handle_specialist_consent"
        if previous_status == SessionStatus.specialist_collecting: return "handle_specialist_collecting"
        if previous_status == SessionStatus.awaiting_schedule_consent: return "handle_schedule_consent"
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
            session.status = SessionStatus.processing
            assistant_message = "Obrigado pelas respostas. Processando as informações para classificar o risco..."
        else:
            assistant_message = self.llm.fixed_response("ask_question", self._current_question(session))
            session.asked_questions.append(assistant_message)
        session.messages.append(ChatMessage(role=Role.assistant, content=assistant_message))
        return {"session": session, "assistant_message": assistant_message}

    def _route_after_collecting(self, state: ConversationGraphState):
        session = state["session"]
        if session.question_count >= MAX_QUESTIONS:
            return "handle_processing"
        return "persist_session"

    def _handle_processing(self, state: ConversationGraphState):
        session = state["session"]
        session.summary = self._build_summary(session)
        report = self._build_report(session)
        assessment = classify(session)
        report = GeneratedReport(content=report + format_assessment(assessment)).content
        classification = assessment.classification
        session.classification = classification
        session.report = report
        if classification in {"Médio / Alerta", "Alto / Crítico"}:
            session.status = SessionStatus.awaiting_specialist_consent
            assistant_message = (
                f"Classificação de risco: **{classification}**.\n\n"
                "Gostaria de compartilhar mais detalhes com um agente especialista em segurança do trabalho "
                "para uma análise mais aprofundada? O especialista consultará os procedimentos internos "
                "e poderá fazer até 5 perguntas adicionais. Responda **'sim'** para continuar ou **'não'** para encerrar."
            )
        else:
            session.status = SessionStatus.complete
            assistant_message = (
                f"Classificação de risco: **{classification}**.\n\n"
                "O risco foi classificado como baixo. A triagem está concluída. "
                "O relatório foi salvo para consulta administrativa."
            )
        session.messages.append(ChatMessage(role=Role.assistant, content=assistant_message))
        return {"session": session, "assistant_message": assistant_message, "report": report, "classification": classification}

    def _route_after_processing(self, state: ConversationGraphState):
        return "persist_session"

    def _handle_specialist_consent(self, state: ConversationGraphState):
        session = state["session"]
        wants_specialist = state["message"].strip().lower() == "sim"
        session.wants_specialist = wants_specialist
        if wants_specialist:
            session.status = SessionStatus.specialist_collecting
            session.specialist_question_count = 0
            assistant_message = self.llm.fixed_response("ask_question", self._current_specialist_question(session))
            session.specialist_asked_questions.append(assistant_message)
        else:
            session.status = SessionStatus.complete
            assistant_message = "Entendido. A triagem está concluída. O relatório foi salvo para consulta administrativa."
        session.messages.append(ChatMessage(role=Role.assistant, content=assistant_message))
        return {"session": session, "assistant_message": assistant_message}

    def _route_after_specialist_consent(self, state: ConversationGraphState):
        return "persist_session"

    def _handle_specialist_collecting(self, state: ConversationGraphState):
        session = state["session"]
        message = self._validate_response(state["message"], "resposta")
        session.specialist_question_count += 1
        session.specialist_answers.append(message)
        if session.specialist_question_count >= SPECIALIST_MAX_QUESTIONS:
            session.status = SessionStatus.awaiting_schedule_consent
            assistant_message = (
                "Obrigado pelas informações adicionais. Com base na análise dos procedimentos e nas suas respostas, "
                "o especialista identificou a necessidade de agendar uma inspeção de segurança no setor. "
                "Deseja solicitar o agendamento agora? Responda **'sim'** para confirmar ou **'não'** para encerrar."
            )
        else:
            assistant_message = self.llm.fixed_response("ask_question", self._current_specialist_question(session))
            session.specialist_asked_questions.append(assistant_message)
        session.messages.append(ChatMessage(role=Role.assistant, content=assistant_message))
        return {"session": session, "assistant_message": assistant_message}

    def _route_after_specialist_collecting(self, state: ConversationGraphState):
        return "persist_session"

    def _handle_schedule_consent(self, state: ConversationGraphState):
        session = state["session"]
        wants_schedule = state["message"].strip().lower() == "sim"
        session.wants_schedule = wants_schedule
        if wants_schedule:
            session.status = SessionStatus.awaiting_approval
            session.pending_tool_calls = [{
                "name": "cal_schedule_appointment",
                "args": {
                    "start_time": "2026-08-25T10:00:00-03:00",
                    "attendee_name": session.user_name or "Colaborador",
                    "attendee_email": "colaborador@empresa.com",
                    "description": f"Inspeção de segurança no setor {session.sector or 'Não informado'} após triagem de risco {session.classification}. Respostas do especialista: {session.specialist_answers}",
                },
                "id": "tool_call_schedule_1"
            }]
            assistant_message = (
                f"O especialista sugeriu agendar uma inspeção de segurança via cal.com "
                f"para o setor **{session.sector}**.\n\n"
                "Para aprovar e agendar, digite **'sim'**. Para cancelar, digite **'não**'."
            )
            # Incluir tool_calls na mensagem para que _handle_approval possa encontrá-los
            session.messages.append(ChatMessage(role=Role.assistant, content=assistant_message, tool_calls=session.pending_tool_calls))
        else:
            session.status = SessionStatus.complete
            assistant_message = "Entendido. A triagem está concluída. O relatório foi salvo para consulta administrativa."
            session.messages.append(ChatMessage(role=Role.assistant, content=assistant_message))
        return {"session": session, "assistant_message": assistant_message}

    def _route_after_schedule_consent(self, state: ConversationGraphState):
        return "persist_session"

    def _handle_complete(self, state: ConversationGraphState):
        session = state["session"]
        if not session.report:
            report = self._build_report(session)
            assessment = classify(session)
            report = GeneratedReport(content=report + format_assessment(assessment)).content
            session.classification = assessment.classification
            session.report = report
        else:
            report = session.report
        assistant_message = "Sessão concluída. O relatório foi salvo com sucesso."
        session.status = SessionStatus.complete
        session.messages.append(ChatMessage(role=Role.assistant, content=assistant_message))
        return {"session": session, "assistant_message": assistant_message, "report": report, "classification": session.classification}

    def _route_after_turn(self, state: ConversationGraphState):
        classification = state.get("classification")
        if classification and classification in {"Médio / Alerta", "Alto / Crítico"}:
            return "send_admin_report_alert"
        return "persist_session"

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
                all_messages = [m for m in session.messages] + [ai_message]
                return {"session": session, "messages": all_messages, "classification": session.classification, "report": session.report}
            else:
                all_messages = [m for m in session.messages]
                return {"session": session, "messages": all_messages, "classification": session.classification, "report": session.report}
        else:
            assistant_message = "Acao cancelada pelo usuario."
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
            tool_calls = getattr(msg, 'tool_calls', None)
            if tool_calls:
                for tool_call in tool_calls:
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

    def _current_specialist_question(self, s: SessionState):
        return SPECIALIST_QUESTION_BANK[min(s.specialist_question_count, len(SPECIALIST_QUESTION_BANK) - 1)]