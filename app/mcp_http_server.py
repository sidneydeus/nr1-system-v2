from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict


@dataclass
class Inspection:
    id: str
    customer: str
    date: str
    time: str
    service: str = "Inspeção de Segurança"
    status: str = "CONFIRMADA"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


_inspections: Dict[str, Inspection] = {}


def _generate_slots(date: str) -> List[str]:
    slots = []
    for hour in range(8, 18):
        for minute in [0, 30]:
            slots.append(f"{date} {hour:02d}:{minute:02d}")
    return slots


app = FastAPI(title="MCP Inspection Calendar", version="1.0.0")


class GetSlotsRequest(BaseModel):
    date: str


class CreateBookingRequest(BaseModel):
    customer_name: str
    date: str
    time: str
    service: str = "Inspeção de Segurança"


class CancelBookingRequest(BaseModel):
    booking_id: str


@app.post("/mcp/tools/get_available_slots")
async def get_available_slots(req: GetSlotsRequest) -> Dict[str, Any]:
    slots = _generate_slots(req.date)
    return {"result": {"content": [{"type": "text", "text": str(slots)}]}}


@app.post("/mcp/tools/create_booking")
async def create_booking(req: CreateBookingRequest) -> Dict[str, Any]:
    booking_id = f"INSP-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    inspection = Inspection(
        id=booking_id,
        customer=req.customer_name,
        date=req.date,
        time=req.time,
        service=req.service,
        status="CONFIRMADA",
    )
    _inspections[booking_id] = inspection
    return {"result": {"content": [{"type": "text", "text": inspection.to_dict().__str__()}]}}


@app.post("/mcp/tools/get_booking")
async def get_booking(req: CancelBookingRequest) -> Dict[str, Any]:
    inspection = _inspections.get(req.booking_id)
    if not inspection:
        raise HTTPException(status_code=404, detail=f"Booking {req.booking_id} not found")
    return {"result": {"content": [{"type": "text", "text": inspection.to_dict().__str__()}]}}


@app.post("/mcp/tools/cancel_booking")
async def cancel_booking(req: CancelBookingRequest) -> Dict[str, Any]:
    if req.booking_id not in _inspections:
        raise HTTPException(status_code=404, detail=f"Booking {req.booking_id} not found")
    _inspections[req.booking_id].status = "CANCELADA"
    return {"result": {"content": [{"type": "text", "text": f'{{"success": true, "message": "Booking {req.booking_id} cancelled"}}'}]}}


@app.post("/mcp/tools/list_bookings")
async def list_bookings() -> Dict[str, Any]:
    bookings = [insp.to_dict() for insp in _inspections.values()]
    return {"result": {"content": [{"type": "text", "text": str(bookings)}]}}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "mcp-inspection-calendar"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)