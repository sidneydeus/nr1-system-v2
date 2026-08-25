import sqlite3

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

    assert response.status.value == "awaiting_approval"

    # Simula a aprovação do usuário para concluir o fluxo (especialista)
    final_response = service.handle_message(session.session_id, "sim")
    assert final_response.status.value == "complete"

    snapshot = service.snapshot(session.session_id)
    assert snapshot.status.value == "complete"
    assert snapshot.question_count == 5
    assert snapshot.user_name == "Ana"
    assert snapshot.sector == "Operações"
    assert snapshot.summary is not None
    # Fluxo com especialista tem mais mensagens (especialista, aprovação, execução de ferramenta)
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
    # Mensagem final agora confirma execução da ação do especialista
    assert "Ação executada com sucesso" in final_response.assistant_message
    assert "Protocolo: INSP-2026-98765" in final_response.assistant_message
    # Relatório NÃO é enviado ao usuário (não contém "Classificação")
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
