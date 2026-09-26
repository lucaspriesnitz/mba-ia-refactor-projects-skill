# Desafio — Skill `refactor-arch` (Auditoria e Refatoração Arquitetural)

Skill de agente que **audita e refatora qualquer backend para MVC**, de forma
agnóstica de tecnologia, em 3 fases sequenciais: **Análise** → **Auditoria**
(com pausa e confirmação humana) → **Refatoração** (com validação de que a
aplicação continua de pé).

- **Ferramenta:** Claude Code (`.claude/skills/refactor-arch/`)
- **Skill:** [`SKILL.md`](code-smells-project/.claude/skills/refactor-arch/SKILL.md) + 5 arquivos de referência
- **Projetos-alvo:** `code-smells-project` (Python/Flask) · `ecommerce-api-legacy` (Node/Express) · `task-manager-api` (Python/Flask)
- **Relatórios:** [`reports/`](reports/)
- O enunciado original do desafio está preservado em [`README_original.md`](README_original.md).

> **Estado da entrega:** os 3 projetos completos nas 3 fases, cada um validado com
> a aplicação de pé e **por fora do log da skill** — 19/19 endpoints no projeto 1,
> a bateria do `api.http` em container `node:20` no projeto 2, 22/22 endpoints no
> projeto 3. Nada aqui declara resultado que não foi medido: cada número desta
> página vem de uma verificação registrada na seção C.

---

## A) Análise Manual

Leitura do código dos três projetos **antes** de confiar na skill. O objetivo
desta etapa não é competir com a auditoria automática: é estabelecer um gabarito
para saber se a skill detecta o que um humano detectaria — e, na prática, para
descobrir o que ela detecta **além** disso (ver seção C).

Escala usada: a definição de severidade do próprio enunciado (CRITICAL =
arquitetura/segurança grave ou violação completa de separação; HIGH = violação
forte de MVC/SOLID; MEDIUM = duplicação, N+1, validação ausente; LOW =
legibilidade, nomenclatura, magic numbers).

### Projeto 1 — `code-smells-project` (Python/Flask, API de e-commerce)

4 arquivos, 784 linhas: `app.py` (89), `controllers.py` (293), `models.py` (315),
`database.py` (87). Os nomes sugerem camadas, mas as responsabilidades vazam.

| # | Severidade | Problema | Onde | Por que importa |
|---|---|---|---|---|
| 1 | CRITICAL | **SQL Injection por concatenação** — praticamente toda query é montada com `+` de string | `models.py:28, 48-49, 58-60, 68, 92, 110, 127-128, 140, 149-150, 155, 158-160, 163-166, 174, 188, 192, 220, 224, 280, 291-297` | O login (`:110`) concatena `email` e `senha` crus: `' OR '1'='1' -- ` autentica como qualquer usuário. A busca (`:291`) permite `UNION SELECT` para extrair a tabela de usuários. É acesso total ao banco por entrada não confiável. |
| 2 | CRITICAL | **Endpoint que executa SQL arbitrário** — `POST /admin/query` recebe `sql` do corpo e executa | `app.py:59-78` | Sem autenticação. `DROP TABLE`, exfiltração, tudo. É um shell de banco exposto na rede. |
| 3 | CRITICAL | **Senhas em texto puro** — coluna `senha TEXT`, seed com `admin123`, comparação direta no login | `database.py:31, 76-78`, `models.py:110` | Dump do banco entrega credenciais utilizáveis; usuários reciclam senha, então o dano passa desta aplicação. |
| 4 | CRITICAL | **Senha devolvida na resposta HTTP** — `GET /usuarios` e `GET /usuarios/<id>` projetam o campo `senha` | `models.py:83, 99` | Vazamento de credencial por endpoint público, sem precisar nem invadir o banco. |
| 5 | CRITICAL | **Segredo hardcoded e exposto pelo `/health`** — `SECRET_KEY` no código e devolvida no payload do health check | `app.py:7`, `controllers.py:289` | Rotacionar exige alterar código e redeploy; e o `/health`, que costuma ser público e monitorado, entrega a chave e o `debug: true`. |
| 6 | HIGH | **`DEBUG=True` fixo no código** com `host="0.0.0.0"` | `app.py:8, 88` | O console interativo do Werkzeug é execução remota de código; ligado por padrão e sem chave de ambiente para desligar. |
| 7 | HIGH | **Rota destrutiva sem autenticação** — `POST /admin/reset-db` apaga as 4 tabelas | `app.py:47-57` | Qualquer requisição anônima zera a base. Não há sequer o conceito de sessão na aplicação. |
| 8 | HIGH | **Criação de pedido sem transação e com corrida no estoque** — valida estoque, depois insere pedido, itens e dá baixa; `commit` só no fim, sem rollback | `models.py:133-169` | Falha no meio deixa pedido sem itens ou estoque descontado sem pedido. E duas requisições simultâneas passam pela mesma validação: vende-se abaixo de zero. |
| 9 | HIGH | **Conexão global compartilhada com `check_same_thread=False`** | `database.py:4-10` | Uma única conexão SQLite servindo todas as threads do Flask — corrupção e erros intermitentes sob concorrência; além de estado global mutável no pior lugar possível. |
| 10 | MEDIUM | **N+1 nos pedidos** — para cada pedido, uma query de itens; para cada item, uma query de produto | `models.py:187-199, 219-231` | 1 + N + N×M queries para montar uma listagem. Cresce com o uso e não aparece em teste com 3 registros. |
| 11 | MEDIUM | **Regra de negócio dentro de `models.py`** — cálculo de total, faixas de desconto (10%/5%/2%) e baixa de estoque moram na camada de dados | `models.py:133-169, 256-262` | Não existe camada de service: o "model" é repositório + regra ao mesmo tempo, então a regra não é testável sem banco e não é reutilizável. |
| 12 | MEDIUM | **Validação duplicada e divergente entre POST e PUT de produto** | `controllers.py:30-54` vs `:74-90` | O `PUT` não valida tamanho de nome nem categoria — o mesmo recurso aceita por uma porta o que a outra rejeita. Duplicação que já divergiu. |
| 13 | MEDIUM | **Serialização repetida à mão em 5 lugares** — o mesmo dicionário de produto/usuário montado campo a campo | `models.py:12-21, 31-40, 79-86, 95-102, 304-313` | Um campo novo exige lembrar de 5 pontos; foi assim que `senha` acabou em dois deles. |
| 14 | MEDIUM | **Efeito colateral de notificação dentro do controller** — "envio" de e-mail/SMS/push via `print` | `controllers.py:208-210, 248-250` | Notificação é responsabilidade de outra camada; como está, não dá para desligar, testar ou trocar o canal. |
| 15 | LOW | **`print` como logging** em toda a aplicação | `controllers.py:8, 11, 57, 61, 106, 161, 179, 182, 208-210, 219, 248-250`, `app.py:56, 83-86` | Sem nível, sem timestamp estruturado, sem destino configurável. |
| 16 | LOW | **`str(e)` devolvido ao cliente em todos os `except`** | `controllers.py:12, 22, 62, 96, 109, 126, 134, 144, 165, 186, 220, 227, 235, 255, 262`, `app.py:78` | A mensagem de exceção entrega caminho de arquivo, nome de tabela e fragmento de SQL para quem chamou — reconhecimento gratuito para um atacante. |
| 17 | LOW | **Magic numbers e listas de domínio soltas** — faixas de desconto, categorias válidas, status válidos escritos inline | `models.py:256-262`, `controllers.py:52, 242` | Regra de negócio como literal no meio do fluxo, repetida e sem nome. |

### Projeto 2 — `ecommerce-api-legacy` (Node/Express, LMS com checkout)

3 arquivos, ~200 linhas: `src/app.js`, `src/AppManager.js`, `src/utils.js`.
Monólito plano — uma classe concentra rota, regra e SQL.

| # | Severidade | Problema | Onde | Por que importa |
|---|---|---|---|---|
| 1 | CRITICAL | **Chave `pk_live_` e senha de banco hardcoded** | `utils.js:2-6` | O prefixo `pk_live_` indica chave de produção: quem tiver o repositório transaciona no gateway real. Já está no histórico do Git — remover do código não basta, tem que rotacionar. |
| 2 | CRITICAL | **Número do cartão e a chave do gateway impressos no log, a cada checkout** | `AppManager.js:45` | PAN completo em claro viola PCI-DSS diretamente, e logs têm retenção longa e controle de acesso mais fraco que o banco. **Reproduzido em execução** (ver seção C). |
| 3 | CRITICAL | **Senha em texto puro no schema e no seed** | `AppManager.js:12, 18` | `pass TEXT` e `INSERT ... '123'`. A coluna guarda valores heterogêneos: texto puro no seed, pseudo-hash no checkout. |
| 4 | CRITICAL | **Criptografia caseira** — `badCrypto` concatena base64 10 mil vezes e corta em 10 caracteres | `utils.js:17-23` | Não é hash: sem salt, sem função de derivação, espaço de saída minúsculo e determinístico. Dá falsa sensação de proteção. |
| 5 | HIGH | **Rotas sensíveis e destrutivas sem autenticação** — relatório financeiro e `DELETE /api/users/:id` abertos | `AppManager.js:80, 131` | Faturamento por curso e por aluno para qualquer um; exclusão de usuário idem. Não existe nenhum conceito de sessão. |
| 6 | HIGH | **Banco em memória** — `new sqlite3.Database(':memory:')` | `AppManager.js:7` | Todo dado desaparece a cada restart. Matrículas e pagamentos não sobrevivem a um deploy. |
| 7 | HIGH | **Escrita multi-tabela sem transação** — matrícula, pagamento e log de auditoria em inserts encadeados | `AppManager.js:50-62` | Falha no meio deixa matrícula sem pagamento (aluno matriculado de graça) ou pagamento órfão. E o fluxo é justamente o de cobrança. |
| 8 | HIGH | **Exclusão sem integridade referencial** — deleta o usuário e deixa matrículas e pagamentos órfãos; a resposta **admite isso ao cliente** | `AppManager.js:14-15, 133-135` | Nenhuma FK declarada. **Reproduzido:** após `DELETE /api/users/1`, o relatório financeiro segue faturando R$997 para `"student":"Unknown"`. |
| 9 | HIGH | **Senha opcional no checkout, com fallback previsível** — `badCrypto(p \|\| "123456")` | `AppManager.js:68` | A validação de entrada (`:35`) não exige `pwd`, então cria-se conta com senha padrão conhecida. **Reproduzido:** checkout sem `pwd` responde `200`. |
| 10 | MEDIUM | **God class `AppManager`** — rota, regra, SQL e gateway de pagamento na mesma classe de 141 linhas | `AppManager.js:4-141` | Não há model, service, repository nem router. Nada é testável isoladamente. |
| 11 | MEDIUM | **N+1 no relatório financeiro** — 1 query de cursos, N de matrículas, e 2 por matrícula (usuário + pagamento) | `AppManager.js:83-106` | Um `JOIN` com agregação resolve. Como está, o custo cresce com as matrículas. |
| 12 | MEDIUM | **Estado global mutável** — `globalCache` sem limite e `totalRevenue` exportado por valor | `utils.js:9-10, 14`, `AppManager.js:59` | Cache que só cresce (vazamento de memória) e um contador que nunca muda para quem importa. |
| 13 | MEDIUM | **Erros engolidos: resposta de sucesso mesmo com falha** | `AppManager.js:57, 104, 106, 133-135` | Vários callbacks ignoram `err` e seguem; o `DELETE` responde sucesso sem olhar o erro. Falha silenciosa no caminho do dinheiro. |
| 14 | LOW | **`console.log` como logging** | `app.js:13`, `utils.js:13`, `AppManager.js:45` | Mesmo problema do projeto 1, agravado pelo conteúdo logado (item 2). |
| 15 | LOW | **Contrato ilegível e mensagem confessional** — `usr`, `eml`, `pwd`, `c_id`, `card`; a resposta do DELETE explica o bug ao cliente | `AppManager.js:29-33, 135` | Payload abreviado sem motivo e resposta que documenta a própria fragilidade para quem consome a API. |

### Projeto 3 — `task-manager-api` (Python/Flask, gerenciador de tarefas)

14 arquivos, 1.158 linhas, **já parcialmente em camadas** (`models/`, `routes/`,
`services/`, `utils/`). É o caso mais interessante do desafio: a estrutura
existe, mas não é respeitada.

| # | Severidade | Problema | Onde | Por que importa |
|---|---|---|---|---|
| 1 | CRITICAL | **O hash da senha vai em toda resposta de usuário** — `User.to_dict()` inclui `password`, usado no `GET /users/<id>`, no `POST /users` (201), no `PUT` e **na resposta do login** | `models/user.py:21`, `routes/user_routes.py:33, 85, 129, 209` | Vazamento de credencial por API pública. O `GET /users` (lista) monta o dicionário à mão e não vaza — o mesmo recurso tem dois formatos, e o mais usado é o que vaza. |
| 2 | CRITICAL | **MD5 sem salt como hash de senha** | `models/user.py:29, 32` | MD5 é quebrável por rainbow table; sem salt, senhas iguais viram hashes iguais. Não é função de derivação de senha. |
| 3 | CRITICAL | **Credenciais SMTP e `SECRET_KEY` hardcoded** — senha `senha123` no serviço de e-mail | `services/notification_service.py:7-10`, `app.py:13` | Credencial de envio no repositório permite mandar e-mail em nome do domínio (phishing com remetente legítimo). |
| 4 | CRITICAL | **Zero autenticação em toda a API, com token forjável** — nenhuma rota exige credencial; o login devolve `'fake-jwt-token-' + id`; `is_admin()` existe e nunca é chamado | `routes/*.py` (todas), `routes/user_routes.py:210`, `models/user.py:34` | Qualquer anônimo lista usuários, deleta tarefas e — via `PUT /users/<id>` com `{"role":"admin"}` (`user_routes.py:119-122`) — se promove a administrador. O token não é assinado: `fake-jwt-token-1` é adivinhável. |
| 5 | HIGH | **`debug=True` com `host='0.0.0.0'`** | `app.py:34` | Mesmo risco do projeto 1: console do Werkzeug exposto. |
| 6 | HIGH | **CORS liberado para qualquer origem** — `CORS(app)` sem restrição | `app.py:15` | Combinado com a ausência de autenticação (item 4), qualquer site consegue operar a API em nome de quem o visita. |
| 7 | HIGH | **Configuração no código e schema criado no import** — URI, `SECRET_KEY` e `db.create_all()` em tempo de import | `app.py:11-13, 30-31` | Sem variáveis de ambiente e sem migrations: a estrutura do banco evolui por acidente, não por versão. |
| 8 | MEDIUM | **Fat controllers: `routes/` faz validação, regra e persistência** — não há camada de service (o único service existente, de notificação, **não é chamado por nenhuma rota**) | `routes/task_routes.py:85-154`, `routes/report_routes.py:12-101` | A pasta `services/` existe e está vazia de propósito: a estrutura aparenta camadas que não existem. Um relatório de 90 linhas de agregação vive dentro do handler HTTP. |
| 9 | MEDIUM | **N+1 em três lugares** — usuário e categoria por tarefa na listagem; tarefas por usuário no relatório; contagem por categoria | `task_routes.py:42, 51`, `report_routes.py:56, 163` | O ORM oferece `join`/`selectinload`; o código consulta em laço. |
| 10 | MEDIUM | **Validador completo escrito e nunca usado** — `process_task_data()` cobre título, status, prioridade, data e tags; as rotas revalidam tudo inline | `utils/helpers.py:57-108` vs `task_routes.py:92-144, 166-213` | Código morto que dá a impressão de haver validação centralizada. A lista de status válidos aparece em **5 lugares** (`task.py:39`, `helpers.py:75, 110`, `task_routes.py:110, 177`). |
| 11 | MEDIUM | **Serialização em três formatos divergentes para o mesmo recurso** — `Task.to_dict()`, montagem manual em `task_routes` e outra em `user_routes`; `overdue` recalculado inline em 4 lugares enquanto `Task.is_overdue()` existe e nunca é chamado | `models/task.py:23-36, 50-60`, `task_routes.py:17-58`, `user_routes.py:162-181`, `report_routes.py:34` | O consumidor recebe campos diferentes conforme o endpoint, e a regra de "atrasada" pode divergir entre telas. |
| 12 | MEDIUM | **`priority` não é convertido para inteiro** — comparação `data['priority'] < 1` com string vinda do JSON | `task_routes.py:113, 182` | `{"priority": "alta"}` levanta `TypeError` e vira 500 em vez de 400. Falha de validação virando erro de servidor. |
| 13 | LOW | **`except:` nu engolindo qualquer exceção** | `task_routes.py:62, 236`, `user_routes.py:130, 149`, `report_routes.py:186, 207, 221`, `helpers.py:46-49` | Captura até `KeyboardInterrupt`; erro real vira "Erro interno" genérico e ninguém fica sabendo. |
| 14 | LOW | **`print` como log e imports mortos em massa** | `user_routes.py:83, 89, 147`, `task_routes.py:149, 153, 219, 234`, `app.py:7`, `helpers.py:3-7` | `os, sys, json, math, hashlib` importados e não usados em vários módulos — ruído que esconde a dependência real. |
| 15 | LOW | **APIs deprecated** — `datetime.utcnow()` (obsoleta desde Python 3.12) usada ~15×, e `Model.query.get()` (legado no SQLAlchemy 2.0) | `models/*.py`, `routes/*.py` | Quebram em versão futura sem aviso. É exatamente o tipo de achado que a detecção de deprecated da skill precisa pegar. |

---

## B) Construção da Skill

### Decisões de design

**Separar procedimento de conhecimento.** O `SKILL.md` (141 linhas) carrega só o
que o agente precisa em **toda** execução: as 3 fases, os formatos de saída
obrigatórios e 5 regras invioláveis. Todo o resto — catálogo, template, diretrizes
MVC, playbook — vive em `references/` e é lido **sob demanda**, com uma tabela
"quando ler o quê" no topo. Isso mantém o contexto enxuto na Fase 1 e permite que
o conhecimento cresça sem inchar o prompt.

```
.claude/skills/refactor-arch/
├── SKILL.md                              # procedimento: 3 fases + regras invioláveis
└── references/
    ├── project-analysis.md               # Fase 1 — como detectar stack e arquitetura
    ├── anti-patterns.md                  # Fase 2 — catálogo (16 APs) + deprecated
    ├── audit-report-template.md          # Fase 2 — formato do relatório
    ├── mvc-guidelines.md                 # Fase 3 — estrutura-alvo por ponto de partida
    └── refactoring-playbook.md           # Fase 3 — 12 transformações antes/depois
```

**As 5 regras invioláveis** são o contrato que impede a skill de virar um
"refatorador criativo":

1. a Fase 2 **sempre** pausa e pede confirmação humana — nenhuma escrita nas fases 1 e 2;
2. comportamento observável preservado (rotas, métodos, formato de resposta);
3. todo achado ancorado em `arquivo:linha` — "código ruim" não é achado;
4. adaptar-se ao ponto de partida, não aplicar uma estrutura fixa;
5. validar de verdade na Fase 3 — e, se não puder bootar, **declarar a limitação** em vez de fingir sucesso.

**Cada fase tem um formato de saída literal** (blocos `PHASE 1: PROJECT ANALYSIS`
e `PHASE 3: REFACTORING COMPLETE`, e a pergunta `Phase 2 complete. Proceed with
refactoring (Phase 3)? [y/n]`). Saída com forma fixa é o que torna a execução
verificável — dá para conferir se a fase rodou sem ler o raciocínio inteiro.

### O catálogo de anti-patterns

16 entradas, cada uma com definição, sinais de detecção em mais de uma linguagem,
severidade e a transformação correspondente no playbook:

| Faixa | Anti-patterns |
|---|---|
| CRITICAL | AP-01 SQL injection por concatenação · AP-02 segredo hardcoded · AP-03 senha em texto puro · AP-04 cripto caseira · AP-05 endpoint que executa entrada arbitrária |
| HIGH | AP-06 rota sensível sem auth · AP-07 `DEBUG` ligado no código · AP-08 banco volátil / conexão global |
| MEDIUM | AP-09 God module · AP-10 fat controller · AP-11 estado global mutável · AP-12 duplicação (WET) · AP-13 N+1 |
| LOW | AP-14 erro engolido ou vazado · AP-15 `print`/`console.log` como log · AP-16 CORS aberto |

O critério de entrada foi: **aparecer nos projetos-alvo ou ser uma falha que muda
o risco da aplicação**. Os CRITICAL são todos de segurança porque a escala do
enunciado coloca exposição de dado no topo; os MEDIUM concentram as violações de
MVC propriamente ditas (God class, fat controller, duplicação), que são o alvo da
refatoração; os LOW são qualidade de código. Três entradas têm severidade
**condicional** (AP-08, AP-14, AP-16) — o catálogo instrui a subir a severidade
conforme o contexto, e isso funcionou na prática: no projeto 2 a auditoria
promoveu o `console.log` de LOW para **CRITICAL** porque a linha logava o número
do cartão, e justificou a promoção no próprio achado.

Há ainda uma seção obrigatória de **detecção de APIs deprecated** — o enunciado
pede, e é um achado que o olho humano perde com facilidade (no projeto 3, os ~15
usos de `datetime.utcnow()` e o `Model.query.get()` do SQLAlchemy 2.0).

### Como a skill ficou agnóstica de tecnologia

- **A Fase 1 detecta antes de julgar.** `project-analysis.md` guia a detecção por
  artefato (manifesto de dependências, ponto de entrada, driver de banco) em vez
  de assumir uma stack.
- **O catálogo descreve padrões, não APIs.** Cada AP traz sinais em Python e em
  JavaScript, e a instrução de generalizar: "concatenação de entrada em string de
  query", não "`cursor.execute` com `+`".
- **A estrutura-alvo é descrita por responsabilidade**, com nomes de pasta
  sugeridos e a ressalva de seguir a convenção da linguagem.
- **Adaptação por ponto de partida (N0/N1/N2)** — `mvc-guidelines.md` define três
  cenários: monólito plano (N0), separação nominal com vazamento (N1), e já em
  camadas com defeitos pontuais (N2). Cada um recebe transformações diferentes.
  É o que impede a skill de "recriar tudo" num projeto que já está organizado.
- **A prova prática:** a skill foi copiada **byte a byte** de `code-smells-project`
  para `ecommerce-api-legacy` (`diff -r` limpo, zero adaptação) e detectou
  corretamente Node/CommonJS + Express + sqlite3.

### Desafios encontrados

**1. Garantir a pausa da Fase 2 numa execução automatizada.** A confirmação humana
é critério de aceite, mas uma execução não-interativa tende a "seguir em frente".
A solução foi estrutural, não textual: as Fases 1 e 2 rodam com **permissão
somente-leitura** (`--allowedTools "Read,Grep,Glob"`), então a skill *não tem como*
escrever mesmo que decida escrever. A pausa deixou de depender de obediência.
Efeito colateral dessa escolha: a própria skill também não consegue salvar
`reports/audit-project-<n>.md`, e o relatório precisa ser materializado a partir
da saída da sessão — é um trade-off consciente, e a alternativa é somar `Write` à
allowlist.

No projeto 3 essa alternativa foi exercida de propósito: as Fases 1+2 rodaram
**com `Write` liberado**, para que a skill salvasse o relatório sozinha e, de
quebra, para trocar uma garantia estrutural por um **teste real**. A pausa
aguentou — a skill parou pedindo confirmação e não tocou em nenhum arquivo do
projeto tendo permissão para tocar. É a evidência mais forte do critério de
aceite entre os três projetos, justamente porque nos outros dois a pausa estava
garantida por construção.

**2. "Preservar os endpoints" versus "fechar a falha".** No projeto 1, o achado
CRITICAL AP-05 pedia remover `POST /admin/query`. Mas o checklist de validação
exige que *todos os endpoints originais respondam*. Remover a rota fecharia a
falha e quebraria o checklist. A decisão foi **manter a rota e responder `403`
sem executar nada** — o endpoint continua existindo, a falha morre, e a
justificativa fica registrada em comentário no código. Foi a primeira vez em que
as duas regras invioláveis (segurança e preservação) colidiram, e a resposta
virou precedente para os outros projetos.

**3. Ponto de partida desigual entre os projetos.** `ecommerce-api-legacy` é um
monólito de uma classe (N0); `task-manager-api` já tem `models/`, `routes/` e
`services/`. Uma estrutura-alvo fixa faria a skill destruir a organização do
terceiro projeto. Daí a seção de adaptação por ponto de partida.

Na execução, esse caso rendeu o achado mais interessante do desafio: a skill
classificou o projeto 3 como **N1 nominal**, não N2, porque reparou que a
`services/` existe e **não é importada por ninguém**. Pastas com os nomes certos
não são separação de camadas — e a heurística de detecção precisava enxergar a
diferença entre a estrutura e o que ela promete.

**4. Validar Node sem Node.** A máquina de desenvolvimento não tem Node/npm
instalados. Em vez de instalar (e alterar o ambiente por causa de um desafio), a
validação do projeto 2 roda em container `node:20` com o projeto montado como
volume. A regra 5 da skill já previa esse caso: "ou container quando não houver
runtime no host".

**5. A Fase 3 foi além do relatório confirmado.** Com permissão de escrita e o
aval humano em mãos, a Fase 3 do projeto 3 aplicou seis mudanças de contrato
além das duas que a confirmação nomeava — todas rastreáveis a recomendações do
próprio relatório (token nos campos privilegiados, JWT real, senha mínima de 12
caracteres, `DELETE` que desassocia em vez de orfanar, CORS restrito, remoção de
código morto), nenhuma inventada, mas nenhuma explicitamente aprovada.

Vale registrar porque é uma lição sobre o desenho da skill, não um acidente de
execução: o gate de confirmação humana só tem valor se **o que roda depois é o
que foi revisado**. Uma Fase 3 que "termina o serviço" a partir das
recomendações do relatório é tecnicamente defensável — o enunciado pede
"eliminando os problemas encontrados" — e ainda assim esvazia a revisão. A
correção não é textual ("não exceda o escopo"), é a mesma do desafio 1: dar à
Fase 3 uma lista fechada do que foi aprovado, e fazer dela a entrada da fase, em
vez de reabrir o relatório inteiro como se tudo tivesse sido homologado. As seis
mudanças estão documentadas em "O que muda para quem consome a API", no README
do projeto 3.

---

## C) Resultados

### Resumo dos relatórios de auditoria

| Projeto | Stack detectada | Arquitetura de partida | CRITICAL | HIGH | MEDIUM | LOW | Total | Relatório |
|---|---|---|---|---|---|---|---|---|
| 1 — `code-smells-project` | Python 3 / Flask 3.1.1 | N1 — separação nominal | 7 | 4 | 10 | 6 | **27** | [`audit-project-1.md`](reports/audit-project-1.md) |
| 2 — `ecommerce-api-legacy` | Node.js (CommonJS) / Express 4.22.1 + sqlite3 5.1.7 | N0 — monólito plano | 4 | 6 | 7 | 5 | **22** | [`audit-project-2.md`](reports/audit-project-2.md) |
| 3 — `task-manager-api` | Python 3.12 / Flask 3.0.0 + Flask-SQLAlchemy 3.1.1 | N1 — separação parcial nominal | 4 | 5 | 9 | 5 | **23** | [`audit-project-3.md`](reports/audit-project-3.md) |

Nos três relatórios, **todo achado carrega `arquivo:linha`**, a ordem
é CRITICAL → LOW, e o mínimo de 5 achados com pelo menos 1 CRITICAL/HIGH foi
superado com folga. A auditoria do projeto 1 encontrou **27 problemas contra os
17 da análise manual**; a do projeto 2, **22 contra 15**; a do projeto 3, **23
contra 15**. Os achados extras foram
majoritariamente MEDIUM/LOW de varredura exaustiva (cada ocorrência de `str(e)`,
cada `except` nu) — a análise humana agrupa, a automática enumera. Nenhum achado
CRITICAL da análise manual passou despercebido pela skill em nenhum dos três
projetos.

O projeto 3 é o caso que o enunciado destaca — "já possui alguma organização".
A skill não se deixou enganar pelo rótulo: classificou a arquitetura como **N1
nominal** observando que a pasta `services/` existe e **não é importada por
ninguém**, e encontrou 23 problemas num projeto que *parece* arrumado. O
achado-âncora combina dois deles: `to_dict()` devolvia o hash da senha em 4
endpoints (incluindo `/login`) e o hash era MD5 sem salt — juntos, um
`GET /users/1` anônimo entregava senha recuperável por rainbow table.

Um comportamento que merece registro: o relatório do projeto 2 traz uma seção de
**categorias sem ocorrência** (AP-01, AP-05, AP-07, AP-12, AP-16), provando que a
varredura foi completa — e não só que "achou 22 coisas". No projeto 2 todas as 11
queries usam parâmetros vinculados, então a skill **não** reportou SQL injection:
não houve falso positivo por analogia com o projeto 1.

### Antes / depois — Projeto 1

```
ANTES (N1 — 4 arquivos, 784 linhas)        DEPOIS (MVC em camadas)
code-smells-project/                        code-smells-project/
├── app.py         (89)  rotas + SQL        ├── wsgi.py            composition root
├── controllers.py (293) validação+fluxo    ├── app.py             entrypoint de dev
├── models.py      (315) repo + regra       └── src/
└── database.py    (87)  conexão global         ├── app_factory.py  fábrica da app
                                                ├── container.py    injeção de dependência
                                                ├── config/         settings via ambiente
                                                ├── models/         constants, errors,
                                                │                   serializers, validators
                                                ├── repositories/   5 repositórios + base
                                                ├── services/       7 services (regra)
                                                ├── controllers/    8 controllers (blueprints)
                                                ├── routers/        registro de rotas
                                                ├── database/       conexão, schema,
                                                │                   unit_of_work, escopo/request
                                                └── middlewares/    auth, erro, logging
```

Os quatro arquivos monolíticos foram dissolvidos: `app.py` deixou de conter SQL,
`models.py` deixou de conter regra de negócio, e a conexão global virou conexão
por requisição com unidade de trabalho.

### Antes / depois — Projeto 2

```
ANTES (N0 — 3 arquivos, 180 linhas)        DEPOIS (MVC em camadas — 28 módulos)
ecommerce-api-legacy/src/                   ecommerce-api-legacy/src/
├── app.js        (14)  bootstrap           ├── server.js        entrypoint HTTP
├── AppManager.js (141) God class:          ├── app.js           montagem do Express
│                      rota + regra + SQL   ├── container.js     injeção de dependência
└── utils.js      (25)  segredos,           ├── config/          index, logger
                        badCrypto,          ├── routes/          registro de rotas
                        cache global        ├── controllers/     checkout, report, user
                                            ├── services/        checkout, report, user
                                            ├── repositories/    user, course, enrollment,
                                            │                    payment, report, auditLog
                                            ├── database/        connection, schema, seed
                                            ├── gateways/        paymentGateway (porta)
                                            │                    + fakePaymentGateway
                                            ├── security/        passwordHasher (scrypt)
                                            ├── models/          errors.js
                                            └── middlewares/     auth, errorHandler,
                                                                 asyncHandler
```

A God class de 141 linhas que concentrava roteamento, regra de negócio e SQL foi
dissolvida, e o `utils.js` com segredos e criptografia caseira desapareceu. O
ponto de design mais relevante: o processamento de cartão virou uma **porta**
(`gateways/paymentGateway.js`) com implementação fake atrás dela — é o que
permite testar checkout sem tocar em serviço externo.

### Antes / depois — Projeto 3

```
ANTES (N1 nominal — 17 arquivos)           DEPOIS (MVC em camadas — 43 módulos)
task-manager-api/                           task-manager-api/
├── app.py        rotas + db.create_all     ├── app.py           entrypoint de dev
├── database.py   conexão global            ├── wsgi.py          alvo WSGI / CLI
├── models/       3 models com regra        ├── seed.py          migrations + dados demo
├── routes/       3 blueprints gordos       ├── migrations/      Alembic versionado
├── services/     existe e NINGUÉM importa  └── src/
└── utils/        helpers soltos                ├── app_factory.py  create_app()
                                                ├── container.py    repos -> services
                                                ├── config/         settings via ambiente
                                                ├── database/       db, migrate, PRAGMA FK
                                                ├── routers/        registro de blueprints
                                                ├── controllers/    task, user, category,
                                                │                   report, health, support
                                                ├── schemas/        marshmallow: valida
                                                │                   entrada, serializa saída
                                                ├── services/       task, user, auth,
                                                │                   category, report
                                                ├── repositories/   base (paginação) +
                                                │                   task, user, category
                                                ├── models/         Task, User, Category
                                                │                   + domain.py (enums)
                                                ├── security/       passwords (scrypt),
                                                │                   tokens (JWT HS256)
                                                └── middlewares/    auth, error_handler,
                                                                    logging_config
```

A diferença de partida em relação aos outros dois: aqui já **havia** pastas com
os nomes certos. O que não havia era a separação que os nomes prometiam — a
`services/` existia sem um único importador, e a regra de negócio morava nos
blueprints. A refatoração deu conteúdo à estrutura em vez de criá-la do zero, e
acrescentou as camadas que faltavam (`schemas/`, `repositories/`, `security/`).
Duas mudanças estruturais que o relatório pediu e a Fase 3 executou: o schema
saiu do `db.create_all()` no import e virou **migration Alembic versionada**, e
a serialização saiu do model (`to_dict()`) para schemas com allowlist de campos
— que é o que fecha o vazamento do hash de senha.

### Checklist de validação — Projeto 1

**Fase 1 — Análise**
- [x] Linguagem detectada corretamente — Python 3
- [x] Framework detectado corretamente — Flask 3.1.1 (+ Flask-CORS 5.0.1)
- [x] Domínio descrito corretamente — API de e-commerce (produtos, usuários, pedidos, relatório)
- [x] Número de arquivos condiz — 4 arquivos, 784 linhas

**Fase 2 — Auditoria**
- [x] Relatório segue o template das referências
- [x] Cada finding tem arquivo e linhas exatos
- [x] Findings ordenados por severidade
- [x] Mínimo de 5 findings — 27 encontrados
- [x] Detecção de APIs deprecated incluída — varredura feita; nenhuma chamada deprecated no código
- [x] Skill pausa e pede confirmação antes da Fase 3

**Fase 3 — Refatoração**
- [x] Estrutura de diretórios segue padrão MVC
- [x] Configuração extraída para módulo de config — o boot falha explicitamente sem `SECRET_KEY`
- [x] Models criados para abstrair dados — `models/` + `repositories/`
- [x] Views/Routes separadas — `controllers/` com blueprints + `routers/`
- [x] Controllers concentram o fluxo — regra movida para `services/`
- [x] Error handling centralizado — `middlewares/error_handler.py`
- [x] Entry point claro — `wsgi.py`
- [x] Aplicação inicia sem erros
- [x] Endpoints originais respondem corretamente — **19/19**

### Checklist de validação — Projeto 2

**Fase 1 — Análise**
- [x] Linguagem detectada corretamente — JavaScript / Node.js (CommonJS)
- [x] Framework detectado corretamente — Express 4.22.1 (+ sqlite3 5.1.7)
- [x] Domínio descrito corretamente — LMS com fluxo de checkout (cursos, matrículas, pagamentos)
- [x] Número de arquivos condiz — 3 arquivos, 180 linhas

**Fase 2 — Auditoria**
- [x] Relatório segue o template das referências
- [x] Cada finding tem arquivo e linhas exatos
- [x] Findings ordenados por severidade
- [x] Mínimo de 5 findings — 22 encontrados
- [x] Detecção de APIs deprecated incluída — 3 APIs deprecated apontadas
- [x] Skill pausa e pede confirmação antes da Fase 3

**Fase 3 — Refatoração**
- [x] Estrutura de diretórios segue padrão MVC
- [x] Configuração extraída para módulo de config — `config/index.js`, sem segredo no fonte
- [x] Models criados para abstrair dados — `repositories/` (6) + `models/errors.js`
- [x] Views/Routes separadas — `routes/index.js`
- [x] Controllers concentram o fluxo — regra movida para `services/`
- [x] Error handling centralizado — `middlewares/errorHandler.js`
- [x] Entry point claro — `server.js` + `container.js`
- [x] Aplicação inicia sem erros — container `node:20`
- [x] Endpoints originais respondem corretamente — 4 cenários do `api.http` + `/health` + rotas admin

### Checklist de validação — Projeto 3

**Fase 1 — Análise**
- [x] Linguagem detectada corretamente — Python 3.12
- [x] Framework detectado corretamente — Flask 3.0.0 + Flask-SQLAlchemy 3.1.1
- [x] Domínio descrito corretamente — gerenciador de tarefas (usuários, tasks, categorias, relatórios)
- [x] Número de arquivos condiz — 15 fontes
- [x] Arquitetura classificada corretamente — N1 **nominal** (`services/` sem importador)

**Fase 2 — Auditoria**
- [x] Relatório segue o template das referências
- [x] Cada finding tem arquivo e linhas exatos
- [x] Findings ordenados por severidade
- [x] Mínimo de 5 findings — 23 encontrados
- [x] Detecção de APIs deprecated incluída — 4 APIs deprecated apontadas
- [x] Skill pausa e pede confirmação antes da Fase 3 — **com permissão de escrita disponível** (ver abaixo)

**Fase 3 — Refatoração**
- [x] Estrutura de diretórios segue padrão MVC
- [x] Configuração extraída para módulo de config — `src/config/`, boot falha sem `SECRET_KEY`
- [x] Models criados para abstrair dados — `models/` + `repositories/` + `schemas/`
- [x] Views/Routes separadas — `routers/` + `controllers/`
- [x] Controllers concentram o fluxo — regra movida para `services/`
- [x] Error handling centralizado — `middlewares/error_handler.py`
- [x] Entry point claro — `wsgi.py` (produção/CLI) e `app.py` (desenvolvimento)
- [x] Aplicação inicia sem erros
- [x] Endpoints originais respondem corretamente — **22/22**

#### A prova mais forte da pausa de confirmação está no projeto 3

Nos projetos 1 e 2, as Fases 1+2 rodaram com uma allowlist somente-leitura: a
skill **não conseguiria** escrever mesmo que tentasse, então a pausa estava
garantida por construção — e isso é uma evidência fraca do critério de aceite.

No projeto 3 a execução foi disparada **com `Write` liberado**, de propósito. A
skill parou em `Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]` e
**não tocou em nenhum arquivo do projeto** tendo permissão para tocar —
conferido por fora do log da skill: o `git status` acusava apenas a pasta
`.claude/` copiada, e nenhum `.py` com data de modificação do dia. É o teste
real do comportamento da skill, não do sandbox em volta dela.

### Logs — aplicação rodando após a refatoração (projeto 1)

```
================================
PHASE 3: REFACTORING COMPLETE
================================
## Validation
  ✓ Application boots without errors
  ✓ All endpoints respond correctly
  ✓ Zero critical anti-patterns remaining
================================
```

Validação conferida de forma independente, com a aplicação de pé:

- **Boot:** sobe limpo, 19 rotas registradas, zero tracebacks. O comportamento
  inverso também foi confirmado: **sem `SECRET_KEY` o boot falha explicitamente**
  com `ConfiguracaoAusente`, como a auditoria exigia.
- **Endpoints:** 68 verificações HTTP contra o servidor real, todas passando,
  zero respostas 500. Paridade de rotas conferida contra a lista original —
  nenhuma rota ausente, nenhuma a mais (**19/19**).
- **Exploits da auditoria, agora fechados e testados:** bypass de login com
  `admin@loja.com' -- ` → **401**; `UNION SELECT` na busca → lista vazia;
  `DROP TABLE` via campo `nome` → gravado como texto, tabela intacta;
  `/admin/query` → **403** sem executar; `/admin/reset-db` → 401 sem token, 403
  com token de cliente, 200 só com admin.
- **Concorrência** (o achado HIGH mais sutil): 14 pedidos simultâneos contra
  estoque 8 → exatamente **8 criados, 6 recusados, estoque final 0**, nunca
  negativo. O código original vendia a descoberto nesse cenário.
- **Varredura final:** nenhum `print`, `str(e)`, segredo hardcoded,
  `check_same_thread` ou global mutável no código novo.

### Logs — o projeto 2 **antes** da refatoração (baseline medido)

Execução do legado em container `node:20`, para registrar o ponto de partida e
conferir os achados da auditoria na prática:

```
[200] POST   /api/checkout               -> {"msg":"Sucesso","enrollment_id":2}
[400] POST   /api/checkout (cartão 5…)   -> Pagamento recusado
[200] GET    /api/admin/financial-report -> [{"course":"Clean Architecture","revenue":997,…}]
[200] DELETE /api/users/1                -> Usuário deletado, mas as matrículas e
                                            pagamentos ficaram sujos no banco.

--- log do servidor ---
Processando cartão 4111222233334444 na chave pk_live_1234567890abcdef
[LOG] Salvando no cache: last_checkout_2
```

Três achados confirmados em execução: o **PAN completo e a chave `pk_live_`
aparecem no log** a cada checkout; o **checkout sem `pwd` responde 200** (cria
conta com a senha padrão `123456`); e, depois do `DELETE /api/users/1`, o
relatório financeiro **continua faturando R$997 para `"student":"Unknown"`** —
os órfãos que a própria resposta da API admite.

### Logs — o projeto 2 **depois** da refatoração

Mesmo container `node:20`, mesma bateria, com a aplicação de pé em
`localhost:3000`:

```
[200] POST   /api/checkout               -> matrícula criada
[400] POST   /api/checkout (cartão 5…)   -> {"error":{"code":"PAYMENT_DECLINED",…}}
[400] POST   /api/checkout (sem pwd)     -> {"error":{"code":"VALIDATION_ERROR",…}}
[404] POST   /api/checkout (curso 999)   -> {"error":{"code":"NOT_FOUND",…}}
[200] GET    /health
[401] GET    /api/admin/financial-report -> sem credencial
[200] GET    /api/admin/financial-report -> com credencial
[204] DELETE /api/users/1                -> e [204] de novo (idempotente)
[404] DELETE /api/users/999

--- log do servidor ---
Processando cartão **** 4444
```

Os três exploits do baseline, re-verificados e fechados:

- **PAN completo e chave `pk_live_` no log** → **0 ocorrências**. O gateway loga
  apenas os 4 últimos dígitos, e a senha em claro sumiu do log.
- **Checkout sem `pwd` respondendo 200** → agora `400 VALIDATION_ERROR`; não
  existe mais criação silenciosa de conta com senha padrão.
- **Receita órfã depois do `DELETE /api/users/1`** → o relatório financeiro
  **preserva os R$997** e atribui a `"Usuário removido"`, em vez de orfanar as
  linhas sob `"Unknown"`.

### Logs — o projeto 3 **depois** da refatoração

```
================================
PHASE 3: REFACTORING COMPLETE
================================
## Validation
  ✓ Application boots without errors
  ✓ All endpoints respond correctly
  ✓ Zero critical anti-patterns remaining
================================
```

Validação conferida de forma independente, com a aplicação de pé em
`127.0.0.1:5000`:

- **Boot:** `python app.py` sobe sem traceback, debug desligado, bind em
  `127.0.0.1` (antes era `0.0.0.0` com `debug=True` fixo no código). O seed
  aplica as migrations e popula os dados de demonstração.
- **Endpoints:** **22/22 rotas originais respondem** — 7 de usuário, 7 de task,
  6 de relatório/categoria, mais `/` e `/health`. **Zero respostas 500** na
  varredura inteira.
- **AP-03 fechado (o achado-âncora):** `GET /users/1` e `POST /login` retornam
  **0 ocorrências** de `password` no corpo. O campo não existe mais na saída, e
  a coluna foi renomeada para `password_hash` para a intenção ficar óbvia.
- **AP-06 fechado onde doía:** `PUT /users/2 {"role":"admin"}` sem token →
  **401**. No código original, qualquer anônimo virava admin por essa rota.
- **`500` → `400` em entrada inválida:** corpo `null`, `title` ausente,
  `due_date` inválida, `status` inexistente e requisição sem `Content-Type`
  todos respondem **400**; `404` segue preservado para recurso inexistente.
- **N+1 eliminado:** `GET /tasks`, `/users` e `/categories` passaram a fazer 2
  queries cada (antes, `GET /tasks` fazia 1+2N).

### Como a skill se comportou em stacks diferentes

- **Mesma skill, zero adaptação.** Os arquivos copiados para o projeto 2 são
  byte-idênticos aos do projeto 1 (`diff -r` limpo). A detecção de stack e a
  classificação funcionaram sem tocar em uma linha das referências.
- **A classificação seguiu o contexto, não o rótulo.** O mesmo AP-15
  (`console.log` como log) saiu como **LOW** no projeto 1 e como **CRITICAL** no
  projeto 2, porque lá a linha logava número de cartão — e a promoção veio
  justificada no achado.
- **Sem falso positivo por analogia.** O projeto 1 é um festival de SQL injection;
  o projeto 2, que usa parâmetros vinculados em 11 de 11 queries, não recebeu
  nenhum achado de AP-01 — e a categoria aparece na lista de "sem ocorrência"
  com as linhas conferidas.
- **Os achados de N0 vieram diferentes dos de N1.** No monólito Node, a skill
  produziu mais HIGH (6) do que no projeto Python (4), concentrados em ausência
  de persistência, transação e integridade referencial — problemas que o projeto
  1 não tinha porque já usava um banco em arquivo com schema declarado.
- **A terceira cópia, também byte-idêntica, voltou para Python — e não repetiu o
  projeto 1.** O projeto 3 é Flask como o projeto 1, mas com SQLAlchemy em vez de
  SQL cru: a skill classificou a arquitetura de partida de forma diferente (N1
  *nominal*, pela `services/` órfã), não reportou um único AP-01 (o ORM
  parametriza por construção) e produziu um conjunto de achados centrado em
  serialização, hash e N+1 de ORM. A prova de agnosticismo não é só "roda em
  outra linguagem" — é **não copiar o diagnóstico do projeto anterior na mesma
  linguagem**.
- **A Fase 3 se adaptou ao ponto de partida.** No projeto 2 (N0) ela criou a
  estrutura inteira do zero; no projeto 3 (N1 nominal) ela **deu conteúdo a
  pastas que já existiam** e acrescentou só as camadas ausentes. As 12
  transformações do playbook não foram aplicadas em bloco em lugar nenhum — em
  cada projeto entrou o subconjunto que os achados justificavam.

---

## D) Como Executar

### Pré-requisitos

- **Claude Code** instalado e autenticado (`claude --version`).
- **Projetos 1 e 3:** Python 3.12+ com as dependências de cada projeto
  (`pip install -r requirements.txt`, de preferência em virtualenv).
- **Projeto 2:** Node 20+ **ou** Docker (o projeto pode ser instalado e validado
  dentro de um container `node:20`, sem instalar Node na máquina).

A skill é **project-local**: cada projeto tem a sua cópia em
`<projeto>/.claude/skills/refactor-arch/`. Para levá-la a um projeto novo, basta
copiar a pasta inteira — não há configuração global.

### Executando a skill

```bash
# Projeto 1 — Python/Flask
cd code-smells-project
claude "/refactor-arch"

# Projeto 2 — Node/Express
cd ecommerce-api-legacy
claude "/refactor-arch"

# Projeto 3 — Python/Flask
cd task-manager-api
claude "/refactor-arch"
```

A skill roda a Fase 1, depois a Fase 2, e **para**, perguntando
`Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]`. Responder `y`
libera a Fase 3. Indique o número do projeto no pedido (ex.:
`/refactor-arch este é o projeto 2`) para que o relatório seja salvo em
`reports/audit-project-<n>.md`.

Para rodar de forma não-interativa, separando as fases — o modo usado nesta
entrega:

```bash
# Fases 1 e 2, sem poder de escrita (a pausa fica garantida por construção)
cd code-smells-project
claude -p "/refactor-arch projeto 1. Rode as Fases 1 e 2 e pare na confirmação." \
  --allowedTools "Read,Grep,Glob" --add-dir ..

# Fase 3, depois da confirmação humana
claude -p "/refactor-arch projeto 1 — Fase 2 confirmada. Execute a Fase 3; a auditoria está em ../reports/audit-project-1.md." \
  --permission-mode acceptEdits --add-dir .. --allowedTools "Read,Grep,Glob,Write,Edit,Bash"
```

> `--add-dir ..` é necessário porque `reports/` fica na raiz do repositório, fora
> do diretório do projeto. Com a allowlist somente-leitura das Fases 1 e 2, a
> skill imprime o relatório mas não consegue salvá-lo — some `Write` à allowlist
> se preferir que ela grave o arquivo sozinha.

### Validando a refatoração

**Projetos 1 e 3 (Python/Flask):**

```bash
cd code-smells-project
python -m venv .venv && . .venv/Scripts/activate   # Linux/macOS: . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                                # SECRET_KEY é obrigatória
python app.py                                       # deve subir sem tracebacks
curl -s http://localhost:5000/produtos              # endpoints originais respondem
```

Confira também o comportamento negativo, que é a prova de que a configuração saiu
do código: **sem `SECRET_KEY` definida, a aplicação deve se recusar a subir.**

**Projeto 2 (Node/Express) sem Node no host:**

```bash
docker run --rm -v "$(pwd)/ecommerce-api-legacy:/app" -w /app -p 3000:3000 node:20 \
  sh -lc "npm install && node src/app.js"

# noutro terminal
curl -X POST http://localhost:3000/api/checkout -H 'Content-Type: application/json' \
  -d '{"usr":"Guilherme","eml":"gui@fullcycle.com.br","pwd":"senhaforte","c_id":2,"card":"4111222233334444"}'
curl http://localhost:3000/api/admin/financial-report
curl -X DELETE http://localhost:3000/api/users/1
```

Os três endpoints de `api.http` devem continuar respondendo nos mesmos caminhos e
métodos após a Fase 3. Como verificação adicional, o log do servidor **não deve
mais conter número de cartão nem a chave do gateway**.
