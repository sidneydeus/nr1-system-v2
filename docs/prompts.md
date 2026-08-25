# Prompts

Este arquivo reúne os prompts principais usados no planejamento, implementação, correção e evolução do agente.

## 1. Planejamento do agente
**Objetivo:** definir o escopo, o fluxo e a saída esperada.

**Prompt-base:**
> Proponha um chat agente em Python com FastAPI e LangGraph para conduzir uma triagem inicial de riscos ocupacionais pela ótica da NR-1, coletando nome, setor, 5 respostas abertas, classificando os riscos e salvando o relatório fora da resposta do chat.

## 2. Estrutura do fluxo
**Objetivo:** dividir a solução em nós claros.

**Prompt-base:**
> Organize o agente em etapas com estado compartilhado, validação de entrada, coleta de nome e setor, 5 perguntas fixas, classificação de risco, geração de relatório e alertas administrativos persistidos.

## 3. Saída estruturada
**Objetivo:** padronizar o retorno do agente.

**Prompt-base:**
> Gere um relatório estruturado com nome, setor, respostas coletadas, categorias identificadas, classificação, evidências e encaminhamento. A resposta do chat deve conter apenas confirmação de conclusão.

## 4. Validação e segurança
**Objetivo:** reduzir risco de entradas inválidas e exposição de dados sensíveis.

**Prompt-base:**
> Ajuste o agente para validar a entrada, evitar afirmações legais definitivas, armazenar as respostas em memória, persistir o relatório e os alertas no SQLite e encerrar a entrevista após 5 perguntas.

## 5. Revisão e melhoria
**Objetivo:** refinar a documentação e o comportamento do agente.

**Prompt-base:**
> Revise a documentação do projeto para garantir coerência entre problema, objetivo, fluxo, ferramenta e limitações.
