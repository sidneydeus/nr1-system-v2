from __future__ import annotations
import os
from typing import Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field
import httpx


class CalComConfig(BaseModel):
    api_key: str = Field(default_factory=lambda: os.getenv("CAL_COM_API_KEY", ""))
    base_url: str = Field(default="https://api.cal.com/v1")
    event_type_id: int = Field(default_factory=lambda: int(os.getenv("CAL_COM_EVENT_TYPE_ID", "0")))
    username: str = Field(default_factory=lambda: os.getenv("CAL_COM_USERNAME", ""))


config = CalComConfig()


@tool
def cal_list_available_slots(
    start_time: str,
    end_time: str,
    event_type_id: Optional[int] = None,
    timezone: str = "America/Sao_Paulo"
) -> str:
    """
    Consulta slots disponíveis no cal.com para um tipo de evento.

    Args:
        start_time: Data/hora inicial no formato ISO 8601 (ex: "2026-08-25T09:00:00-03:00")
        end_time: Data/hora final no formato ISO 8601 (ex: "2026-08-25T18:00:00-03:00")
        event_type_id: ID do tipo de evento (opcional, usa o padrão do config se não informado)
        timezone: Fuso horário (padrão: America/Sao_Paulo)

    Returns:
        Lista de slots disponíveis em formato legível.
    """
    if not config.api_key:
        return "Erro: CAL_COM_API_KEY não configurada."

    event_type = event_type_id or config.event_type_id
    if not event_type:
        return "Erro: event_type_id não configurado."

    url = f"{config.base_url}/slots"
    params = {
        "apiKey": config.api_key,
        "eventTypeId": event_type,
        "start": start_time,
        "end": end_time,
        "timeZone": timezone,
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        if not data.get("slots"):
            return "Nenhum slot disponível no período solicitado."

        slots = data["slots"]
        formatted = []
        for date, times in slots.items():
            for slot in times:
                formatted.append(f"- {date} às {slot['time']}")

        return f"Slots disponíveis para o evento {event_type}:\n" + "\n".join(formatted[:20])

    except httpx.HTTPStatusError as e:
        return f"Erro HTTP {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Erro ao consultar slots: {str(e)}"


@tool
def cal_schedule_appointment(
    start_time: str,
    event_type_id: Optional[int] = None,
    attendee_name: str = "",
    attendee_email: str = "",
    attendee_timezone: str = "America/Sao_Paulo",
    metadata: Optional[dict] = None,
    description: str = "",
) -> str:
    """
    Agenda um compromisso no cal.com.

    Args:
        start_time: Data/hora de início no formato ISO 8601 (ex: "2026-08-25T10:00:00-03:00")
        event_type_id: ID do tipo de evento (opcional, usa o padrão do config se não informado)
        attendee_name: Nome do participante
        attendee_email: Email do participante
        attendee_timezone: Fuso horário do participante (padrão: America/Sao_Paulo)
        metadata: Metadados adicionais (opcional)
        description: Descrição do agendamento

    Returns:
        Confirmação do agendamento com detalhes.
    """
    if not config.api_key:
        return "Erro: CAL_COM_API_KEY não configurada."

    event_type = event_type_id or config.event_type_id
    if not event_type:
        return "Erro: event_type_id não configurado."

    if not attendee_name or not attendee_email:
        return "Erro: attendee_name e attendee_email são obrigatórios."

    url = f"{config.base_url}/bookings"
    payload = {
        "apiKey": config.api_key,
        "eventTypeId": event_type,
        "start": start_time,
        "attendee": {
            "name": attendee_name,
            "email": attendee_email,
            "timeZone": attendee_timezone,
        },
        "metadata": metadata or {},
        "description": description,
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        booking = data.get("booking", {})
        return (
            f"Agendamento confirmado!\n"
            f"- UID: {booking.get('uid')}\n"
            f"- Início: {booking.get('startTime')}\n"
            f"- Fim: {booking.get('endTime')}\n"
            f"- Participante: {booking.get('attendees', [{}])[0].get('name')} "
            f"({booking.get('attendees', [{}])[0].get('email')})\n"
            f"- Status: {booking.get('status')}"
        )

    except httpx.HTTPStatusError as e:
        return f"Erro HTTP {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Erro ao agendar: {str(e)}"


@tool
def cal_cancel_appointment(booking_uid: str, reason: str = "Cancelado pelo usuário") -> str:
    """
    Cancela um agendamento no cal.com.

    Args:
        booking_uid: UID do agendamento a ser cancelado
        reason: Motivo do cancelamento

    Returns:
        Confirmação do cancelamento.
    """
    if not config.api_key:
        return "Erro: CAL_COM_API_KEY não configurada."

    url = f"{config.base_url}/bookings/{booking_uid}/cancel"
    payload = {
        "apiKey": config.api_key,
        "reason": reason,
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        return f"Agendamento {booking_uid} cancelado com sucesso."

    except httpx.HTTPStatusError as e:
        return f"Erro HTTP {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Erro ao cancelar: {str(e)}"


@tool
def cal_list_event_types() -> str:
    """
    Lista os tipos de evento disponíveis no cal.com.

    Returns:
        Lista de tipos de evento com IDs.
    """
    if not config.api_key:
        return "Erro: CAL_COM_API_KEY não configurada."

    url = f"{config.base_url}/event-types"
    params = {"apiKey": config.api_key}

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        event_types = data.get("event_types", [])
        if not event_types:
            return "Nenhum tipo de evento encontrado."

        formatted = []
        for et in event_types:
            formatted.append(
                f"- ID: {et.get('id')} | Nome: {et.get('title')} | "
                f"Duração: {et.get('length')}min | Oculto: {et.get('hidden')}"
            )

        return "Tipos de evento disponíveis:\n" + "\n".join(formatted)

    except httpx.HTTPStatusError as e:
        return f"Erro HTTP {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"Erro ao listar tipos de evento: {str(e)}"


def get_cal_tools():
    """Retorna a lista de ferramentas cal.com disponíveis."""
    return [
        cal_list_available_slots,
        cal_schedule_appointment,
        cal_cancel_appointment,
        cal_list_event_types,
    ]


if __name__ == "__main__":
    print("Testando ferramentas cal.com:")
    print("\n1. Listando tipos de evento:")
    print(cal_list_event_types.invoke({}))