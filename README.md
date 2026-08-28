# NR-1 Agent v2

Agente conversacional com LangGraph para triagem inicial de riscos ocupacionais + Agente Especialista com RAG e ferramentas para ambientes industriais.

## Visão Geral

O **NR-1 Agent v2** estende a triagem básica (v1) com um **Agente Especialista** que atua quando o risco é classificado como `Médio / Alerta` ou `Alto / Crítico`. O especialista utiliza:

- **RAG persistente** com SQLite + sqlite-vec (base de conhecimento de procedimentos de segurança)
- **Ferramentas** para agendar inspeções internas, serviços externos e inspeções via MCP
- **Aprovação humana** obrigatória antes de ações críticas
- **Webhooks** para notificação de sistemas externos (ex: n8n, webhook.site)
- **Logs estruturados** JSON com correlation ID para observabilidade completa

## Arquitetura v2

```
┌─────────────────┐     ┌──────────────────┐     ┌────────────────────┐
│   Triagem       │────▶│  Classificação   │────▶│  Agente Especialista│
│   (5 perguntas) │     │  (Baixo/Médio/   │     │  (se Médio/Alto)   │
└─────────────────┘     │   Alto/Crítico)  │     └─────────┬──────────┘
                        └──────────────────┘               │
                              │                            │
                              ▼                            ▼
                        ┌──────────────────┐     ┌────────────────────┐
                        │  Risco Baixo:    │     │  1. Consentimento  │
                        │  Fim + Relatório │     │  2. 5 perguntas    │
                        └──────────────────┘     │     RAG + Tools    │
                                                 │  3. Consentimento  │
                                                 │     agendamento    │
                                                 │  4. Aprovação      │
                                                 │     humana         │
                                                 │  5. Webhook        │
                                                 └────────────────────┘
```

## Fluxo Completo

1. **Nome** - Assistente pede o nome do colaborador
2. **Setor** - Pergunta o setor de atuação
3. **5 Perguntas de Triagem** - Coleta informações sobre o trabalho, local, rotina, imprevistos e proteções
4. **Classificação de Risco** - LLM classifica conforme diretrizes NR-1 (Baixo / Médio / Alto)
5. **Se Risco Médio/Alto → Agente Especialista**:
   - Consentimento para atendimento especializado
   - **5 Perguntas RAG** - Especialista consulta base de conhecimento e faz perguntas contextuais
   - Consentimento para agendamento de inspeção
   - **Aprovação Humana** - Confirmação explícita antes de acionar ferramenta
   - **Execução da Ferramenta** - Agenda inspeção (MCP) ou registra solicitação interna/externo
   - **Webhook** - Notifica sistema externo (ex: webhook.site) com detalhes do agendamento
6. **Fim** - Relatório salvo em `data/nr1.db`, disponível em `/admin/reports`

## RAG / Vector Store (Persistente)

- **Tecnologia**: SQLite + sqlite-vec (extensão vetorial nativa)
- **Armazenamento**: `data/nr1.db` (tabela virtual `vec_chunks`, embedding float[384])
- **Modelo de Embedding**: `sentence-transformers/all-MiniLM-L6-v2` (384 dims)
- **Documento Base**: `data/procedimentos_seguranca_industria.md`
- **Ingestão**: `scripts/ingest_vectors.py` (CLI compatível com n8n)
  ```bash
  # Reindexar tudo
  python scripts/ingest_vectors.py --reindex
  
  # Ingerir novo documento
  python scripts/ingest_vectors.py --file data/novo_doc.md --source "novo_doc.md"
  
  # Estatísticas
  python scripts/ingest_vectors.py --stats
  ```

## Ferramentas do Especialista

| Ferramenta | Descrição | Parâmetros |
|---|---|---|
| `schedule_inspection` | Agenda inspeção via servidor MCP | `customer`, `date`, `time` |
| `agendar_inspecao_interna` | Agendamento interno da equipe de segurança | `setor`, `detalhes` |
| `agendar_servico_externo` | Aciona fornecedor especializado externo | `tipo_servico`, `detalhes` |

## Observabilidade (Logs Estruturados)

Todos os eventos do agente emitem logs JSON no console + SQLite:

```json
{
  "timestamp": "2026-08-27T19:53:47.284514+00:00",
  "level": "INFO",
  "logger": "nr1.agent",
  "session_id": "abc-123",
  "correlation_id": "abc-123-xyz789",
  "user_name": "João",
  "sector": "Manutenção",
  "event": "RISK_CLASSIFICATION",
  "classification": "Médio / Alerta",
  "categories": ["Altura"],
  "evidence": ["Trabalho sem PT"]
}
```

**Eventos rastreados**: `SESSION_START`, `SESSION_END`, `RISK_CLASSIFICATION`, `RAG_QUERY`, `TOOL_INVOCATION`, `HUMAN_APPROVAL`, `STATE_TRANSITION`, `ADMIN_REPORT_ALERT`

## CI/CD Pipeline

GitHub Actions (`.github/workflows/ci.yml`):
- Trigger: push/PR para branch `develop`
- Executa: `pytest -v --tb=short`
- Python 3.10, instala dependências via `pip install -e .`

## Variáveis de Ambiente

Copie `.env.example` para `.env` e preencha:

| Variável | Obrigatória | Descrição |
|---|---|---|
| `GROQ_API_KEY` | Sim | Chave da API Groq |
| `GROQ_MODEL` | Não | Modelo (default: `llama-3.1-8b-instant`) |
| `WEBHOOK_URL` | Não | URL webhook.site para notificações de agendamento |
| `SQLITE_DB_PATH` | Não | Caminho do banco (default: `data/nr1.db`) |
| `MCP_INSPECTION_URL` | Não | URL servidor MCP (default: `http://localhost:8001`) |
| `USE_MCP_SERVER` | Não | Usar MCP real vs fallback (default: `false`) |

## Execução Local

```bash
# Ativar venv
source .venv/bin/activate

# Instalar dependências (se necessário)
pip install -e .

# Subir aplicação
uvicorn app.main:app --reload
```

Acesse `http://127.0.0.1:8000/` para a interface web.

## Testes

```bash
# Todos os testes
pytest -v

# Apenas testes de fluxo
pytest tests/test_specialist_flow.py -v

# Com coverage
pytest --cov=app --cov-report=term-missing
```

## Endpoints Principais

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/sessions` | Inicia nova sessão |
| `POST` | `/chat` | Envia mensagem do usuário |
| `GET` | `/sessions/{id}` | Snapshot da sessão |
| `GET` | `/admin/reports` | Lista todos os relatórios |
| `GET` | `/admin/reports/{id}` | Relatório específico |
| `GET` | `/admin/logs` | Logs administrativos |
| `GET` | `/config` | Configuração da LLM |
| `GET` | `/health` | Health check |
| `GET` | `/` | Interface web |

## Diagrama de Arquitetura

O fluxo completo está documentado em [`docs/fluxo-aplicacao.mmd`](docs/fluxo-aplicacao.mmd) (formato Mermaid).

## Decisões Técnicas

- **LangGraph**: Orquestração de estado, nós condicionais, ferramentas
- **SQLite + sqlite-vec**: Vetores persistentes sem servidor externo
- **Groq (Llama 3.1)**: LLM rápida para classificação e geração de relatórios
- **Fallback MCP**: Modo em memória para testes, servidor real opcional
- **Aprovação Humana**: Estado `awaiting_approval` no grafo antes de tools críticas

## Reset do Banco de Dados

Para limpar todos os dados (logs, relatórios, vetores RAG) e reiniciar do zero:

```bash
# Opção 1: Script dedicado (recomendado)
python scripts/reset_db.py

# Opção 2: Remover arquivo (tabelas recriadas automaticamente no próximo start)
rm data/nr1.db

# Após reset, reindexar base de conhecimento RAG:
python scripts/ingest_vectors.py --reindex
```

**Tabelas afetadas:**
- `logs` - Logs estruturados JSON
- `reports` - Relatórios de triagem
- `vec_chunks` - Vetores RAG (sqlite-vec)

## Limitações

- Triagem inicial, não substitui avaliação técnica completa
- Qualidade depende das respostas do colaborador
- RAG limitado ao documento `procedimentos_seguranca_industria.md`
- Classificação baseada em regras NR-1 codificadas, não ML puro
