from __future__ import annotations

from langchain_core.tools import tool
from app.mcp_server import get_available_slots as mcp_get_slots, schedule_inspection as mcp_schedule, cancel_inspection as mcp_cancel


@tool
def get_available_slots(date: str = "") -> str:
    """
    Consulta slots disponíveis para agendamento de inspeções.

    Args:
        date: Data no formato YYYY-MM-DD (ex: "2026-08-26"). Se vazio, usa a data de hoje.

    Returns:
        Lista de horários disponíveis para a data informada.
    """
    return mcp_get_slots(date if date else None)


@tool
def schedule_inspection(customer: str, date: str, time: str) -> str:
    """
    Agenda uma inspeção de segurança.

    Args:
        customer: Nome do cliente/colaborador (ex: "João")
        date: Data no formato YYYY-MM-DD (ex: "2026-08-26")
        time: Horário no formato HH:MM (ex: "14:00")

    Returns:
        Confirmação do agendamento com ID da inspeção.
    """
    return mcp_schedule(customer, date, time)


@tool
def cancel_inspection(inspection_id: str) -> str:
    """
    Cancela uma inspeção agendada.

    Args:
        inspection_id: ID da inspeção a ser cancelada (ex: "INSP-20260826-A1B2C3")

    Returns:
        Confirmação do cancelamento.
    """
    return mcp_cancel(inspection_id)


def get_mcp_tools():
    """Retorna a lista de ferramentas MCP disponíveis."""
    return [get_available_slots, schedule_inspection, cancel_inspection]


if __name__ == "__main__":
    print("Testando ferramentas MCP:")
    print("\n1. Slots disponíveis:")
    print(get_available_slots.invoke({"date": "2026-08-26"}))
    print("\n2. Agendando inspeção:")
    print(schedule_inspection.invoke({"customer": "João", "date": "2026-08-26", "time": "14:00"}))
    print("\n3. Cancelando inspeção:")
    print(cancel_inspection.invoke({"inspection_id": "INSP-20260826-A1B2C3"}))