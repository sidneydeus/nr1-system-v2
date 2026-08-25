from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List
from dataclasses import dataclass, field, asdict
from langchain_core.tools import tool


MCP_BASE_URL = os.getenv("MCP_INSPECTION_URL", "http://localhost:8001")
USE_MCP_SERVER = os.getenv("USE_MCP_SERVER", "false").lower() == "true"


# In-memory fallback for tests and local dev
@dataclass
class _Inspection:
    id: str
    customer: str
    date: str
    time: str
    service: str = "Inspeção de Segurança"
    status: str = "CONFIRMADA"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


_inspections: Dict[str, _Inspection] = {}


def _generate_slots(date: str) -> List[str]:
    slots = []
    for hour in range(8, 18):
        for minute in [0, 30]:
            slots.append(f"{date} {hour:02d}:{minute:02d}")
    return slots


def _mcp_call_sync(tool_name: str, arguments: Dict[str, Any]) -> Any:
    if USE_MCP_SERVER:
        import httpx
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{MCP_BASE_URL}/mcp/tools/{tool_name}",
                json=arguments,
            )
            response.raise_for_status()
            data = response.json()
            if "result" in data:
                import json
                text = data["result"]["content"][0]["text"]
                return json.loads(text.replace("'", '"'))
            raise RuntimeError(f"MCP error: {data}")
    else:
        # Direct function calls for tests/local dev
        if tool_name == "get_available_slots":
            return _generate_slots(arguments["date"])
        elif tool_name == "create_booking":
            booking_id = f"INSP-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
            inspection = _Inspection(
                id=booking_id,
                customer=arguments["customer_name"],
                date=arguments["date"],
                time=arguments["time"],
                service=arguments.get("service", "Inspeção de Segurança"),
            )
            _inspections[booking_id] = inspection
            return inspection.to_dict()
        elif tool_name == "cancel_booking":
            bid = arguments["booking_id"]
            if bid not in _inspections:
                return {"error": f"Booking {bid} not found"}
            _inspections[bid].status = "CANCELADA"
            return {"success": True, "message": f"Booking {bid} cancelled"}
        elif tool_name == "list_bookings":
            return [i.to_dict() for i in _inspections.values()]
        raise ValueError(f"Unknown tool: {tool_name}")


@tool
def get_available_slots(date: str) -> str:
    """
    Consulta slots disponíveis para agendamento de inspeções.

    Args:
        date: Data no formato YYYY-MM-DD (ex: "2026-08-26")

    Returns:
        Lista de horários disponíveis para a data informada.
    """
    slots = _mcp_call_sync("get_available_slots", {"date": date})
    return "Slots disponíveis para " + date + ":\n" + "\n".join([f"- {s}" for s in slots])


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
    result = _mcp_call_sync("create_booking", {
        "customer_name": customer,
        "date": date,
        "time": time,
    })
    return (
        f"Inspeção agendada com sucesso!\n"
        f"- ID: {result['id']}\n"
        f"- Cliente: {result['customer']}\n"
        f"- Data: {result['date']}\n"
        f"- Horário: {result['time']}\n"
        f"- Status: {result['status']}"
    )


@tool
def cancel_inspection(inspection_id: str) -> str:
    """
    Cancela uma inspeção agendada.

    Args:
        inspection_id: ID da inspeção a ser cancelada (ex: "INSP-20260826-A1B2C3")

    Returns:
        Confirmação do cancelamento.
    """
    result = _mcp_call_sync("cancel_booking", {"booking_id": inspection_id})
    return result.get("message", f"Erro: {result}")


def get_mcp_tools():
    """Retorna a lista de ferramentas MCP disponíveis."""
    return [get_available_slots, schedule_inspection, cancel_inspection]


if __name__ == "__main__":
    print("=== Testing MCP HTTP Tools ===\n")
    print("1. Slots:")
    print(get_available_slots.invoke({"date": "2026-08-26"}))
    print("\n2. Schedule:")
    print(schedule_inspection.invoke({"customer": "João", "date": "2026-08-26", "time": "14:00"}))
    print("\n3. Cancel:")
    print(cancel_inspection.invoke({"inspection_id": "INSP-20260825-FD2305"}))