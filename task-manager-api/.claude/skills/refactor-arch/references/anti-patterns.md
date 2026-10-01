# Referência — Catálogo de Anti-patterns (Fase 2)

Catálogo **agnóstico** para classificar achados. Cada entrada traz: o **sinal**
que dispara a detecção (independente de linguagem), a **severidade** e a
**recomendação**. Varra o catálogo INTEIRO contra cada arquivo-fonte — mesmo em
projeto pequeno.

## Escala de severidade

| Nível | Critério | Exemplos |
|---|---|---|
| **CRITICAL** | Exploração remota, vazamento de dado, corrupção. Fecha primeiro. | SQL injection, segredo commitado, senha em texto puro, endpoint que executa query arbitrária |
| **HIGH** | Falha grave sem exploração trivial, ou risco em produção. | `DEBUG` ligado, banco volátil, ausência total de autenticação em rota sensível |
| **MEDIUM** | Dívida arquitetural que trava evolução/manutenção. | God module, regra de negócio na rota, estado global mutável, N+1 |
| **LOW** | Higiene/qualidade sem risco imediato. | `print`/`console.log` como log, código morto, número mágico |

Regra de ancoragem: **todo achado cita `arquivo:linha`**. "Código ruim" não é
achado; "segredo hardcoded em `utils.js:3`" é.

---

## Catálogo

### AP-01 · Injeção de SQL por concatenação de string — CRITICAL
**Sinal:** query montada com `+`, template string ou f-string interpolando input
(`"... WHERE id = " + id`, `` `... WHERE x = ${v}` ``, `f"... {v}"`) em vez de
parâmetros vinculados (`?`, `%s`, `:nome`).
**Impacto:** um atacante lê/apaga a base inteira.
**Recomendação:** query parametrizada / prepared statement, sempre. Nenhum input
entra na string SQL.
*Visto em `models.py:28` (`"SELECT * FROM produtos WHERE id = " + str(id)`).*

### AP-02 · Segredo hardcoded no código — CRITICAL
**Sinal:** chave, senha, token ou string de conexão literal no fonte
(`SECRET_KEY = "..."`, `dbPass: "..."`, `paymentGatewayKey: "pk_live_..."`).
**Impacto:** vaza no repositório/histórico; rotação impossível sem redeploy.
**Recomendação:** ler de variável de ambiente (`os.environ`, `process.env`) via
módulo de config; `.env` fora do versionamento.
*Visto em `app.py:7` e `utils.js:2-4`.*

### AP-03 · Senha armazenada/transmitida em texto puro — CRITICAL
**Sinal:** coluna `senha`/`pass TEXT` populada com o valor cru; `INSERT ... VALUES
('123')`; comparação de login `senha == input`.
**Impacto:** vazamento do banco expõe todas as credenciais.
**Recomendação:** hash com algoritmo forte e salt (bcrypt/argon2/scrypt). Nunca
comparar texto puro.
*Visto em `AppManager.js:18` e no schema `usuarios.senha TEXT`.*

### AP-04 · Criptografia caseira ("roll your own crypto") — CRITICAL
**Sinal:** função própria de hash/cifra com laço manual, `base64`/XOR/substring
apresentados como segurança.
**Impacto:** reversível trivialmente; falsa sensação de proteção.
**Recomendação:** biblioteca padrão auditada (bcrypt/argon2, `crypto` nativo).
*Visto em `utils.js:17` (`badCrypto` com laço de `base64`).*

### AP-05 · Endpoint que executa entrada arbitrária — CRITICAL
**Sinal:** rota que recebe SQL/comando/código do corpo e roda (`/admin/query`,
`eval(req.body)`, `exec(input)`).
**Impacto:** RCE / acesso total ao banco a partir da rede.
**Recomendação:** remover. Operação administrativa é código versionado com
autenticação, não string vinda do cliente.
*Visto em `app.py:59` (`/admin/query`).*

### AP-06 · Rota destrutiva/sensível/de escrita sem autenticação — HIGH/CRITICAL
**Sinal:** rota que apaga ou reseta dados, expõe informação privada, **ou escreve em
dado de negócio** sem checagem de identidade/permissão (`/admin/reset-db`, `DELETE`
aberto, `POST`/`PUT` de catálogo aberto).
**Severidade:** **CRITICAL** quando, sem qualquer autenticação, a rota permite
operação destrutiva (DELETE, reset), escalada de privilégio (alterar role/senha de
outro usuário), exposição de dados sensíveis, **ou qualquer escrita em dado de
negócio** (criar/editar produto, preço, estoque, pedido, status). HIGH só para
**leitura** de dado não-sensível que ainda assim deveria ser restrita.
**Impacto:** qualquer um destrói, lê dados, toma conta de contas ou adultera o
catálogo — anônimo zerando o preço de um produto é dano de negócio imediato, mesmo
sem `DELETE` nenhum.
**Recomendação:** middleware/decorator de auth + autorização por papel; remover o
que não deveria existir. **Na Fase 3, a correção prevalece sobre preservar o
contrato original da rota** — a rota passa a exigir credencial, e isso é a
correção esperada, não uma quebra de contrato. Quando a rota é "ver o meu", a
correção não para na autenticação: exige **posse** (o próprio id, ou admin), senão a
rota continua sendo enumeração por id com credencial qualquer.
**Armadilha de varredura, e ela já custou uma reprova:** `DELETE` salta aos olhos e
`POST`/`PUT` não. Enumere as rotas de escrita **método a método** e confira o
decorator de cada uma — o padrão real é fechar a destrutiva e esquecer a criação e a
edição ao lado dela. Na Fase 2, liste a matriz `método × rota × decorator` antes de
concluir que o AP-06 está coberto.
*Visto em `app.py:47` (`/admin/reset-db` sem auth) e em `controllers.py:24,64`
(`POST /produtos` e `PUT /produtos/<id>` sem auth, ao lado de um `DELETE` protegido).*

### AP-07 · `DEBUG`/modo verboso ligado no código — HIGH
**Sinal:** `DEBUG = True`, `app.debug`, stack trace exposto ao cliente, config de
dev fixa no fonte.
**Impacto:** vaza stack traces e caminhos; em Flask, habilita o console de debug
(execução remota).
**Recomendação:** ligar só em dev via env var; produção com `DEBUG=False`.
*Visto em `app.py:8`.*

### AP-08 · Banco volátil / conexão global mutável — HIGH/MEDIUM
**Sinal:** `sqlite3.Database(':memory:')` (perde tudo no restart) → HIGH;
singleton global de conexão compartilhado com `check_same_thread=False` → MEDIUM.
**Impacto:** perda de dados; corrida entre requisições concorrentes.
**Recomendação:** persistência real; conexão por requisição ou pool gerenciado.
*Visto em `AppManager.js:7` (`:memory:`) e `database.py:4,10`.*

### AP-09 · God module / God class — MEDIUM
**Sinal:** um arquivo/classe concentra rotas + regra de negócio + acesso a dados;
centenas de linhas; uma classe que "faz tudo".
**Impacto:** impossível testar/evoluir isoladamente; mudança em um ponto quebra
outro.
**Recomendação:** separar em camadas (controller / service / repository) — ver
`mvc-guidelines.md`.
*Visto em `AppManager.js` (initDb + rotas + pagamento na mesma classe).*

### AP-10 · Regra de negócio na camada de rota (fat controller) — MEDIUM
**Sinal:** validação, cálculo, orquestração de várias tabelas e persistência
dentro do handler HTTP; o controller conhece SQL.
**Impacto:** lógica não reutilizável nem testável fora do HTTP.
**Recomendação:** controller só traduz HTTP↔domínio; regra vai para `services/`,
dados para `repositories/`.
*Visto no handler `/api/checkout` (`AppManager.js:28+`) e em `controllers.py:24+`.*

### AP-11 · Estado global mutável — MEDIUM
**Sinal:** cache/acumulador em variável de módulo (`globalCache = {}`,
`totalRevenue = 0`, `db_connection` global) mutado a cada request.
**Impacto:** vazamento entre requisições, resultados não determinísticos, difícil
de escalar horizontalmente.
**Recomendação:** estado por requisição ou store explícito; injeção de
dependência em vez de global.
*Visto em `utils.js:9-10`.*

### AP-12 · Duplicação de lógica (WET) — MEDIUM
**Sinal:** o mesmo bloco repetido (mapeamento `row → dict` copiado em cada
função, validação idêntica colada em vários handlers).
**Impacto:** correção precisa ser feita em N lugares; divergência silenciosa.
**Recomendação:** extrair para função/serializer/validador único.
*Visto no mapeamento repetido de produto em `models.py` (get/getById/...).*

### AP-13 · Query em laço / N+1 — MEDIUM
**Sinal:** consulta ao banco dentro de um `for`/`map` sobre resultados de outra
consulta.
**Impacto:** latência linear no volume; derruba sob carga.
**Recomendação:** `JOIN` ou consulta única com `IN`; carregar em lote.

### AP-14 · Tratamento de erro engolido ou vazado — LOW/MEDIUM
**Sinal:** `except Exception: pass`; retornar `str(e)` cru ao cliente; `catch`
vazio; mesmo `try` gigante em torno de tudo.
**Impacto:** erros silenciados (LOW) ou vazamento de detalhes internos ao cliente
(MEDIUM).
**Recomendação:** handler de erro central; logar internamente, responder mensagem
genérica + status correto.
*Visto em `controllers.py:10-12` (`return jsonify({"erro": str(e)})`).*

### AP-15 · `print`/`console.log` como logging — LOW
**Sinal:** `print(...)`, `console.log(...)` para rastrear execução em produção.
**Impacto:** sem níveis, sem destino, ruído; pode logar dado sensível.
**Recomendação:** logger real (`logging`, `pino`/`winston`) com nível e formato.
*Visto em `controllers.py:8` e `AppManager.js:45` (loga cartão + chave!).*

### AP-16 · CORS/permissão totalmente aberta — LOW/MEDIUM
**Sinal:** `CORS(app)` sem origem, `Access-Control-Allow-Origin: *` em API com
sessão/credencial.
**Impacto:** qualquer site consome a API autenticada do usuário.
**Recomendação:** allowlist de origens explícita.
*Visto em `app.py:9`.*

---

## Detecção de APIs deprecated (obrigatória na Fase 2)

Sinalize APIs obsoletas com o **equivalente moderno**. Severidade padrão MEDIUM
(HIGH se a versão antiga tem CVE conhecido). Fontes do sinal: warnings no boot,
versão declarada no manifest, chamadas abaixo.

| Deprecated / legado | Sinal | Substituir por |
|---|---|---|
| `datetime.utcnow()` (Python 3.12+) | chamada direta | `datetime.now(datetime.UTC)` |
| `crypto.createCipher` (Node) | import/chamada | `crypto.createCipheriv` |
| `new Buffer(...)` (Node) | construtor | `Buffer.from(...)` / `Buffer.alloc(...)` |
| `url.parse()` (Node legacy) | import `url` | `new URL(...)` (WHATWG) |
| `request` / `request-promise` (npm) | dependência | `fetch` nativo / `undici` / `axios` |
| `moment` (em manutenção) | dependência | `Temporal` / `date-fns` / `Luxon` |
| Werkzeug/Flask major desatualizado | versão no manifest | atualizar; conferir breaking changes |
| `md5`/`sha1` para senha | chamada de hash | bcrypt/argon2 (ver AP-03/AP-04) |
| `pkg_resources` (Python) | import | `importlib.metadata` / `importlib.resources` |
| `body-parser` como dep separada (Express 4.16+) | dependência | `express.json()` / `express.urlencoded()` nativos |

Como agir: registre `deprecated · arquivo:linha · API atual → substituta`.
Aplique a troca na Fase 3 apenas se não quebrar contrato de endpoint; caso
contrário, registre como recomendação no relatório.

---

## Mínimo de qualidade da Fase 2

- **≥ 8 categorias do catálogo** consideradas contra o código.
- **≥ 5 findings** reais, **≥ 1 CRITICAL ou HIGH**, todos com `arquivo:linha`.
- Distribuição de severidade explícita no resumo (quantos CRITICAL/HIGH/MEDIUM/LOW).
- Seção de deprecated preenchida (ou "nenhuma API deprecated detectada").
