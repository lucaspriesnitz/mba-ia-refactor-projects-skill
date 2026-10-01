# Relatório de Auditoria Arquitetural — task-manager-api (revisão 4)

- **Data:** 2026-09-28
- **Stack:** Python 3.12 / Flask 3.1.1 + Flask-SQLAlchemy 3.1.1 + SQLAlchemy 2.1.1
- **Arquitetura de partida:** N2 — em camadas, com defeitos pontuais
- **Arquivos analisados:** 48 fontes `.py` (46 em `src/` + `app.py`, `wsgi.py`, `seed.py`, 2 de `migrations/`) + `requirements.txt`, `.env.example`, `.gitignore`, `README.md`
- **Escopo:** árvore de trabalho atual, **não commitada**, já com o terceiro patch de autorização aplicado (`@requer_autenticacao` em todas as rotas de `/tasks` e em `PUT /users/<id>`; `actor` chegando aos três métodos de escrita de `TaskService` e aos três de `CategoryService`)
- **Método:** auditoria **estática**. Nesta sessão a execução de comandos está negada (ambiente não-interativo), então nada foi observado rodando — nenhuma afirmação abaixo depende de boot ou de resposta de endpoint.

> Quarta auditoria do projeto. `audit-project-3.md` (23 achados) descreve o estado pré-refatoração; a rev2 (13 achados) auditou o primeiro patch de auth; a rev3 (16 achados) auditou o segundo. Dos 16 achados da rev3, **3 estão fechados** (o CRITICAL de `PUT /users/<id>` anônimo, o HIGH das leituras de task abertas e o HIGH do fail-open em `CategoryService`), **1 está parcialmente fechado** (posse de task: a checagem existe, o campo `user_id` continua livre) e **12 seguem abertos** — inclusive os 7 MEDIUM e os 5 LOW, intactos pela terceira rodada consecutiva. Dois deles **pioraram em volume**: a duplicação da regra de autorização passou de 3 para 6 cópias e os imports locais de 3 para 8.

## Resumo por severidade

| Severidade | Qtd |
|---|---|
| CRITICAL | 0 |
| HIGH | 2 |
| MEDIUM | 9 |
| LOW | 7 |
| **Total** | **18** |

APIs deprecated detectadas em código executável: **nenhuma** (1 item de atenção para migração futura — ver seção própria).

---

## Achados

### 🔴 CRITICAL

Nenhum. É a primeira revisão sem achado CRITICAL: toda rota destrutiva (`DELETE /tasks/<id>`, `DELETE /users/<id>`, `DELETE /categories/<id>`) e toda escrita em campo de identidade ou privilégio exige credencial, e a checagem agora existe **no service**, não só no decorator. Os dois HIGH abaixo são o que restou do modelo de posse.

### 🟠 HIGH

#### [AP-06] Leitura e busca de tasks sem escopo por dono: qualquer conta lê o sistema inteiro, e `POST /users` é aberto — `src/controllers/task_controller.py:27,34,62,75`, `src/controllers/user_controller.py:33,41,49`, `src/services/task_service.py:21-25`

- **O que:** o patch fechou as quatro leituras de task com `@requer_autenticacao` (`task_controller.py:28,35,63,76`), mas parou na autenticação — não há autorização por objeto. `TaskService.list_tasks` (`task_service.py:21-22`) devolve `list_with_relations`, que é `select(Task)` sem filtro (`src/repositories/task_repository.py:15`), e `search_tasks` (`:24-25`) aceita `user_id` como filtro livre (`task_controller.py:70`). `GET /users` (`user_controller.py:33`) devolve nome, e-mail, papel e contagem de tasks de todo mundo para qualquer portador de token. E `POST /users` (`:49`) é a única rota de escrita sem guarda: cadastro aberto, por definição de produto.
- **Impacto:** a cadeia é de duas requisições — `POST /users` com um e-mail qualquer, `POST /login`, e a partir daí `GET /tasks` entrega título, descrição, tags, prazo e `user_name` de todas as tasks do sistema, `GET /tasks/search?q=` faz busca livre sobre esse conteúdo e `GET /tasks/search?user_id=<vítima>` devolve a carteira inteira de um usuário específico. Ou seja: `GET /users/<id>/tasks` está atrás de token (`:72`) e continua tendo um bypass exato ao lado. Na prática o dado não ficou protegido, ficou atrás de um formulário de cadastro; e `GET /users` entrega a lista de e-mails que alimenta a força bruta do login (ver M7). A inversão de prioridade que a rev3 apontou persiste em outra forma: o relatório agregado exige admin (`report_controller.py:16,22`), o dado bruto que o compõe basta estar logado.
- **Recomendação:** decidir o escopo no service, não na rota: admin vê tudo, os demais veem as próprias tasks — e aplicar a mesma regra dentro de `search` (rejeitar `user_id` de terceiro para não-admin), senão a busca continua sendo a porta lateral. Para `GET /users`, restringir a admin ou reduzir a projeção (`id`, `name`) para não-admin. Se o cadastro aberto é requisito, ele precisa ser tratado como tal no modelo de ameaça: toda rota que hoje confia em "tem token" está, de fato, confiando em "conseguiu se cadastrar".

#### [AP-06] `PUT /tasks/<id>` aceita `user_id` do corpo: o dono reatribui a task para qualquer usuário (ou para ninguém) — `src/services/task_service.py:69-71`, `src/schemas/task.py:77`

- **O que:** `update_task` (`:54`) passou a exigir actor (`:59-65`) e a checar "admin ou dono" (`:66-68`) — e então aplica `setattr` em **todos** os campos recebidos (`:70-71`), inclusive `user_id`, que o schema aceita com `allow_none=True` (`schemas/task.py:77`). A única validação é de existência (`_ensure_references_exist`, `:69,109-110`). É incoerente com a rota irmã: `create_task` (`:45-46`) força `values["user_id"] = user.id` justamente para impedir que o cliente escolha o dono — uma linha depois, o `PUT` deixa escolher.
- **Impacto:** qualquer conta válida (ver o HIGH anterior sobre como obter uma) cria uma task e a injeta na carteira de outro usuário — inclusive de um admin — com o conteúdo que quiser: é plantar dado atribuído a terceiro, e o alvo não tem como recusar. Com `user_id: null` a task fica órfã: nenhum não-admin volta a satisfazer `task.user_id != user.id` (`:66`), então ela só pode ser editada ou apagada por admin, sem caminho de volta pela API. O teto do dano é a task do próprio atacante (ele não edita a de outro), mas o efeito é derrotar o modelo de posse que o patch acabou de instalar, justamente pelo campo que define a posse.
- **Recomendação:** `user_id` só aceito de admin; para os demais, remover o campo do payload antes do `setattr` (ou 403 explícito se vier). Rejeitar `user_id: null` vindo de não-admin. O `setattr` cego sobre `changes` é o padrão de fundo: a lista de campos alteráveis deve ser explícita por papel.

### 🟡 MEDIUM

#### [AP-12] Seis implementações concorrentes da mesma regra de autorização — `src/middlewares/auth.py:44-57`, `src/services/user_service.py:113-124`, `src/services/category_service.py:32-39`, `src/services/task_service.py:38-44,59-65,83-89`

- **O que:** "resolver o actor, conferir que existe e está ativo, conferir se é admin" está escrito seis vezes: `requer_admin` (`auth.py:47-56`), `UserService.resolve_actor` + `_require_admin` (`user_service.py:113-124`), `CategoryService._require_admin` (`category_service.py:32-39`) e três cópias inline em `TaskService.create_task`, `update_task` e `delete_task` (`task_service.py:38-44`, `:59-65`, `:83-89` — o mesmo bloco de 6 linhas, colado). M1 da rev2 e da rev3, ainda aberto: eram 3 cópias, agora são 6. Cada patch fechou um fail-open **copiando** a checagem em vez de chamar a que já existia.
- **Impacto:** a política de acesso não tem fonte de verdade. As cópias já divergiram uma vez (foi assim que a rev2 nasceu com dois achados de autorização quebrada) e divergem hoje: `resolve_actor` levanta `Unauthenticated` para usuário inexistente, enquanto `requer_admin` levanta `NotFound` (M2, abaixo). Qualquer mudança de política — adicionar `manager`, checar `active` de outra forma, logar acesso negado — precisa acertar seis lugares, e nada avisa quando um fica para trás.
- **Recomendação:** uma fonte única fail-closed (`resolve_actor`/`_require_admin` é a boa implementação, ou um `AuthorizationService` no container) com decorators e services **delegando** a ela. Fazer isso antes dos dois HIGH: senão o escopo por dono também nasce em cópias.

#### [AP-06 / correctness] `requer_admin` responde 404 onde deveria responder 401, e a checagem seguinte é código morto — `src/middlewares/auth.py:51-53`

- **O que:** o decorator chama `container.users.get_user(actor.user_id)` (`:51`), e `UserService.get_user` (`user_service.py:36-40`) **levanta `NotFound`** quando não acha — nunca devolve `None`. Logo `if user is None or not user.active` (`:52`) só é alcançável pelo segundo termo; o primeiro é inalcançável. M6 da rev3, ainda aberto.
- **Impacto:** um token válido cujo usuário foi apagado recebe `404 {"error": "Usuário não encontrado"}` em `/reports/*` e nas escritas de `/categories`, em vez de `401`. O cliente não distingue "recurso inexistente" de "credencial morta" e não sabe que deve reautenticar; e a resposta confirma a um portador de token antigo que a conta foi removida. Sintoma direto do M1.
- **Recomendação:** delegar a `UserService.resolve_actor` (`user_service.py:113-120`), que já levanta `Unauthenticated` nesse caso, e apagar a condição morta.

#### [AP-13 adjacente] Actor resolvido duas vezes por requisição; em `requer_admin`, usuário lido duas vezes — `src/middlewares/auth.py:37,48,51`, `src/controllers/task_controller.py:44,52,58`, `src/controllers/user_controller.py:52,61,68`

- **O que:** o decorator chama `current_actor()` (`auth.py:37`, `:48`), que decodifica o JWT, descarta o resultado, e o handler decorado chama `current_actor()` de novo (`task_controller.py:44,52,58`; `user_controller.py:52,61,68`) para passar o actor ao service — segunda verificação HMAC do mesmo token. Em `requer_admin`, o `SELECT` do usuário (`auth.py:51`) é refeito pelo service logo depois (`user_service.py:117` ou `category_service.py:35`). M2 da rev2 e da rev3, ainda aberto.
- **Impacto:** duas verificações de assinatura e até dois `SELECT` por request — custo pequeno. O problema é semântico: não existe um lugar onde "o actor desta requisição" viva, então guarda de rota e guarda de service são dois universos, e é exatamente essa lacuna que produziu o CRITICAL da rev3 (rota sem decorator, service sem como perceber).
- **Recomendação:** resolver uma vez por request, guardar em `flask.g`, e ter decorators, handlers e services lendo de lá.

#### [AP-13] `GET /users/<id>` lê o mesmo usuário duas vezes — `src/controllers/user_controller.py:44-45`, `src/services/user_service.py:42-44`

- **O que:** o handler chama `get_user(user_id)` (`:44`) e em seguida `get_user_tasks(user_id)` (`:45`), que refaz `self.get_user(user_id)` (`user_service.py:43`) só para validar existência. M3 da rev2 e da rev3, ainda aberto.
- **Impacto:** um `SELECT` redundante por request em caminho quente. Sem gravidade — é a mesma classe de desperdício que a rev1 eliminou nos relatórios, sobrevivendo num handler.
- **Recomendação:** um método de service que devolva usuário e tasks numa passagem, ou `get_user_tasks` aceitando a entidade já carregada.

#### [AP-08 adjacente] Listagens sem teto efetivo — `src/config/settings.py:94`, `.env.example:27`, `src/controllers/support.py:41-44`, `src/repositories/task_repository.py:33,38`, `src/repositories/user_repository.py:23`

- **O que:** `LIST_DEFAULT_LIMIT` tem default `None` (`settings.py:94`) e vem vazio no `.env.example:27`; em `page_from_request` (`support.py:41-44`) isso significa `limit=None` — **sem limite** quando o cliente não passa `?limit=`. `LIST_MAX_LIMIT=500` (`settings.py:95`) só age sobre o valor informado pelo cliente. Além disso `list_by_user` (`task_repository.py:33`), `list_overdue` (`:38`) e `list_all` (`user_repository.py:23`) não aceitam `Page`: `GET /users/<id>/tasks` e `GET /reports/summary` carregam tudo por construção. M7 da rev3, ainda aberto.
- **Impacto:** `GET /tasks` sem parâmetros materializa a tabela inteira e a serializa; `GET /reports/summary` percorre todos os usuários e todas as tasks atrasadas. Com o patch de auth, a rota exige token — e, como o cadastro é aberto (ver HIGH 1), o custo de obter um é uma requisição. Segue sendo a rota de saturação mais barata da API.
- **Recomendação:** default numérico para `LIST_DEFAULT_LIMIT` (ex.: 50) e `Page` nas três consultas que ainda não a aceitam. A mudança é aditiva se a resposta continuar lista pura com `X-Total-Count` (`support.py:48-52`) — ver L7.

#### [test-coverage] Nenhum teste automatizado — árvore inteira (sem `tests/`, sem `pytest` em `requirements.txt:1-23`)

- **O que:** não existe diretório de testes nem dependência de teste. **Três** patches de autorização consecutivos foram aplicados sem um único caso de regressão. M4 da rev2, M4 da rev3, ainda aberto.
- **Impacto:** é a causa raiz direta do histórico deste projeto: um teste de `GET /reports/summary` com token de admin teria pegado na hora o `AttributeError` que a rev2 encontrou; um teste "sem token → 401" por rota teria pegado o `PUT /users/<id>` que a rev3 encontrou. Sem suíte, "o comportamento foi preservado" é afirmação sem evidência — e nesta sessão eu também não pude executar nada, então o patch atual está, neste momento, **sem nenhuma verificação dinâmica, de ninguém**.
- **Recomendação:** `pytest` + test client do Flask, com suíte fina de contrato: status e shape por endpoint, e três casos por rota com guarda (sem token → 401, token sem permissão → 403, token válido → 200). É o item que impede a rev5.

#### [AP-06] `POST /login` sem rate limiting nem lockout — `src/controllers/user_controller.py:79`, `src/services/auth_service.py:16`

- **O que:** `login()` compara a senha (`auth_service.py:23`) e devolve 401 sem contabilizar tentativas, sem atraso e sem bloqueio por conta ou por IP. Não há dependência de rate limit em `requirements.txt:1-23`. M5 da rev3, ainda aberto.
- **Impacto:** força bruta livre contra qualquer e-mail conhecido — e `GET /users` (HIGH 1) entrega a lista de e-mails a qualquer conta recém-criada. A política de 12 caracteres (`settings.py:92`) mitiga senhas novas, mas não as três de demonstração documentadas no `README.md:27-31`, que seguem válidas no seed.
- **Recomendação:** limite por IP e por conta (`flask-limiter` ou equivalente) com atraso progressivo, e log da sequência de falhas pelo logger já centralizado.

#### [contrato] `POST /tasks` descarta silenciosamente o `user_id` do corpo — `src/services/task_service.py:45-46`, `src/schemas/task.py:77`

- **O que:** `create_task` sobrescreve `values["user_id"] = user.id` (`:46`) depois de mesclar o payload (`:45`), mas o schema continua aceitando `user_id` (`schemas/task.py:77`). O campo é lido, validado, e então ignorado sem aviso.
- **Impacto:** duas coisas. (a) Um cliente legítimo que envie `user_id` recebe `201` com a task criada **em outro dono** do que pediu — falha silenciosa, o pior formato de erro. (b) Admin perdeu a capacidade de criar task para outro usuário, que o contrato original tinha; isso é mudança de comportamento que **não** está coberta pela exceção do AP-06 (a exceção autoriza exigir credencial, não reescrever um campo), e não está registrada em nenhum lugar — o `README.md:123-136` não menciona.
- **Recomendação:** `user_id` de terceiro só para admin; para os demais, ou 403 explícito quando vier divergente do actor, ou remover o campo do `TaskInputSchema` de criação. Qualquer decisão precisa entrar na lista de mudanças de contrato do README. Mesma raiz do HIGH 2.

#### [documentação] README e docstrings descrevem uma postura de segurança que não é a do código — `README.md:123-136,140-143`, `src/middlewares/auth.py:3-10`

- **O que:** o `README.md:140-143` afirma, como "próximo passo fora do escopo", que `DELETE /users/<id>`, `DELETE /tasks/<id>` e `GET /reports/summary` "seguem abertas: exigir token nelas mudaria a resposta de endpoints que a Fase 2 homologou" — as três exigem token hoje (`user_controller.py:66`, `task_controller.py:56`, `report_controller.py:16`). A lista de mudanças intencionais de contrato (`:123-136`) tem 8 itens e **nenhum** cobre os dois patches seguintes: `/tasks` inteira, `GET /users*`, escrita de `/categories` e `/reports/*` passaram a exigir credencial sem registro. O `auth.py:3-5` ainda diz "a autenticação é opcional por rota — o contrato homologado mantém as rotas abertas", contradito por `:7-10` no mesmo docstring.
- **Impacto:** a documentação é o entregável que descreve as quebras de contrato deliberadas (regra 2 da skill) e hoje ela lista como pendente um trabalho já feito e omite as quebras que existem. Quem integra com a API pelo README erra em quais rotas precisam de `Authorization`; quem lê `auth.py` não sabe qual das duas frases vale.
- **Recomendação:** reescrever a seção de contrato a partir do estado atual (uma linha por rota que passou a exigir credencial e qual papel), remover de "próximos passos" o que foi feito, e deixar um docstring por módulo descrevendo o comportamento atual.

### 🔵 LOW

#### Imports locais dentro do corpo da função, 8 ocorrências — `src/services/task_service.py:39,43,60,64,67,84,88,91`

- **O que:** `from ..errors import Unauthenticated` (`:39,43,60,64,84,88`) e `from ..errors import Forbidden` (`:67,91`) estão dentro dos métodos, enquanto o módulo já importa `NotFound` do mesmo pacote no topo (`:6`). Não há ciclo de import que justifique. LOW da rev2 e da rev3: eram 3, agora são 8 — cada cópia do bloco de auth trouxe os imports consigo.
- **Impacto:** esconde a dependência do módulo e destoa dos outros services (`user_service.py:17` importa os cinco erros no topo). É o marcador visível do M1.
- **Recomendação:** mover para o topo junto de `NotFound` — e resolver junto o M1, que é o que os multiplicou.

#### Docstrings narram a decisão da auditoria em vez do comportamento — `src/middlewares/auth.py:3-10`, `src/controllers/task_controller.py:3-5`, `src/controllers/user_controller.py:6-9`, `src/controllers/category_controller.py:4-5`, `src/controllers/report_controller.py:3-4`, `src/services/task_service.py:34-37,55-58,78-81`, `src/services/category_service.py:4-6`, `src/services/user_service.py:66-68,101-103`

- **O que:** dez blocos repetem a fórmula "EXCEÇÃO CRÍTICA (AP-06): … a correção do CRITICAL prevalece sobre preservar o contrato original da rota" — texto de processo, colado em cada patch, dentro do código. Em `auth.py` o acúmulo virou contradição (ver M9). LOW da rev2 e da rev3, ainda aberto.
- **Impacto:** o docstring descreve o histórico da refatoração, não o que o módulo faz; as referências a `AP-06` só significam algo com o relatório na mão. A repetição cresce a cada revisão.
- **Recomendação:** um docstring por módulo sobre o comportamento atual. Justificativa histórica pertence ao relatório e à mensagem de commit.

#### `/health` usa hora local em vez do UTC do domínio — `src/controllers/health_controller.py:3,14`

- **O que:** `str(datetime.now())` (`:14`) devolve horário local do host, naive, enquanto todo o resto passa por `utc_now()` (`src/models/domain.py:41-47`), função criada para unificar isso. LOW da rev2 e da rev3, ainda aberto.
- **Impacto:** o timestamp do health check não é comparável com `created_at`, `updated_at` nem com o `generated_at` dos relatórios (`report_service.py:35`). Em host fora de UTC, atrapalha correlação de log.
- **Recomendação:** usar `utc_now()`, já disponível.

#### `LIKE` sem escapar os curingas do input — `src/repositories/task_repository.py:22-23`

- **O que:** `pattern = f"%{text}%"` (`:22`) monta o padrão com o texto cru de `?q=` (`task_controller.py:68`). Não é SQL injection — o valor vai ligado como parâmetro —, mas `%` e `_` digitados pelo cliente viram curingas. LOW da rev2 e da rev3, ainda aberto.
- **Impacto:** `?q=%` casa com todas as tasks; `?q=a_b` casa com `axb`. Resultado errado e, em base grande, varredura completa ao custo de um caractere — combinado com a ausência de teto de paginação (M5).
- **Recomendação:** escapar `%`, `_` e o caractere de escape, e declarar `escape="\\"` no `.like()`.

#### Hash MD5 legado aceito no login sem prazo de validade — `src/security/passwords.py:30-33`

- **O que:** `verify_password` reconhece qualquer hash de 32 hex como MD5 legado (`:30`) e o aceita, regravando em scrypt depois (`auth_service.py:26-29`). A ponte de migração é correta, mas não tem data de corte nem contador. LOW da rev3, ainda aberto.
- **Impacto:** o banco segue contendo credenciais quebráveis por rainbow table; um vazamento expõe exatamente as contas que nunca mais logaram, as menos monitoradas.
- **Recomendação:** medir quantas linhas ainda estão em MD5 (`SELECT count(*) FROM users WHERE length(password_hash) = 32`), definir uma data de corte e, passada ela, invalidar o hash legado forçando reset.

#### `GET /categories` é a única leitura totalmente aberta — `src/controllers/category_controller.py:21-22`

- **O que:** depois do patch, todas as leituras exigem token (`/tasks` × 4, `/users` × 3, `/reports` × 2) menos `GET /categories` (`:21`), que não tem decorator. As escritas da mesma rota exigem admin (`:29,36,44`).
- **Impacto:** um anônimo lê nome, descrição, cor e **contagem de tasks** por categoria (`:24`) — sinal de volume e de organização interna, sem conteúdo sensível. O incômodo real é a inconsistência: é a exceção não documentada no meio de uma postura agora uniforme.
- **Recomendação:** decidir explicitamente — ou `@requer_autenticacao` como as outras leituras, ou um comentário de uma linha dizendo que é pública de propósito (catálogo consumido por tela de login, por exemplo).

#### `X-Total-Count` não é exposto ao cliente de browser — `src/app_factory.py:49-54`, `src/controllers/support.py:48-52`

- **O que:** a paginação devolve o total em `X-Total-Count` (`support.py:51`), mas a configuração de CORS (`app_factory.py:49-54`) declara `origins`, `methods` e `allow_headers` e **não** declara `expose_headers`. Por padrão, o browser só entrega ao JavaScript os headers da lista segura do CORS.
- **Impacto:** qualquer front-end em origem permitida recebe a lista paginada sem conseguir ler o total — a feature de paginação fica pela metade exatamente para o consumidor principal de uma API com CORS habilitado. Não aparece em teste com `curl`, que vê todos os headers.
- **Recomendação:** `expose_headers=["X-Total-Count"]` na chamada de `CORS(...)`, usando a mesma constante `TOTAL_COUNT_HEADER` (`support.py:8`) em vez de repetir a string.

---

## APIs deprecated

Nenhuma chamada a API deprecated em código executável. As migrações das auditorias anteriores se mantêm: `datetime.utcnow()` → `utc_now()` (`src/models/domain.py:41-47`), `Model.query`/`Query.get()` → `select()` e `session.get()` (`src/repositories/base.py:29-33`), `md5` → `scrypt` (`src/security/passwords.py:22-23`). As ocorrências que o grep ainda encontra estão em **comentários** descrevendo o que foi substituído (`task_repository.py:13-14`, `base.py:3-4`, `domain.py:44`, `errors.py:4`) — mais a única chamada real de `hashlib.md5`, que é a ponte de compatibilidade do login (`passwords.py:31`, ver LOW acima).

| Item | Local | Situação |
|---|---|---|
| `marshmallow` 3.26.1 → 4.x | `requirements.txt:5`; uso em `src/schemas/task.py:27,41` (`fields.Field`) | Ainda não deprecated: `fields.Field` vira `fields.Raw` na 4.x. Atenção na próxima atualização, não é achado. |

## Recomendação de refatoração

Ordem sugerida para a Fase 3 (fecha risco antes de organizar):

1. **M1 primeiro, antes de qualquer HIGH.** Uma fonte única fail-closed de autorização, com decorators e services delegando. É a terceira revisão pedindo isso, e é a razão pela qual cada patch anterior virou "mais uma rodada rota a rota": sem ponto único, o escopo por dono do passo 2 nasceria em seis cópias novas. Fecha junto o M2 (404→401) e o L1 (imports).
2. **HIGH 2** — `user_id` só de admin em `PUT /tasks/<id>`, lista explícita de campos alteráveis por papel, e o `POST /tasks` (M8) coerente com ela: ou aceita `user_id` de admin, ou rejeita em vez de ignorar.
3. **HIGH 1** — escopo por dono nas leituras de task decidido no service, aplicado **também** dentro de `search` (é o bypass de qualquer regra posta só nas outras três), e projeção reduzida em `GET /users` para não-admin.
4. **M6 (testes)** — suíte de contrato: status e shape por endpoint, e os três casos de cada rota com guarda. Colocar aqui e não no fim é deliberado: os passos 2 e 3 mudam contrato de novo, e é a quarta revisão em que ninguém tem evidência de que a rodada anterior não quebrou nada. Nesta sessão eu não pude executar a aplicação — a suíte é o que substitui essa verificação de forma durável.
5. **M3, M4, M5** — actor resolvido uma vez em `flask.g`; leitura única em `GET /users/<id>`; teto numérico de paginação e `Page` nas três consultas sem ela.
6. **M7 + M9** — rate limit no login; README e docstrings reescritos a partir do estado atual, com a lista de contrato completa (é o que documenta as quebras deliberadas exigidas pela regra 2).
7. **LOW restantes** — `utc_now()` no health, escape do `LIKE`, prazo para o MD5 legado, decisão explícita sobre `GET /categories`, `expose_headers` do `X-Total-Count`.

Nota de contrato: os passos 2 e 3 alteram deliberadamente o contrato de rotas hoje permissivas (`PUT /tasks/<id>` com `user_id`; escopo de `GET /tasks`, `/tasks/<id>`, `/tasks/search`, `/tasks/stats`, `GET /users`), conforme a exceção prevista no AP-06 (`references/anti-patterns.md:73-75`). O passo 6 registra isso — e as quebras das duas rodadas anteriores, hoje não documentadas.

Nota de validação: esta revisão é **estática**. A execução de comandos está negada nesta sessão, então o boot da aplicação e as respostas dos endpoints **não** foram observados; nenhum achado acima depende disso, mas a Fase 3 precisaria de execução liberada para a validação que a skill exige.

> **Fase 2 completa. Prosseguir com a refatoração (Fase 3)? [y/n]**
