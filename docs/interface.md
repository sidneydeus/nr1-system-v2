# Implementação da Interface Conversacional - NR-1 Agent

## Objetivo

Desenvolver uma interface web de chat para consumir a API já existente do projeto **NR-1 Agent**.

**Importante:**
- Não alterar nenhuma regra de negócio do backend.
- Não implementar lógica de classificação ou relatório no frontend.
- Todo o fluxo conversacional é controlado pela API.
- O frontend deve enviar mensagens, exibir confirmações e manter o `session_id`.

---

# Tecnologias

Utilizar:

- HTML5
- Bootstrap 5
- JavaScript ES6
- Fetch API

Não utilizar frameworks como React, Vue ou Angular.

A interface deve ser simples, moderna e responsiva.

---

# Objetivo da interface

A experiência deve lembrar um ChatGPT, porém extremamente simples.

Layout:

```
+---------------------------------------------------+
|              Avaliação NR-1                       |
+---------------------------------------------------+

                mensagens

 Usuário
 ------------------------

 Assistente
 ------------------------

 ....................................

+--------------------------------------+------+
| Digite sua mensagem...               | Enviar|
+--------------------------------------+------+
```

---

# Comunicação com a API

## Iniciar conversa

Quando a página abrir:

```
POST /sessions
```

Não envia corpo.

Resposta esperada:

```json
{
    "session_id": "...",
    "status": "awaiting_name",
    "assistant_message": "Olá. Para começarmos, qual é o seu nome?"
}
```

Salvar o `session_id`.

Exibir a primeira mensagem imediatamente.

---

## Enviar mensagem

Sempre que o usuário enviar uma mensagem:

```
POST /chat
```

Body:

```json
{
    "session_id": "...",
    "message": "texto digitado"
}
```

A resposta deverá ser exibida na conversa.

---

## Recuperar sessão

Caso seja necessário reconstruir a conversa:

```
GET /sessions/{session_id}
```

Usar apenas quando existir um session_id salvo.

---

## Endpoints administrativos

As consultas administrativas não são utilizadas pelo frontend conversacional, mas ficam disponíveis na API para consulta dos dados persistidos:

```
GET /admin/reports
GET /admin/reports/{session_id}
GET /admin/logs
```

`GET /admin/reports` retorna uma lista de relatórios com `session_id`, `user_name`, `sector`, `report`, `classification` e `created_at`.

`GET /admin/reports/{session_id}` retorna um relatório específico e responde `404` quando ele não existe.

`GET /admin/logs` retorna os logs administrativos com `id`, `session_id`, `level`, `event`, `message` e `created_at`.

---

# Persistência

Salvar o `session_id` em:

```
localStorage
```

Ao abrir novamente a página:

- verificar se existe um session_id;
- caso exista, recuperar a sessão;
- caso contrário iniciar uma nova.

---

# Interface

## Cabeçalho

Título:

```
Avaliação Inicial NR-1
```

Subtítulo:

```
Assistente para triagem de riscos ocupacionais
```

---

## Área do chat

As mensagens devem aparecer em ordem cronológica.

Mensagem do assistente:

- alinhada à esquerda
- fundo cinza claro

Mensagem do usuário:

- alinhada à direita
- fundo azul
- texto branco

Cada mensagem deve possuir:

- conteúdo
- horário

---

## Campo de entrada

Na parte inferior:

- textarea com crescimento automático
- botão Enviar
- botão Finalizar, exibido quando a sessão estiver concluída

Pressionar ENTER envia.

SHIFT+ENTER cria nova linha.

---

# Estados da interface

Enquanto aguarda resposta da API:

- desabilitar textarea
- desabilitar botão
- mostrar indicador:

```
Assistente está digitando...
```

Assim que chegar a resposta:

- remover indicador
- habilitar novamente.

Quando a API retornar `status: "complete"`:

- exibir a confirmação de conclusão;
- desabilitar o campo e o botão Enviar;
- exibir o botão Finalizar.

Ao clicar em Finalizar, limpar a conversa, remover o `session_id` do `localStorage` e iniciar uma nova sessão.

---

# Scroll

Sempre manter o scroll no final da conversa.

---

# Tratamento de erros

Caso a API esteja indisponível:

Mostrar um alerta Bootstrap:

```
Não foi possível comunicar com o servidor.
Tente novamente.
```

---

# Organização do código

Estrutura sugerida:

```
frontend/

    index.html

    css/
        style.css

    js/

        api.js
        chat.js
        ui.js
        storage.js

```

Responsabilidades:

## api.js

Toda comunicação HTTP.

Funções:

```
startSession()

sendMessage()

getSession()
```

---

## storage.js

Persistência.

Funções:

```
saveSession()

loadSession()

clearSession()
```

---

## ui.js

Manipulação da interface.

Funções:

```
appendAssistantMessage()

appendUserMessage()

showTyping()

hideTyping()

scrollBottom()

setLoading()
```

---

## chat.js

Orquestração.

Responsável por:

- iniciar conversa
- recuperar sessão
- enviar mensagens
- atualizar interface

---

# Estilo visual

Utilizar Bootstrap 5.

Container centralizado.

Largura máxima:

```
800px
```

Altura:

```
90vh
```

Área de mensagens com scroll.

Bordas arredondadas.

Sombras suaves.

Visual limpo semelhante a aplicações modernas de chat.

---

# Recursos adicionais

Implementar:

- animação suave na chegada das mensagens
- indicador de carregamento
- auto focus no campo de texto
- textarea com auto resize
- suporte a dispositivos móveis

---

# Não implementar

Não criar:

- autenticação
- persistência de relatórios ou alertas (responsabilidade do backend)
- websocket
- streaming
- lógica de perguntas
- IA no frontend
- histórico próprio

Toda inteligência pertence ao backend.

---

# Código

Produzir código limpo seguindo boas práticas:

- módulos ES6
- funções pequenas
- comentários apenas quando necessários
- sem código duplicado
- fácil manutenção
