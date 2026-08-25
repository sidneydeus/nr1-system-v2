from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class Inspection:
    id: str
    customer: str
    date: str
    time: str
    status: str = "CONFIRMADA"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class InspectionMCPServer:
    def __init__(self) -> None:
        self.inspections: Dict[str, Inspection] = {}
        self._load_default_slots()

    def _load_default_slots(self) -> None:
        pass

    def get_available_slots(self, date: Optional[str] = None) -> List[Dict[str, Any]]:
        base_date = date or datetime.now().strftime("%Y-%m-%d")
        slots = []
        for hour in range(8, 18):
            for minute in [0, 30]:
                time_str = f"{hour:02d}:{minute:02d}"
                slots.append({"date": base_date, "time": time_str, "available": True})
        return slots

    def schedule_inspection(self, customer: str, date: str, time: str) -> Dict[str, Any]:
        inspection_id = f"INSP-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        inspection = Inspection(
            id=inspection_id,
            customer=customer,
            date=date,
            time=time,
            status="CONFIRMADA",
        )
        self.inspections[inspection_id] = inspection
        return {"success": True, "inspection": inspection.to_dict()}

    def cancel_inspection(self, inspection_id: str) -> Dict[str, Any]:
        if inspection_id in self.inspections:
            self.inspections[inspection_id].status = "CANCELADA"
            return {"success": True, "message": f"Inspeção {inspection_id} cancelada com sucesso."}
        return {"success": False, "message": f"Inspeção {inspection_id} não encontrada."}

    def list_inspections(self) -> List[Dict[str, Any]]:
        return [insp.to_dict() for insp in self.inspections.values()]

    def get_inspection(self, inspection_id: str) -> Optional[Dict[str, Any]]:
        insp = self.inspections.get(inspection_id)
        return insp.to_dict() if insp else None


mcp_server = InspectionMCPServer()


def get_available_slots(date: Optional[str] = None) -> str:
    slots = mcp_server.get_available_slots(date)
    if not slots:
        return "Nenhum slot disponível para a data solicitada."
    formatted = "\n".join([f"- {s['date']} às {s['time']}" for s in slots[:20]])
    return f"Slots disponíveis para {date or 'hoje'}:\n{formatted}"


def schedule_inspection(customer: str, date: str, time: str) -> str:
    result = mcp_server.schedule_inspection(customer, date, time)
    if result["success"]:
        insp = result["inspection"]
        return (
            f"Inspeção agendada com sucesso!\n"
            f"- ID: {insp['id']}\n"
            f"- Cliente: {insp['customer']}\n"
            f"- Data: {insp['date']}\n"
            f"- Horário: {insp['time']}\n"
            f"- Status: {insp['status']}"
        )
    return f"Erro ao agendar: {result.get('message', 'Erro desconhecido')}"


def cancel_inspection(inspection_id: str) -> str:
    result = mcp_server.cancel_inspection(inspection_id)
    if result["success"]:
        return result["message"]
    return f"Erro: {result['message']}"


if __name__ == "__main__":
    print("=== MCP Server de Agendamento de Inspeções ===\n")
    print("1. Slots disponíveis:")
    print(get_available_slots("2026-08-26"))
    print("\n2. Agendando inspeção:")
    print(schedule_inspection("João", "2026-08-26", "14:00"))
    print("\n3. Listando inspeções:")
    for insp in mcp_server.list_inspections():
        print(f"- {insp['id']} | {insp['customer']} | {insp['date']} {insp['time']} | {insp['status']}")
    print("\n4. Cancelando inspeção:")
    insp_id = list(mcp_server.inspections.keys())[0]
    print(cancel_inspection(insp_id))