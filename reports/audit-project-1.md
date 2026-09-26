```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python 3 (100% .py — 784 linhas de fonte)
Framework:     Flask 3.1.1 (+ Flask-CORS 5.0.1)
Dependencies:  flask==3.1.1, flask-cors==5.0.1, sqlite3 (stdlib)
Domain:        API REST de e-commerce/loja — CRUD de produtos, cadastro e
               login de usuários, criação e acompanhamento de pedidos com
               baixa de estoque, relatório de vendas, health check e rotas
               administrativas
Architecture:  N1 — separação parcial nominal. Existem arquivos com nomes de
               camada (app.py / controllers.py / models.py / database.py),
               mas as responsabilidades vazam: models.py acumula repositório
               + regra de negócio (cálculo de pedido, faixas de desconto),
               controllers.py concentra validação + orquestração + efeitos
               colaterais, app.py define rotas de negócio inline com SQL, e
               não existe camada de service nem módulo de config. Rotas
               registradas por add_url_rule num único módulo, sem blueprints.
Source files:  4 files analyzed (app.py 89, controllers.py 293,
               models.py 315, database.py 87)
DB tables:     4 tabelas (SQLite, arquivo loja.db, schema criado em runtime)
               · produtos (id, nome, descricao, preco, estoque, categoria,
                 ativo, criado_em)
               · usuarios (id, nome, email, senha, tipo, criado_em)
               · pedidos (id, usuario_id, status, total, criado_em)
               · itens_pedido (id, pedido_id, produto_id, quantidade,
                 preco_unitario)
               Sem chaves estrangeiras, sem índices, sem constraint UNIQUE.
================================
```

---

# Relatório de Auditoria Arquitetural — code-smells-project

- **Data:** 2026-09-24
- **Stack:** Python 3 / Flask 3.1.1 + Flask-CORS 5.0.1
- **Arquitetura de partida:** N1 — separação parcial nominal
- **Arquivos analisados:** 4 (`app.py`, `controllers.py`, `models.py`, `database.py`)

## Resumo por severidade

| Severidade | Qtd |
|---|---|
| CRITICAL | 7 |
| HIGH | 4 |
| MEDIUM | 10 |
| LOW | 6 |
| **Total** | **27** |

APIs deprecated detectadas: nenhuma chamada deprecated no código (detalhe na seção própria).

## Achados

### 🔴 CRITICAL

#### [AP-01] Injeção de SQL por concatenação de string — `models.py:28, 47-50, 57-61, 68, 92, 126-129, 140, 148-151, 155, 157-161, 163-166, 174, 188, 192, 220, 224, 279-281, 289-297`
- **O que:** praticamente **toda** query do projeto é montada com `+` sobre input do cliente, em vez de parâmetros vinculados. Exemplos: `"SELECT * FROM produtos WHERE id = " + str(id)` (`models.py:28`); `"INSERT INTO produtos ... VALUES ('" + nome + "', '" + descricao + "', ..."` (`models.py:47-50`); `"UPDATE pedidos SET status = '" + novo_status + "'"` (`models.py:279-281`); e o construtor dinâmico de busca que interpola `termo`, `categoria`, `preco_min` e `preco_max` direto vindos da querystring (`models.py:289-297`). O único ponto que usa placeholder `?` é o seed em `database.py:70-83`.
- **Impacto:** leitura, alteração e destruição arbitrária do banco a partir da rede. `GET /produtos/busca?categoria=x' UNION SELECT ...` exfiltra a tabela `usuarios` (com senhas em texto puro — ver AP-03). Um `nome` contendo aspas simples já quebra o `INSERT` mesmo sem intenção maliciosa.
- **Recomendação:** converter 100% das queries para parametrizadas (`WHERE id = ?`, `(id,)`); no builder de busca, acumular fragmentos com `?` e uma lista de params em paralelo. Nenhum input concatenado em string SQL.

#### [AP-01] Injeção de SQL no login → bypass total de autenticação — `models.py:109-111`
- **O que:** `"SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"` interpola credenciais cruas do corpo da requisição.
- **Impacto:** `POST /login` com `{"email": "admin@loja.com' -- ", "senha": "x"}` autentica como admin sem conhecer a senha. Este é o caminho de exploração mais barato de toda a aplicação.
- **Recomendação:** query parametrizada buscando **apenas pelo e-mail**, e verificação da senha em código contra o hash (`bcrypt.checkpw`) — a senha nunca deve participar da cláusula `WHERE`.

#### [AP-05] Endpoint que executa SQL arbitrário do cliente — `app.py:59-78`
- **O que:** `POST /admin/query` lê `dados.get("sql")` e executa direto (`cursor.execute(query)`, `app.py:69`), com `commit` para não-SELECT (`app.py:75`). Sem autenticação, sem allowlist.
- **Impacto:** controle total do banco por qualquer pessoa na rede — `DROP TABLE`, dump de credenciais, escalação para admin. Em SQLite ainda permite `ATTACH DATABASE` e escrita de arquivo no host.
- **Recomendação:** remover a rota. Operação administrativa é código versionado atrás de autenticação e autorização, nunca string vinda do cliente.

#### [AP-02] Segredo hardcoded no fonte — `app.py:7`
- **O que:** `app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"` literal, versionado no git. O caminho do banco também é fixo (`database.py:5`).
- **Impacto:** o segredo vive no histórico do repositório; rotacionar exige redeploy e reescrita de histórico. Qualquer pessoa com acesso ao repo forja sessões/tokens assinados.
- **Recomendação:** módulo `config/` lendo de `os.environ` com falha explícita no boot se a variável faltar; `.env` no `.gitignore`; rotacionar a chave atual, que deve ser considerada comprometida.

#### [AP-02] Segredo e configuração interna devolvidos por endpoint público — `controllers.py:285-289`
- **O que:** `GET /health` responde com `"db_path": "loja.db"`, `"debug": True`, `"ambiente": "producao"` e `"secret_key": "minha-chave-super-secreta-123"`.
- **Impacto:** vazamento da `SECRET_KEY` por uma rota não autenticada — o atacante nem precisa do repositório. Confirma também ao atacante que o modo debug está ativo.
- **Recomendação:** health check devolve apenas `status` e, no máximo, conectividade do banco. Nenhum valor de configuração, caminho de arquivo ou segredo no payload.

#### [AP-03] Senhas armazenadas e comparadas em texto puro — `database.py:31, 76-78`, `models.py:110, 126-129`
- **O que:** a coluna é `senha TEXT` crua (`database.py:31`); o seed grava `admin123`, `123456`, `senha123` (`database.py:76-78`); o cadastro insere o valor recebido sem transformação (`models.py:126-129`); e o login compara string contra string dentro do SQL (`models.py:110`). Não há import de nenhuma biblioteca de hash em todo o projeto.
- **Impacto:** qualquer vazamento do banco (trivial via AP-01/AP-05) expõe todas as credenciais em claro — e usuários reutilizam senha entre serviços.
- **Recomendação:** hash com `bcrypt` ou `argon2` (salt por usuário) na escrita; no login, buscar por e-mail e usar `checkpw`. Migrar os registros existentes forçando redefinição de senha.

#### [AP-03] Hash de senha devolvido nas respostas da API — `models.py:83, 99` → `controllers.py:132, 140`
- **O que:** os serializers de usuário incluem `"senha": row["senha"]` no dicionário retornado, e os handlers `GET /usuarios` e `GET /usuarios/<id>` devolvem esse dicionário integralmente. (`login_usuario` em `models.py:114-119` é o único que omite o campo.)
- **Impacto:** `curl http://host/usuarios` entrega nome, e-mail e senha em texto puro de **todos** os usuários, sem autenticação. É o vazamento mais direto do sistema.
- **Recomendação:** serializer único de usuário que nunca projeta o campo de credencial; selecionar colunas explicitamente em vez de `SELECT *`; e exigir autenticação/autorização na listagem.

### 🟠 HIGH

#### [AP-06] Rota destrutiva sem autenticação — `app.py:47-57`
- **O que:** `POST /admin/reset-db` apaga `itens_pedido`, `pedidos`, `produtos` e `usuarios` (`app.py:51-54`) e commita, sem qualquer checagem de identidade ou permissão.
- **Impacto:** um `curl -X POST` anônimo destrói a base inteira. Combinado com o CORS aberto (AP-16), qualquer site visitado pelo usuário pode disparar a chamada.
- **Recomendação:** remover do runtime de produção; se necessário em dev, protegê-la com autenticação + papel `admin` e habilitá-la só por variável de ambiente.

#### [AP-06] Ausência total de autenticação e autorização na API — `app.py:11-30`, `controllers.py:176-183`
- **O que:** nenhuma das 16 rotas registradas exige credencial. `login` valida e retorna os dados do usuário (`controllers.py:180`), mas **não emite token nem sessão** — não existe mecanismo para uma rota posterior saber quem está chamando. `PUT /pedidos/<id>/status`, `GET /pedidos`, `DELETE /produtos/<id>` e `GET /usuarios` são abertos.
- **Impacto:** qualquer cliente lê pedidos de terceiros, altera status de pedidos alheios, deleta o catálogo e lista a base de usuários. O login é decorativo.
- **Recomendação:** emitir credencial no login (JWT assinado com a `SECRET_KEY` vinda do ambiente, ou sessão server-side), decorator `@requer_auth` / `@requer_papel("admin")` aplicado nas rotas, e checagem de propriedade nos recursos por usuário.

#### [AP-07] `DEBUG` ligado fixo no código — `app.py:8, 88`
- **O que:** `app.config["DEBUG"] = True` e `app.run(..., debug=True)`, sem leitura de ambiente. `controllers.py:288` confirma o estado na resposta de `/health`.
- **Impacto:** stack traces com trechos de código expostos ao cliente e ativação do console interativo do Werkzeug — que, se o PIN for contornado, é execução remota de código. O `host="0.0.0.0"` (`app.py:88`) expõe isso em toda a interface de rede.
- **Recomendação:** `DEBUG` derivado de env var, default `False`; servidor de produção via WSGI (gunicorn/waitress), nunca `app.run`.

#### Criação de pedido sem transação nem rollback — `models.py:133-169`
- **O que:** a rotina valida estoque num primeiro laço (`models.py:139-146`), insere o pedido (`148-151`), e só então, num segundo laço, insere itens e debita estoque (`154-166`), com um único `commit` no fim (`168`). Não há `BEGIN`/`rollback` explícito, e o retorno antecipado de erro (`models.py:143, 145`) acontece **depois** de escritas já terem sido enfileiradas em chamadas anteriores na mesma conexão global.
- **Impacto:** uma exceção entre `models.py:151` e `168` (ex.: `produto` removido entre os dois laços, `models.py:155-160` → `TypeError` em `produto["preco"]`) deixa pedido e estoque inconsistentes. Pior: a validação de estoque e a baixa são separadas por dois laços sobre a mesma conexão global compartilhada (AP-08), então duas requisições concorrentes podem ambas passar na validação e levar o estoque a negativo.
- **Recomendação:** envolver a operação em transação explícita com `rollback` no `except`; fazer o débito com guarda atômica (`UPDATE produtos SET estoque = estoque - ? WHERE id = ? AND estoque >= ?`) e verificar `rowcount`; mover a orquestração para um `PedidoService`.

### 🟡 MEDIUM

#### [AP-08 / AP-11] Conexão de banco global mutável compartilhada entre threads — `database.py:4-5, 10`
- **O que:** `db_connection = None` em escopo de módulo (`database.py:4`), inicializada uma única vez e reusada por todas as requisições, com `check_same_thread=False` (`database.py:10`) desativando justamente a proteção do driver. O `db_path` também é global mutável (`database.py:5`). Cursores são criados ad hoc em três módulos distintos.
- **Impacto:** requisições concorrentes compartilham a mesma transação implícita — um `commit` de uma requisição publica escritas parciais de outra; `lastrowid` (`models.py:52, 131, 152`) pode retornar o id de uma inserção de outra thread. Impede escalar em múltiplos processos/threads de forma previsível.
- **Recomendação:** conexão por requisição (`flask.g` + `teardown_appcontext`) ou pool gerenciado, entregue às repositories por injeção de dependência em vez de import global.

#### [AP-09] God module: `models.py` acumula repositório, regra de negócio e serialização — `models.py:1-315`
- **O que:** 315 linhas com acesso a 4 tabelas, montagem de SQL, mapeamento `row → dict`, e regra de negócio pura no meio — o cálculo do total do pedido (`models.py:146`), as faixas de desconto (`models.py:256-262`) e o ticket médio (`models.py:272`).
- **Impacto:** impossível testar a regra de desconto sem um banco; qualquer mudança de schema toca lógica financeira no mesmo arquivo; nenhuma fronteira para substituir SQLite depois.
- **Recomendação:** quebrar em `repositories/` (um por agregado: produto, usuario, pedido) e `services/` (`PedidoService`, `RelatorioService`) com as regras puras, testáveis sem I/O.

#### [AP-10] Fat controller: validação, orquestração e efeitos colaterais no handler HTTP — `controllers.py:24-58, 64-96, 188-216, 237-252`
- **O que:** `criar_produto` faz 9 validações inline mais a lista de categorias válidas (`controllers.py:28-54`); `criar_pedido` dispara notificações de e-mail/SMS/push (`controllers.py:208-210`); `atualizar_status_pedido` decide efeitos de negócio por status — "devolver estoque" no cancelamento (`controllers.py:247-250`) — como `print`, sem executar nada.
- **Impacto:** a regra só existe dentro do ciclo HTTP: não é reutilizável por um job, uma CLI ou outro endpoint, e testá-la exige subir o Flask. O comentário de devolução de estoque revela regra **não implementada** mascarada como log.
- **Recomendação:** controller apenas traduz HTTP↔domínio (parse, chamada de service, status code). Validação em schema/validador dedicado; notificações num `NotificationService` injetado; efeito de cancelamento implementado de fato no service.

#### [AP-12] Duplicação de lógica (WET) — mapeamento e validação copiados — `models.py:12-21, 31-40, 304-313` · `models.py:79-86, 95-102` · `models.py:177-200, 209-232` · `controllers.py:28-54 vs 72-90`
- **O que:** o serializer de produto aparece idêntico 3 vezes; o de usuário 2 vezes; o bloco inteiro de montagem de pedido com itens está duplicado entre `get_pedidos_usuario` e `get_todos_pedidos` (~22 linhas cada, diferindo apenas no `WHERE`); e o bloco de validação de produto está colado em `criar_produto` e `atualizar_produto`.
- **Impacto:** divergência silenciosa já existe — `atualizar_produto` **não** valida tamanho de nome nem categoria (`controllers.py:81-90`), regras que `criar_produto` aplica (`controllers.py:47-54`). Ou seja, um `PUT` contorna validações que o `POST` impõe.
- **Recomendação:** um serializer por entidade, um validador por entidade compartilhado entre criar/atualizar, e uma função de listagem de pedidos parametrizada pelo filtro.

#### [AP-13] Query em laço (N+1, na verdade N+2) — `models.py:187-193, 219-225`
- **O que:** para cada pedido, uma query de itens (`models.py:188`); para cada item, uma query de nome do produto (`models.py:192`). Idem em `get_todos_pedidos` (`models.py:220, 224`). Há também consulta redundante dentro do laço de criação de pedido (`models.py:155`), relendo um produto já carregado em `models.py:140`.
- **Impacto:** `GET /pedidos` com 100 pedidos de 5 itens executa 601 queries. A latência cresce linearmente e derruba a rota sob carga.
- **Recomendação:** consulta única com `JOIN` entre `pedidos`, `itens_pedido` e `produtos`, agrupando em memória; ou carregamento em lote com `IN (...)`. No `criar_pedido`, reaproveitar o produto já lido no primeiro laço.

#### [AP-14] Detalhes internos de exceção devolvidos ao cliente — `controllers.py:12, 22, 62, 96, 109, 126, 134, 144, 165, 186, 220, 227, 235, 255, 262, 292` · `app.py:78`
- **O que:** 17 handlers seguem o mesmo padrão `except Exception as e: return jsonify({"erro": str(e)}), 500`, cada um com um `try` gigante envolvendo o corpo inteiro da função.
- **Impacto:** mensagens do SQLite (nomes de tabela, colunas, SQL malformado) vazam para o cliente, entregando o schema a quem está sondando injeção. Além disso, o `try` amplo mascara erros de programação como 500 genérico e torna o log inútil.
- **Recomendação:** `@app.errorhandler` central: logar a exceção com stack trace internamente e responder mensagem genérica com o status correto; exceções de domínio tipadas (`ProdutoNaoEncontrado` → 404, `ValidacaoError` → 400) em vez de `try/except` por handler.

#### [AP-16] CORS liberado para qualquer origem — `app.py:9`
- **O que:** `CORS(app)` sem argumentos — equivale a `Access-Control-Allow-Origin: *` em todas as rotas, incluindo `/admin/reset-db`, `/admin/query` e `/usuarios`.
- **Impacto:** qualquer página web que a vítima visite pode chamar a API, inclusive as rotas destrutivas e a de listagem de usuários com senhas, e **ler** a resposta. Isso converte AP-05/AP-06 em ataques exploráveis via navegador.
- **Recomendação:** allowlist explícita de origens vinda da config (`CORS(app, origins=config.ALLOWED_ORIGINS)`), restrita às rotas que realmente precisam.

#### SQL executado diretamente na camada de controller — `controllers.py:3, 264-274`
- **O que:** `controllers.py` importa `get_db` (`controllers.py:3`) e `health_check` abre cursor e roda quatro queries de contagem inline (`controllers.py:266-274`), sem passar por `models.py`. Mesmo vazamento em `app.py:49-55, 66-76`.
- **Impacto:** a fronteira de camadas é furada em três módulos — trocar a persistência exigiria mexer em controllers e no entry point, não só na camada de dados.
- **Recomendação:** nenhum acesso a banco fora das repositories; `health_check` chama um método de checagem exposto pela camada de dados.

#### Validação sem checagem de tipo produz 500 em vez de 400 — `controllers.py:43-46, 87-90`
- **O que:** `if preco < 0` compara diretamente o valor do JSON, sem verificar o tipo. Não há nenhuma conversão ou `isinstance` antes.
- **Impacto:** `POST /produtos {"nome":"x","preco":"abc","estoque":1}` levanta `TypeError: '<' not supported between instances of 'str' and 'int'`, cai no `except` genérico e devolve **500 com a mensagem do Python** em vez de um 400 de validação. Um `preco` booleano ou `null` produz comportamentos igualmente imprevisíveis.
- **Recomendação:** coerção e validação de tipo explícitas (ou schema declarativo — `pydantic`/`marshmallow`) antes de qualquer comparação, retornando 400 com o campo problemático.

#### E-mail de usuário sem unicidade no schema nem checagem na aplicação — `database.py:30`, `models.py:122-131`, `controllers.py:146-162`
- **O que:** a coluna é `email TEXT` sem `UNIQUE` (`database.py:30`); `criar_usuario` insere sem consultar existência prévia (`models.py:126-129`); o controller valida apenas presença dos campos (`controllers.py:157`), não formato nem duplicidade.
- **Impacto:** contas duplicadas com o mesmo e-mail. Como o login busca por e-mail **e** senha (`models.py:109-111`) e usa `fetchone`, o usuário autentica em uma conta arbitrária entre as duplicadas — comportamento não determinístico no caminho de autenticação.
- **Recomendação:** `UNIQUE` no schema (com migração para deduplicar), verificação prévia no service retornando 409, e validação de formato de e-mail.

### 🔵 LOW

#### [AP-15] `print` usado como logging — `controllers.py:8, 11, 57, 61, 106, 161, 179, 182, 208-210, 219, 248, 250` · `app.py:56, 83-86`
- **O que:** 17 ocorrências de `print` para rastrear execução, incluindo `print("Login bem-sucedido: " + email)` (`controllers.py:179`) e `print("Login falhou: " + email)` (`controllers.py:182`).
- **Impacto:** sem níveis, sem timestamp, sem destino configurável; vai para stdout e some. As duas linhas de login registram PII (e-mail) e, junto, entregam um oráculo de enumeração de contas a quem lê os logs.
- **Recomendação:** módulo `logging` configurado centralmente, com nível por ambiente e formato estruturado; não logar identificadores de usuário em texto livre.

#### Regras de negócio como números mágicos espalhados — `models.py:256-262, 272` · `controllers.py:52, 242`
- **O que:** faixas de desconto (`10000`/`0.1`, `5000`/`0.05`, `1000`/`0.02`) embutidas no meio do relatório; a lista de categorias válidas literal dentro do handler (`controllers.py:52`); a lista de status válidos literal em outro handler (`controllers.py:242`) — sem relação com o `DEFAULT 'pendente'` do schema (`database.py:40`).
- **Impacto:** mudar uma regra comercial exige caçar literais em dois arquivos; nada impede que a lista de status do controller e o schema divirjam.
- **Recomendação:** constantes/enums nomeados em um módulo de domínio, referenciados por controller, service e schema.

#### Código morto e imports não utilizados — `models.py:2` · `database.py:2, 22`
- **O que:** `import sqlite3` em `models.py:2` nunca é usado; `import os` em `database.py:2` nunca é usado; a coluna `ativo INTEGER DEFAULT 1` (`database.py:22`) é lida e devolvida nos serializers mas **nenhuma** query jamais filtra por ela, e `deletar_produto` (`models.py:65-70`) faz `DELETE` físico em vez de soft delete.
- **Impacto:** ruído que sugere uma intenção de soft delete que não existe; leitor futuro assume que produtos inativos são ocultados — não são.
- **Recomendação:** remover imports mortos; decidir entre implementar o soft delete (filtrar `ativo = 1` e trocar o `DELETE` por `UPDATE`) ou remover a coluna.

#### Filtro de preço igual a zero é silenciosamente ignorado — `models.py:294, 296` (origem em `controllers.py:118-121`)
- **O que:** `if preco_min:` e `if preco_max:` testam veracidade, não presença. A conversão em `controllers.py:119` transforma `"0"` em `0.0`, que é falsy.
- **Impacto:** `GET /produtos/busca?preco_max=0` devolve o catálogo inteiro em vez de lista vazia — o filtro some sem erro nem aviso.
- **Recomendação:** testar `is not None` em vez de veracidade, tanto no controller quanto no builder de query.

#### Contrato de resposta de erro inconsistente — `controllers.py:20, 29, 70, 103, 142, 183, 206`
- **O que:** alguns erros incluem `"sucesso": False` (`controllers.py:20, 183, 206`), outros trazem só `"erro"` (`controllers.py:29, 70, 103, 142`). Sucessos ora têm `"mensagem"` (`controllers.py:58`), ora não (`controllers.py:9`), ora `"total"` (`controllers.py:124`).
- **Impacto:** clientes não podem checar um campo único para decidir sucesso/falha; cada endpoint vira um caso especial no front.
- **Recomendação:** envelope de resposta único produzido por um helper/serializer, aplicado inclusive pelo error handler central.

#### Listagens sem paginação nem limite — `controllers.py:5-12, 128-134, 229-235` · `models.py:7, 75, 206`
- **O que:** `GET /produtos`, `GET /usuarios` e `GET /pedidos` executam `SELECT *` sem `LIMIT`/`OFFSET` e materializam tudo em memória.
- **Impacto:** com a base crescendo, a resposta e o consumo de memória crescem sem teto; combinado ao N+1 (AP-13), `GET /pedidos` é um vetor de exaustão de recursos.
- **Recomendação:** paginação por `limit`/`offset` (ou cursor) com teto máximo, e projeção explícita de colunas em vez de `SELECT *`.

## APIs deprecated

Varredura feita contra a tabela de deprecated do catálogo. **Nenhuma chamada a API deprecated foi encontrada** no código-fonte:

| Item verificado | Resultado |
|---|---|
| `datetime.utcnow()` | Ausente — o projeto não importa `datetime`; timestamps vêm do `CURRENT_TIMESTAMP` do SQLite (`database.py:23, 33, 42`) |
| `pkg_resources` | Ausente |
| `md5`/`sha1` para senha | Ausente — mas por motivo pior: **não existe hash nenhum** (ver AP-03, CRITICAL) |
| Flask/Werkzeug major desatualizado | Não — `flask==3.1.1` e `flask-cors==5.0.1` (`requirements.txt:1-2`) são versões da linha atual |
| Adaptadores default de `sqlite3` (deprecados no 3.12) | Não utilizados — não há adapt/convert de tipos customizados |

Observações fora da tabela, sem achado de deprecação:
- `requirements.txt` não fixa as transitivas (`Werkzeug`, `Jinja2`), então o ambiente instalado não é reprodutível. Recomendo pinning completo via lockfile e uma passada de `pip-audit` para conferir advisories das versões efetivamente instaladas — não avaliei vulnerabilidades de dependência neste relatório.
- Não há `runtime.txt`/`python_requires`, então a versão-alvo de Python não está declarada.

## Recomendação de refatoração

Ordem sugerida para a Fase 3 (fecha risco antes de organizar):

1. **CRITICAL de segurança** — parametrizar todas as queries (AP-01), remover `/admin/query` (AP-05), extrair `SECRET_KEY` para config de ambiente e tirá-la de `/health` (AP-02), aplicar `bcrypt` e parar de projetar o campo de senha nas respostas (AP-03).
2. **HIGH** — `DEBUG` por env var (AP-07), autenticação/autorização com emissão de credencial no login e proteção de `/admin/reset-db` (AP-06), transação com rollback e débito atômico de estoque no `criar_pedido`.
3. **Reestruturação em camadas MVC** (MEDIUM arquiteturais) — `config/`, `repositories/`, `services/`, `controllers/` com blueprints, conexão por requisição, error handler central, serializers/validadores únicos, eliminação do N+1 e allowlist de CORS.
4. **LOW** — `logging` no lugar de `print`, constantes de domínio nomeadas, remoção de código morto, envelope de resposta consistente, paginação.

Observação sobre preservação de contrato: quatro correções **alteram respostas observáveis** por necessidade — remoção do campo `senha` de `GET /usuarios` e `GET /usuarios/<id>`, remoção de `secret_key`/`db_path`/`debug` de `GET /health`, substituição de `str(e)` por mensagem genérica nos 500, e remoção de `POST /admin/query`. São mudanças intencionais de correção de vazamento, não regressões; as rotas, métodos e o formato do envelope permanecem. Vou confirmar isso explicitamente com você antes de aplicar, caso queira preservar alguma delas.


## Decisão do dono sobre preservação de contrato — 2026-09-24

Homologado antes da Fase 3:

1. **As três correções de vazamento seguem** — remover `senha` de `GET /usuarios`
   e `GET /usuarios/<id>`, remover `secret_key`/`db_path`/`debug` de `GET /health`,
   e trocar `str(e)` por mensagem genérica nos 500. Mudam o corpo da resposta, não
   o endpoint: rota, método e envelope permanecem.
2. **`POST /admin/query` NÃO é removida — a rota permanece e responde `403`**, sem
   executar nada. Fecha o CRITICAL (AP-05) e mantém o endpoint original
   respondendo, como o checklist de validação exige.

Exigência de rastreabilidade da decisão 2: a rota desativada carrega **comentário
no código** justificando o `403` (qual anti-pattern fechou e por que a rota não foi
deletada), e a mesma justificativa aparece no antes/depois do `README.md` do repo.
