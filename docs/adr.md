# ADR

## ADR 001 - Usar FastAPI como camada de exposição do agente

### Contexto
O projeto precisa ser executável de forma simples, com entrada padronizada e fácil demonstração.

### Decisão
Usar `FastAPI` para expor endpoints HTTP, com suporte ao fluxo de chat e a endpoints de consulta de sessões, relatórios e logs administrativos.

### Consequências
- integração simples com frontend, testes e ferramentas de avaliação;
- documentação automática com OpenAPI;
- validação de request/response com tipos explícitos.

---

## ADR 002 - Usar LangGraph para orquestrar o fluxo do agente

### Contexto
Os requisitos pedem um agente com estado, nós, conexões e uso controlado de ferramentas.

### Decisão
Implementar o fluxo com `LangGraph`, usando um `StateGraph` com etapas separadas para:
- abertura da sessão e coleta de nome/setor;
- registro da mensagem do usuário no estado;
- roteamento por status da sessão;
- pergunta padronizada e controle de limite;
- classificação de risco, geração do relatório, alerta administrativo e persistência no SQLite.

### Consequências
- fluxo mais rastreável do que uma cadeia linear de chamadas;
- facilidade para inspecionar o estado durante a execução;
- melhor aderência aos critérios acadêmicos do projeto;
- o fluxo pode evoluir sem quebrar o contrato HTTP atual.

---

## ADR 003 - Representar contexto com estado tipado

### Contexto
O agente precisa manter informações úteis entre etapas, sem depender de variáveis soltas.

### Decisão
Usar um estado compartilhado tipado com `Pydantic` ou `TypedDict`, armazenando:
- entrada normalizada;
- identificação do usuário;
- setor;
- perguntas realizadas;
- respostas armazenadas em memória;
- mensagem atual;
- resposta do assistente;
- status anterior;
- classificação, relatório e alerta administrativo produzidos ao final da sessão.

### Consequências
- menor risco de inconsistência entre nós;
- fácil serialização para debug e testes;
- estrutura clara para evolução do projeto.

---

## ADR 004 - Usar o PDF como referência da classificação

### Contexto
As regras de classificação precisam ser rastreáveis e alinhadas ao material de referência do projeto.

### Decisão
Usar `docs/pdf/Diretrizes_NR1_Classificacao_Riscos.pdf` como referência para as categorias de risco, os níveis de classificação e os encaminhamentos.

### Consequências
- classificação determinística e verificável;
- regras de negócio documentadas e rastreáveis;
- o agente continua útil mesmo quando a LLM externa não está disponível.

---

## ADR 005 - Persistir relatório fora da resposta do chat

### Contexto
A entrega precisa ser verificável, mas o relatório não deve ser exibido diretamente ao usuário do chat.

### Decisão
Gerar o relatório, persistir seu texto e classificação na tabela `reports` do SQLite e retornar somente uma confirmação ao chat.

### Consequências
- mantém o relatório disponível para uso administrativo;
- separa a resposta conversacional do resultado interno da triagem;
- facilita auditoria e testes automatizados.

---

## ADR 006 - Usar memória em sessão e SQLite para resultados

### Contexto
O foco do mini-projeto é demonstrar o agente funcionando de forma clara, não construir uma plataforma completa.

### Decisão
Manter a conversa em memória durante a sessão ativa, mas persistir relatórios em `reports` e alertas administrativos em `logs` no SQLite.

### Consequências
- evita persistir todo o histórico conversacional;
- mantém relatório e auditoria disponíveis após o encerramento;
- usa o SQLite disponibilizado pelo Docker.

---

## ADR 007 - Separar validação, análise e resposta final

### Contexto
Misturar essas etapas em um único bloco dificulta manutenção e compreensão.

### Decisão
Criar etapas separadas para validação, coleta de respostas, roteamento por estado e síntese.

### Consequências
- maior clareza do fluxo;
- melhor rastreabilidade de falhas;
- possibilidade de melhorar cada nó de forma independente.

---

## ADR 008 - Limitar o chat a 5 perguntas por sessão

### Contexto
O produto precisa manter a entrevista curta, previsível e adequada ao escopo acadêmico.

### Decisão
Restringir a sessão a no máximo 5 perguntas padronizadas, após a coleta inicial de nome e setor.

### Consequências
- fluxo mais objetivo;
- menor fricção para o usuário;
- facilita o encerramento com classificação, relatório persistido e alertas administrativos quando necessários.
