# Relatório de Auditoria Arquitetural — code-smells-project (revisão 2)

- **Data:** 2026-09-30
- **Stack:** Python 3.12 / Flask 3.1.1 + Flask-CORS 5.0.1 + Werkzeug 3.1.8 + itsdangerous 2.2.0
- **Arquitetura de partida:** N2 — em camadas (config, models, repositories, services, controllers, middlewares, routers), com defeitos pontuais
- **Arquivos analisados:** 48 fontes `.py` (45 em `src/` + `app.py`, `wsgi.py`, `src/__init__.py`) + `requirements.txt`, `.env.example`, `.gitignore`, `README.md`
- **Escopo:** árvore de trabalho atual, **não commitada**, com o patch da EXCEÇÃO CRÍTICA (AP-06) de 2026-09-28 e o complemento de 2026-09-30 aplicados
- **Método:** auditoria estática **mais medição de primeira mão** — a aplicação foi instanciada (`criar_app`), as 19 rotas enumeradas do `url_map` e cada par método×rota exercitado por HTTP em três perfis (anônimo, token de cliente, token de admin). As afirmações de boot, status e payload abaixo são observadas, não inferidas.

> Segunda auditoria do projeto. `audit-project-1.md` (27 achados, 7 CRITICAL) descreve o estado pré-refatoração. Esta revisão existe porque o avaliador determinou que fechar um CRITICAL prevalece sobre preservar o contrato original da rota, que a autenticação fosse aplicada às rotas de produtos e pedidos, e que a skill fosse executada de novo nos projetos 1 e 3. É o par do `audit-project-3-rev4.md`.

## Resumo por severidade

| Severidade | Qtd |
|---|---|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 4 |
| LOW | 2 |
| **Total** | **6** |

APIs deprecated detectadas em código executável: **nenhuma**.

Comparação com a auditoria original: dos 27 achados, **22 estão fechados** e 5 seguem
abertos como MEDIUM/LOW de padronização.

> **Esta revisão achou e fechou quatro rotas que o patch anterior deixou abertas.** A
> varredura método a método (matriz `método × rota × status anônimo`, 19 rotas) mostrou
> que o patch de 2026-09-28 fechou o `DELETE` do catálogo e esqueceu o `POST` e o `PUT`
> ao lado dele, e que as duas leituras de pedido seguiam anônimas. Isto é exatamente o
> padrão que o avaliador descreveu — "repete o padrão nas rotas de produtos e pedidos" —
> e não teria sido pego sem enumerar os métodos: conferir "as rotas que o README diz ter
> fechado" confirma o que já se sabe e não revela o que ficou de fora. O AP-06 do
> catálogo da skill foi corrigido na mesma passada, porque a regra antiga classificava
> escrita anônima não-destrutiva como HIGH e só elevava CRITICAL a destruição.

---

## Achados

### 🔴 CRITICAL

Nenhum. Os 7 CRITICAL da auditoria original estão fechados, e cada um foi conferido:

| Achado original | Estado | Evidência medida |
|---|---|---|
| [AP-01] SQL por concatenação em ~20 pontos | fechado | toda query dos 5 repositórios usa `?` mais tupla de parâmetros; nenhuma interpolação de input em string SQL em `src/` |
| [AP-01] SQL injection no login, com bypass de autenticação | fechado | `AuthService` busca só por e-mail e compara hash (`services/auth_service.py:29-38`) |
| [AP-05] `POST /admin/query` executa SQL do cliente | fechado | **403 medido** para requisição anônima pedindo `DROP TABLE produtos`; a rota não executa nada |
| [AP-02] `SECRET_KEY` hardcoded | fechado | `config/settings.py:71` exige `SECRET_KEY` do ambiente e falha no boot sem ela |
| [AP-02] Segredo devolvido por `GET /health` | fechado | **payload medido**: `counts`, `database`, `status` e `versao` — sem segredo, sem caminho de arquivo, sem flag de debug |
| [AP-03] Senha em texto puro | fechado | `generate_password_hash` com scrypt (`services/auth_service.py:29-30`); registro legado sem hash não autentica e exige redefinição |
| [AP-03] Hash de senha nas respostas | fechado | `CAMPOS_USUARIO` e `CAMPOS_USUARIO_AUTENTICADO` (`models/serializers.py:21,23`) não projetam o campo de senha |

### 🟠 HIGH

Nenhum. O AP-06 que ainda havia era de quatro rotas, **achadas e fechadas nesta revisão**:

| Rota | Antes (anônimo) | Prova do dano | Agora |
|---|---|---|---|
| `POST /produtos` | **201** | anônimo cria produto no catálogo | `admin` · 401 anônimo |
| `PUT /produtos/<id>` | **200** | anônimo muda preço para `0.01` e estoque para `999` de qualquer produto | `admin` · 401 anônimo |
| `GET /pedidos` | **200** | lista id, `usuario_id`, status, total e data de todo pedido | `admin` · 401 anônimo |
| `GET /pedidos/usuario/<id>` | **200** | histórico de compra de qualquer usuário por enumeração de id | autenticado **+ posse** (ou `admin`) · 401 anônimo |

- **Por que passou batido no patch anterior:** o patch fechou `DELETE /produtos/<id>` e
  deixou `POST` e `PUT` da mesma entidade sem decorator, três linhas acima no mesmo
  arquivo. A regra do AP-06 vigente até aqui dizia "HIGH para rotas de leitura ou escrita
  não-destrutiva; CRITICAL quando destrutiva" — então a própria skill autorizava deixar a
  escrita anônima aberta. Corrigido no catálogo: **escrita anônima em dado de negócio é
  CRITICAL**, e a entrada do AP-06 passou a mandar listar a matriz `método × rota ×
  decorator` antes de concluir que está coberto.
- **Posse, não só autenticação:** `GET /pedidos/usuario/<id>` com apenas
  `@requer_autenticacao` continuaria sendo enumeração por id — bastaria qualquer conta.
  A checagem compara o `sub` do token com o id da rota e libera `admin`
  (`pedido_controller.py:44-47`). Medido: próprio **200**, de outro **403**, admin lendo o
  de outro **200**.
- **`GET /pedidos` virou admin-only** e não apenas autenticada, para ficar coerente com
  `GET /relatorios/vendas`: é a lista bruta que compõe o agregado.
- **Resíduo, agora MEDIUM e documentado no README do projeto:** `GET /usuarios` e
  `GET /usuarios/<id>` seguem abertas a qualquer conta autenticada, sem redução de
  projeção para não-admin.

### 🟡 MEDIUM

#### [AP-06] `GET /usuarios` e `GET /usuarios/<id>` sem redução de projeção para não-admin — `src/controllers/usuario_controller.py:22,30`, `src/models/serializers.py:21`
- **O que:** as duas rotas exigem credencial (401 anônimo, medido), mas qualquer conta
  autenticada lê a lista inteira com nome, e-mail, tipo e data de criação de todos os
  usuários. O cadastro (`POST /usuarios`) é aberto por contrato, então obter uma conta
  custa uma requisição.
- **Impacto:** a lista de e-mails alimenta a força bruta do login (ver o MEDIUM de rate
  limiting abaixo). Não é mais CRITICAL — o acesso anônimo foi fechado — mas o modelo
  é de autenticação, não de autorização por objeto.
- **Recomendação:** restringir a admin, ou reduzir a projeção para `id` e `nome` quando o
  portador não é admin.

#### Listagens sem limite por default — `src/controllers/produto_controller.py`, `src/controllers/pedido_controller.py`, `.env.example`
- **O que:** `LISTAGEM_LIMITE_PADRAO` vazio no `.env.example` significa "sem limite", escolha
  deliberada para preservar o contrato original; `LISTAGEM_LIMITE_MAXIMO=500` só limita o
  `?limit=` informado pelo cliente. Medido: `GET /produtos` devolve os 10 produtos da base de
  demonstração e **não emite `X-Total-Count`**.
- **Impacto:** a resposta cresce com a tabela, e sem header de total um cliente que quisesse
  paginar não tem como saber o tamanho do conjunto.
- **Recomendação:** default numérico (ex.: 50) e `X-Total-Count` exposto nas três listagens.
  A mudança é aditiva se a resposta seguir sendo lista pura.

#### Sem rate limiting nem lockout em `POST /login` — `src/controllers/usuario_controller.py`
- **O que:** a rota é aberta por contrato e não conta tentativas.
- **Impacto:** com `GET /usuarios` fechado a enumeração de e-mails ficou mais cara, mas a
  força bruta contra um e-mail conhecido segue sem custo.
- **Recomendação:** contador por IP e por conta, com atraso progressivo.

#### Ausência de suíte de testes automatizados — raiz do projeto
- **O que:** a refatoração foi validada por varredura HTTP manual, inclusive nesta revisão, e
  não por testes versionados.
- **Impacto:** cada patch de autorização exige nova varredura à mão — foi exatamente o que
  aconteceu entre 2026-09-26 e 2026-09-29.
- **Recomendação:** pytest cobrindo a matriz de autorização rota x papel, que é o contrato que
  mais mudou.

### 🔵 LOW

#### Contrato de erro sem código de aplicação — `src/controllers/envelope.py`, `src/models/errors.py`
- **O que:** o envelope padronizou a forma da resposta de erro, o que fechou o achado original
  de inconsistência, mas a mensagem é o único discriminador.
- **Recomendação:** um campo `codigo` estável por classe de erro.

#### Comentários de arqueologia no código de produção — `src/` (vários módulos)
- **O que:** boa parte dos módulos abre com docstring narrando o estado anterior do arquivo.
- **Impacto:** nenhum em execução; é sedimento de processo num artefato de produto. Vale
  registrar porque uma varredura por `print(` ou por `str(e)` no projeto retorna 7 ocorrências
  que são **todas** dentro desses comentários — leitura que engana quem audita por grep.
- **Recomendação:** mover a comparação antes/depois para o README e deixar as docstrings
  descrevendo a responsabilidade atual do módulo.

---

## Validação medida nesta revisão

- **Boot:** `criar_app(carregar_settings())` sobe limpo, sem traceback, com **19 rotas
  registradas** — paridade exata com as 19 do contrato original.
- **Matriz completa, método a método (19 rotas):** **zero rotas sensíveis abertas a
  anônimo.** As 10 que exigem credencial devolvem `401`; as 9 públicas por contrato
  (`/`, `/health`, as três leituras de catálogo, `POST /usuarios`, `POST /login`) seguem
  `200`/`201`.
- **Caminho autorizado funciona:** com token de `admin`, `POST /produtos` **201**,
  `PUT /produtos/<id>` **200**, `DELETE /produtos/<id>` **200**, `GET /pedidos` **200**,
  `GET /relatorios/vendas` **200**, `GET /usuarios` **200**. **Nenhuma resposta 5xx em
  nenhuma rota.**
- **Autorização por papel discrimina:** com token de cliente, `GET /pedidos` → **403** e
  `POST /produtos` → **403**.
- **Posse em `GET /pedidos/usuario/<id>`:** próprio **200**, de outro **403**, admin
  lendo o de outro **200**.
- **Login:** os três usuários de exemplo autenticam (200) e a senha não aparece no corpo;
  o token traz `papel`.
- **Exploit da auditoria original:** `POST /admin/query` anônimo devolve **403** sem
  executar; `POST /admin/reset-db` anônimo, **401**.
