from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from groq import Groq

from app.models import ChatMessage, Role


SYSTEM_PROMPT = """Você é um assistente conversacional para triagem NR-1.
Objetivo da fase 1: conduzir uma conversa curta, manter memória da sessão e perguntar de forma objetiva.
Regras:
- faça uma pergunta por vez;
- lembre do nome e do setor do usuário;
- seja consistente com o histórico;
- quando a sessão estiver completa, produza um resumo curto do que foi coletado;
- não invente respostas que não estejam no histórico;
- escreva em português do Brasil.
"""


def _load_dotenv() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.is_file():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue

        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        os.environ[key] = value


@dataclass(slots=True)
class LLMResult:
    text: str


class LLMClient:
    def __init__(self) -> None:
        _load_dotenv()
        self._model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        api_key = os.getenv("GROQ_API_KEY")
        self._enabled = bool(api_key)
        self._client = Groq(api_key=api_key) if self._enabled else None

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def model(self) -> str:
        return self._model

    def respond(self, messages: list[ChatMessage], next_action: str, question_text: str | None = None) -> LLMResult:
        if not self._enabled or self._client is None:
            return LLMResult(text=self._fallback_response(messages, next_action, question_text))

        payload = [{"role": "system", "content": SYSTEM_PROMPT}]
        payload.extend({"role": msg.role.value, "content": msg.content} for msg in messages)
        payload.append(
            {
                "role": "user",
                "content": (
                    "Aplique a próxima ação da sessão: "
                    f"{next_action}. "
                    f"{f'Pergunta fixa: {question_text}. ' if question_text else ''}"
                    "Responda somente com a próxima mensagem do assistente."
                ),
            }
        )

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=payload,
                temperature=0.2,
            )
            text = response.choices[0].message.content or ""
            return LLMResult(text=text.strip())
        except Exception:
            # Keep the app testable and usable offline if the external API is unreachable.
            return LLMResult(text=self._fallback_response(messages, next_action, question_text))

    def respond_with_tools(self, messages: list[ChatMessage], prompt_name: str, tools: list) -> ChatMessage:
        if not self._enabled or self._client is None:
            # Fallback para testes offline
            tool_call = {
                "name": "agendar_inspecao_interna",
                "args": {"setor": "Test Sector", "detalhes": "Risco crítico detectado."},
                "id": "tool_call_123"
            }
            return ChatMessage(role=Role.assistant, content="", tool_calls=[tool_call])

        self._client.models.with_tools = self._client.chat.completions.with_tools
        model_with_tools = self._client.models.with_tools(tools=tools, model=self._model)

        system_prompt = self._get_system_prompt(prompt_name)
        payload = [{"role": "system", "content": system_prompt}]
        payload.extend({"role": msg.role.value, "content": msg.content} for msg in messages)
        
        response = model_with_tools.create(messages=payload, temperature=0.2)
        
        return ChatMessage(
            role=Role.assistant,
            content=response.choices[0].message.content or "",
            tool_calls=response.choices[0].message.tool_calls or []
        )

    def fixed_response(self, next_action: str, question_text: str | None = None) -> str:
        """Return the deterministic conversation prompt instead of an LLM rewrite."""
        return self._fallback_response([], next_action, question_text)

    def _get_system_prompt(self, name: str) -> str:
        # Simplificado para este exemplo. Em um projeto maior, carregaria de um arquivo.
        if name == "specialist_agent_v2":
            return """Você é um agente especialista em segurança do trabalho industrial. Sua missão é dar continuidade a uma conversa iniciada por um agente de triagem, que já classificou um risco como 'Médio' ou 'Alto'.
Você tem acesso a um histórico da conversa e a um documento interno de procedimentos de segurança. Use este documento para aprofundar a investigação e tomar as ações corretivas necessárias.
**Suas Ferramentas são:**
1. `cal_list_available_slots(start_time: str, end_time: str, event_type_id: int, timezone: str)`: Consulta slots disponíveis no cal.com para agendamento de inspeções.
2. `cal_schedule_appointment(start_time: str, event_type_id: int, attendee_name: str, attendee_email: str, attendee_timezone: str, metadata: dict, description: str)`: Agenda um compromisso no cal.com.
3. `cal_cancel_appointment(booking_uid: str, reason: str)`: Cancela um agendamento no cal.com.
4. `cal_list_event_types()`: Lista os tipos de evento disponíveis no cal.com.
5. `agendar_servico_externo(tipo_servico: str, detalhes: str)`: Use esta ferramenta se for necessária uma consultoria ou serviço especializado que a equipe interna não pode prover.
**Seu Processo:**
1. Analise o histórico da conversa para entender o risco relatado.
2. Com base no documento de procedimentos, faça perguntas adicionais ao colaborador para obter mais detalhes sobre o risco.
3. Determine a ação mais apropriada com base nas respostas e nos procedimentos.
4. Para agendar inspeções, primeiro consulte slots disponíveis com `cal_list_available_slots`, depois agende com `cal_schedule_appointment`.
5. Antes de acionar uma ferramenta de agendamento, confirme com o usuário se ele deseja prosseguir.
6. Seja claro, objetivo e foque em resolver a situação de risco."""
        return SYSTEM_PROMPT


    def _fallback_response(self, messages: list[ChatMessage], next_action: str, question_text: str | None = None) -> str:
        if next_action == "ask_name":
            return "Olá. Para começarmos, qual é o seu nome?"
        if next_action == "ask_sector":
            return "Obrigado. Em qual setor você trabalha?"
        if next_action == "ask_question":
            return question_text or "Pode me dizer como é sua rotina de trabalho?"
        if next_action == "summarize":
            return "Sessão encerrada. Vou resumir o que foi coletado."
        return "Vamos continuar a sessão."
