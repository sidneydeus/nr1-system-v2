from __future__ import annotations

import httpx
from typing import Any, Dict, List


class MCPHttpClient:
    def __init__(self, base_url: str = "http://localhost:8001/mcp") -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=30.0)

    async def __aenter__(self) -> "MCPHttpClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self._client.aclose()

    async def _call(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        response = await self._client.post(
            self.base_url,
            json={"jsonrpc": "2.0", "method": method, "params": params, "id": 1},
        )
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            raise RuntimeError(data["error"])
        return data.get("result", {})

    async def get_available_slots(self, date: str) -> List[str]:
        result = await self._call("tools/call", {"name": "get_available_slots", "arguments": {"date": date}})
        return result.get("content", [{}])[0].get("text", "").split("\n") if result.get("content") else []

    async def create_booking(self, customer_name: str, date: str, time: str, service: str = "Inspeção de Segurança") -> Dict[str, Any]:
        result = await self._call("tools/call", {
            "name": "create_booking",
            "arguments": {"customer_name": customer_name, "date": date, "time": time, "service": service},
        })
        import json
        text = result.get("content", [{}])[0].get("text", "{}")
        return json.loads(text)

    async def get_booking(self, booking_id: str) -> Dict[str, Any]:
        result = await self._call("tools/call", {"name": "get_booking", "arguments": {"booking_id": booking_id}})
        import json
        text = result.get("content", [{}])[0].get("text", "{}")
        return json.loads(text)

    async def cancel_booking(self, booking_id: str) -> Dict[str, Any]:
        result = await self._call("tools/call", {"name": "cancel_booking", "arguments": {"booking_id": booking_id}})
        import json
        text = result.get("content", [{}])[0].get("text", "{}")
        return json.loads(text)

    async def list_bookings(self) -> List[Dict[str, Any]]:
        result = await self._call("tools/call", {"name": "list_bookings", "arguments": {}})
        import json
        text = result.get("content", [{}])[0].get("text", "[]")
        return json.loads(text)


async def main():
    async with MCPHttpClient("http://localhost:8001/mcp") as client:
        print("=== MCP HTTP Client Test ===\n")
        
        print("1. Available slots for 2026-08-26:")
        slots = await client.get_available_slots("2026-08-26")
        for slot in slots[:5]:
            print(f"  - {slot}")
        print(f"  ... ({len(slots)} total)")
        
        print("\n2. Creating booking:")
        booking = await client.create_booking("João", "2026-08-26", "14:00")
        print(f"  {booking}")
        
        print("\n3. Getting booking:")
        booking = await client.get_booking(booking["id"])
        print(f"  {booking}")
        
        print("\n4. Listing bookings:")
        bookings = await client.list_bookings()
        for b in bookings:
            print(f"  - {b['id']} | {b['customer']} | {b['date']} {b['time']} | {b['status']}")
        
        print("\n5. Cancelling booking:")
        result = await client.cancel_booking(booking["id"])
        print(f"  {result}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())