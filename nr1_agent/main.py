from __future__ import annotations

import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, BackgroundTasks, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from nr1_agent.log_store import setup_json_logging
from nr1_agent.models import (
    ChatRequest,
    ChatResponse,
    LogResponse,
    ReportResponse,
    SessionCreateResponse,
    SessionSnapshot,
)
from nr1_agent.service import ConversationService
from scripts.ingest_vectors import ingest_file, reindex_all


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


class IngestRequest(BaseModel):
    file_path: str
    source: str | None = None


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


@app.post("/admin/ingest")
def ingest_document(request: IngestRequest, background_tasks: BackgroundTasks) -> dict[str, str]:
    def run_ingest():
        try:
            ingest_file(request.file_path, request.source)
        except Exception as e:
            logging.getLogger(__name__).error(f"Ingestão falhou: {e}")

    background_tasks.add_task(run_ingest)
    return {"status": "started", "file": request.file_path, "source": request.source or request.file_path}


@app.post("/admin/reindex")
def reindex(background_tasks: BackgroundTasks) -> dict[str, str]:
    def run_reindex():
        try:
            reindex_all()
        except Exception as e:
            logging.getLogger(__name__).error(f"Reindexação falhou: {e}")

    background_tasks.add_task(run_reindex)
    return {"status": "started"}


@app.get("/admin/vector-stats")
def vector_stats() -> dict[str, int]:
    from nr1_agent.vector_store import count_vectors
    return {"total_vectors": count_vectors()}


TEST_UPLOAD_DIR = "/tmp/test_uploads"


@app.get("/test-upload", include_in_schema=False)
def test_upload_get() -> FileResponse:
    """Servir formulário de teste de upload de arquivo."""
    html = """
    <html>
    <head><title>Teste de Ingestão de Arquivos</title></head>
    <body>
    <h2>Upload de Documento para Vector DB</h2>
    <form method="post" enctype="multipart/form-data" action="/test-upload">
        <label>Arquivo:</label>
        <input type="file" name="file" accept=".pdf,.md,.txt,.markdown" required><br><br>
        <label>Nome da Fonte (opcional):</label>
        <input type="text" name="source" placeholder="ex: procedimentos.md"><br><br>
        <button type="submit">Enviar para Ingestão</button>
    </form>
    </body>
    </html>
    """
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html)


@app.post("/test-upload", include_in_schema=False)
def test_upload_post(file: bytes = File(...), source: str = Form(None)) -> dict[str, str]:
    """Processar upload de arquivo de teste."""
    import os
    from pathlib import Path

    # Salvar arquivo temporariamente
    upload_dir = Path(TEST_UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Determinar nome do arquivo (usar source ou gerar um único)
    filename = source or f"test_{os.urandom(4).hex()}.pdf"
    filepath = upload_dir / filename

    with open(filepath, "wb") as f:
        f.write(file)

    # Ingerir usando o script existente
    from scripts.ingest_vectors import ingest_file
    try:
        chunks = ingest_file(str(filepath), source or filename)
        return {
            "status": "success",
            "message": f"Arquivo uploadado e ingerido com sucesso!",
            "chunks": str(chunks),
            "file": filename,
        }
    except Exception as e:
        return {"status": "error", "message": f"Erro na ingestão: {e}"}


def main() -> None:
    import uvicorn
    uvicorn.run("nr1_agent.main:app", host="0.0.0.0", port=8000)
