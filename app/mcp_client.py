from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPInspectionClient:
    def __init__(self, server_script: str = "app/mcp_server_fast.py") -> None:
        self.server_script = server_script
        self._session: Optional[ClientSession] = None
        self._read_stream = None
        self._write_stream = None

    async def __aenter__(self) -> "MCPInspectionClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.disconnect()

    async def connect(self) -> None:
        server_params = StdioServerParameters(
            command="python",
            args=[self.server_script],
        )
        self._read_stream, self._write_stream = await stdio_client(server_params).__aenter__()
        self._session = ClientSession(self._read_stream, self._write_stream)
        await self._session.__aenter__()
        await self._session.initialize()

    async def disconnect(self) -> None:
        if self._session:
            await self._session.__aexit__(None, None, None)
        if self._read_stream:
            await stdio_client(None).__aexit__(None, None, None)

    async def get_available_slots(self, date: str) -> List[str]:
        result = await self._session.call_tool("get_available_slots", {"date": date})
        return result.content[0].text if result.content else []

    async def create_booking(self, customer_name: str, date: str, time: str, service: str = "Inspeção de Segurança") -> Dict[str, Any]:
        result = await self._session.call_tool("create_booking", {
            "customer_name": customer_name,
            "date": date,
            "time": time,
            "service": service,
        })
        import json
        return json.loads(result.content[0].text)

    async def get_booking(self, booking_id: str) -> Dict[str, Any]:
        result = await self._session.call_tool("get_booking", {"booking_id": booking_id})
        import json
        return json.loads(result.content[0].text)

    async def cancel_booking(self, booking_id: str) -> Dict[str, Any]:
        result = await self._session.call_tool("cancel_booking", {"booking_id": booking_id})
        import json
        return json.loads(result.content[0].text)

    async def list_bookings(self) -> List[Dict[str, Any]]:
        result = await self._session.call_tool("list_bookings", {})
        import json
        return json.loads(result.content[0].text)


async def main():
    async with MCPInspectionClient() as client:
        print("=== MCP Client Test ===\n")
        
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
    asyncio.run(main())