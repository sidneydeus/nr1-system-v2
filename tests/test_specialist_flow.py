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

    # Mock para forçar o especialista a chamar uma ferramenta
    mock_tool_call_response = ChatMessage(
        role=Role.assistant,
        content="",
        tool_calls=[{
            "name": "agendar_inspecao_interna",
            "args": {"setor": "Test Sector", "detalhes": "Risco crítico detectado."},
            "id": "tool_call_123"
        }]
    )

    with patch('app.risk_classifier.classify', return_value=mock_assessment), \
         patch.object(service.graph.llm, 'respond_with_tools', return_value=mock_tool_call_response):

        # 1. Inicia a conversa
        start = service.start()
        session_id = start.session_id

        # 2. Preenche os dados da triagem
        service.handle_message(session_id, "Test User")
        service.handle_message(session_id, "Test Sector")
        for i in range(5):
            response = service.handle_message(session_id, f"High risk answer {i+1}")

        # 3. Verifica se o sistema está aguardando aprovação
        snapshot = service.snapshot(session_id)
        assert snapshot.status == SessionStatus.awaiting_approval
        assert "O especialista sugeriu a ação:" in response.assistant_message
        assert "agendar_inspecao_interna" in response.assistant_message

        # 4. Simula a aprovação do usuário
        final_response = service.handle_message(session_id, "sim")

        # 5. Verifica se a ação foi executada e a sessão concluída
        final_snapshot = service.snapshot(session_id)
        assert final_snapshot.status == SessionStatus.complete
        assert "Ação executada com sucesso" in final_response.assistant_message
        assert "Protocolo: INSP-2026-98765" in final_response.assistant_message
