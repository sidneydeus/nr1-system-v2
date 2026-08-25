from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class SessionStatus(str, Enum):
    awaiting_name = "awaiting_name"
    awaiting_sector = "awaiting_sector"
    collecting = "collecting"
    processing = "processing"
    awaiting_specialist_consent = "awaiting_specialist_consent"
    specialist_collecting = "specialist_collecting"
    awaiting_schedule_consent = "awaiting_schedule_consent"
    awaiting_approval = "awaiting_approval"
    complete = "complete"
    error = "error"

class Role(str, Enum):
    system = "system"
    user = "user"
    assistant = "assistant"


class ChatMessage(BaseModel):
    role: Role
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    tool_calls: list = Field(default_factory=list)


class SessionState(BaseModel):
    session_id: str
    status: SessionStatus = SessionStatus.awaiting_name
    user_name: str | None = None
    sector: str | None = None
    question_count: int = 0
    asked_questions: list[str] = Field(default_factory=list)
    answers: list[str] = Field(default_factory=list)
    messages: list[ChatMessage] = Field(default_factory=list)
    summary: str | None = None
    pending_tool_calls: list = Field(default_factory=list)
    classification: str | None = None
    report: str | None = None
    specialist_question_count: int = 0
    specialist_asked_questions: list[str] = Field(default_factory=list)
    specialist_answers: list[str] = Field(default_factory=list)
    wants_specialist: bool | None = None
    wants_schedule: bool | None = None


class SessionCreateResponse(BaseModel):
    session_id: str
    status: SessionStatus
    assistant_message: str


class ChatRequest(BaseModel):
    session_id: str
    message: str = Field(min_length=1, max_length=4000)

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("A mensagem não pode estar vazia")
        return normalized


class ChatResponse(BaseModel):
    session_id: str
    status: SessionStatus
    assistant_message: str
    question_count: int
    user_name: str | None = None
    sector: str | None = None


class SessionSnapshot(BaseModel):
    session_id: str
    status: SessionStatus
    user_name: str | None
    sector: str | None
    question_count: int
    asked_questions: list[str]
    answers: list[str]
    messages: list[ChatMessage]
    summary: str | None


class ReportResponse(BaseModel):
    session_id: str
    user_name: str | None
    sector: str | None
    report: str
    classification: str | None
    created_at: datetime


class LogResponse(BaseModel):
    id: int
    session_id: str
    level: str
    event: str
    message: str
    created_at: datetime


class GeneratedReport(BaseModel):
    content: str = Field(min_length=20)

    @field_validator("content")
    @classmethod
    def content_must_have_assessment_sections(cls, value: str) -> str:
        required_sections = (
            "Classificação de risco:",
            "Categorias identificadas:",
            "Evidências consideradas:",
            "Encaminhamento:",
        )
        if any(section not in value for section in required_sections):
            raise ValueError("O relatório não possui todas as seções esperadas")
        return value


class TranscriptLine(BaseModel):
    role: Role
    content: str
