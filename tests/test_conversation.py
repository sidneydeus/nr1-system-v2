import os
import sqlite3
from unittest.mock import patch, MagicMock

os.environ["CAL_COM_API_KEY"] = "test_api_key"
os.environ["CAL_COM_EVENT_TYPE_ID"] = "12345"
os.environ["CAL_COM_USERNAME"] = "test"

from app.llm import LLMClient
from app.report_store import SQLiteReportStore
from app.service import ConversationService


def test_conversation_saves_report_without_sending_it_to_user(tmp_path, caplog) -> None:
    caplog.set_level("WARNING", logger="app.alerts")
    database_path = tmp_path / "reports.db"
    service = ConversationService(
        llm=LLMClient(),
        report_store=SQLiteReportStore(database_path),
    )
    start = service.start()
    session = service.store.list()[-1]

    assert start.assistant_message
    assert start.assistant_message == "Olá. Para começarmos, qual é o seu nome?"
    assert session.status.value == "awaiting_name"

    response = service.handle_message(session.session_id, "Ana")
    assert response.user_name == "Ana"
    assert response.status.value == "awaiting_sector"
    assert session.messages[-1].content == "Obrigado. Em qual setor você trabalha?"

    response = service.handle_message(session.session_id, "Operações")
    assert response.sector == "Operações"
    assert response.status.value == "collecting"
    assert session.messages[-1].content == "Conte como é o trabalho que você realiza e em que local ele acontece."

    for i in range(5):
        response = service.handle_message(session.session_id, f"resposta {i + 1}")

    # 5ª resposta: processamento e classificação acontecem na mesma invocação
    # Para risco Médio/Alto, status vai para awaiting_specialist_consent
    assert response.status.value == "awaiting_specialist_consent"
    assert "Classificação de risco: **Médio / Alerta**" in response.assistant_message
    assert "Gostaria de compartilhar mais detalhes com um agente especialista" in response.assistant_message

    # Usuário aceita falar com especialista
    response = service.handle_message(session.session_id, "sim")
    assert response.status.value == "specialist_collecting"
    assert "Considerando os procedimentos de segurança" in response.assistant_message

    # Usuário responde 5 perguntas do especialista
    for i in range(5):
        response = service.handle_message(session.session_id, f"resposta especialista {i + 1}")

    # Após 5 perguntas do especialista, pergunta sobre agendamento
    assert response.status.value == "awaiting_schedule_consent"
    assert "Deseja solicitar o agendamento agora" in response.assistant_message

    # Usuário aceita agendar
    response = service.handle_message(session.session_id, "sim")
    assert response.status.value == "awaiting_approval"
    assert "cal.com" in response.assistant_message

    # Usuário aprova o agendamento
    mock_booking_response = MagicMock()
    mock_booking_response.status_code = 200
    mock_booking_response.json.return_value = {
        "booking": {
            "uid": "test-booking-uid",
            "startTime": "2026-08-25T10:00:00-03:00",
            "endTime": "2026-08-25T11:00:00-03:00",
            "status": "confirmed",
            "attendees": [{"name": "Ana", "email": "colaborador@empresa.com"}],
        }
    }
    with patch("httpx.Client.post", return_value=mock_booking_response):
        final_response = service.handle_message(session.session_id, "sim")
        assert final_response.status.value == "complete"

    snapshot = service.snapshot(session.session_id)
    assert snapshot.status.value == "complete"
    assert snapshot.question_count == 5
    assert snapshot.user_name == "Ana"
    assert snapshot.sector == "Operações"
    assert snapshot.summary is not None
    assert len(snapshot.messages) > 14
    assert snapshot.asked_questions == [
        "Conte como é o trabalho que você realiza e em que local ele acontece.",
        "Como é o local onde você trabalha e o que você utiliza para realizar suas atividades?",
        "Conte como é um dia típico de trabalho, do início ao fim da jornada.",
        "O que costuma acontecer quando algo sai do esperado durante o trabalho?",
        "Que orientações, treinamentos ou formas de proteção existem para essa atividade? Como você avalia o funcionamento delas?",
    ]
    assert snapshot.answers == [
        "resposta 1",
        "resposta 2",
        "resposta 3",
        "resposta 4",
        "resposta 5",
    ]
    assert "Ação executada com sucesso" in final_response.assistant_message
    assert "test-booking-uid" in final_response.assistant_message
    assert "Classificação" not in final_response.assistant_message

    with sqlite3.connect(database_path) as connection:
        report = connection.execute(
            "SELECT session_id, user_name, sector, report, classification FROM reports WHERE session_id = ?",
            (session.session_id,),
        ).fetchone()
        log = connection.execute(
            "SELECT session_id, level, event, message FROM logs WHERE session_id = ?",
            (session.session_id,),
        ).fetchone()

    assert report is not None
    assert report[:3] == (session.session_id, "Ana", "Operações")
    assert "Classificação de risco: Médio / Alerta" in report[3]
    assert report[4] == "Médio / Alerta"
    assert log == (
        session.session_id,
        "WARNING",
        "ADMIN_REPORT_ALERT",
        "classification=Médio / Alerta; O relatório gerado necessita de ação de verificação de risco.",
    )
    assert "ADMIN_REPORT_ALERT" in caplog.text
    assert session.session_id in caplog.text
    assert "necessita de ação de verificação de risco" in caplog.text