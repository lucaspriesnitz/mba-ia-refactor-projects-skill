# Relatório de Auditoria Arquitetural — task-manager-api (revisão 2)

- **Data:** 2026-09-28
- **Stack:** Python 3.12 / Flask 3.1.1 + Flask-SQLAlchemy 3.1.1 + SQLAlchemy 2.1.1
- **Arquitetura de partida:** N2 — em camadas com defeitos pontuais (MVC já implantado pela refatoração anterior; ver `reports/audit-project-3.md`)
- **Arquivos analisados:** 48 fontes `.py` (43 em `src/`, + `app.py`, `wsgi.py`, `seed.py`, 2 de `migrations/`) + `requirements.txt`, `.env.example`, `.gitignore`, `README.md`
- **Escopo:** árvore de trabalho atual, **incluindo o patch de autenticação não commitado** (decorators `requer_autenticacao` / `requer_admin` em `src/middlewares/auth.py`, aplicado a `DELETE /tasks`, `DELETE /users` e `GET /reports/*`)

> Esta é a **segunda** auditoria do projeto. A primeira (`audit-project-3.md`, 23 achados) descreve o estado pré-refatoração e foi preservada. Os 23 achados originais foram conferidos: **22 estão fechados**; o AP-06 permanece **parcialmente** aberto e reaparece abaixo.

## Resumo por severidade

| Severidade | Qtd |
|---|---|
| CRITICAL | 1 |
| HIGH | 4 |
| MEDIUM | 4 |
| LOW | 4 |
| **Total** | **13** |

APIs deprecated detectadas em código executável: **nenhuma** (1 item de atenção para migração futura — ver seção própria).

---

## Achados

### 🔴 CRITICAL

#### [AP-06] `DELETE /categories/<id>` continua sem autenticação — `src/controllers/category_controller.py:36`
- **O que:** o patch de auth cobriu `DELETE /tasks/<id>` (`task_controller.py:52-53`) e `DELETE /users/<id>` (`user_controller.py:61-62`), mas a terceira rota destrutiva ficou de fora: `@category_bp.delete("/categories/<int:cat_id>")` (`category_controller.py:36-39`) não tem decorator, não recebe `actor`, e `CategoryService.delete_category` (`category_service.py:43-49`) não faz nenhuma checagem de identidade ou papel.
- **Impacto:** qualquer chamador anônimo apaga qualquer categoria com um `curl -X DELETE`. Por causa do `ON DELETE SET NULL` (`models/task.py:22`) mais o `PRAGMA foreign_keys=ON` (`database/__init__.py:31`), o efeito colateral é em cascata: **todas as tasks daquela categoria perdem a classificação** (`category_id = NULL`) de forma irreversível — os dados não voltam sem backup. O mesmo se aplica a `POST/PUT /categories`, tratados no achado H3.
- **Recomendação:** aplicar o mesmo padrão das outras duas rotas destrutivas. Decidir o papel exigido (categoria é dado global, não pertence a um usuário → `requer_admin` é o corte natural) e mover a decisão de autorização para o service, como em `UserService.delete_user`, para que a guarda não dependa do decorator.

### 🟠 HIGH

#### [AP-06 / correctness] `requer_admin` chama um método que não existe — `src/middlewares/auth.py:51`
- **O que:** o decorator faz `current_app.extensions["container"].users.get(actor.user_id)`. Mas `container.users` é uma instância de `UserService` (`src/container.py:22`), e `UserService` (`src/services/user_service.py:27-133`) **não define `get`** — define `get_user` (`:36`). Quem tem `.get()` é `UserRepository`, via `BaseRepository.get` (`repositories/base.py:29`), que não está exposto no container.
- **Impacto:** todo request autenticado a `GET /reports/summary` e `GET /reports/user/<id>` (`report_controller.py:15-24`) estoura `AttributeError` antes de chegar ao handler. O error handler genérico (`middlewares/error_handler.py:32-35`) captura e responde **500 `{"error": "Erro interno"}`**. Os dois endpoints de relatório estão **100% inacessíveis** — inclusive para um admin legítimo. Falha fechada (não é vazamento), mas é uma quebra total de contrato que o patch introduziu.
- **Recomendação:** usar `users.get_user(actor.user_id)` (que já levanta `NotFound`) ou, melhor, delegar a `UserService.resolve_actor` + `_require_admin`, que já implementam exatamente essa regra (ver M1). Cobrir com teste antes de commitar.

#### [AP-06] Guarda de autorização *fail-open* em `TaskService.delete_task` — `src/services/task_service.py:57`
- **O que:** a checagem inteira está dentro de `if actor is not None:` (`:57-64`). Chamar `delete_task(task_id)` sem `actor` — a assinatura permite, o default é `None` (`:51`) — apaga a task **sem nenhuma verificação**. A única coisa que hoje impede isso é o decorator no controller (`task_controller.py:53`). Contraste direto com `UserService.delete_user` (`user_service.py:99`), que chama `resolve_actor(actor)` e **levanta `Unauthenticated` quando `actor is None`** — fail-closed. Duas rotas irmãs, dois comportamentos opostos.
- **Impacto:** a regra de autorização vive na camada errada e é opcional. Qualquer outro caminho de chamada — um comando de CLI, um job, um novo controller, um teste que passe a valer como documentação — apaga tasks de qualquer usuário sem passar pela guarda. Remover ou esquecer o decorator não quebra nada visivelmente: simplesmente desliga a segurança em silêncio.
- **Recomendação:** inverter a lógica para fail-closed, como em `UserService`: resolver o actor sempre e levantar `Unauthenticated` se for `None`. O service é a fronteira de autorização; o decorator é conveniência de HTTP, não a garantia.

#### [AP-06] Escritas não-destrutivas seguem abertas a anônimos — `src/controllers/task_controller.py:39,45`, `src/controllers/category_controller.py:23,29`
- **O que:** `POST /tasks` (`task_controller.py:39`), `PUT /tasks/<id>` (`:45`), `POST /categories` (`category_controller.py:23`) e `PUT /categories/<id>` (`:29`) não exigem credencial nenhuma. `TaskService.create_task`/`update_task` (`task_service.py:33,42`) nem recebem `actor`.
- **Impacto:** um anônimo cria e edita tasks à vontade — e, como `user_id` é campo de entrada aceito pelo schema (`schemas/task.py:77`) e só é validado quanto à existência (`task_service.py:81`), ele **atribui ou reatribui qualquer task a qualquer usuário**. Também pode reescrever título, descrição e prazo de tasks alheias via `PUT`. Somado ao AP-06 já fechado no `UserService`, o resultado é incoerente: mudar o `role` de um usuário exige token de admin, mas sequestrar a carteira de tasks dele não exige nada.
- **Recomendação:** exigir autenticação nas quatro rotas e mover a decisão para os services (`create_task`/`update_task` recebendo `actor`), com a regra "dono ou admin" que `delete_task` já esboça. `user_id` no corpo só deve ser aceito de um admin.

#### [AP-06] Dados pessoais de todos os usuários expostos sem autenticação — `src/controllers/user_controller.py:32,39,68`
- **O que:** `GET /users` (`:32-36`), `GET /users/<id>` (`:39-43`) e `GET /users/<id>/tasks` (`:68-71`) não têm guarda. O `UserSchema` (`schemas/user.py:75-83`) — que corretamente removeu o hash de senha (AP-03, fechado) — ainda serializa `email`, `role` e `active` de cada usuário.
- **Impacto:** enumeração completa de contas por um anônimo: lista de e-mails, quem é admin e quais contas estão ativas. É o alvo pronto para um ataque de credencial contra `POST /login` (`user_controller.py:74`), que não tem rate limiting nem lockout. `GET /users/<id>/tasks` ainda entrega o conteúdo de trabalho de cada pessoa. O `requer_admin` foi aplicado a relatórios agregados (`report_controller.py:16,22`), que expõem *menos* dado pessoal que estas três rotas — a priorização ficou invertida.
- **Recomendação:** exigir autenticação nas três; `GET /users` restrito a admin, `GET /users/<id>` e `/tasks` liberados para o próprio usuário ou admin. A regra já existe pronta em `UserService.resolve_actor` (`user_service.py:106`).

### 🟡 MEDIUM

#### [AP-12] Três implementações concorrentes da mesma regra de autorização — `src/middlewares/auth.py:44-57`, `src/services/user_service.py:106-117`, `src/services/task_service.py:57-64`
- **O que:** "resolver o actor, conferir que existe e está ativo, conferir se é admin" está escrito três vezes, com divergências: `requer_admin` (`auth.py:47-55`) lê do container e usa `.get()` — quebrado (H1); `UserService.resolve_actor` + `_require_admin` (`user_service.py:106-117`) lê do repositório e é a versão correta; `TaskService.delete_task` (`task_service.py:58-64`) tem uma terceira cópia inline, com `if actor is not None` em vez de fail-closed (H2). Exatamente o AP-12 que a refatoração anterior fechou para status, roles e `completion_rate` (`models/domain.py:1-5`) reabriu aqui, e para a regra mais sensível do sistema.
- **Impacto:** já divergiram — uma das três está quebrada e outra é fail-open. Qualquer correção de política de acesso precisa ser feita em três lugares, e nada avisa quando um é esquecido.
- **Recomendação:** uma única fonte de verdade. `UserService.resolve_actor`/`_require_admin` é a implementação boa; os decorators devem delegar a ela (ou a um `AuthorizationService` dedicado), e `TaskService` deve consumi-la em vez de reimplementar.

#### [AP-13 adjacente] Token decodificado e usuário relido duas vezes por request — `src/middlewares/auth.py:37,50` + `src/controllers/user_controller.py:64`, `src/controllers/task_controller.py:55`
- **O que:** o decorator chama `current_actor()` (`auth.py:37`), que decodifica o JWT; o handler decorado chama `current_actor()` **de novo** (`user_controller.py:64`, `task_controller.py:55`) e decodifica o mesmo token pela segunda vez. Em seguida o service faz o `SELECT` do usuário (`user_service.py:110`, `task_service.py:58`) — e em `requer_admin` esse `SELECT` já tinha sido feito (`auth.py:51`).
- **Impacto:** duas verificações HMAC e até dois `SELECT` por request. Custo pequeno por chamada, mas o problema real é semântico: o resultado do decorator é jogado fora, então não há um ponto único onde o actor da requisição existe. É o que permite os achados H2 e M1.
- **Recomendação:** resolver o actor uma vez por request e guardá-lo no contexto (`flask.g`), com os handlers e services lendo de lá.

#### [AP-13] `GET /users/<id>` lê o mesmo usuário duas vezes — `src/controllers/user_controller.py:41-42`
- **O que:** o handler chama `_users().get_user(user_id)` (`:41`) e logo depois `_users().get_user_tasks(user_id)` (`:42`), que por sua vez chama `self.get_user(user_id)` outra vez (`user_service.py:43`) só para validar existência.
- **Impacto:** um `SELECT` redundante por request. Sem gravidade, mas é a mesma classe de desperdício (query supérflua em caminho quente) que a refatoração anterior atacou nos relatórios.
- **Recomendação:** um método de service que devolva usuário e tasks numa passagem, ou `get_user_tasks` aceitando a entidade já carregada.

#### [test-coverage] Nenhum teste automatizado no projeto — árvore inteira (sem `tests/`, sem `pytest` em `requirements.txt:1-23`)
- **O que:** não existe diretório de testes nem dependência de teste. As mudanças de contrato documentadas no `README.md:123-136` (401/403 em rotas antes abertas, 400 no lugar de 500, JWT real) e o patch de auth em cima delas não têm um único caso de regressão.
- **Impacto:** é exatamente por isso que H1 passou despercebido — um teste de `GET /reports/summary` com token de admin teria pegado o `AttributeError` na hora. Sem suíte, "preservar o comportamento observável" é uma afirmação sem evidência, e cada novo ajuste de autorização é uma aposta.
- **Recomendação:** `pytest` + `pytest-flask`, com uma suíte fina de contrato: para cada endpoint, o status e o shape da resposta; e para cada rota com guarda, os três casos — sem token (401), token sem permissão (403), token válido (200).

### 🔵 LOW

#### Imports locais dentro do corpo da função — `src/services/task_service.py:60,63`
- **O que:** `from ..errors import Unauthenticated` (`:60`) e `from ..errors import Forbidden` (`:63`) estão dentro do `delete_task`, enquanto o módulo já importa `NotFound` do mesmo pacote no topo (`:6`). Não há ciclo de import que justifique.
- **Impacto:** esconde a dependência do módulo e destoa de todos os outros services (`user_service.py:17` importa os cinco erros no topo). Custo de import a cada chamada.
- **Recomendação:** mover para o topo, junto de `NotFound`.

#### Docstrings de processo, uma delas contradizendo o próprio código — `src/middlewares/auth.py:3-10`, `src/controllers/task_controller.py:3-5`, `src/controllers/user_controller.py:6-8`, `src/controllers/report_controller.py:3-4`, `src/services/task_service.py:52-54`, `src/services/user_service.py:94-96`
- **O que:** o patch anexou em seis arquivos um bloco "EXCEÇÃO CRÍTICA (AP-06): ... a correção do CRITICAL prevalece sobre preservar o contrato original", que narra a decisão da auditoria, não o comportamento do código. Pior: em `auth.py` o texto novo (`:7-10`, "rotas destrutivas exigem autenticação obrigatória") foi colado logo abaixo do texto antigo (`:3-5`, "a autenticação é **opcional** por rota — o contrato homologado mantém as rotas abertas"), que não foi removido. O módulo agora afirma as duas coisas. Há também espaço em branco à direita em `user_service.py:93`.
- **Impacto:** quem ler `auth.py` não sabe qual das duas frases vale. Referências a IDs de achado (`AP-06`) só fazem sentido com o relatório na mão.
- **Recomendação:** um docstring por módulo, descrevendo o que o código faz hoje. A justificativa histórica pertence ao relatório e à mensagem de commit.

#### `/health` usa hora local em vez do UTC do domínio — `src/controllers/health_controller.py:3,14`
- **O que:** `str(datetime.now())` (`:14`) devolve o horário local do host, naive. Todo o resto do sistema passa por `utc_now()` (`models/domain.py:41-47`), justamente a função criada para unificar isso.
- **Impacto:** o timestamp do health check não é comparável com `created_at`, `updated_at` ou o `generated_at` dos relatórios (`report_service.py:35`). Em host fora de UTC, a diferença confunde qualquer correlação de log.
- **Recomendação:** usar `utc_now()`, já disponível.

#### `LIKE` sem escapar os curingas do input — `src/repositories/task_repository.py:22-23`
- **O que:** `pattern = f"%{text}%"` (`:22`) monta o padrão com o texto cru vindo de `?q=` (`task_controller.py:63`). Não é SQL injection — o valor vai ligado como parâmetro pelo SQLAlchemy —, mas `%` e `_` digitados pelo usuário são interpretados como curingas.
- **Impacto:** `?q=%` casa com todas as tasks; `?q=a_b` casa com `axb`. Busca com resultado errado e, em base grande, varredura completa a custo de um caractere.
- **Recomendação:** escapar `%`, `_` e o próprio escape no input, e declarar `escape="\\"` no `.like()`.

---

## APIs deprecated

Nenhuma chamada a API deprecated encontrada em código executável. As migrações da auditoria anterior se mantêm: `datetime.utcnow()` → `utc_now()` (`models/domain.py:41`), `Model.query`/`Query.get()` → `select()` e `session.get()` (`repositories/base.py:29-33`), `md5` → `scrypt` (`security/passwords.py:22-23`, com aceitação do hash legado apenas no login). As ocorrências que o grep encontra hoje estão em **comentários** descrevendo o que foi substituído (`task_repository.py:13-14`, `base.py:3-4`, `domain.py:44`).

| Item | Local | Situação |
|---|---|---|
| `marshmallow` 3.26.1 → 4.x | `requirements.txt:5`; uso em `schemas/task.py:27,41` (`fields.Field`) | Ainda não deprecated: `fields.Field` foi renomeado para `fields.Raw` na 4.x. Atenção na próxima atualização, não é achado. |

---

## Recomendação de refatoração

Ordem sugerida para a Fase 3 (fecha risco antes de organizar):

1. **H1 primeiro** — `requer_admin` está quebrando dois endpoints em produção agora. É uma linha.
2. **C1 + H3 + H4** — fechar o AP-06 restante de forma coerente: as três rotas destrutivas, as quatro rotas de escrita e as três de leitura de dado pessoal, todas pelo mesmo mecanismo.
3. **H2 + M1** — unificar a autorização numa fonte de verdade fail-closed no service, com os decorators delegando. Isso torna os passos 1 e 2 estruturalmente corretos em vez de pontuais.
4. **M2 + M3** — actor resolvido uma vez por request (`flask.g`); eliminar as leituras redundantes.
5. **M4** — suíte de contrato cobrindo status e shape de cada endpoint, e os três casos de cada rota com guarda. É o que evita a próxima ocorrência de H1.
6. **LOW** — imports no topo, docstrings coerentes, `utc_now()` no health, escape do `LIKE`.

Nota de contrato: os passos 1–2 alteram deliberadamente o contrato de 8 rotas hoje abertas, conforme a exceção prevista no AP-06 (`references/anti-patterns.md:73-75`). O `README.md:138-148` já as listava como "próximos passos fora do escopo homologado" — fechá-las agora torna o patch em andamento coerente em vez de parcial.

> **Fase 2 completa. Prosseguir com a refatoração (Fase 3)? [y/n]**
