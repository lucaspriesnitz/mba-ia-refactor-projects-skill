# Relatório de Auditoria Arquitetural — task-manager-api

- **Data:** 2026-09-25
- **Stack:** Python 3 (host 3.12.10) / Flask 3.0.0 + Flask-SQLAlchemy 3.1.1
- **Arquitetura de partida:** N1 — separação parcial nominal (`models/`, `routes/`, `services/`, `utils/` existem, mas `services/` nunca é importado e as rotas falam direto com o ORM)
- **Arquivos analisados:** 15 fontes `.py` (`app.py`, `database.py`, `seed.py`, `models/`×4, `routes/`×4, `services/`×2, `utils/`×2) + `requirements.txt`, `README.md`

## Resumo por severidade

| Severidade | Qtd |
|---|---|
| CRITICAL | 4 |
| HIGH | 5 |
| MEDIUM | 9 |
| LOW | 5 |
| **Total** | **23** |

APIs deprecated / legadas detectadas: **4**.

---

## Achados

### 🔴 CRITICAL

#### [AP-03] Hash de senha devolvido nas respostas da API — `models/user.py:22`
- **O que:** `User.to_dict()` inclui `'password': self.password` (`models/user.py:22`) — o hash do usuário. Esse dicionário é serializado para o cliente em **quatro** endpoints: `GET /users/<id>` (`routes/user_routes.py:33`), `POST /users` (`user_routes.py:85-86`), `PUT /users/<id>` (`user_routes.py:129`) e, o pior, `POST /login` (`user_routes.py:209`, dentro de `'user': user.to_dict()`). O único handler que monta a resposta à mão e escapa do problema é `GET /users` (`user_routes.py:15-23`).
- **Impacto:** vazamento de credencial pela própria API, sem precisar de acesso ao banco. Combinado com o MD5 sem salt do achado seguinte, o hash devolvido é revertido por rainbow table pública em segundos — ou seja, `GET /users/1` entrega a senha em claro de qualquer usuário a um chamador **anônimo** (não há autenticação — ver AP-06). O seed confirma a facilidade: `'1234'`, `'abcd'`, `'pass'` (`seed.py:19,26,33`).
- **Recomendação:** remover o campo `password` de `to_dict()`. A serialização de saída não deve ser responsabilidade do model — extrair um schema/serializer explícito (marshmallow já está em `requirements.txt:4`, sem uso) com allowlist de campos, e renomear a coluna para `password_hash` para que a intenção fique óbvia no código.

#### [AP-04] MD5 sem salt como hash de senha — `models/user.py:29,32`
- **O que:** `set_password()` faz `hashlib.md5(pwd.encode()).hexdigest()` (`models/user.py:29`) e `check_password()` compara o MD5 recalculado (`models/user.py:32`). Sem salt, sem alongamento de chave, algoritmo quebrado para colisão desde 2004 e projetado para ser rápido.
- **Impacto:** um dump do banco (ou uma resposta da API, ver AP-03 acima) entrega todas as senhas: uma GPU comum testa bilhões de MD5 por segundo, e o determinismo sem salt permite atacar todos os usuários de uma vez com a mesma tabela. A política de senha de 4 caracteres (`user_routes.py:64-65`) reduz o espaço de busca a quase nada.
- **Recomendação:** bcrypt/argon2id (ou `hashlib.scrypt` da stdlib) com salt por registro e custo calibrado, isolados atrás de um módulo de `security/`, não dentro do model. Os hashes atuais são irrecuperáveis — exigem rehash no próximo login válido ou reset forçado de senha.

#### [AP-02] Segredos hardcoded no fonte — `app.py:13`, `services/notification_service.py:9-10`
- **O que:** `app.config['SECRET_KEY'] = 'super-secret-key-123'` (`app.py:13`) e as credenciais SMTP `self.email_user = 'taskmanager@gmail.com'` / `self.email_password = 'senha123'` (`notification_service.py:9-10`), junto de host e porta fixos (`notification_service.py:7-8`). A URI do banco também é literal (`app.py:11`). Nada é lido do ambiente, e `python-dotenv` está declarado em `requirements.txt:6` sem nunca ser importado.
- **Impacto:** os segredos ficam no histórico do Git — rotação exige alterar código e redeployar, e qualquer clone/fork/backup os carrega. A `SECRET_KEY` previsível permite forjar qualquer coisa que o Flask assine (sessões, tokens de `itsdangerous`). A senha SMTP dá acesso de envio à conta de e-mail da aplicação.
- **Recomendação:** módulo `config/` lendo `os.environ` com validação fail-fast no boot; `.env` no `.gitignore` (**o projeto não tem `.gitignore` nem `.env.example` hoje** — ver LOW) e `.env.example` versionado. Os valores expostos precisam ser **revogados e rotacionados**, não só removidos do código.

#### [AP-06] Ausência total de autenticação, com escalada de privilégio disponível — `routes/user_routes.py:92,119-122,134`, `routes/task_routes.py:225`
- **O que:** nenhuma rota do projeto verifica identidade ou permissão — não existe middleware, decorator ou checagem de token em nenhum dos três blueprints. `User.is_admin()` (`models/user.py:34-38`) e o campo `role` existem, mas **nunca são consultados**. Consequências diretas: `PUT /users/<id>` aceita `{'role': 'admin'}` de qualquer chamador anônimo (`user_routes.py:119-122`) e também troca a senha de qualquer usuário (`user_routes.py:114-117`); `DELETE /users/<id>` apaga o usuário **e todas as suas tasks** (`user_routes.py:134,140-142`); `DELETE /tasks/<id>` apaga qualquer task (`task_routes.py:225`); `GET /reports/summary` expõe a produtividade nominal de todos os usuários (`report_routes.py:53-68`).
- **Impacto:** qualquer requisição da rede se promove a admin, assume a conta de outra pessoa trocando a senha dela, ou destrói a base inteira um id por vez. Classificado como CRITICAL (acima do HIGH padrão do AP-06) porque a escalada de privilégio em `PUT /users/<id>` é uma tomada de conta remota trivial, não apenas "rota sensível aberta".
- **Recomendação:** autenticação real (ver achado do token fake, abaixo) aplicada por `before_request`/decorator antes dos handlers, com autorização por papel. `role` só deve ser alterável por admin; senha só pelo próprio usuário mediante senha atual; `DELETE /users/<id>` restrito a admin ou ao próprio dono.

---

### 🟠 HIGH

#### [AP-07] `debug=True` no fonte, escutando em `0.0.0.0` — `app.py:34`
- **O que:** `app.run(debug=True, host='0.0.0.0', port=5000)` — o modo debug é fixo no código, sem controle por variável de ambiente, e o bind é em todas as interfaces.
- **Impacto:** habilita o console interativo do Werkzeug: um stack trace na resposta vira execução de Python arbitrário no servidor (o PIN de proteção é derivado de dados frequentemente descobríveis, e o tráfego é HTTP em claro). Combinado com `0.0.0.0`, isso fica exposto à rede, não só ao localhost. Além disso, todo `500` devolve caminhos internos e trechos de código ao cliente.
- **Recomendação:** `debug` vindo de env (`FLASK_DEBUG`), default `False`; `host` também configurável, com `127.0.0.1` como default de desenvolvimento. Em produção, servir por WSGI (gunicorn/waitress) com um entry point `wsgi.py`, não `app.run()`.

#### Token de autenticação falso e forjável — `routes/user_routes.py:210`
- **O que:** `POST /login` responde `'token': 'fake-jwt-token-' + str(user.id)` (`user_routes.py:210`). O valor não é assinado, não tem expiração, não é verificado por nenhuma rota, e é **totalmente previsível** a partir do id do usuário.
- **Impacto:** qualquer cliente monta `fake-jwt-token-1` sozinho — o login é decorativo. Pior: a `SECRET_KEY` existe (`app.py:13`) e dá a impressão de que há sessão assinada, quando não há nada. Consumidores do front-end vão tratar esse token como credencial e construir a autorização sobre uma base vazia.
- **Recomendação:** emitir JWT assinado (HS256 com segredo vindo de env) ou sessão do servidor, com `exp` curto, e exigir verificação nas rotas protegidas. Enquanto isso não existir, o endpoint não deveria devolver campo `token` algum — é pior que não ter.

#### Senha mínima de 4 caracteres, sem verificação da senha atual na troca — `routes/user_routes.py:64-65,114-117`
- **O que:** `if len(password) < 4` na criação (`user_routes.py:64-65`) e `if len(data['password']) < 4` na atualização (`user_routes.py:116`). A troca de senha em `PUT /users/<id>` não pede a senha atual nem qualquer prova de identidade. O seed usa exatamente 4 caracteres em todos os usuários (`seed.py:19,26,33`).
- **Impacto:** o espaço de busca de uma senha de 4 caracteres é exaurido instantaneamente, e o hash MD5 sem salt (AP-04) elimina qualquer custo de tentativa. Não há rate limiting nem lockout em `POST /login` (`user_routes.py:185-211`), então o ataque é online também.
- **Recomendação:** mínimo de 12 caracteres com checagem contra lista de senhas vazadas; troca de senha exigindo a senha atual; rate limiting no login.

#### Schema criado por `db.create_all()` no import, sem migrations — `app.py:30-31`
- **O que:** `with app.app_context(): db.create_all()` executa como **efeito colateral de importar `app.py`** (`app.py:30-31`). Não há Alembic/Flask-Migrate. `db.create_all()` só cria tabelas ausentes: nunca altera coluna, índice ou constraint de tabela já existente.
- **Impacto:** deriva silenciosa de schema — qualquer mudança futura em `models/` (renomear coluna, mudar tipo, adicionar `NOT NULL`) não é aplicada ao `tasks.db` existente, e a falha aparece só em runtime, como erro de query. Como o efeito é no import, qualquer processo que importe `app` (por exemplo `seed.py:2`) toca o banco — inclusive uma futura suíte de testes ou um worker.
- **Recomendação:** Flask-Migrate/Alembic com migrations versionadas; criação de schema em comando CLI explícito, nunca no import. Ver também o achado de app factory (MEDIUM).

#### Integridade referencial ausente e regras de deleção inconsistentes — `models/task.py:13-14`, `routes/report_routes.py:211-223`, `routes/user_routes.py:140-142`
- **O que:** as FKs de `Task` não declaram `ondelete` nem cascade (`models/task.py:13-14`), e o SQLite não aplica FK por padrão (`PRAGMA foreign_keys` fica `OFF` e não é ligado em lugar nenhum). `DELETE /categories/<id>` (`report_routes.py:211-223`) apaga a categoria sem tocar nas tasks que a referenciam. Já `DELETE /users/<id>` faz o oposto: apaga manualmente **todas as tasks do usuário** (`user_routes.py:140-142`), mesmo com `user_id` sendo `nullable=True`.
- **Impacto:** deletar uma categoria deixa tasks com `category_id` apontando para uma linha inexistente — `GET /tasks` então devolve `category_name: null` sem explicação (`task_routes.py:51-55`), e `GET /categories` passa a não somar o total de tasks. Deletar um usuário destrói trabalho registrado que poderia apenas ser desatribuído: **perda de dados irreversível** disparada por uma rota anônima (ver AP-06).
- **Recomendação:** decidir a semântica por relação e declará-la no model (`ondelete='SET NULL'` para ambas, dado que as colunas são nulláveis), ligar `PRAGMA foreign_keys=ON` no connect do SQLite, e mover a decisão para a camada de service — não repetir laços de deleção à mão nos handlers.

---

### 🟡 MEDIUM

#### [AP-10] Regra de negócio inteira dentro dos handlers HTTP (fat controllers) — `routes/task_routes.py:85-154,273-299`, `routes/report_routes.py:12-101`, `routes/user_routes.py:42-90`
- **O que:** os três blueprints concentram validação, regra de domínio, consultas ao ORM e commit no mesmo handler. `create_task` (`task_routes.py:85-154`) valida título, status e prioridade, checa existência de FKs, faz parsing de data, serializa tags e commita — 70 linhas. `summary_report` (`report_routes.py:12-101`) é um handler de 90 linhas com 15 consultas e toda a agregação inline. `task_stats` (`task_routes.py:273-299`) calcula estatística de domínio na rota. **A pasta `services/` existe e não é importada por nenhum arquivo do projeto** — não há camada de service nem de repositório; as rotas conhecem o ORM diretamente.
- **Impacto:** nada disso é testável ou reutilizável fora de um request HTTP; a mesma regra precisa ser reescrita para um comando CLI, um job agendado ou outro endpoint (e já foi — ver AP-12). É a dívida central que caracteriza o nível N1 deste projeto.
- **Recomendação:** `controllers/` só traduzem HTTP↔domínio (parse de request, código de status); regra e orquestração em `services/`; acesso a dados em `repositories/`. Extrair `TaskService`, `UserService`, `CategoryService` e `ReportService`, com os controllers passando a ter poucas linhas cada.

#### [AP-13] Consultas em laço (N+1) em quatro endpoints — `routes/task_routes.py:42,51`, `routes/report_routes.py:56,163`, `routes/user_routes.py:22`
- **O que:**
  - `GET /tasks` — dentro do laço sobre todas as tasks (`task_routes.py:16`), faz `User.query.get()` (`:42`) e `Category.query.get()` (`:51`): **2 queries por task**, mais a inicial.
  - `GET /reports/summary` — `Task.query.filter_by(user_id=u.id).all()` dentro do laço sobre usuários (`report_routes.py:55-56`); o handler já dispara ~15 `count()` separados antes disso (`:15-51`), vários dos quais seriam um único `GROUP BY`.
  - `GET /categories` — `Task.query.filter_by(category_id=c.id).count()` por categoria (`report_routes.py:161-163`).
  - `GET /users` — `len(u.tasks)` (`user_routes.py:22`) carrega a coleção inteira de tasks de cada usuário só para contá-la (o `backref` de `models/task.py:20` é lazy), no laço de `:14`.
- **Impacto:** latência linear no volume de dados. Com 500 tasks, `GET /tasks` executa ~1001 queries; `GET /users` materializa todas as tasks da base em memória para produzir números. Sob carga, esses endpoints esgotam o pool de conexões.
- **Recomendação:** `joinedload`/`selectinload` para as relações em `GET /tasks`; `GROUP BY` com `func.count()` para os contadores de `/categories`, `/reports/summary` e `task_stats`; `column_property` ou subquery de contagem para `task_count` em `GET /users`.

#### [AP-12] Lógica duplicada em cinco eixos, com o código canônico já existente e morto — `models/task.py:23-60`, `routes/*.py`
- **O que:** cada regra aparece em vários lugares, sempre reescrita:
  - **Cálculo de "overdue"** — o mesmo aninhamento de 3 `if` copiado em **6 lugares**: `task_routes.py:30-39`, `task_routes.py:71-80`, `task_routes.py:283-287`, `user_routes.py:171-180`, `report_routes.py:33-37`, `report_routes.py:132-135`. E `Task.is_overdue()` (`models/task.py:50-60`) implementa exatamente isso e **nunca é chamado**.
  - **Serialização de task → dict** — `task_routes.py:17-28` remonta à mão campo por campo o que `Task.to_dict()` (`models/task.py:23-36`) já faz, e `user_routes.py:162-169` faz uma terceira versão parcial.
  - **Whitelist de status** — `['pending', 'in_progress', 'done', 'cancelled']` literal em `task_routes.py:110`, `task_routes.py:177`, `models/task.py:39`, `utils/helpers.py:75` e `utils/helpers.py:110`.
  - **Whitelist de roles** — `['user', 'admin', 'manager']` em `user_routes.py:71`, `user_routes.py:120`, `utils/helpers.py:111`.
  - **Regex de e-mail** — idêntica em `user_routes.py:61`, `user_routes.py:106` e `utils/helpers.py:21` (`validate_email`, nunca usada).
  - **`completion_rate`** — a fórmula `round((x / total) * 100, 2) if total > 0 else 0` em `task_routes.py:296`, `report_routes.py:67` e `report_routes.py:151`, enquanto `calculate_percentage` (`helpers.py:14-17`) é **importada em `report_routes.py:7` e nunca chamada**.
- **Impacto:** mudar a definição de "atrasada" (por exemplo, para considerar fuso ou um novo status) exige seis edições coerentes; adicionar um status exige cinco. A divergência é silenciosa — nenhum teste cobre isso. `Task.validate_status()` e `validate_priority()` (`models/task.py:38-48`) também não são chamados por ninguém, então as validações reais nas rotas podem divergir das do model sem aviso.
- **Recomendação:** um único ponto de verdade por regra: `Enum` para status/role/prioridade, `Task.is_overdue()` como o cálculo canônico (e usado), serializer único por recurso, e as funções de `helpers.py` efetivamente chamadas ou deletadas.

#### [AP-14] `except:` nu em 11 pontos, engolindo qualquer erro — `routes/task_routes.py:62,137,204,236`, `routes/user_routes.py:130,149`, `routes/report_routes.py:186,207,221`, `utils/helpers.py:46,48,88`
- **O que:** blocos `except:` sem tipo. O mais grave é `task_routes.py:62`: um `try` envolvendo o corpo **inteiro** de `GET /tasks` (`:13-61`) e devolvendo `{'error': 'Erro interno'}, 500` para qualquer exceção — inclusive um `AttributeError` num campo novo ou um bug de serialização. `helpers.py:44-50` tem `try/except` aninhados nus que transformam qualquer falha de parsing em `None` silencioso.
- **Impacto:** bugs ficam invisíveis: a API responde 500 genérico sem nada nos logs (não há logger — ver AP-15), e a causa raiz é perdida. `except:` nu também captura `KeyboardInterrupt` e `SystemExit`, atrapalhando shutdown. Fora dos `try`, o oposto acontece: erros vazam como 500 do Flask com stack trace, porque `debug=True` (AP-07).
- **Recomendação:** errorhandler centralizado no app (`@app.errorhandler`) traduzindo exceções de domínio em status HTTP; nos handlers, capturar apenas o tipo esperado (`SQLAlchemyError`, `ValueError`) e sempre logar com `exc_info=True` antes de responder mensagem genérica.

#### Entrada não validada derruba dois endpoints com 500 — `routes/task_routes.py:113,182,261,264`
- **O que:** `if priority < 1 or priority > 5` (`task_routes.py:113`, e igual em `:182`) compara o valor cru do JSON com inteiros. Um `{"priority": "alta"}` levanta `TypeError: '<' not supported between 'str' and 'int'` **antes** de qualquer `try`. Em `GET /tasks/search`, `int(priority)` (`:261`) e `int(user_id)` (`:264`) recebem query string arbitrária: `?priority=abc` levanta `ValueError` num handler que não tem tratamento de erro nenhum. Ironicamente, `helpers.py:82-89` tem exatamente a coerção com `int()` protegida que resolveria isso — e não é usada.
- **Impacto:** 500 (com stack trace, dado o `debug=True`) onde a resposta correta é 400. Cliente não distingue "meu request está errado" de "o servidor caiu".
- **Recomendação:** validação de schema na borda (marshmallow, já em `requirements.txt:4`) com coerção de tipo e mensagens de erro por campo, antes de a regra de negócio ser executada.

#### CRUD de categorias vive no blueprint de relatórios — `routes/report_routes.py:157-223`
- **O que:** `GET/POST /categories` e `PUT/DELETE /categories/<id>` (`report_routes.py:157-223`, 67 linhas) estão registrados no `report_bp` (`report_routes.py:10`), junto de `/reports/summary` e `/reports/user/<id>`. Não existe `routes/category_routes.py`, apesar de `Category` ser um dos três models.
- **Impacto:** a fronteira dos blueprints não corresponde ao domínio — quem procura o CRUD de categoria não o encontra onde deveria, e o arquivo de relatórios cresce por um motivo que não é relatório. Esse tipo de agrupamento acidental é o que faz um projeto N1 virar N0 com o tempo.
- **Recomendação:** `category_controller` próprio, registrado com seu próprio prefixo; `report_bp` mantém apenas rotas `/reports/*`. O contrato das rotas (caminhos e métodos) não muda.

#### Ausência de app factory / composition root — `app.py:9-31`
- **O que:** `app = Flask(__name__)` no escopo de módulo (`app.py:9`), config atribuída em seguida (`:11-13`), extensões inicializadas (`:15-16`), blueprints registrados (`:18-20`), duas rotas definidas no próprio arquivo (`:22-28`) e `db.create_all()` executado (`:30-31`) — tudo como efeito de importar o módulo. `db` é um singleton global em `database.py:3`.
- **Impacto:** impossível instanciar a app com config alternativa (teste, staging) sem variáveis de ambiente globais; impossível ter duas configurações no mesmo processo; qualquer import de `app` (como `seed.py:2`) paga o custo e os efeitos colaterais de construir a aplicação e tocar o banco. É estado global mutável no sentido do AP-11, com o agravante de ser o objeto central.
- **Recomendação:** `create_app(config)` como factory, `wsgi.py` como entry point de produção, e `app.run()` restrito ao bloco `__main__` de um script de dev. As rotas `/` e `/health` vão para um blueprint próprio.

#### Endpoints de listagem sem paginação nem limite — `routes/task_routes.py:14,266`, `routes/user_routes.py:12`, `routes/report_routes.py:30,159`
- **O que:** `Task.query.all()` (`task_routes.py:14`), o `.all()` da busca (`task_routes.py:266`), `User.query.all()` (`user_routes.py:12`), `Task.query.all()` no relatório (`report_routes.py:30`) e `Category.query.all()` (`report_routes.py:159`) — nenhum aceita `limit`/`offset` ou impõe teto. `GET /reports/summary` ainda monta `overdue_list` sem limite (`report_routes.py:38-43`).
- **Impacto:** o tamanho da resposta e o consumo de memória crescem sem limite com a base; um `GET /tasks` numa base grande materializa tudo em Python (e dispara o N+1 do AP-13 em cima disso). É um DoS acidental a um request de distância. O próprio seed registra isso como dívida conhecida (`seed.py:70`: "Endpoints retornam todos os registros").
- **Recomendação:** paginação por `limit`/`offset` (ou cursor) com default e máximo definidos em config, retornando metadados de total e página. Aplicar na camada de repositório, uma vez, para todos os recursos.

#### Serviço de notificação inteiro morto, com estado global mutável — `services/notification_service.py:1-49` [AP-11]
- **O que:** `NotificationService` não é importado por nenhum arquivo do projeto (`services/__init__.py` está vazio). Dentro dele, `self.notifications = []` (`:6`) acumula notificações em memória (`:31-36`) e `get_notifications()` (`:43-48`) varre a lista com laço linear. `send_email` (`:12-25`) abre conexão SMTP síncrona sem timeout no meio do que seria um request.
- **Impacto:** como código morto, é uma armadilha: o próximo dev vai ligá-lo, e aí herda três problemas de uma vez — credenciais hardcoded (AP-02), estado que se perde no restart e não é compartilhado entre workers, e um `smtplib.SMTP()` sem timeout bloqueando o handler HTTP indefinidamente se o servidor de e-mail não responder.
- **Recomendação:** decidir: deletar, ou implementar de verdade com config por env, fila/worker assíncrono para o envio, timeout explícito e persistência das notificações em tabela. Não deixar no meio.

#### `PUT /categories/<id>` sem verificação de corpo nulo — `routes/report_routes.py:196-197`
- **O que:** `data = request.get_json()` seguido direto de `if 'name' in data` (`report_routes.py:196-197`). É o único handler de escrita do projeto sem a guarda `if not data: return 400` que os outros têm (`task_routes.py:89`, `task_routes.py:163`, `user_routes.py:46`, `report_routes.py:170`).
- **Impacto:** um corpo `null` (JSON válido) faz `data` ser `None` e `'name' in None` levanta `TypeError` → 500 em vez de 400.
- **Recomendação:** a guarda não deveria ser repetida em cada handler — centralizar a extração e validação do corpo em um decorator/schema aplicado a todas as rotas de escrita, o que elimina a classe inteira de inconsistência.

---

### 🔵 LOW

#### [AP-15] `print()` como logging, em 13 pontos — `routes/task_routes.py:149,153,219,234`, `routes/user_routes.py:83,89,147`, `services/notification_service.py:21,24`, `utils/helpers.py:39,41`, `seed.py:93-96`
- **O que:** rastreio de execução e de erro via `print` — inclusive os dois únicos lugares que registram exceção: `print(f"Erro ao criar task: {str(e)}")` (`task_routes.py:153`) e `print(f"ERRO: {str(e)}")` (`user_routes.py:89`). `helpers.py:36-41` define um `log_action()` que é `print` com timestamp, e não é usado por ninguém. Nenhum módulo importa `logging`.
- **Impacto:** sem nível, sem timestamp estruturado, sem destino configurável, sem contexto de request. Em produção o stdout se perde ou vira ruído indiferenciável, e a mensagem de exceção (`str(e)`) chega sem traceback — não dá para diagnosticar o 500 que o usuário viu.
- **Recomendação:** `logging` configurado no factory da app (nível por env, formato JSON em produção), com `logger.exception()` nos blocos de erro para preservar o traceback.

#### [AP-16] CORS liberado para qualquer origem — `app.py:15`
- **O que:** `CORS(app)` sem argumentos (`app.py:15`) — equivale a `Access-Control-Allow-Origin: *` em todas as rotas, incluindo `POST /login` e os `DELETE`.
- **Impacto:** qualquer site consegue chamar a API a partir do navegador da vítima. Hoje o impacto é limitado porque não há cookie de sessão nem autenticação alguma (o que é um problema pior, não um consolo — ver AP-06); no momento em que a autenticação por header for adicionada, esse `*` passa a ser o vetor para exfiltração cross-origin.
- **Recomendação:** allowlist explícita de origens, vinda de config/env, e restringir métodos e headers permitidos.

#### Código morto em `utils/helpers.py` — `utils/helpers.py:19-34,36-41,52-55,57-108,110-116`
- **O que:** das 9 funções do módulo, **7 não são chamadas em lugar nenhum**: `validate_email` (`:19`), `sanitize_string` (`:25`), `generate_id` (`:31`), `log_action` (`:36`), `is_valid_color` (`:52`) e `process_task_data` (`:57-108`, 52 linhas — uma camada de validação completa, nunca conectada). O bloco de constantes `VALID_STATUSES`…`DEFAULT_COLOR` (`:110-116`) também não é importado por ninguém. As duas funções vivas (`format_date`, `calculate_percentage`) são **importadas em `report_routes.py:7` e nunca chamadas**, então na prática o módulo inteiro é inerte. `generate_id` faz `import uuid` dentro do corpo (`:33`).
- **Impacto:** 116 linhas que parecem ser a camada de utilidades do projeto e não são — quem lê acredita que a validação passa por `process_task_data` quando ela está duplicada à mão nas rotas (AP-12). Também mascara o fato de que as constantes já existiam quando alguém colou o literal `['pending', ...]` pela quinta vez.
- **Recomendação:** deletar o que não serve; o que serve (`process_task_data`, as constantes) deve ser promovido à camada de validação real e efetivamente usado. Código morto em `utils/` é o sintoma clássico do nível N1.

#### Imports não utilizados em 6 arquivos — `app.py:7`, `routes/task_routes.py:7`, `routes/user_routes.py:6`, `routes/report_routes.py:7-8`, `models/task.py:3`, `utils/helpers.py:3-7`
- **O que:** `import os, sys, json, datetime` em `app.py:7` (só `datetime` é usado, em `:24`); `import json, os, sys, time` em `task_routes.py:7` (nenhum usado); `import hashlib, json, re` em `user_routes.py:6` (`hashlib` e `json` não usados — o hash acontece no model); `from utils.helpers import format_date, calculate_percentage` + `import json` em `report_routes.py:7-8` (nenhum usado); `import json` em `models/task.py:3`; `import os, json, sys, math, hashlib` em `helpers.py:3-7` (nenhum usado). Em `requirements.txt`, `marshmallow` (`:4`), `requests` (`:5`) e `python-dotenv` (`:6`) são declaradas e nunca importadas.
- **Impacto:** ruído que esconde as dependências reais de cada módulo e inflaciona a superfície declarada do projeto. `python-dotenv` no `requirements.txt` sugere falsamente que a config vem de `.env` (não vem — ver AP-02).
- **Recomendação:** remover; adotar linter (`ruff`/`flake8`) no CI para impedir a reincidência. Reavaliar as três dependências: `marshmallow` deveria ser usada (validação), `requests` provavelmente removida.

#### Ausência de `.gitignore` e `.env.example` — raiz do projeto
- **O que:** a raiz não tem `.gitignore` nem `.env.example`. O `README.md:13` instrui rodar `python seed.py`, que gera `tasks.db`; `__pycache__/` também aparece a cada execução.
- **Impacto:** o banco SQLite com os hashes de senha e os bytecodes compilados entram no repositório no próximo `git add .`. Sem `.env.example`, não há registro de quais variáveis a aplicação precisa — o que torna a correção do AP-02 (externalizar segredos) mais difícil de adotar.
- **Recomendação:** `.gitignore` com `__pycache__/`, `*.db`, `.env`, `instance/`, `.venv/`; `.env.example` versionado listando cada variável com valor de exemplo inócuo.

---

## APIs deprecated

| API | Local | Substituir por |
|---|---|---|
| `datetime.utcnow()` — deprecada no Python 3.12 (o host roda 3.12.10, então **já emite `DeprecationWarning`**) | `models/task.py:15,16,52`; `models/user.py:14`; `routes/task_routes.py:31,72,215,285`; `routes/user_routes.py:172`; `routes/report_routes.py:35,42,45,71,133`; `utils/helpers.py:38`; `seed.py:66,67,69,70,74` | `datetime.now(datetime.UTC)` — retorna datetime *aware*. Requer também decidir o armazenamento: as colunas são `DateTime` sem timezone (`models/task.py:15-17`), e hoje todo o código compara naive com naive por coincidência. |
| `Query.get()` — legado no SQLAlchemy 2.0 (emite `LegacyAPIWarning`); `flask-sqlalchemy==3.1.1` exige SQLAlchemy ≥ 2.0 | `routes/task_routes.py:67,117,122,158,188,195,227`; `routes/user_routes.py:29,94,136,155`; `routes/report_routes.py:105,192,213` | `db.session.get(Model, pk)` |
| `Model.query` — interface legada do SQLAlchemy 1.x, mantida por compatibilidade no Flask-SQLAlchemy 3.x | em todos os arquivos de `routes/` (~40 ocorrências) e `seed.py:11-13,94-96` | `db.session.execute(db.select(Model)...)` — o estilo 2.0. A troca é boa oportunidade para centralizar o acesso a dados em `repositories/`. |
| `hashlib.md5` para senha | `models/user.py:29,32` | `bcrypt`/`argon2` (ver AP-04) — não é só "deprecated", é inadequado por projeto: MD5 é rápido de propósito. |

`app.py:12` também merece nota: `SQLALCHEMY_TRACK_MODIFICATIONS = False` é um resquício do Flask-SQLAlchemy 2.x, onde o default era `True` e gerava warning. Na 3.x o rastreamento já vem desligado, então a linha é inofensiva mas redundante.

---

## Recomendação de refatoração

Ordem sugerida para a Fase 3 (fecha risco antes de organizar):

1. **CRITICAL de segurança.** Remover `password` de `to_dict()` e introduzir serializers por recurso; substituir MD5 por bcrypt/argon2 atrás de um módulo `security/`; externalizar `SECRET_KEY` e credenciais SMTP para um módulo `config/` lido do ambiente (+ `.gitignore`/`.env.example`); implementar autenticação e autorização por papel, bloqueando a escalada de privilégio em `PUT /users/<id>`.
2. **HIGH.** `debug` e `host` por env var com defaults seguros; token JWT assinado com expiração no lugar do `fake-jwt-token-`; política de senha e verificação da senha atual na troca; migrations (Alembic) substituindo `db.create_all()` no import; `ondelete` declarado nas FKs + `PRAGMA foreign_keys=ON`, com a política de deleção movida para service.
3. **Reestruturação em camadas MVC (MEDIUM arquiteturais).** `create_app()` factory + `wsgi.py`; `controllers/` finos; `services/` com a regra de negócio (incluindo `ReportService` para o handler de 90 linhas); `repositories/` encapsulando o ORM e resolvendo os quatro N+1 com eager loading e `GROUP BY`; `schemas/` de validação com marshmallow na borda; paginação na camada de repositório; `category_controller` separado do de relatórios; errorhandler central substituindo os 11 `except:` nus; um ponto de verdade por regra (Enums, `Task.is_overdue()` usado de fato).
4. **LOW.** `logging` estruturado no lugar dos `print`; CORS com allowlist; expurgo do código morto de `utils/helpers.py` e decisão sobre `NotificationService`; limpeza de imports e das dependências não usadas.

Restrição a preservar durante toda a Fase 3: **os contratos dos endpoints atuais** — mesmos caminhos, métodos e formato de resposta. Exceção deliberada e necessária: o campo `password` sai das respostas de `/users/*` e `/login` (é o próprio AP-03), e respostas que hoje são 500 por entrada inválida passam a ser 400 (correção de bug, não mudança de contrato).

> **Fase 2 completa. Prosseguir com a refatoração (Fase 3)? [y/n]**

---

## Adendo — Fase 3 (Refatoração): mudanças intencionais de contrato

Registrado após a confirmação humana, conforme `mvc-guidelines.md` ("se um endpoint precisar mudar de contrato, registre no relatório como mudança intencional"). As duas primeiras já estavam previstas acima; as demais decorrem diretamente da correção dos achados.

1. `password` removido das respostas de `/users*` e `/login` (AP-03) — previsto.
2. 500 por entrada inválida → 400 (`priority` não numérico, `?priority=abc`, corpo `null` em `PUT /categories/<id>`) — previsto.
3. `POST /login`: `token` passa a ser JWT HS256 assinado, com `exp` (mesmo campo, continua string).
4. AP-06 (escalada de privilégio): `PUT /users/<id>` com `role`/`active` exige token de admin; com `password` exige token do próprio usuário + `current_password`, ou admin; `POST /users` com `role` ≠ `user` exige admin. Demais campos/rotas sem mudança. As rotas destrutivas restantes (`DELETE /users/<id>`, `DELETE /tasks/<id>`) e os relatórios **permanecem sem autenticação** para respeitar a restrição de contrato — risco residual de nível HIGH (AP-06 padrão), registrado no README como próximo passo.
5. Senha mínima de 4 → 12 caracteres (`PASSWORD_MIN_LENGTH`).
6. `DELETE /users/<id>` e `DELETE /categories/<id>` desassociam as tasks (`ON DELETE SET NULL`) em vez de apagá-las / deixá-las órfãs. Corpo e status de resposta inalterados.
7. CORS restrito à allowlist `CORS_ORIGINS` (vazio = sem headers CORS).
8. Corpo ausente ou não-JSON em rotas de escrita → 400 `Dados inválidos` (antes 415 HTML/500). A mensagem de data inválida em `PUT /tasks/<id>` foi unificada com a do `POST` (`Formato de data inválido. Use YYYY-MM-DD`).
