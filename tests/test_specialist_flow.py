import os
from unittest.mock import MagicMock, patch

os.environ["CAL_COM_API_KEY"] = "test_api_key"
os.environ["CAL_COM_EVENT_TYPE_ID"] = "12345"
os.environ["CAL_COM_USERNAME"] = "test"

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
        assert "cal.com" in response.assistant_message

        # 8. Simula a aprovação do usuário
        mock_booking_response = MagicMock()
        mock_booking_response.status_code = 200
        mock_booking_response.json.return_value = {
            "booking": {
                "uid": "test-booking-uid",
                "startTime": "2026-08-25T10:00:00-03:00",
                "endTime": "2026-08-25T11:00:00-03:00",
                "status": "confirmed",
                "attendees": [{"name": "Test User", "email": "colaborador@empresa.com"}],
            }
        }
        with patch("httpx.Client.post", return_value=mock_booking_response):
            final_response = service.handle_message(session_id, "sim")

        # 9. Verifica se a ação foi executada e a sessão concluída
        final_snapshot = service.snapshot(session_id)
        assert final_snapshot.status == SessionStatus.complete
        assert "Ação executada com sucesso" in final_response.assistant_message
        assert "test-booking-uid" in final_response.assistant_message