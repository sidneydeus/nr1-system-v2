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

-   [ ] **(RAG) Criar Base de Conhecimento:**
    -   [ ] Criar o arquivo `data/procedimentos_seguranca_industria.md` para simular as normas internas da empresa.
    -   [ ] Implementar a lógica para carregar, processar (chunking) e criar um `retriever` para este documento.
-   [ ] **(Tools) Desenvolver Ferramentas do Especialista:**
    -   [ ] Implementar a função `agendar_inspecao_interna(setor: str, detalhes: str)`.
    -   [ ] Implementar a função `agendar_servico_externo(tipo_servico: str, detalhes: str)`.
-   [ ] **(LangGraph) Integrar o Agente Especialista ao Fluxo:**
    -   [ ] Modificar o grafo para adicionar um nó `especialista_atendimento`.
    -   [ ] Criar uma aresta condicional que direcione para o novo nó se o risco for `Médio` ou `Alto`.
    -   [ ] Desenvolver o prompt de sistema para o agente especialista, instruindo-o a usar RAG e as ferramentas.

---

## Sprint 2: Segurança, Governança e Testes

**Foco:** Garantir que o novo agente opere de forma segura e que seu comportamento seja testável.

-   [ ] **(Governança) Implementar Aprovação Humana:**
    -   [ ] Adicionar um novo estado ao grafo que represente "espera por aprovação" antes de acionar ações críticas (ex: agendamento de inspeção).
-   [ ] **(QA) Criar Testes para o Novo Fluxo:**
    -   [ ] Escrever testes unitários para a rota condicional (risco `Médio`/`Alto` -> especialista).
    -   [ ] Escrever testes para a execução das novas ferramentas.
    -   [ ] Escrever um teste para validar o funcionamento do `retriever` do RAG.
-   [ ] **(Segurança) Teste de Prompt Injection:**
    -   [ ] Criar um cenário de teste para verificar se uma entrada maliciosa pode fazer o agente especialista desviar de suas instruções ou acionar ferramentas indevidamente.
-   [ ] **(Observabilidade) Logs Estruturados do Agente:**
    -   [ ] Implementar logging estruturado (JSON) para rastrear decisões do agente: classificação de risco, consulta RAG (query + documentos recuperados), ferramentas acionadas (nome + parâmetros + resultado), aprovações humanas.
    -   [ ] Adicionar correlation ID para rastrear uma sessão completa do início ao fim.
    -   [ ] Incluir timestamps, nível de log e contexto da sessão (session_id, user_name, setor) em cada entrada.

---

## Sprint 3: DevOps, Automação e Entrega Final

**Foco:** Automatizar a verificação de qualidade e preparar a entrega.

-   [ ] **(DevOps) Configurar Pipeline de CI:**
    -   [ ] Criar um workflow no GitHub Actions (`.github/workflows/ci.yml`) que execute `pytest` automaticamente a cada push na branch `develop`.
-   [ ] **(Automação Low-Code) Integração com Webhook:**
    -   [ ] Após uma ferramenta ser executada com sucesso (ex: agendamento), acionar um webhook para notificar um serviço externo (usar `webhook.site` para simulação).
-   [ ] **(Documentação) Atualizar README.md:**
    -   [ ] Descrever o novo fluxo com o agente especialista, a base de conhecimento RAG e as ferramentas.
    -   [ ] Adicionar um novo diagrama da arquitetura.
-   [ ] **(Entrega) Gravar Vídeo de Demonstração:**
    -   [ ] Produzir um vídeo (10-12 min) demonstrando um caso de uso completo: da triagem ao atendimento especializado, incluindo o uso de RAG e ferramentas.
    -   [ ] Publicar no YouTube e adicionar o link ao README.
-   [ ] **(Entrega) Checklist Final:**
    -   [ ] Organizar todas as evidências (prompts, testes, análises) na pasta `/docs`.
    -   [ ] Revisar e submeter todos os artefatos no AVA.
