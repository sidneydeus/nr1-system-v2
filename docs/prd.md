# PRD

## Nome do Projeto
Chat Agente NR-1 para Triagem Inicial de Riscos Ocupacionais

## Resumo
Aplicação em Python com FastAPI e LangGraph que conduz uma conversa estruturada com o usuário, coleta nome e setor, faz 5 perguntas abertas por sessão, classifica os riscos conforme `docs/pdf/Diretrizes_NR1_Classificacao_Riscos.pdf` e salva o relatório no SQLite.

## Problema do Usuário
Quando uma triagem é feita de forma livre, as respostas tendem a ficar incompletas ou fora de ordem. Isso dificulta transformar o conteúdo em uma estrutura compatível com um levantamento inicial de riscos ocupacionais.

## Objetivo do Produto
Padronizar a entrevista inicial e gerar uma saída estruturada que ajude o usuário a:
- informar nome e setor;
- responder perguntas padronizadas sobre o trabalho;
- acompanhar o histórico da sessão;
- concluir a conversa sem receber o relatório no chat;
- iniciar uma nova sessão pelo botão `Finalizar`.

## Personas
### Estudante
Precisa entregar um projeto funcional e bem documentado sobre NR-1.

### Analista Iniciante
Quer uma base inicial para organizar a leitura de um cenário de trabalho.

### Instrutor/avaliador
Precisa entender claramente o fluxo, a ferramenta e a justificativa das decisões técnicas.

### Usuário Final
Responde ao chat guiado para receber uma triagem inicial do seu contexto de trabalho.

## Casos de Uso
1. O usuário informa nome e setor no início da conversa.
2. O agente faz 5 perguntas abertas sobre atividade, local, rotina, situações fora do esperado e proteções.
3. O agente armazena as respostas em memória da sessão.
4. O agente identifica categorias de risco e classifica o nível como Baixo, Médio ou Alto.
5. O agente gera o relatório e o salva na tabela `reports` do SQLite.
6. Para níveis Médio ou Alto, registra um alerta na tabela `logs`.
7. O agente retorna apenas uma confirmação de conclusão ao chat.

## Entradas
### Obrigatórias
- nome do usuário;
- setor;
- respostas às perguntas padronizadas do chat.

### Opcionais
- observações adicionais do usuário;
- arquivos de apoio com descrição do ambiente;
- contexto complementar para enriquecer o relatório.

## Saídas
### Estrutura mínima
- identificação do usuário e setor;
- relatório gerado com as evidências consideradas;
- categorias de risco identificadas;
- classificação e encaminhamento recomendado;
- registro de alerta administrativo quando aplicável.

## Requisitos Funcionais
- validar a entrada antes do processamento;
- executar um fluxo orientado por LangGraph;
- manter estado compartilhado durante a sessão;
- usar ao menos uma ferramenta real;
- limitar a entrevista a no máximo 5 perguntas por sessão;
- produzir relatório estruturado persistido no SQLite;
- não enviar o relatório ao usuário do chat;
- registrar prompts principais em arquivo `.md`;
- expor a funcionalidade por API HTTP.

## Requisitos Não Funcionais
- arquitetura simples de manter;
- respostas previsíveis e verificáveis;
- baixo acoplamento entre análise e ferramenta;
- proteção contra dados sensíveis em logs e repositório;
- execução local fácil de reproduzir.

## Fluxo do Agente
1. Receber solicitação via FastAPI.
2. Validar e normalizar a entrada.
3. Criar ou recuperar a sessão em memória.
4. Coletar nome e setor.
5. Executar perguntas padronizadas, respeitando o limite de 5 por sessão.
6. Armazenar as respostas no estado da sessão.
7. Classificar categorias e nível de risco.
8. Gerar o relatório com a LLM.
9. Persistir o relatório em `reports`.
10. Persistir o alerta em `logs` quando a classificação for Média ou Alta.

## Regras de Negócio
- o agente não deve afirmar conformidade legal definitiva;
- o agente deve sinalizar quando faltar contexto para conclusão;
- o agente deve encerrar a etapa de perguntas após 5 respostas por sessão.

## Critérios de Aceite
- o endpoint responde com estrutura consistente;
- o fluxo usa LangGraph com nós identificáveis;
- a ferramenta é acionada de forma explícita;
- o estado preserva contexto e respostas da sessão;
- o resultado final persiste relatório e classificação;
- classificações Média e Alta geram alerta em `logs`;
- a documentação explica execução, decisão técnica e limitações.

## Limitações
- não substitui avaliação técnica formal;
- depende da qualidade das respostas do usuário;
- a análise é inicial e pode exigir validação humana.

## Fora de Escopo
- integração com sistemas externos da empresa;
- armazenamento permanente de dados sensíveis;
- ingestão automática de múltiplos formatos complexos sem validação;
- geração de documentos legais ou regulatórios finais.
