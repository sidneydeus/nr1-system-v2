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
- **Documento Base**: `data/procedimentos_seguranca_ambientes_industriais.pdf`
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

---

## Observabilidade Avançada: OpenTelemetry + Jaeger

O NR-1 Agent v2 também suporta OpenTelemetry nativo para coleta de traces em infraestrutura open-source.

### Configuração do Jaeger (Docker)

```bash
docker run -d --name jaeger \
  -e "COLLECTOR_ZIPKIN_HOST_PORT=:8080" \
  -p 16686:16686 \
  -p 4318:4318 \
  jaegertracing/all-in-one:1.55
```

Acesse a UI em: http://localhost:16686

### Variáveis de Ambiente

Adicione ao seu `.env`:

| Variável | Obrigatória | Descrição |
|---|---|---|
| `JAEGER_ENDPOINT` | Não | URL do collector OTLP (ex: `http://localhost:4318/v1/traces`) |
| `LANGFUSE_PUBLIC_KEY` | Não | Chave pública Langfuse (opcional, para UI complementar) |
| `LANGFUSE_SECRET_KEY` | Não | Chave secreta Langfuse (opcional) |

### Modos de Operação

| Modo | Configuração | Onde os spans vão |
|---|---|---|
| **Console** (padrão) | `JAEGER_ENDPOINT` vazio/unset | `stdout` (terminal) |
| **Jaeger** | `JAEGER_ENDPOINT="http://host:4318/v1/traces"` | UI http://localhost:16686 |
| **Langfuse Cloud** | `LANGFUSE_PUBLIC_KEY` + `LANGFUSE_SECRET_KEY` | UI http://localhost:3000 |
| **Jaeger + Langfuse** | Ambas as configurações acima | Ambos os UIs |

### Como Funciona

O código usa o SDK OpenTelemetry nativo com:

- `TracerProvider` + `BatchSpanProcessor` (console por padrão)
- Exportador OTLP para Jaeger quando `JAEGER_ENDPOINT` estiver definido
- `CallbackHandler` compatível com LangGraph (mesma interface do Langfuse)
- 7 funções `trace_*`: `trace_tool_invocation`, `trace_state_transition`, `trace_risk_classification`, `trace_webhook_event` + helpers

### Exemplos de Spans no Jaeger

Ao executar o agente com `JAEGER_ENDPOINT` configurado, os seguintes spans aparecerão:

```
Span: tool.agendar_servico_externo
  - attributes: session.id, user.name, sector, tool, tool.input, tool.output

Span: state.transition
  - attributes: session.id, user.name, sector, from, to, state.from, state.to

Span: risk.classification
  - attributes: session.id, user.name, sector, classification, categories_count, evidence_count, risk.categories, risk.evidence

Span: webhook.scheduling
  - attributes: session.id, event.type, event.success, event.error, webhook.payload, webhook.output
```

### Código - Nenhuma alteração no grafo necessário

O `ConversationGraph` continua exatamente o mesmo - o `langfuse_handler` é polimórfico e funciona tanto com Langfuse quanto com OpenTelemetry:

```python
from nr1_agent.graph import ConversationGraph
graph = ConversationGraph(store, llm, log_store)
result = graph.invoke("session_id", "mensagem do usuário")
# Spans são automaticamente gerados conforme configuração JAEGER_ENDPOINT
```

### Integração com n8n

O workflow `n8n/workflow_ingestao_arquivos.json` pode ser estendido para incluir calls ao OpenTelemetry Collector, permitindo traces de upload de arquivos de ponta a ponta (from n8n file upload → agent processing → database storage).

---

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

## Serviços e Acesso

| Serviço | Porta | URL | Descrição |
|---|---|---|---|
| **NR-1 Agent (App Principal)** | 8003 | http://localhost:8003 | Interface web, API REST, Health check |
| **MCP Inspection Server** | 8001 | http://localhost:8001 | Servidor MCP para agendamento de inspeções |
| **n8n** | 5678 | http://localhost:5678 | Workflow automation (admin/admin123) |
| **SQLite (Container)** | - | Interno | Banco de dados compartilhado (volumes) |

### Endpoints Principais (NR-1 Agent - porta 8003)

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/` | Interface web do chat |
| `GET` | `/health` | Health check |
| `GET` | `/docs` | Documentação Swagger/OpenAPI |
| `POST` | `/sessions` | Inicia nova sessão |
| `POST` | `/chat` | Envia mensagem do usuário |
| `GET` | `/sessions/{id}` | Snapshot da sessão |
| `GET` | `/admin/reports` | Lista todos os relatórios |
| `GET` | `/admin/reports/{id}` | Relatório específico |
| `GET` | `/admin/logs` | Logs administrativos |
| `GET` | `/config` | Configuração da LLM |
| `POST` | `/admin/ingest` | Ingestão de arquivo (n8n) |
| `POST` | `/admin/reindex` | Reindexação completa (n8n) |
| `GET` | `/admin/vector-stats` | Stats do vector store (n8n) |

### Endpoints MCP Inspection (porta 8001)

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/inspection/schedule` | Agenda inspeção |
| `GET` | `/inspection/{id}` | Consulta agendamento |

---

## Sequência de Execução Local

### Opção A: Docker Compose (Recomendado - Todos os Serviços)

```bash
# 1. Configurar variáveis de ambiente
cp .env.example .env
# Edite .env e preencha GROQ_API_KEY (obrigatório)

# 2. Subir todos os serviços (app + MCP + n8n + SQLite)
docker compose up --build -d

# 3. Verificar status dos containers
docker compose ps

# 4. Ver logs da aplicação
docker compose logs -f nr1-agent

# 5. Inicializar RAG (após containers subirem e estarem healthy)
docker compose exec nr1-agent python scripts/ingest_vectors.py --reindex

# 6. Acessar serviços
# - App: http://localhost:8003
# - MCP: http://localhost:8001
# - n8n: http://localhost:5678 (admin/admin123)
```

### Opção B: Desenvolvimento Local (Python + MCP Opcional)

```bash
# Terminal 1: MCP Server (opcional - só se USE_MCP_SERVER=true)
uvicorn nr1_agent.mcp_http_server:app --reload --port 8001

# Terminal 2: App Principal
# 1. Criar e ativar ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac

# 2. Instalar dependências
pip install -e .

# 3. Configurar variáveis de ambiente
cp .env.example .env
# Edite .env: GROQ_API_KEY (obrigatório), USE_MCP_SERVER=true se usar MCP real

# 4. Inicializar banco e RAG
python scripts/ingest_vectors.py --reindex

# 5. Subir aplicação
uvicorn nr1_agent.main:app --reload --host 0.0.0.0 --port 8000

# Acesse: http://127.0.0.1:8000
```

### Opção C: Apenas Testes (Sem Subir Serviços)

```bash
# Instalar dependências
pip install -e .

# Configurar .env com GROQ_API_KEY
cp .env.example .env

# Inicializar RAG
python scripts/ingest_vectors.py --reindex

# Rodar testes
pytest -v
```

---

### Verificar se Está Funcionando

```bash
# Health check (Docker Compose usa porta 8003, local usa 8000)
curl http://localhost:8003/health    # Docker
curl http://127.0.0.1:8000/health    # Local

# Health check MCP
curl http://localhost:8001/health

# Criar sessão
curl -X POST http://localhost:8003/sessions \
  -H "Content-Type: application/json" \
  -d '{"user_name": "João", "sector": "Manutenção"}'

# Ver relatórios (admin)
curl http://localhost:8003/admin/reports

# Ver stats do vector store
curl http://localhost:8003/admin/vector-stats
```

---

### Comandos Úteis

```bash
# Rodar testes
pytest -v

# Reindexar RAG após adicionar documentos
python scripts/ingest_vectors.py --reindex

# Ver stats do vector store
python scripts/ingest_vectors.py --stats

# Reset completo do banco
python scripts/reset_db.py
python scripts/ingest_vectors.py --reindex

# Ver logs estruturados (SQLite)
sqlite3 data/nr1.db "SELECT * FROM logs ORDER BY timestamp DESC LIMIT 10;"

# Ver containers Docker
docker compose ps
docker compose logs -f [serviço]

# Parar tudo
docker compose down

# Parar e remover volumes (reset total)
docker compose down -v
```

---

## Testes

```bash
# Todos os testes
pytest -v

# Apenas testes de fluxo
pytest tests/test_specialist_flow.py -v

# Com coverage
pytest --cov=app --cov-report=term-missing
```

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
- RAG baseado no documento `procedimentos_seguranca_ambientes_industriais.pdf`
- Classificação baseada em regras NR-1 codificadas, não ML puro
