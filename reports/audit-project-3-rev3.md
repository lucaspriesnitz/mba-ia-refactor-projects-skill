# Relatório de Auditoria Arquitetural — task-manager-api (revisão 3)

- **Data:** 2026-09-28
- **Stack:** Python 3.12 / Flask 3.1.1 + Flask-SQLAlchemy 3.1.1 + SQLAlchemy 2.1.1
- **Arquitetura de partida:** N2 — em camadas, com defeitos pontuais
- **Arquivos analisados:** 48 fontes `.py` (43 em `src/`, + `app.py`, `wsgi.py`, `seed.py`, 2 de `migrations/`) + `requirements.txt`, `.env.example`, `.gitignore`, `README.md`
- **Escopo:** árvore de trabalho atual, **não commitada**, já com o segundo patch de autorização aplicado (`requer_admin` em `/categories` e `/reports`, `requer_autenticacao` em `/tasks` de escrita e nas leituras de `/users`)

> Terceira auditoria do projeto. A primeira (`audit-project-3.md`, 23 achados) descreve o estado pré-refatoração; a segunda (`audit-project-3-rev2.md`, 13 achados) auditou o primeiro patch de auth. Dos 13 achados da rev2, **6 estão fechados** (C1 `DELETE /categories`, H1 `requer_admin` chamando `.get()` inexistente, H2 fail-open em `TaskService.delete_task`, H4 leituras de `/users` abertas, e a metade de H3 referente a `/categories`), **7 seguem abertos** e reaparecem abaixo com a numeração nova.

## Resumo por severidade

| Severidade | Qtd |
|---|---|
| CRITICAL | 1 |
| HIGH | 3 |
| MEDIUM | 7 |
| LOW | 5 |
| **Total** | **16** |

APIs deprecated detectadas em código executável: **nenhuma** (1 item de atenção para migração futura — ver seção própria).

---

## Achados

### 🔴 CRITICAL

#### [AP-06] `PUT /users/<id>` continua sem autenticação — `src/controllers/user_controller.py:56`

- **O que:** o segundo patch decorou `GET /users` (`:34`), `GET /users/<id>` (`:42`), `DELETE /users/<id>` (`:65`) e `GET /users/<id>/tasks` (`:72`) com `@requer_autenticacao`, mas o `PUT` (`:56-61`) ficou de fora. `UserService.update_user` (`src/services/user_service.py:65-88`) só exige credencial para três casos: `role`/`active` (`:66-67`, via `_require_admin`) e `password` (`:68-70`, via `_authorize_password_change`). Um corpo como `{"name": "...", "email": "..."}` não passa por nenhuma checagem — `actor` chega `None` (`user_controller.py:60`) e o método segue direto para `:72-77`.
- **Impacto:** qualquer anônimo reescreve o `name` e o `email` de qualquer conta, inclusive a de um admin, com um `curl -X PUT /users/1`. Como o login é feito **por e-mail** (`src/services/auth_service.py:19`, `UserRepository.get_by_email`), trocar o e-mail da vítima a tranca para fora da própria conta imediatamente e aponta a identidade para um endereço do atacante — a senha continua protegida, mas o dono perde o acesso e o atacante passa a controlar o canal de recuperação de qualquer fluxo futuro de reset. A unicidade de e-mail (`:73-75`) ainda deixa o atacante "queimar" um endereço de propósito. É a mesma classe de escalada que a rev1 fechou para `role`/`password`, deixada aberta no campo que define quem é o usuário.
- **Recomendação:** `@requer_autenticacao` na rota e, no service, resolver o actor sempre (`resolve_actor`, `user_service.py:106`) com a regra "próprio usuário ou admin" — a mesma já aplicada em `delete_user` (`:99-101`). A guarda tem de ficar no service; o decorator é conveniência.

### 🟠 HIGH

#### [AP-06] Escrita de tasks autenticada, mas sem dono: qualquer usuário edita e reatribui a task de qualquer outro — `src/controllers/task_controller.py:38,45`, `src/services/task_service.py:33,42`

- **O que:** `POST /tasks` (`:38-42`) e `PUT /tasks/<id>` (`:45-50`) agora exigem token, mas param aí: `create_task(self, data)` (`task_service.py:33`) e `update_task(self, task, changes)` (`:42`) **nem recebem `actor`**, e nenhuma das duas consulta o dono da task. `user_id` é campo de entrada aceito pelo schema (`src/schemas/task.py:77`) e a única validação é de existência (`task_service.py:83`).
- **Impacto:** qualquer conta válida — inclusive a mais nova, criada pelo `POST /users` aberto (`user_controller.py:49`) — reescreve título, descrição, status, prazo e tags das tasks de todo mundo, e reatribui qualquer task para qualquer `user_id`. Fica incoerente com a rota irmã: `delete_task` (`task_service.py:64`) já checa "admin ou dono", `update_task` não checa nada. Na prática, deletar exige permissão e esvaziar/sequestrar não exige.
- **Recomendação:** `create_task`/`update_task` recebendo `actor` e aplicando a mesma regra de `delete_task` (admin ou dono); `user_id` no corpo só aceito de admin — para os demais, o dono é o próprio actor.

#### [AP-06] Todo o conteúdo de tasks segue legível por anônimos — `src/controllers/task_controller.py:27,33,60,72`

- **O que:** `GET /tasks` (`:27-30`), `GET /tasks/<id>` (`:33-35`), `GET /tasks/search` (`:60-69`) e `GET /tasks/stats` (`:72-74`) não têm guarda nenhuma. O `TaskListItemSchema` (`src/schemas/task.py:103-105`) ainda anexa `user_name` a cada item. `GET /categories` (`category_controller.py:21`) está na mesma situação, com dado bem menos sensível.
- **Impacto:** um anônimo lê título, descrição, tags, prazo e responsável de todas as tasks do sistema, e o `?q=` (`:64`) transforma isso em busca livre sobre o conteúdo. Depois do patch, `GET /users/<id>/tasks` exige token (`user_controller.py:72`) mas `GET /tasks/search?user_id=<id>` (`:67`) devolve exatamente a mesma carteira sem token — a rota fechada tem um bypass direto ao lado. A priorização ficou invertida pela segunda vez: relatórios agregados exigem admin (`report_controller.py:16,22`), o dado bruto que os alimenta é público.
- **Recomendação:** exigir autenticação nas quatro rotas de leitura de task e decidir o escopo no service (todas, para admin; as próprias, para os demais) — senão `search` continua sendo a porta lateral de qualquer regra aplicada às outras.

#### [AP-06] Autorização de categorias mora só no decorator; o service não checa nada — `src/services/category_service.py:26,37,43`

- **O que:** `create_category` (`:26`), `update_category` (`:37`) e `delete_category` (`:43`) não recebem `actor` nem consultam papel. A única guarda é o `@requer_admin` nos três handlers (`category_controller.py:29,36,44`). É exatamente o defeito fail-open que a rev2 apontou em `TaskService.delete_task` e que **foi corrigido lá** (`task_service.py:57-66` hoje levanta `Unauthenticated` quando `actor is None`) — a mesma lição não foi aplicada aqui.
- **Impacto:** a segurança de uma operação destrutiva depende de uma linha de decorator. Qualquer outro caminho de chamada (CLI, job, um controller novo, um teste que vire documentação) apaga categorias sem verificação; e apagar categoria não é inócuo — o `ON DELETE SET NULL` (`src/models/task.py:22`) com `PRAGMA foreign_keys=ON` (`src/database/__init__.py:31`) zera o `category_id` de todas as tasks daquela categoria, sem volta. Remover o decorator por engano desliga a proteção em silêncio, sem quebrar nada visível.
- **Recomendação:** mover a decisão para o service (actor obrigatório + `_require_admin`), mantendo o decorator apenas como resposta rápida de HTTP.

### 🟡 MEDIUM

#### [AP-12] Três implementações concorrentes da mesma regra de autorização — `src/middlewares/auth.py:44-57`, `src/services/user_service.py:106-117`, `src/services/task_service.py:56-66`

- **O que:** "resolver o actor, conferir que existe e está ativo, conferir se é admin" segue escrito três vezes: `requer_admin` (`auth.py:47-56`), `UserService.resolve_actor`/`_require_admin` (`user_service.py:106-117`) e a cópia inline de `TaskService.delete_task` (`task_service.py:57-66`). Achado M1 da rev2, ainda aberto — o patch consertou os *sintomas* (o `.get()` inexistente e o fail-open) sem remover a duplicação que os produziu.
- **Impacto:** as três já divergiram uma vez. Cada mudança de política de acesso precisa ser feita em três lugares e nada avisa quando um fica para trás — foi assim que a rev2 nasceu com dois achados de autorização quebrada.
- **Recomendação:** uma fonte de verdade. `resolve_actor`/`_require_admin` é a implementação boa; os decorators e `TaskService` devem delegar a ela (ou a um `AuthorizationService` dedicado).

#### [AP-13 adjacente] Token decodificado e usuário relido duas vezes por request — `src/middlewares/auth.py:37,48` + `src/controllers/task_controller.py:56`, `src/controllers/user_controller.py:67`

- **O que:** o decorator chama `current_actor()` (`auth.py:37` e `:48`), que decodifica o JWT; o handler decorado chama `current_actor()` de novo (`task_controller.py:56`, `user_controller.py:67`) e decodifica o mesmo token pela segunda vez. Em `requer_admin`, o `SELECT` do usuário (`auth.py:51`) é refeito depois pelo service (`user_service.py:110`). M2 da rev2, ainda aberto.
- **Impacto:** duas verificações HMAC e até dois `SELECT` por request. O custo é pequeno; o problema é semântico — o resultado do decorator é descartado, então não existe um ponto único onde o actor da requisição vive. É essa lacuna que permite achados como o CRITICAL acima (a rota sem decorator não tem como o service perceber).
- **Recomendação:** resolver o actor uma vez por request, guardar em `flask.g`, e ter handlers e services lendo de lá.

#### [AP-13] `GET /users/<id>` lê o mesmo usuário duas vezes — `src/controllers/user_controller.py:44-45`

- **O que:** o handler chama `_users().get_user(user_id)` (`:44`) e em seguida `_users().get_user_tasks(user_id)` (`:45`), que refaz `self.get_user(user_id)` (`user_service.py:43`) só para validar existência. M3 da rev2, ainda aberto.
- **Impacto:** um `SELECT` redundante por request em caminho quente. Sem gravidade, mas é a mesma classe de desperdício que a rev1 atacou nos relatórios.
- **Recomendação:** um método de service que devolva usuário e tasks numa passagem, ou `get_user_tasks` aceitando a entidade já carregada.

#### [test-coverage] Nenhum teste automatizado — árvore inteira (sem `tests/`, sem `pytest` em `requirements.txt:1-23`)

- **O que:** não existe diretório de testes nem dependência de teste. Dois patches de autorização consecutivos foram aplicados sem um único caso de regressão. M4 da rev2, ainda aberto.
- **Impacto:** é a causa raiz direta dos achados da rev2 — um teste de `GET /reports/summary` com token de admin teria pegado o `AttributeError` na hora, em vez de deixar dois endpoints em 500. Sem suíte, "preservar o comportamento observável" é afirmação sem evidência, e cada ajuste de autorização é aposta.
- **Recomendação:** `pytest` + client de teste do Flask, com suíte fina de contrato: status e shape por endpoint, e três casos por rota com guarda (sem token → 401, token sem permissão → 403, token válido → 200).

#### [AP-06] `POST /login` sem rate limiting nem lockout — `src/controllers/user_controller.py:78`, `src/services/auth_service.py:16`

- **O que:** `login()` compara a senha (`auth_service.py:23`) e devolve 401 sem contabilizar tentativas, sem atraso e sem bloqueio por conta ou por IP. Não há dependência de rate limit em `requirements.txt:1-23`.
- **Impacto:** força bruta livre contra qualquer e-mail conhecido. A política de senha (`PASSWORD_MIN_LENGTH=12`, `settings.py:92`) ajuda, mas o fechamento do enumerador de contas (`GET /users`) perde valor enquanto o oráculo de tentativas continua ilimitado.
- **Recomendação:** limite por IP e por conta (`flask-limiter` ou equivalente), com atraso progressivo; logar a sequência de falhas pelo logger já centralizado.

#### [AP-06 / correctness] `requer_admin` responde 404 onde deveria responder 401 — `src/middlewares/auth.py:51`

- **O que:** o decorator chama `container.users.get_user(actor.user_id)` (`:51`), e `UserService.get_user` (`user_service.py:36-40`) **levanta `NotFound`** quando o usuário não existe — a linha seguinte (`auth.py:52`, `if user is None`) é código morto, porque `get_user` nunca devolve `None`.
- **Impacto:** um token válido cujo usuário foi apagado recebe `404 {"error": "Usuário não encontrado"}` em `/reports/*` e `/categories` de escrita, em vez de `401`. O cliente não tem como distinguir "recurso inexistente" de "credencial inválida" e não sabe que deve reautenticar; de quebra, confirma a um portador de token antigo que a conta foi removida.
- **Recomendação:** delegar a `UserService.resolve_actor` (`user_service.py:106-113`), que já levanta `Unauthenticated` nesse caso — resolve junto o M1.

#### [AP-08 adjacente] Listagens sem teto efetivo — `src/config/settings.py:94`, `.env.example:27`, `src/repositories/task_repository.py:33,38`, `src/repositories/user_repository.py:23`

- **O que:** `LIST_DEFAULT_LIMIT` tem default `None` (`settings.py:94`) e vem vazio no `.env.example:27`; em `page_from_request` (`src/controllers/support.py:41-44`) isso significa `limit=None`, ou seja, **sem limite** quando o cliente não passa `?limit=`. O `LIST_MAX_LIMIT=500` (`:95`) só age sobre o valor que o cliente informou. Além disso, `list_by_user` (`task_repository.py:33`), `list_overdue` (`:38`) e `list_all` (`user_repository.py:23`) nem aceitam `Page` — `GET /users/<id>/tasks` e `GET /reports/summary` carregam tudo por construção.
- **Impacto:** `GET /tasks` sem parâmetros materializa a tabela inteira em memória e serializa tudo; `GET /reports/summary` percorre todos os usuários e todas as tasks atrasadas. Com a base crescendo, é a rota de saturação mais barata que a API oferece, e ela é pública (ver HIGH acima).
- **Recomendação:** um default numérico para `LIST_DEFAULT_LIMIT` (ex.: 50) e paginação nas três consultas que hoje não a aceitam. A mudança de contrato é aditiva se a resposta continuar sendo lista pura com `X-Total-Count` (`support.py:48-52`).

### 🔵 LOW

#### Imports locais dentro do corpo da função — `src/services/task_service.py:58,62,65`

- **O que:** `from ..errors import Unauthenticated` (`:58`, `:62`) e `from ..errors import Forbidden` (`:65`) estão dentro de `delete_task`, enquanto o módulo já importa `NotFound` do mesmo pacote no topo (`:6`). Não há ciclo de import que justifique. Achado LOW da rev2, ainda aberto — o patch que tornou a função fail-closed manteve os imports onde estavam.
- **Impacto:** esconde a dependência do módulo e destoa dos outros services (`user_service.py:17` importa os cinco erros no topo).
- **Recomendação:** mover para o topo, junto de `NotFound`.

#### Docstring de `auth.py` afirma o contrário de si mesmo — `src/middlewares/auth.py:3-10`

- **O que:** o bloco `:3-5` diz "a autenticação é **opcional** por rota — o contrato homologado mantém as rotas abertas"; o bloco `:7-10`, colado logo abaixo pelo patch, diz que rotas destrutivas e relatórios "exigem autenticação obrigatória". Os dois textos continuam no arquivo. O mesmo tipo de nota de processo ("EXCEÇÃO CRÍTICA (AP-06)… a correção prevalece sobre preservar o contrato") aparece em `task_controller.py:3-5`, `user_controller.py:6-9`, `category_controller.py:4-5`, `report_controller.py:3-4`, `task_service.py:52-54`, `user_service.py:93-96` — narram a decisão da auditoria, não o comportamento do código. Achado LOW da rev2, ainda aberto.
- **Impacto:** quem lê `auth.py` não sabe qual das duas frases vale hoje, e as referências a `AP-06` só fazem sentido com o relatório na mão.
- **Recomendação:** um docstring por módulo descrevendo o comportamento atual; a justificativa histórica pertence ao relatório e à mensagem de commit.

#### `/health` usa hora local em vez do UTC do domínio — `src/controllers/health_controller.py:3,14`

- **O que:** `str(datetime.now())` (`:14`) devolve horário local do host, naive, enquanto todo o resto passa por `utc_now()` (`src/models/domain.py:41-47`), função criada justamente para unificar isso. Achado LOW da rev2, ainda aberto.
- **Impacto:** o timestamp do health check não é comparável com `created_at`, `updated_at` nem com o `generated_at` dos relatórios (`report_service.py:35`). Em host fora de UTC, atrapalha qualquer correlação de log.
- **Recomendação:** usar `utc_now()`, já disponível.

#### `LIKE` sem escapar os curingas do input — `src/repositories/task_repository.py:22-23`

- **O que:** `pattern = f"%{text}%"` (`:22`) monta o padrão com o texto cru de `?q=` (`task_controller.py:64`). Não é SQL injection — o valor vai ligado como parâmetro —, mas `%` e `_` digitados pelo usuário viram curingas. Achado LOW da rev2, ainda aberto.
- **Impacto:** `?q=%` casa com todas as tasks; `?q=a_b` casa com `axb`. Resultado errado e, em base grande, varredura completa ao custo de um caractere — agravado por ser rota pública e sem teto de paginação.
- **Recomendação:** escapar `%`, `_` e o próprio caractere de escape, e declarar `escape="\\"` no `.like()`.

#### Hash MD5 legado aceito no login sem prazo de validade — `src/security/passwords.py:30-33`

- **O que:** `verify_password` reconhece qualquer hash de 32 hex como MD5 legado (`:30`) e o aceita, regravando em scrypt depois (`auth_service.py:26-29`). A ponte de migração é correta, mas não tem data de expiração nem contador — uma conta que nunca mais fizer login mantém o MD5 sem salt no banco indefinidamente.
- **Impacto:** o banco continua contendo credenciais quebráveis por rainbow table; um vazamento expõe exatamente as contas inativas, que são as menos monitoradas.
- **Recomendação:** medir quantas linhas ainda estão em MD5 (`SELECT count(*) ... WHERE length(password_hash) = 32`), definir uma data de corte e, passada ela, invalidar o hash legado forçando reset.

---

## APIs deprecated

Nenhuma chamada a API deprecated em código executável. As migrações das auditorias anteriores se mantêm: `datetime.utcnow()` → `utc_now()` (`src/models/domain.py:41-47`), `Model.query`/`Query.get()` → `select()` e `session.get()` (`src/repositories/base.py:29-33`), `md5` → `scrypt` (`src/security/passwords.py:22-23`). As ocorrências que o grep ainda encontra estão em **comentários** descrevendo o que foi substituído (`task_repository.py:13-14`, `base.py:3-4`, `domain.py:44`, `errors.py:4`).

| Item | Local | Situação |
|---|---|---|
| `marshmallow` 3.26.1 → 4.x | `requirements.txt:5`; uso em `src/schemas/task.py:27,41` (`fields.Field`) | Ainda não deprecated: `fields.Field` vira `fields.Raw` na 4.x. Atenção na próxima atualização, não é achado. |

---

## Recomendação de refatoração

Ordem sugerida para a Fase 3 (fecha risco antes de organizar):

1. **CRITICAL** — `@requer_autenticacao` + regra "próprio ou admin" em `PUT /users/<id>`. É a rota que o segundo patch esqueceu e a única que ainda permite escrita anônima em dado de identidade.
2. **MEDIUM (M1) antes dos demais HIGH** — unificar a autorização numa fonte de verdade fail-closed no service, com os decorators delegando. Fazer isso primeiro torna os passos 3 e 4 estruturalmente corretos em vez de mais uma rodada de remendo rota a rota; é o terceiro patch consecutivo sobre o mesmo tema.
3. **HIGH 1 + HIGH 3** — `create_task`/`update_task` e os três métodos de `CategoryService` recebendo `actor` e decidindo pela fonte única do passo 2.
4. **HIGH 2** — fechar as quatro leituras de task, lembrando que `search` é bypass de qualquer regra aplicada só às outras três.
5. **MEDIUM (M2, M3, M7)** — actor resolvido uma vez por request em `flask.g`; `resolve_actor` no lugar de `get_user` no decorator; leitura redundante de `GET /users/<id>`.
6. **MEDIUM (M5, M6)** — suíte de contrato cobrindo status e shape de cada endpoint e os três casos de cada rota com guarda; rate limit no login. A suíte é o que impede a rev4.
7. **MEDIUM (M4) + LOW** — teto de paginação; imports no topo, docstrings coerentes, `utc_now()` no health, escape do `LIKE`, prazo para o MD5 legado.

Nota de contrato: os passos 1, 3 e 4 alteram deliberadamente o contrato de 7 rotas hoje abertas ou permissivas (`PUT /users/<id>`; `GET /tasks`, `/tasks/<id>`, `/tasks/search`, `/tasks/stats`; e o escopo de `POST`/`PUT /tasks`), conforme a exceção prevista no AP-06 (`references/anti-patterns.md:73-75`).

> **Fase 2 completa. Prosseguir com a refatoração (Fase 3)? [y/n]**
