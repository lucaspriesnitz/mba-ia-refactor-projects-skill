# Referência — Playbook de Transformação (Fase 3)

Cada padrão é uma transformação **antes → depois** acionável, ligada a um
anti-pattern do catálogo. Aplique na ordem de severidade (segurança primeiro).
Os exemplos são ilustrativos — adapte à linguagem do projeto, preserve o
contrato do endpoint.

---

## T-01 · Parametrizar query (fecha AP-01) — CRITICAL

**Antes**
```python
cursor.execute("SELECT * FROM produtos WHERE id = " + str(id))
```
**Depois**
```python
cursor.execute("SELECT * FROM produtos WHERE id = ?", (id,))
```
Regra: nenhum input entra na string SQL. Vale para `INSERT`/`UPDATE` também —
troque a concatenação por placeholders e uma tupla/lista de parâmetros.

---

## T-02 · Segredo para variável de ambiente (fecha AP-02) — CRITICAL

**Antes**
```python
app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"
```
```javascript
const config = { paymentGatewayKey: "pk_live_1234567890abcdef" };
```
**Depois**
```python
# config/settings.py
import os
SECRET_KEY = os.environ["SECRET_KEY"]          # falha cedo se ausente
```
```javascript
// config/index.js
module.exports = { paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY };
```
Adicione `.env` ao `.gitignore` e um `.env.example` com as chaves (sem valores).

---

## T-03 · Hash de senha (fecha AP-03/AP-04) — CRITICAL

**Antes**
```javascript
function badCrypto(pwd) { /* laço de base64 caseiro */ }
db.run("INSERT INTO users (pass) VALUES ('123')");
```
**Depois**
```javascript
const bcrypt = require('bcrypt');
const hash = await bcrypt.hash(pwd, 12);
// login: const ok = await bcrypt.compare(input, user.pass);
```
Nunca comparar texto puro; nunca hash caseiro. Em Python: `bcrypt`/`argon2-cffi`.

---

## T-04 · Remover endpoint de execução arbitrária (fecha AP-05) — CRITICAL

**Antes**
```python
@app.route("/admin/query", methods=["POST"])
def executar_query():
    db.cursor().execute(request.get_json()["sql"])   # RCE no banco
```
**Depois** — deletar a rota. Operação administrativa vira script versionado ou
comando de manutenção com autenticação; nunca SQL vindo do cliente.

---

## T-05 · Proteger rota sensível com auth (fecha AP-06) — CRITICAL/HIGH

**Antes**
```python
@app.route("/admin/reset-db", methods=["POST"])
def reset_database(): ...        # qualquer um reseta

@app.route("/produtos", methods=["POST"])
def criar_produto(): ...         # anonimo cria

@app.route("/produtos/<int:id>", methods=["PUT"])
def atualizar_produto(id): ...   # anonimo zera o preco

@app.route("/pedidos/usuario/<int:uid>")
def pedidos_do_usuario(uid): ... # qualquer um le o historico de qualquer um
```
**Depois**
```python
@app.route("/admin/reset-db", methods=["POST"])
@require_auth(role="admin")      # middleware/decorator central
def reset_database(): ...

@app.route("/produtos", methods=["POST"])
@require_auth(role="admin")      # escrita em dado de negocio: admin
def criar_produto(): ...

@app.route("/produtos/<int:id>", methods=["PUT"])
@require_auth(role="admin")
def atualizar_produto(id): ...

@app.route("/pedidos/usuario/<int:uid>")
@require_auth()                  # autenticar NAO basta aqui:
def pedidos_do_usuario(uid):
    portador = usuario_atual()
    if portador["papel"] != "admin" and portador["sub"] != uid:
        raise NaoAutorizado()    # ... precisa de POSSE
    ...
```
Autenticação e autorização como middleware reutilizável, não checagem colada em
cada handler. Três regras que esta transformação carrega:

1. **Enumere as rotas de escrita método a método.** Proteger o `DELETE` e deixar o
   `POST`/`PUT` da mesma entidade aberto é o erro mais comum — e o mais caro, porque
   dá a impressão de que o AP-06 foi tratado.
2. **Escrita anônima em dado de negócio é CRITICAL**, não HIGH. Não precisa de
   `DELETE` para o dano existir: anônimo zerando preço já é dano imediato.
3. **Rota "ver o meu" exige posse**, não só credencial. Com apenas autenticação ela
   continua sendo enumeração por id, bastando qualquer conta.

---

## T-06 · Config de produção fora do código (fecha AP-07) — HIGH

**Antes**
```python
app.config["DEBUG"] = True
```
**Depois**
```python
app.config["DEBUG"] = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
```
Default seguro (`false`); dev liga por env. Vale para qualquer flag de dev.

---

## T-07 · Persistência real / conexão gerenciada (fecha AP-08) — HIGH/MEDIUM

**Antes**
```javascript
this.db = new sqlite3.Database(':memory:');   // perde tudo no restart
```
**Depois**
```javascript
this.db = new sqlite3.Database(process.env.DB_PATH || './data/app.db');
```
Em Python, trocar o singleton global por conexão por requisição (ou pool);
remover `check_same_thread=False` compartilhado.

---

## T-08 · Extrair regra de negócio para service (fecha AP-10/AP-09) — MEDIUM

**Antes** (tudo no handler)
```javascript
app.post('/api/checkout', (req, res) => {
    // valida, consulta curso, cria matrícula, processa pagamento, grava... 
});
```
**Depois**
```javascript
// controllers/checkout.controller.js
app.post('/api/checkout', async (req, res, next) => {
  try {
    const result = await checkoutService.enroll(req.body);
    res.status(201).json(result);
  } catch (e) { next(e); }
});
// services/checkout.service.js  → regra + repositories.
```
Controller só traduz HTTP↔service; regra fica testável sem HTTP.

---

## T-09 · Mover SQL para repository (fecha AP-09) — MEDIUM

**Antes** (rota/classe fala SQL direto)
```javascript
this.db.get("SELECT * FROM courses WHERE id = ?", [cid], cb);
```
**Depois**
```javascript
// repositories/course.repository.js
findActiveById(id) { return this.db.get(
  "SELECT * FROM courses WHERE id = ? AND active = 1", [id]); }
```
O service chama `courseRepo.findActiveById(id)`; nenhuma camada acima conhece SQL.

---

## T-10 · Eliminar estado global mutável (fecha AP-11) — MEDIUM

**Antes**
```javascript
let globalCache = {};
let totalRevenue = 0;
module.exports = { globalCache, totalRevenue };
```
**Depois** — estado explícito, com dono: um `CacheService` injetado, ou
recalcular a partir do banco (`SELECT SUM(amount) FROM payments`). Nada de
acumulador de módulo mutado por request.

---

## T-11 · Desduplicar mapeamento/validação (fecha AP-12) — MEDIUM

**Antes** — o mesmo `row → dict` copiado em cada função de `models.py`.
**Depois**
```python
def _to_produto(row):
    return {k: row[k] for k in
            ("id","nome","descricao","preco","estoque","categoria","ativo","criado_em")}
```
Uma função de serialização; as queries só retornam linhas e passam por ela.

---

## T-12 · Tratamento de erro central (fecha AP-14/AP-15) — MEDIUM/LOW

**Antes**
```python
except Exception as e:
    return jsonify({"erro": str(e)}), 500     # vaza interno, repetido em todo handler
```
**Depois**
```python
@app.errorhandler(Exception)
def handle(e):
    app.logger.exception(e)                   # loga interno
    return jsonify({"erro": "erro interno"}), 500   # resposta genérica
```
Um handler central; controllers deixam de ter `try/except` gigante. Trocar
`print`/`console.log` por logger com nível (`app.logger`, `pino`/`winston`) —
e nunca logar cartão/segredo (ver `AppManager.js:45`).

---

## Ordem de aplicação

1. **T-01..T-04** — CRITICAL de segurança (SQLi, segredo, senha, RCE).
2. **T-05..T-07** — HIGH (auth, config, persistência).
3. **T-08..T-11** — reestruturação em camadas (MEDIUM).
4. **T-12** — erro/logging (limpeza final).

Depois de cada bloco crítico, revalide o boot para não acumular quebra. O
critério de pronto é o bloco `PHASE 3: REFACTORING COMPLETE`: app sobe,
endpoints respondem, zero CRITICAL restante.
