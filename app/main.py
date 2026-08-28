from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.log_store import setup_json_logging
from app.models import (
    ChatRequest,
    ChatResponse,
    LogResponse,
    ReportResponse,
    SessionCreateResponse,
    SessionSnapshot,
)
from app.service import ConversationService


setup_json_logging(logging.INFO)


app = FastAPI(title="NR-1 Agent", version="0.1.0")
service = ConversationService()
frontend_dir = Path(__file__).resolve().parents[1] / "frontend"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

if frontend_dir.exists():
    app.mount("/frontend", StaticFiles(directory=frontend_dir), name="frontend")
    app.mount("/css", StaticFiles(directory=frontend_dir / "css"), name="css")
    app.mount("/js", StaticFiles(directory=frontend_dir / "js"), name="js")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/config")
def config() -> dict[str, object]:
    return {
        "llm_enabled": service.llm.enabled,
        "model": service.llm.model,
        "max_questions_per_session": 7,
    }


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    index_path = frontend_dir / "index.html"
    return FileResponse(index_path, media_type="text/html")


@app.post("/sessions", response_model=SessionCreateResponse)
def create_session() -> SessionCreateResponse:
    step = service.start()
    return SessionCreateResponse(
        session_id=step.session_id,
        status=step.status,
        assistant_message=step.assistant_message,
    )


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        return service.handle_message(request.session_id, request.message)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Sessão não encontrada") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/sessions/{session_id}", response_model=SessionSnapshot)
def get_session(session_id: str) -> SessionSnapshot:
    try:
        return service.snapshot(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Sessão não encontrada") from exc


@app.get("/admin/reports", response_model=list[ReportResponse])
def list_reports() -> list[ReportResponse]:
    return [ReportResponse(**report) for report in service.list_reports()]


@app.get("/admin/reports/{session_id}", response_model=ReportResponse)
def get_report(session_id: str) -> ReportResponse:
    report = service.report(session_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")
    return ReportResponse(**report)


@app.get("/admin/logs", response_model=list[LogResponse])
def list_logs() -> list[LogResponse]:
    return [LogResponse(**log) for log in service.list_logs()]
