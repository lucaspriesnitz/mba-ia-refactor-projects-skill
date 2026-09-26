# code-smells-project

API de E-commerce em Python/Flask, reorganizada em **MVC em camadas** pela skill
`refactor-arch`. Os endpoints originais continuam os mesmos; o que mudou é a
estrutura interna e o fechamento dos anti-patterns apontados na auditoria
(`reports/audit-project-1.md`).

## Como rodar

```bash
pip install -r requirements.txt

cp .env.example .env        # preencha SECRET_KEY -- a app NÃO sobe sem ela
python -c "import secrets; print(secrets.token_urlsafe(48))"

python app.py
```

A aplicação sobe em `http://127.0.0.1:5000` (antes era `0.0.0.0`; agora o bind
vem de `HOST`). O banco SQLite é criado no primeiro boot, com produtos e usuários
de exemplo — as credenciais de demonstração seguem `admin123` / `123456` /
`senha123`, mas agora ficam **hasheadas** no banco.

Em produção, use um servidor WSGI apontando para `wsgi:app`, não o `app.run`:

```bash
waitress-serve --port=5000 wsgi:app
```

### Configuração

Tudo vem do ambiente (`src/config/settings.py`); nada de segredo no código. Veja
`.env.example` para a lista completa. `SECRET_KEY` é obrigatória e a ausência
dela **falha no boot**, de propósito. Dois defaults mudaram para o lado seguro:
`FLASK_DEBUG=false` e CORS fechado enquanto `CORS_ORIGINS` não for preenchido.

## Estrutura

```
app.py                      entry point (composition root)
wsgi.py                     alvo para servidor WSGI de produção
src/
├── config/                 leitura de ambiente (segredos, flags, limites)
├── routers/                registro rota -> controller (blueprints)
├── controllers/            HTTP <-> service: parse, chamada, status code
├── services/               regra de negócio, orquestração, transação
├── repositories/           acesso a dados, 100% parametrizado
├── models/                 constantes de domínio, erros, serializers, validadores
├── middlewares/            auth, error handler central, logging
├── database/               conexão, escopo de requisição, schema, unit of work
└── container.py            grafo de dependências
```

Dependência de fora para dentro: controller → service → repository → banco.
Nenhuma camada de baixo importa de cima, e SQL só existe em `repositories/`.

## Antes → depois

### Estrutura

| Antes | Depois |
|---|---|
| 4 arquivos na raiz, 784 linhas, com nomes de camada mas responsabilidades vazando | 8 camadas explícitas em `src/`, cada uma com uma responsabilidade |
| `models.py` acumulava repositório + regra de negócio + serialização (315 linhas) | `repositories/` (SQL) e `services/` (regra pura, testável sem banco) |
| `controllers.py` fazia validação, orquestração e efeitos colaterais | controllers só traduzem HTTP; validadores e services separados |
| `app.py` definia rotas de negócio com SQL inline | `app.py` só compõe e sobe; rotas em blueprints |
| 16 `add_url_rule` num módulo | um blueprint por recurso, registrados em `routers/` |
| nenhum módulo de config | `config/settings.py` como fonte única, lendo do ambiente |

### Segurança (CRITICAL/HIGH da auditoria)

| Achado | Antes | Depois |
|---|---|---|
| AP-01 SQL injection | ~25 pontos de SQL concatenado com input do cliente | toda query parametrizada (`?` + tupla); nos filtros dinâmicos, fragmentos com placeholder e lista de params paralela |
| AP-01 bypass de login | `WHERE email = '...' AND senha = '...'` — `admin@loja.com' -- ` logava como admin | busca só pelo e-mail; senha verificada em código contra o hash |
| AP-05 RCE no banco | `POST /admin/query` executava SQL do cliente | rota preservada respondendo **403**, sem ler nem executar nada (ver nota abaixo) |
| AP-02 segredo hardcoded | `SECRET_KEY = "minha-chave-super-secreta-123"` no fonte | vem de `SECRET_KEY` no ambiente; boot falha se faltar; `.env` no `.gitignore` |
| AP-02 segredo vazado | `GET /health` devolvia `secret_key`, `db_path`, `debug`, `ambiente` | health devolve só `status`, `database`, `counts`, `versao` |
| AP-03 senha em texto puro | senha crua no banco e comparada dentro do SQL | hash pbkdf2-sha256 com salt por usuário (`werkzeug.security`), inclusive no seed |
| AP-03 senha na resposta | `GET /usuarios` e `/usuarios/<id>` devolviam `senha` de todos | serializers públicos não conhecem o campo; colunas projetadas explicitamente |
| AP-06 rota destrutiva aberta | `POST /admin/reset-db` apagava tudo para qualquer `curl` | exige token com papel `admin` **e** `ADMIN_RESET_HABILITADO=true` (default off) |
| AP-06 sem credencial | login validava mas não emitia nada | login emite token assinado (`itsdangerous`); decorators `requer_autenticacao` / `requer_papel` |
| AP-07 DEBUG fixo | `DEBUG = True` e `app.run(debug=True)` | vem de `FLASK_DEBUG` (default `false`); `wsgi.py` para produção |
| AP-16 CORS aberto | `CORS(app)` = `*` em todas as rotas | allowlist explícita de `CORS_ORIGINS`; sem valor, nenhum header CORS |
| Pedido sem transação | validação e débito em laços separados, sem rollback | transação única com rollback + débito atômico (`WHERE ... AND estoque >= ?` e checagem de `rowcount`) |

### Arquitetura e qualidade (MEDIUM/LOW)

| Achado | Antes | Depois |
|---|---|---|
| AP-08/AP-11 conexão global | singleton de módulo com `check_same_thread=False` | conexão por requisição (`flask.g` + teardown), injetada nas repositories |
| AP-13 N+1 (N+2) | `GET /pedidos` com 100 pedidos de 5 itens = 601 queries | 2 queries de custo fixo (página de ids + um JOIN) |
| AP-12 duplicação | serializer de produto 3x, de usuário 2x, listagem de pedidos duplicada, validação colada em criar/atualizar | um serializer e um validador por entidade; listagem parametrizada pelo filtro |
| AP-14 exceção vazada | 17x `except Exception as e: jsonify({"erro": str(e)}), 500` | zero `try/except` nos controllers; erros de domínio tipados + `errorhandler` central que loga stack trace e responde mensagem genérica |
| AP-15 `print` como log | 17 `print`, incluindo e-mail do usuário no login | `logging` configurado centralmente, com nível por ambiente e sem PII |
| Números mágicos | faixas de desconto, categorias e status literais nos handlers | `models/constants.py` |
| SQL no controller | `health_check` e as rotas admin abriam cursor direto | todo SQL em `repositories/` |
| Validação sem tipo | `preco: "abc"` → 500 com traceback do Python | checagem de tipo antes da comparação → 400 com o campo |
| `preco_max=0` ignorado | `if preco_min:` descartava o zero | `is not None` no controller e na query |
| E-mail sem unicidade | duplicatas permitidas; login pegava conta arbitrária | `UNIQUE` no schema + checagem no service → 409 |
| Código morto | `import sqlite3`/`os` não usados; coluna `ativo` nunca filtrada | imports removidos; soft delete implementado de fato (todas as leituras filtram `ativo = 1`) |
| Contrato de erro inconsistente | uns erros com `sucesso: False`, outros sem | envelope único em `controllers/envelope.py`, usado também pelo error handler |
| Sem paginação | `SELECT *` sem limite | `?limit=&offset=` opcional com teto configurável |
| Regra não implementada | `print("... Devolver estoque.")` no cancelamento | devolução de estoque executada de verdade no service |

## Mudanças intencionais de resposta

Homologadas antes da Fase 3 (registro em `reports/audit-project-1.md`). Rota,
método e envelope permanecem; o que muda é o corpo:

1. `GET /usuarios` e `GET /usuarios/<id>` **não trazem mais o campo `senha`**.
2. `GET /health` **não traz mais** `secret_key`, `db_path`, `debug` e `ambiente`.
3. Erros 500 respondem mensagem genérica em vez de `str(e)`.
4. `POST /admin/query` responde **403** (detalhe abaixo).

Decorrências dos achados corrigidos, no mesmo espírito: `POST /usuarios` com
e-mail repetido agora é 409 (era 201); tipos inválidos viram 400 em vez de 500;
`PUT /produtos/<id>` aplica as mesmas validações do `POST` (antes o PUT
contornava tamanho de nome e categoria); `POST /login` ganha o campo `token` em
`dados` (aditivo); e o `sucesso: False` passa a estar presente em **todos** os
erros, inclusive nos que antes o omitiam.

### Por que `POST /admin/query` não foi deletada

A auditoria recomendou **remover** a rota (AP-05, CRITICAL): ela lia
`dados["sql"]` e executava a string vinda do cliente, com `commit` para
não-SELECT — controle total do banco por qualquer pessoa na rede.

O dono do projeto decidiu, no fim da Fase 2, **manter a rota registrada
respondendo 403**, porque o checklist de validação exige que todos os endpoints
originais continuem respondendo. O CRITICAL está fechado do mesmo jeito: o
handler não lê o corpo, não interpreta e não executa nada — só levanta
`NaoAutorizado`. Não existe variável de ambiente que reabilite o comportamento
antigo. A justificativa também está no docstring de
`src/controllers/admin_controller.py`, junto do código.

## Próximo passo conhecido (fora do escopo homologado)

O mecanismo de autenticação está pronto e aplicado nas rotas administrativas,
mas as rotas de negócio (`GET /usuarios`, `GET /pedidos`,
`PUT /pedidos/<id>/status`, `DELETE /produtos/<id>`) **seguem abertas**: exigir
credencial nelas mudaria a resposta de endpoints que a Fase 2 homologou como
preservados, o que é uma decisão de contrato do dono. Para fechá-las, basta
aplicar `@requer_autenticacao` / `@requer_papel("admin")` nos controllers
correspondentes e acrescentar a checagem de propriedade por usuário nos pedidos.
