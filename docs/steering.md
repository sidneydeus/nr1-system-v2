# Steering

## Visão do Produto
Construir um agente em Python com FastAPI e LangGraph para conduzir um chat estruturado de triagem inicial de riscos ocupacionais sob a ótica da NR-1.

O agente inicia a conversa coletando nome e setor do usuário e, em seguida, conduz cinco perguntas abertas. As respostas ficam em memória durante a sessão e, ao final, o agente gera um relatório privado, classifica o risco e persiste o resultado no SQLite.

## Problema
Pequenas equipes e estudantes que precisam interpretar a NR-1 costumam ter dificuldade para transformar descrições soltas de ambiente de trabalho em uma análise organizada de perigos, riscos e ações preventivas.

## Objetivo
Reduzir o esforço manual de triagem e organização da informação, padronizando a entrevista inicial, registrando as respostas em memória de sessão e gerando um relatório útil, rastreável e verificável.

## Público-Alvo
- estudantes e equipes que estejam construindo um projeto sobre NR-1;
- profissionais ou analistas em fase inicial de levantamento de riscos;
- pessoas que precisam estruturar uma triagem de risco psicossocial a partir de um chat guiado.

## Princípios de Solução
- Entradas simples e controladas via API.
- Fluxo explícito com nós bem definidos no LangGraph.
- Coleta conversacional padronizada com limite de 5 perguntas por sessão.
- Uso de contexto/state para manter respostas, nome, setor e progresso da entrevista.
- Pelo menos uma ferramenta real e limitada, sem ações irrestritas.
- Saída estruturada em formato legível por humanos e fácil de reutilizar.
- Relatório não é exibido no chat; classificações Média e Alta geram alerta administrativo persistido.
- Validação básica e proteção contra entradas inválidas.

## Escopo Inicial
### Dentro do escopo
- entrevista guiada com perguntas padronizadas;
- armazenamento em memória das respostas da sessão;
- classificação de categorias e nível de risco com base nas respostas e no PDF de diretrizes;
- geração e persistência de relatório no SQLite;
- alertas administrativos persistidos para riscos Médios e Altos;
- renovação da sessão pelo frontend;
- endpoint HTTP para execução do agente.

### Fora do escopo
- substituição de laudo técnico;
- emissão de parecer jurídico;
- automação de decisões trabalhistas;
- conexão com sistemas corporativos reais;
- coleta automática de dados sensíveis.

## Direção Técnica
- `Python` como linguagem principal.
- `FastAPI` como camada de API.
- `LangGraph` para orquestração do agente conversacional.
- `Pydantic` para validação de entrada e saída.
- PDF versionado como referência das regras de classificação;
- SQLite para persistência de relatórios e alertas;
- LLM usada apenas para o texto-base do relatório; perguntas são fixas.

## Critérios de Qualidade
- fluxo compreensível e demonstrável;
- uso claro de estado, ferramenta e contexto;
- documentação completa no repositório;
- prompts principais versionados em `docs/prompts.md`;
- sem exposição de credenciais ou dados sensíveis.

## Métricas de Sucesso
- o agente conduz a entrevista com no máximo 5 perguntas por sessão;
- o relatório é persistido com classificação e evidências;
- alertas Médios e Altos ficam registrados para ação administrativa;
- o fluxo pode ser executado localmente por uma API;
- o projeto atende aos requisitos acadêmicos de LangGraph, ferramenta, memória e documentação.
