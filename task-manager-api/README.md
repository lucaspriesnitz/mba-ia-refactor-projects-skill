# task-manager-api

API de Task Manager em Python/Flask, reorganizada em **MVC em camadas** pela skill
`refactor-arch`. Os endpoints originais continuam os mesmos (rotas, métodos e
formato de resposta); o que mudou é a estrutura interna e o fechamento dos
anti-patterns apontados na auditoria (`reports/audit-project-3.md`).

## Como rodar

```bash
python -m venv .venv && .venv/Scripts/activate      # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env        # preencha SECRET_KEY (>= 32 chars) -- a app NÃO sobe sem ela
python -c "import secrets; print(secrets.token_urlsafe(48))"

python seed.py              # aplica as migrations e popula dados de demonstração
python app.py               # servidor de desenvolvimento
```

A aplicação sobe em `http://127.0.0.1:5000` (antes era `0.0.0.0`; agora o bind
vem de `HOST`). O banco SQLite fica em `instance/tasks.db`.

Credenciais de demonstração do seed (agora com hash scrypt e dentro da política
de senha de 12 caracteres):

| Usuário | Senha | Role |
|---|---|---|
| joao@email.com | `joao-demo-2026` | admin |
| maria@email.com | `maria-demo-2026` | user |
| pedro@email.com | `pedro-demo-2026` | manager |

### Schema e migrations

O schema não é mais criado no import da app (`db.create_all()`). Ele é versionado
em `migrations/` (Flask-Migrate/Alembic):

```bash
flask --app wsgi db upgrade                         # aplica migrations pendentes
flask --app wsgi db migrate -m "descricao"          # gera migration após mudar um model
```

Um `tasks.db` criado pela versão antiga não tem a coluna `password_hash` nem as
FKs com `ON DELETE SET NULL`: recrie-o com `python seed.py` (dados de demo) ou
migre os dados manualmente antes de apontar a app para ele.

### Produção

Use o servidor WSGI apontando para `wsgi:app`, não o `app.run`:

```bash
waitress-serve --host=0.0.0.0 --port=5000 wsgi:app
```

### Configuração

Tudo vem do ambiente (`src/config/settings.py`); veja `.env.example`. `SECRET_KEY`
é obrigatória e a ausência dela **falha no boot**, de propósito. Defaults do lado
seguro: `FLASK_DEBUG=false`, `HOST=127.0.0.1` e CORS fechado enquanto
`CORS_ORIGINS` não for preenchido.

## Estrutura

```
app.py                  entry point de desenvolvimento
wsgi.py                 alvo WSGI de produção e da CLI (flask --app wsgi ...)
seed.py                 dados de demonstração (aplica migrations antes)
migrations/             schema versionado (Alembic)
src/
├── app_factory.py      composition root: create_app()
├── container.py        grafo de dependências (repositories -> services)
├── config/             leitura de ambiente, fail-fast
├── routers/            registro dos blueprints
├── controllers/        HTTP <-> service: parse, chamada, status code
├── schemas/            validação de entrada e serialização de saída (marshmallow)
├── services/           regra de negócio, autorização, orquestração
├── repositories/       acesso a dados (SQLAlchemy 2.0), agregações, paginação
├── models/             entidades ORM + regras/constantes de domínio
├── security/           hash de senha e token JWT
├── middlewares/        auth (Bearer), error handler central, logging
├── database/           db, migrate, PRAGMA foreign_keys
└── errors.py           erros de domínio -> status HTTP
```

Dependência de fora para dentro: controller → service → repository → banco.
Controllers não conhecem o ORM; repositories não conhecem HTTP.

## Antes → depois

### Segurança (CRITICAL/HIGH)

| Achado | Antes | Depois |
|---|---|---|
| AP-03 hash na resposta | `User.to_dict()` devolvia `password` em 4 endpoints, incluindo `/login` | `UserSchema` com allowlist; o campo nem existe na saída. Coluna renomeada para `password_hash` |
| AP-04 MD5 sem salt | `hashlib.md5` no model | scrypt com salt (`werkzeug.security`) em `security/passwords.py`; hash MD5 legado é aceito uma vez no login e regravado |
| AP-02 segredos | `SECRET_KEY`, URI e credenciais SMTP no fonte | `config/` lendo do ambiente, fail-fast; `.env` no `.gitignore`, `.env.example` versionado. **Os valores antigos estão no histórico do Git: revogue a senha SMTP e não reutilize a `SECRET_KEY` antiga** |
| AP-06 escalada de privilégio | qualquer anônimo virava admin via `PUT /users/<id>` e trocava a senha de qualquer um | `role`/`active` só com token de admin; senha só pelo próprio usuário **com a senha atual**, ou por admin; `POST /users` com role ≠ `user` exige admin. Papel efetivo relido do banco |
| Token falso | `'fake-jwt-token-' + id` | JWT HS256 assinado com `SECRET_KEY`, com `exp` (`TOKEN_TTL_SECONDS`) |
| Senha fraca | mínimo 4 caracteres, troca sem senha atual | mínimo 12 (`PASSWORD_MIN_LENGTH`), troca exige `current_password` |
| AP-07 debug | `debug=True`, `0.0.0.0` fixos | `FLASK_DEBUG` (default `false`), `HOST` (default `127.0.0.1`), `wsgi.py` para produção |
| Schema no import | `db.create_all()` ao importar `app.py` | migrations Alembic, aplicadas por comando explícito |
| Integridade referencial | FKs sem `ondelete`, SQLite sem `PRAGMA foreign_keys`; deletar usuário apagava as tasks dele | `ON DELETE SET NULL` nas duas FKs + `PRAGMA foreign_keys=ON`; tasks são desassociadas, não apagadas |

### Arquitetura e qualidade (MEDIUM/LOW)

| Achado | Antes | Depois |
|---|---|---|
| AP-10 fat controllers | validação, regra, ORM e commit nos handlers; `services/` nunca importado | controllers de poucas linhas; `TaskService`, `UserService`, `AuthService`, `CategoryService`, `ReportService` |
| AP-13 N+1 | `GET /tasks` = 1+2N queries; `/users`, `/categories`, `/reports/summary` com query por linha | custo fixo: `/tasks` 2, `/users` 2, `/categories` 2, `/reports/summary` 10 — independente do volume |
| AP-12 duplicação | "atrasada" em 6 lugares, status em 5, roles em 3, regex de e-mail em 3, `completion_rate` em 3 | `Task.is_overdue` (hybrid: vale em Python e SQL), `models/domain.py` com enums e regras, um schema por recurso |
| AP-14 `except:` nu (11x) | erros engolidos sem log | zero `try/except` nos controllers; error handler central com `logger.exception` |
| Entrada não validada | `priority: "alta"` e `?priority=abc` → 500 | marshmallow na borda → 400 com a mensagem do campo |
| Categorias no blueprint de relatórios | CRUD em `report_routes.py` | `category_controller` próprio, mesmas rotas |
| App factory | app global criado no import | `create_app()` + `container.py` |
| Sem paginação | `.all()` em todas as listagens | `?limit=&offset=` opcionais, teto `LIST_MAX_LIMIT`, total em `X-Total-Count` |
| `PUT /categories` sem guarda de corpo | `null` → 500 | 400 `Dados inválidos` |
| AP-11 `NotificationService` morto | credenciais fixas, estado em memória, SMTP sem timeout, nunca usado | removido (ver "Próximos passos") |
| AP-15 `print` (13x) | sem nível nem traceback | `logging` central com nível por `LOG_LEVEL` |
| AP-16 CORS `*` | `CORS(app)` | allowlist `CORS_ORIGINS`, métodos e headers explícitos |
| Código morto / imports | `utils/helpers.py` inerte, imports não usados em 6 arquivos, `requests` sem uso | removidos; `marshmallow` e `python-dotenv` passaram a ser usados de fato |
| APIs deprecated | `datetime.utcnow()`, `Query.get()`, `Model.query` | `utc_now()` (`datetime.now(UTC)`), `db.session.get`, `select()` estilo 2.0 |

## Mudanças intencionais de contrato

Rotas, métodos e formato das respostas de sucesso foram preservados — conferido
comparando o JSON completo de todos os endpoints antes e depois. O que mudou, de
propósito:

1. `password` (hash) **saiu** das respostas de `GET/POST/PUT /users*` e `POST /login` (AP-03, homologado).
2. Entrada inválida que antes derrubava o handler com 500 agora é **400** (homologado).
3. `POST /login` → `token` agora é um JWT real (continua string, mesmo campo).
4. `PUT /users/<id>` com `role`, `active` ou `password`, e `POST /users` com `role` ≠ `user`, exigem `Authorization: Bearer <token>` (401/403 sem permissão).
5. Senha mínima passou de 4 para 12 caracteres (configurável).
6. `DELETE /users/<id>` desassocia as tasks do usuário em vez de apagá-las; `DELETE /categories/<id>` também desassocia (antes deixava referência pendurada).
7. CORS só para origens em `CORS_ORIGINS`.
8. Corpo ausente/não-JSON em rotas de escrita responde 400 `Dados inválidos` (antes 415 HTML ou 500).
9. **EXCEÇÃO CRÍTICA (AP-06):** rotas destrutivas e administrativas agora exigem autenticação. A correção do CRITICAL prevalece sobre preservar o contrato original da rota:
   - `DELETE /users/<id>` exige token do próprio usuário ou admin
   - `DELETE /tasks/<id>` exige token do dono da task ou admin
   - `DELETE /categories/<id>` exige token admin
   - `POST/PUT /tasks` exigem token (criação/edição de tasks)
   - `POST/PUT/DELETE /categories` exigem token admin
   - `GET /reports/*` exigem token admin
   - `GET /users`, `GET /users/<id>`, `GET /users/<id>/tasks` exigem token
   - `GET /tasks`, `GET /tasks/<id>`, `GET /tasks/search`, `GET /tasks/stats` exigem token
   - `PUT /users/<id>` exige token do próprio usuário ou admin

## Próximos passos (fora do escopo homologado)

- **Escopo por dono nas leituras.** Atualmente qualquer usuário autenticado vê todas as tasks e usuários. O modelo ideal é: admin vê tudo, demais veem apenas as próprias tasks.
- **Rate limiting / lockout em `POST /login`.**
- **Notificações:** se forem necessárias, reimplementar com config por env, fila assíncrona, timeout explícito e persistência em tabela.
- **Timezone:** datas continuam armazenadas como UTC *naive*; migrar para colunas com timezone exige migration de dados.
- **Suíte de testes automatizados.**
