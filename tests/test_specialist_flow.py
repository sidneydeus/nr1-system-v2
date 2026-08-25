import os
from unittest.mock import MagicMock, patch

from app.llm import LLMClient
from app.models import ChatMessage, Role, SessionStatus
from app.report_store import SQLiteReportStore
from app.service import ConversationService


def test_high_risk_triggers_specialist_and_approval_flow(tmp_path):
    """
    Verifica se uma classificação de risco 'Alto' aciona o agente especialista
    e, em seguida, o fluxo de aprovação humana.
    """
    database_path = tmp_path / "test.db"
    service = ConversationService(
        llm=LLMClient(),
        report_store=SQLiteReportStore(database_path),
    )

    # Mock para forçar a classificação de risco "Alto"
    mock_assessment = MagicMock()
    mock_assessment.classification = "Alto / Crítico"

    with patch('app.graph.classify', return_value=mock_assessment):

        # 1. Inicia a conversa
        start = service.start()
        session_id = start.session_id

        # 2. Preenche os dados da triagem
        service.handle_message(session_id, "Test User")
        service.handle_message(session_id, "Test Sector")
        for i in range(5):
            response = service.handle_message(session_id, f"High risk answer {i+1}")

        # 5ª resposta: processamento e classificação acontecem na mesma invocação
        # Para risco Alto, status vai para awaiting_specialist_consent
        assert response.status == SessionStatus.awaiting_specialist_consent
        assert "Classificação de risco: **Alto / Crítico**" in response.assistant_message
        assert "Gostaria de compartilhar mais detalhes com um agente especialista" in response.assistant_message

        # 4. Usuário aceita especialista
        response = service.handle_message(session_id, "sim")
        assert response.status == SessionStatus.specialist_collecting

        # 5. Usuário responde 5 perguntas do especialista
        for i in range(5):
            response = service.handle_message(session_id, f"Specialist answer {i+1}")

        # 6. Verifica se está pedindo consentimento para agendamento
        assert response.status == SessionStatus.awaiting_schedule_consent
        assert "Deseja solicitar o agendamento agora" in response.assistant_message

        # 7. Usuário aceita agendar
        response = service.handle_message(session_id, "sim")
        assert response.status == SessionStatus.awaiting_approval
        assert "inspeção de segurança" in response.assistant_message.lower()

        # 8. Usuário aprova o agendamento (MCP tool não precisa de mock HTTP)
        final_response = service.handle_message(session_id, "sim")

        # 9. Verifica se a ação foi executada e a sessão concluída
        final_snapshot = service.snapshot(session_id)
        assert final_snapshot.status == SessionStatus.complete
        assert "Ação executada com sucesso" in final_response.assistant_message
        assert "INSP-" in final_response.assistant_message