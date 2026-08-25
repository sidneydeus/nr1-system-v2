# NR-1 Agent

Chat conversacional com memória em sessão para triagem inicial de riscos ocupacionais, orquestrado com LangGraph.

## Como funciona
- `POST /sessions` inicia a conversa e pergunta o nome.
- `POST /chat` envia a próxima mensagem do usuário.
- `GET /sessions/{session_id}` retorna o histórico e o estado atual.
- `GET /admin/reports` lista os relatórios persistidos.
- `GET /admin/reports/{session_id}` retorna um relatório específico.
- `GET /admin/logs` lista os logs administrativos persistidos.
- `GET /config` mostra se a LLM está habilitada e qual modelo está configurado.
- `GET /` abre a interface web do chat.
- O fluxo interno usa LangGraph para direcionar as etapas da sessão.
- No encerramento, o agente classifica os riscos conforme `docs/pdf/Diretrizes_NR1_Classificacao_Riscos.pdf` e salva o relatório no SQLite.
- Classificações `Médio / Alerta` e `Alto / Crítico` geram um alerta administrativo persistido na tabela `logs`.

## Fluxo
1. O assistente pede o nome.
2. Depois pede o setor.
3. Em seguida faz 5 perguntas fixas e abertas sobre o trabalho.
4. As respostas ficam armazenadas em memória na sessão.
5. Ao final, o risco é classificado conforme as diretrizes da NR-1.
6. O relatório é salvo na tabela `reports` e não é enviado ao usuário do chat.
7. O botão `Finalizar` limpa a conversa e inicia uma nova sessão.

O fluxo completo está documentado em [`docs/fluxo-aplicacao.mmd`](docs/fluxo-aplicacao.mmd).

Os dados persistentes ficam no arquivo `data/nr1.db`, compartilhado com o serviço SQLite do Docker.

## Exemplo de entrada e saída

O usuário responde às mensagens guiadas do agente. Um fluxo de entrada simplificado é:

```text
Assistente: Olá. Para começarmos, qual é o seu nome?
Usuário: Ana Souza

Assistente: Obrigado. Em qual setor você trabalha?
Usuário: Operações

Assistente: Conte como é o trabalho que você realiza e em que local ele acontece.
Usuário: Trabalho com manutenção de máquinas na área de produção.
Assistente: Como é o local onde você trabalha e o que você utiliza para realizar suas atividades?
Usuário: Há ruído e uso ferramentas manuais.
Assistente: Conte como é um dia típico de trabalho, do início ao fim da jornada.
Usuário: Faço inspeções e reparos durante toda a jornada.
Assistente: O que costuma acontecer quando algo sai do esperado durante o trabalho?
Usuário: Às vezes ocorre uma parada inesperada da máquina.
Assistente: Que orientações, treinamentos ou formas de proteção existem para essa atividade? Como você avalia o funcionamento delas?
Usuário: Recebemos treinamento e utilizamos EPI.
```

Depois das cinco respostas, o chat retorna apenas uma confirmação. O relatório fica disponível para consulta administrativa:

```text
Sessão concluída. O relatório foi salvo com sucesso.

Exemplo de relatório gerado:
Resumo da sessão: manutenção de máquinas na área de produção.

Classificação de risco: Médio / Alerta
Categorias identificadas: Físicos
Evidências consideradas: Há ruído e uso ferramentas manuais. | Às vezes ocorre uma parada inesperada da máquina.
Encaminhamento: Programar vistoria e revisar as medidas de prevenção.
```

## Decisões técnicas, ferramenta e limitações

- `LangGraph` organiza o fluxo em estado compartilhado, nós e conexões para controlar as etapas da entrevista.
- `SQLite` é a ferramenta integrada usada para persistir relatórios e alertas administrativos e disponibilizá-los pelas rotas `/admin`.
- O PDF [`Diretrizes_NR1_Classificacao_Riscos.pdf`](docs/pdf/Diretrizes_NR1_Classificacao_Riscos.pdf) é a referência utilizada para definir as categorias, classificações e encaminhamentos da triagem. A implementação aplica essas regras por meio do classificador local; o PDF não é enviado ao usuário nem à LLM durante cada conversa.
- As perguntas são pré-definidas para tornar o processo guiado, previsível e comparável entre sessões. Por isso, a solução não substitui uma entrevista técnica completa.
- A análise é inicial, depende da qualidade das respostas e pode exigir validação humana especializada.

## Execução local
```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

Depois de subir a aplicação, abra `http://127.0.0.1:8000/` para usar a interface web.

## Testes
```bash
pytest -q
```

## Variáveis de ambiente
- `GROQ_API_KEY`
- `GROQ_MODEL`
