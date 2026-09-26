# ecommerce-api-legacy

LMS API (checkout, relatório financeiro, exclusão de usuário) em Node.js/Express.
Entrada do desafio `refactor-arch` — **refatorada para MVC em camadas** na Fase 3,
a partir dos achados de [`reports/audit-project-2.md`](../reports/audit-project-2.md).

## Como rodar

```bash
cp .env.example .env     # preencha ADMIN_API_TOKEN e PAYMENT_GATEWAY_KEY
npm install
npm start
```

Sem Node no host, use um container:

```bash
docker run --rm -p 3000:3000 \
  -v "$PWD:/app" -v ecom_nm:/app/node_modules -w /app \
  node:20 sh -c "npm install && npm start"
```

A aplicação sobe em `http://localhost:3000`. O banco SQLite agora é **um arquivo
persistente** (`DB_PATH`, default `./data/app.db`), criado e migrado no boot;
os seeds de desenvolvimento só rodam com `SEED_ENABLED` ligado.

Exemplos de requisições em [`api.http`](./api.http).

## Arquitetura

```
HTTP → routes → controllers → services → repositories → database
                                  ↓
                          gateways (porta de pagamento)
```

| Camada | Pasta | Responsabilidade |
|---|---|---|
| Router | `src/routes/` | rota + método → controller, com os middlewares da rota |
| Controller | `src/controllers/` | traduz HTTP ↔ domínio; não conhece SQL |
| Service | `src/services/` | regra de negócio e transação; não conhece `req`/`res` |
| Repository | `src/repositories/` | todo o SQL, parametrizado |
| Database | `src/database/` | conexão promisificada, migrations, seeds |
| Config | `src/config/` | ambiente e logger; fonte única, nada hardcoded |
| Middlewares | `src/middlewares/` | auth, error handler central, async handler |
| Gateways | `src/gateways/` | porta do provedor de pagamento (+ implementação fake) |
| Models | `src/models/` | erros de domínio |
| Composition root | `src/container.js`, `src/server.js` | monta o grafo e sobe o servidor |

`src/AppManager.js` (God class de 142 linhas) e `src/utils.js` (segredos +
`badCrypto` + cache global) foram removidos; suas responsabilidades estão
distribuídas nas camadas acima.

## O que mudou, por achado

| Achado | Onde estava | Como foi fechado |
|---|---|---|
| AP-02 · segredos hardcoded | `utils.js:2-6` | `src/config/index.js` lê `process.env` com fail-fast; `.env` no `.gitignore`, `.env.example` versionado |
| AP-15↑ · PAN e chave live em log | `AppManager.js:45` | log estruturado (pino) com `redact`; o gateway loga só os 4 últimos dígitos |
| AP-03 · senha em texto puro | `AppManager.js:12,18` | coluna `password_hash`; seed passa pelo mesmo hasher da aplicação |
| AP-04 · `badCrypto` | `utils.js:17-23` | `crypto.scrypt` com salt por registro e comparação em tempo constante (`src/security/passwordHasher.js`) |
| AP-06 · rotas sensíveis abertas | `AppManager.js:80,131` | middleware `requerAdmin` (Bearer token de ambiente) no relatório e no DELETE |
| AP-08 · banco em memória | `AppManager.js:7` | arquivo SQLite via `DB_PATH` + migrations versionadas |
| senha default `"123456"` | `AppManager.js:68` | senha obrigatória quando a conta não existe |
| escrita multi-tabela sem transação | `AppManager.js:50-62` | `db.transaction()` envolve usuário + matrícula + pagamento + auditoria |
| exclusão sem integridade referencial | `AppManager.js:14-15,133` | FKs com `ON DELETE RESTRICT` + `PRAGMA foreign_keys = ON`; exclusão vira anonimização |
| `err` ignorado em callback | `AppManager.js:92-93,104,106` | driver promisificado + `asyncHandler` + error handler central |
| AP-09/AP-10 · God class e fat controller | `AppManager.js:4-141` | camadas acima |
| AP-11 · cache global sem limite | `utils.js:9-14` | removido (nunca era lido) |
| AP-13 · N+1 no relatório | `AppManager.js:83-106` | uma consulta com `JOIN` e `ORDER BY` (`report.repository.js`) |
| AP-14 · erro engolido / 200 em falha | `AppManager.js:57,133-135` | error handler central; nenhuma resposta de sucesso sem commit |
| gateway simulado no controller | `AppManager.js:46` | porta `paymentGateway` + `FakePaymentGateway` injetado |
| `.verbose()` incondicional | `AppManager.js:1` | opt-in por `SQLITE_VERBOSE`, desligado em produção |
| AP-15 · `console.log` como logging | 3 pontos | pino com nível por env e campos redigidos |
| código morto (`dbUser`, `smtpUser`, `totalRevenue`) | `utils.js` | removido junto com o arquivo |
| ordem não determinística do relatório | `AppManager.js:96,119` | `ORDER BY c.id, e.id` |

## Contratos: o que foi preservado e o que mudou de propósito

Preservado — mesmos caminhos, métodos e corpo de sucesso:

- `POST /api/checkout` → `200 {"msg":"Sucesso","enrollment_id":N}`; aceita os
  campos originais `usr`/`eml`/`pwd`/`c_id`/`card` (e, como alias de migração,
  `name`/`email`/`password`/`courseId`).
- `GET /api/admin/financial-report` → `200 [{course, revenue, students:[{student, paid}]}]`.
- `DELETE /api/users/:id`.

Mudanças intencionais, todas recomendadas pela auditoria homologada:

1. **Autenticação** em `/api/admin/financial-report` e `DELETE /api/users/:id`:
   requisição sem `Authorization: Bearer <ADMIN_API_TOKEN>` agora recebe `401`.
2. **Corpo de erro padronizado** em `{"error":{"code","message"}}` (antes eram
   textos soltos como `"Bad Request"` / `"Erro DB"`); status HTTP preservados —
   400 para validação e recusa de pagamento, 404 para curso inexistente.
3. **`DELETE` responde `204`** sem corpo, no lugar do texto
   *"Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco."*.
   A exclusão passou a ser lógica com anonimização: o dado pessoal some, a
   matrícula e o pagamento continuam íntegros. Id inexistente → `404`.
4. **Senha obrigatória** para criar conta nova no checkout (antes caía em
   `"123456"` silenciosamente).
5. **Recusa de pagamento não cria mais o usuário** — a autorização acontece antes
   da transação de escrita.
6. Rota nova, aditiva: `GET /health`.

## Próximos passos (fora do escopo desta fase)

- **Rotacionar as credenciais expostas** (`pk_live_...` e a senha de banco): elas
  continuam no histórico do Git; removê-las do código não as revoga.
- Trocar o token admin estático por credencial por usuário com papel — o
  middleware já é o ponto único de aplicação.
- Persistir a `Idempotency-Key` do checkout (hoje ela é gerada e repassada ao
  gateway, mas não deduplica retries do cliente).
- Paginar a lista de alunos do relatório; tokenizar o cartão no cliente para que
  o PAN não trafegue pela aplicação.
- Avaliar Express 5 e um driver com API de Promise (`node:sqlite` em Node 22+).
