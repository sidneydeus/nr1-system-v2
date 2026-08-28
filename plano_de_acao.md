# Plano de Ação - Projeto v2: Agente Especialista

Este plano de ação descreve os passos para evoluir o `nr1-agent`, introduzindo um agente especialista para atendimento de riscos em ambientes industriais, em conformidade com os requisitos do Módulo 2.

## 1. Definição do Projeto e Escopo (v1 - Concluído)

- [x] **Problema:** Triagem inicial de riscos ocupacionais.
- [x] **Público:** Colaboradores em geral.
- [x] **Solução:** Agente conversacional com LangGraph para triagem e classificação.
- [x] **Evolução (v2):** Foco em indústrias, com um agente especialista que atua em riscos médios/altos, utilizando RAG e ferramentas para agendar ações corretivas.

## 2. Configuração do Ambiente de Desenvolvimento (v1 - Concluído)

- [x] Repositório no GitHub, branches `main` e `develop`.
- [x] Quadro Kanban no GitHub Projects.
- [x] Estrutura de diretórios e ambiente local com `.env.example`.

---

## Sprint 1: Implementação do Agente Especialista (RAG e Tools)

**Foco:** Construir o "cérebro" e os "braços" do novo agente.

-   [x] **(RAG) Criar Base de Conhecimento:**
    -   [x] Criar o arquivo `data/procedimentos_seguranca_industria.md` para simular as normas internas da empresa.
    -   [x] Implementar a lógica para carregar, processar (chunking) e criar um `retriever` para este documento.
-   [x] **(Tools) Desenvolver Ferramentas do Especialista:**
    -   [x] Implementar a função `agendar_inspecao_interna(setor: str, detalhes: str)`.
    -   [x] Implementar a função `agendar_servico_externo(tipo_servico: str, detalhes: str)`.
-   [x] **(LangGraph) Integrar o Agente Especialista ao Fluxo:**
    -   [x] Modificar o grafo para adicionar um nó `especialista_atendimento`.
    -   [x] Criar uma aresta condicional que direcione para o novo nó se o risco for `Médio` ou `Alto`.
    -   [x] Desenvolver o prompt de sistema para o agente especialista, instruindo-o a usar RAG e as ferramentas.

---

## Sprint 2: Segurança, Governança e Testes

**Foco:** Garantir que o novo agente opere de forma segura e que seu comportamento seja testável.

-   [x] **(Governança) Implementar Aprovação Humana:**
    -   [x] Adicionar um novo estado ao grafo que represente "espera por aprovação" antes de acionar ações críticas (ex: agendamento de inspeção).
-   [x] **(QA) Criar Testes para o Novo Fluxo:**
    -   [x] Escrever testes unitários para a rota condicional (risco `Médio`/`Alto` -> especialista).
    -   [x] Escrever testes para a execução das novas ferramentas.
    -   [x] Escrever um teste para validar o funcionamento do `retriever` do RAG.
-   [x] **(Segurança) Teste de Prompt Injection:**
    -   [x] Criar um cenário de teste para verificar se uma entrada maliciosa pode fazer o agente especialista desviar de suas instruções ou acionar ferramentas indevidamente.
-   [x] **(Observabilidade) Logs Estruturados do Agente:**
    -   [x] Implementar logging estruturado (JSON) para rastrear decisões do agente: classificação de risco, consulta RAG (query + documentos recuperados), ferramentas acionadas (nome + parâmetros + resultado), aprovações humanas.
    -   [x] Adicionar correlation ID para rastrear uma sessão completa do início ao fim.
    -   [x] Incluir timestamps, nível de log e contexto da sessão (session_id, user_name, setor) em cada entrada.

---

## Sprint 3: DevOps, Automação e Entrega Final

**Foco:** Automatizar a verificação de qualidade e preparar a entrega.

-   [x] **(DevOps) Configurar Pipeline de CI:**
    -   [x] Criar um workflow no GitHub Actions (`.github/workflows/ci.yml`) que execute `pytest` automaticamente a cada push na branch `develop`.
-   [x] **(DevOps) Migrar RAG para SQLite + sqlite-vec (Persistência Local):**
    -   [x] Adicionar dependência `sqlite-vec` (via `sqlite-utils` ou `sqlite-vec-py`) ao `pyproject.toml`.
    -   [x] Criar tabela virtual `vec_chunks` no `data/nr1.db` existente (embedding float[384] + content + source).
    -   [x] Reescrever `app/tools/retriever.py` para usar sqlite-vec em vez de FAISS em memória.
    -   [x] Criar script de ingestão standalone (`scripts/ingest_vectors.py`) compatível com n8n (CLI/HTTP).
    -   [x] Testar busca vetorial e validar qualidade equivalente ao FAISS.
-   [x] **(Automação Low-Code) Integração com Webhook:**
    -   [x] Após uma ferramenta ser executada com sucesso (ex: agendamento), acionar um webhook para notificar um serviço externo (usar `webhook.site` para simulação).
-   [x] **(Documentação) Atualizar README.md:**
    -   [x] Descrever o novo fluxo com o agente especialista, a base de conhecimento RAG e as ferramentas.
    -   [x] Adicionar um novo diagrama da arquitetura.

-   [ ] **(Entrega) Checklist Final:**
    -   [ ] Organizar todas as evidências (prompts, testes, análises) na pasta `/docs`.
    -   [ ] Revisar e submeter todos os artefatos no AVA.
