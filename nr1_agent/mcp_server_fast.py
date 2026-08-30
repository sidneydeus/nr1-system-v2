from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict
from fastmcp import FastMCP


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


mcp = FastMCP("Inspection Calendar")

_inspections: Dict[str, Inspection] = {}


def _generate_slots(date: str) -> List[str]:
    slots = []
    for hour in range(8, 18):
        for minute in [0, 30]:
            slots.append(f"{date} {hour:02d}:{minute:02d}")
    return slots


@mcp.tool()
def get_available_slots(date: str) -> List[str]:
    """Return available inspection slots for a date (YYYY-MM-DD)."""
    return _generate_slots(date)


@mcp.tool()
def create_booking(customer_name: str, date: str, time: str, service: str = "Inspeção de Segurança") -> Dict[str, Any]:
    """Schedule an inspection."""
    booking_id = f"INSP-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    inspection = Inspection(
        id=booking_id,
        customer=customer_name,
        date=date,
        time=time,
        service=service,
        status="CONFIRMADA",
    )
    _inspections[booking_id] = inspection
    return inspection.to_dict()


@mcp.tool()
def get_booking(booking_id: str) -> Dict[str, Any]:
    """Get an existing booking."""
    inspection = _inspections.get(booking_id)
    if not inspection:
        return {"error": f"Booking {booking_id} not found"}
    return inspection.to_dict()


@mcp.tool()
def cancel_booking(booking_id: str) -> Dict[str, Any]:
    """Cancel an existing booking."""
    if booking_id not in _inspections:
        return {"error": f"Booking {booking_id} not found"}
    _inspections[booking_id].status = "CANCELADA"
    return {"success": True, "message": f"Booking {booking_id} cancelled"}


@mcp.tool()
def list_bookings() -> List[Dict[str, Any]]:
    """List all bookings."""
    return [insp.to_dict() for insp in _inspections.values()]


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--http":
        mcp.run(transport="http", host="0.0.0.0", port=8001)
    else:
        mcp.run()