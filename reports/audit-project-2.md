# Relatório de Auditoria Arquitetural — ecommerce-api-legacy

- **Data:** 2026-09-24
- **Stack:** JavaScript (Node.js / CommonJS) / Express 4.22.1 + sqlite3 5.1.7
- **Arquitetura de partida:** N0 — monólito plano (God class `AppManager` concentra rota + regra + SQL)
- **Arquivos analisados:** 3 fontes (`src/app.js`, `src/AppManager.js`, `src/utils.js`) + `package.json`, `package-lock.json`, `api.http`

## Resumo por severidade

| Severidade | Qtd |
|---|---|
| CRITICAL | 4 |
| HIGH | 6 |
| MEDIUM | 7 |
| LOW | 5 |
| **Total** | **22** |

APIs deprecated / stack legada detectadas: 3.

---

## Achados

### 🔴 CRITICAL

#### [AP-02] Segredos de produção hardcoded no fonte — `src/utils.js:2-6`
- **O que:** o objeto `config` carrega literais de produção: `dbPass: "senha_super_secreta_prod_123"` (`utils.js:3`), `paymentGatewayKey: "pk_live_1234567890abcdef"` (`utils.js:4`) — prefixo `pk_live_` indica chave **live**, não sandbox —, além de `dbUser` (`utils.js:2`), `smtpUser` (`utils.js:5`) e `port` (`utils.js:6`). Nada é lido de `process.env`.
- **Impacto:** as credenciais já estão no histórico do Git; qualquer pessoa com acesso ao repositório (ou a um clone/fork/backup) transaciona no gateway de pagamento real. Rotação exige alterar código e redeployar.
- **Recomendação:** módulo `config/` lendo `process.env` com validação de presença no boot (fail-fast); `.env` no `.gitignore` + `.env.example` versionado. As chaves expostas precisam ser **revogadas e rotacionadas**, não só removidas do código — o histórico permanece.

#### [AP-15 ↑ CRITICAL] Número do cartão e chave do gateway impressos em log — `src/AppManager.js:45`
- **O que:** `console.log(\`Processando cartão ${cc} na chave ${config.paymentGatewayKey}\`)` grava o PAN completo recebido em `req.body.card` (`AppManager.js:33`) junto da chave live do gateway, a cada checkout.
- **Impacto:** vazamento de dado de cartão em stdout/arquivo de log/agregador — violação direta de PCI-DSS (PAN nunca pode ser logado em claro) e segunda via de vazamento da chave do gateway. Logs costumam ter retenção longa e controle de acesso mais fraco que o banco.
- **Recomendação:** remover a linha. Se precisar de rastro, logar apenas os 4 últimos dígitos e um id de transação, via logger estruturado com redação de campos sensíveis. Escalado de LOW (AP-15) para CRITICAL porque o critério da escala é "vazamento de dado".

#### [AP-03] Senha em texto puro no schema e no seed — `src/AppManager.js:12,18`
- **O que:** a coluna é declarada como `pass TEXT` (`AppManager.js:12`) e o seed insere a senha crua `'123'` (`AppManager.js:18`). O único caminho que aplica alguma transformação é `AppManager.js:69`, e ainda assim com `badCrypto` (ver AP-04) — a coluna guarda valores heterogêneos (texto puro e pseudo-hash).
- **Impacto:** o dump do banco entrega credenciais utilizáveis; como usuários reciclam senhas, o dano extrapola esta aplicação.
- **Recomendação:** coluna `password_hash`, populada exclusivamente por bcrypt/argon2id com salt por usuário; seeds usando o mesmo caminho de hash da aplicação; nunca comparar em texto puro.

#### [AP-04] Criptografia caseira (`badCrypto`) — `src/utils.js:17-23`
- **O que:** função própria que concatena 10 000 vezes os 2 primeiros caracteres de `Buffer.from(pwd).toString('base64')` (`utils.js:19-21`) e devolve `hash.substring(0, 10)` (`utils.js:22`). O laço é puro teatro: a saída é o mesmo par de caracteres repetido 5 vezes. Sem salt, determinística, e derivada apenas do **primeiro byte e meio** da senha.
- **Impacto:** reversível trivialmente — o espaço de saída tem algumas centenas de valores, e `"senhaforte"` e `"senhaqualquer"` colidem (ambas começam com `se`). Qualquer senha é recuperável por tabela pré-computada em segundos. Pior que não ter hash, porque cria falsa confiança.
- **Recomendação:** deletar `badCrypto` e usar `bcrypt`/`argon2` (ou `crypto.scrypt` nativo) com custo calibrado e salt aleatório por registro.

---

### 🟠 HIGH

#### [AP-06] Rotas sensíveis e destrutivas sem autenticação — `src/AppManager.js:80, 131`
- **O que:** `GET /api/admin/financial-report` (`AppManager.js:80`) devolve receita por curso e a lista nominal de alunos com valores pagos (`AppManager.js:112-115`); `DELETE /api/users/:id` (`AppManager.js:131`) apaga qualquer usuário por id. Nenhuma das duas tem middleware de autenticação, verificação de papel ou sequer um token estático — não existe **nenhum** mecanismo de auth em todo o projeto.
- **Impacto:** qualquer requisição anônima na rede lê o faturamento completo e os dados pessoais de todos os alunos, ou apaga a base de usuários um id por vez.
- **Recomendação:** middleware de autenticação aplicado antes das rotas, com autorização por papel para o prefixo `/api/admin`. `DELETE /api/users/:id` só deve aceitar o próprio usuário ou um admin.

#### [AP-08] Banco volátil em memória — `src/AppManager.js:7`
- **O que:** `new sqlite3.Database(':memory:')` no construtor, com o schema e os seeds recriados a cada boot (`AppManager.js:10-23`).
- **Impacto:** todo checkout, matrícula e pagamento desaparece no restart ou crash do processo. Impossibilita mais de uma instância (cada worker teria seu próprio banco isolado) e torna o relatório financeiro ficção.
- **Recomendação:** persistência real (arquivo SQLite fora do bundle ou Postgres) com caminho/URL vindo de env; schema em migrations versionadas, separado do código de aplicação; seeds só em ambiente de desenvolvimento.

#### [extra] Senha padrão previsível para usuário criado no checkout — `src/AppManager.js:68`
- **O que:** `badCrypto(p || "123456")` — quando o corpo da requisição não traz `pwd`, o usuário é criado silenciosamente com a senha `"123456"`. A validação de entrada em `AppManager.js:35` exige `u`, `e`, `cid` e `cc`, mas **não** `p`, então esse caminho é alcançável pela API pública.
- **Impacto:** contas criadas com credencial conhecida e idêntica para todos; tomada de conta trivial por quem souber o e-mail.
- **Recomendação:** ou exigir `password` na validação, ou criar a conta sem senha utilizável e disparar fluxo de definição por token de uso único. Nunca um default literal.

#### [extra] Escrita multi-tabela no checkout sem transação — `src/AppManager.js:50-62`
- **O que:** `INSERT enrollments` (`:50`), `INSERT payments` (`:54`) e `INSERT audit_logs` (`:57`) são executados como três statements independentes, encadeados por callback. Cada falha intermediária responde 500 (`:51`, `:55`) deixando o que já foi gravado no banco.
- **Impacto:** estado financeiro inconsistente — matrícula sem pagamento correspondente (falha em `:54`) ou pagamento sem trilha de auditoria (falha em `:57`). O relatório de `AppManager.js:80` então contabiliza aluno com `paid: 0`, e não há como distinguir isso de inadimplência real.
- **Recomendação:** envolver o bloco em `BEGIN`/`COMMIT`/`ROLLBACK` numa única unidade de trabalho, exposta pela camada de repositório; o service de checkout orquestra a transação e só responde sucesso após o commit.

#### [extra] Exclusão de usuário sem integridade referencial — `src/AppManager.js:14-15, 133`
- **O que:** `enrollments` (`:14`) e `payments` (`:15`) guardam `user_id`/`enrollment_id` como inteiros soltos, sem `FOREIGN KEY` nem `ON DELETE`; o SQLite tampouco tem `PRAGMA foreign_keys = ON`. O `DELETE FROM users` em `:133` remove só a linha do usuário — a própria resposta em `:135` admite o problema ("as matrículas e pagamentos ficaram sujos no banco").
- **Impacto:** matrículas e pagamentos órfãos permanentemente. O relatório financeiro passa a emitir `student: 'Unknown'` (`AppManager.js:113`) com receita ainda somada, e não existe caminho de recuperação do vínculo.
- **Recomendação:** declarar FKs com `ON DELETE RESTRICT` (ou `CASCADE`, conforme a regra de negócio) e habilitar o enforcement; para dados financeiros, preferir soft delete / anonimização do usuário a remoção física.

#### [extra] Callbacks do relatório sem tratamento de erro derrubam ou travam a requisição — `src/AppManager.js:92-93, 104, 106`
- **O que:** em `:92` o parâmetro `err` de `db.all(...)` é ignorado e a linha seguinte faz `enrollments.length` (`:93`) — se a query falhar, `enrollments` vem `undefined` e o acesso lança `TypeError` de dentro de um callback assíncrono, sem `try`/`catch` em volta e sem handler de `uncaughtException`. Em `:104` e `:106` o `err` também é descartado.
- **Impacto:** exceção não capturada em callback derruba o processo Node inteiro — uma falha de banco vira indisponibilidade total do serviço. Nos caminhos em que não lança, os contadores `enrPending`/`coursesPending` (`:93`, `:86`) nunca chegam a zero, `res.json` nunca é chamado e a conexão fica pendurada até o timeout do cliente.
- **Recomendação:** tratar `err` em todo callback e encerrar a requisição com 500; ao migrar para a camada de repositório, usar a API baseada em Promise com `async/await` e um error handler central no Express — o que elimina a classe inteira de defeito.

---

### 🟡 MEDIUM

#### [AP-09] God class `AppManager` — `src/AppManager.js:4-141`
- **O que:** uma única classe de 142 linhas concentra conexão com o banco (`:7`), DDL (`:12-16`), seeds (`:18-21`), registro de rotas (`:28`, `:80`, `:131`), validação de entrada (`:35`), decisão de pagamento (`:46`), persistência (`:50`, `:54`, `:57`, `:69`, `:133`), auditoria (`:57`) e cache (`:59`). O nome "Manager" é o próprio sintoma — não descreve responsabilidade alguma.
- **Impacto:** nada é testável isoladamente (testar a regra de cobrança exige subir Express e SQLite); toda mudança toca o mesmo arquivo, maximizando conflito e regressão.
- **Recomendação:** quebrar em `controllers/` (HTTP), `services/` (regra), `repositories/` (SQL) e `models/`, com a infraestrutura de banco em `config/database` e o schema em migrations.

#### [AP-10] Regra de negócio dentro do handler HTTP (fat controller) — `src/AppManager.js:28-78`
- **O que:** o handler de `/api/checkout` faz, em 50 linhas aninhadas, validação (`:35`), busca de curso (`:37`), busca/criação de usuário (`:40`, `:69`), hashing (`:68`), autorização do pagamento (`:46`), três persistências (`:50`, `:54`, `:57`) e cache (`:59`). O controller conhece SQL cru e o formato das tabelas. Mesmo padrão em `/api/admin/financial-report` (`:80-129`) e `DELETE /api/users/:id` (`:131-137`).
- **Impacto:** a regra de checkout não é reutilizável fora de uma requisição HTTP (nada de job, CLI ou reprocessamento) nem testável sem servidor; o aninhamento de 6 níveis ("callback hell") esconde os caminhos de erro.
- **Recomendação:** controller apenas traduz HTTP↔domínio (parse, chamada de service, status code); `CheckoutService` orquestra; `UserRepository`/`CourseRepository`/`PaymentRepository` isolam o SQL.

#### [AP-11] Estado global mutável e cache sem limite — `src/utils.js:9-10,14`, `src/AppManager.js:59`
- **O que:** `globalCache = {}` e `totalRevenue = 0` são variáveis de módulo (`utils.js:9-10`); `logAndCache` muta `globalCache` a cada checkout (`utils.js:14`, chamada em `AppManager.js:59`), gravando `last_checkout_<userId>` sem TTL nem limite de tamanho.
- **Impacto:** crescimento monotônico da memória (uma entrada por usuário, para sempre) — vazamento em processo de vida longa; o estado não sobrevive a restart nem é compartilhado entre instâncias, então qualquer lógica que passe a depender dele dá resultado diferente por réplica.
- **Recomendação:** remover o cache (não é lido em lugar nenhum hoje) ou, se houver requisito real, um store explícito com TTL e limite, injetado como dependência em vez de singleton de módulo.

#### [AP-13] N+1 no relatório financeiro — `src/AppManager.js:83-106`
- **O que:** uma query lista os cursos (`:83`); para cada curso, outra query busca as matrículas (`:92`); para cada matrícula, mais duas — usuário (`:104`) e pagamento (`:106`). Total: `1 + C + 2·M` consultas.
- **Impacto:** com 50 cursos e 10 000 matrículas são mais de 20 000 round-trips sequenciais numa única requisição HTTP sem paginação. Latência cresce linearmente e o endpoint se torna um vetor de esgotamento de recursos — agravado por estar sem autenticação (ver AP-06).
- **Recomendação:** uma consulta com `JOIN` entre `courses`, `enrollments`, `users` e `payments`, agregando receita via `SUM(...) FILTER (WHERE status = 'PAID')`; paginar a lista de alunos.

#### [AP-14] Erros engolidos e resposta de sucesso em caso de falha — `src/AppManager.js:57, 104, 106, 133-135`
- **O que:** o callback do `INSERT audit_logs` (`:57`) recebe `err` e o ignora, respondendo 200 (`:60`) mesmo se a auditoria falhar; o `DELETE` em `:133` idem — `(err) => { res.send("Usuário deletado...") }` devolve 200 com mensagem de sucesso mesmo quando a exclusão falhou; `:104` e `:106` descartam `err` silenciosamente.
- **Impacto:** o cliente recebe confirmação de operações que não aconteceram; falhas de banco ficam invisíveis em monitoramento; a trilha de auditoria tem buracos sem registro de que houve buraco.
- **Recomendação:** propagar todo erro para um error handler central do Express (`app.use((err, req, res, next) => ...)`) que loga o detalhe internamente e responde status correto com mensagem genérica.

#### [extra] Gateway de pagamento simulado dentro do controller — `src/AppManager.js:46`
- **O que:** `let status = cc.startsWith("4") ? "PAID" : "DENIED"` — a autorização da cobrança é decidida pelo primeiro dígito do cartão (o BIN da Visa), sem chamada externa, sem validação de Luhn, sem validade/CVV, sem idempotência e sem tratamento de timeout. A chave do gateway (`config.paymentGatewayKey`) é apenas logada (`:45`), nunca usada.
- **Impacto:** não há ponto de extensão para o gateway real — integrá-lo significa reescrever o handler. A ausência de chave de idempotência é o defeito estrutural que vira cobrança duplicada em retry.
- **Recomendação:** extrair um `PaymentGateway` como porta (interface) com implementação real e um fake para testes, injetado no `CheckoutService`; a decisão de aprovação vem da resposta do provedor, nunca de heurística sobre o PAN — que, aliás, não deveria trafegar pela aplicação (tokenização no cliente).

#### [deprecated] Stack sobre linha legada e driver em modo verboso — `package.json:10-11`, `src/AppManager.js:1`
- **O que:** `express ^4.18.2` (`package.json:10`) fixa a linha 4.x, em manutenção desde o GA da 5.x; `sqlite3 ^5.1.6` (`package.json:11`) é o binding nativo callback-only, sem API de Promise; `require('sqlite3').verbose()` (`AppManager.js:1`) liga o modo de diagnóstico com captura de stack em toda operação — custo de performance e detalhe interno em log. Detalhes na tabela de deprecated abaixo.
- **Impacto:** a API callback-only é a causa direta do aninhamento de `AppManager.js:28-78` e do N+1 de `:83-106`; a 4.x recebe só correção de segurança.
- **Recomendação:** remover `.verbose()` (ou condicioná-lo a `NODE_ENV !== 'production'`); encapsular o driver atrás de repositórios com `util.promisify` ou `node:sqlite`; avaliar Express 5 como passo separado, após a refatoração em camadas.

---

### 🔵 LOW

#### [AP-15] `console.log` como mecanismo de logging — `src/app.js:13`, `src/utils.js:13`, `src/AppManager.js:45`
- **O que:** três chamadas de `console.log` são todo o logging da aplicação — boot (`app.js:13`, mensagem "Frankenstein LMS" divergente do nome do projeto), cache (`utils.js:13`) e checkout (`AppManager.js:45`, tratado à parte como CRITICAL). Nenhuma dependência de log no `package.json`.
- **Impacto:** sem níveis, sem correlação de requisição, sem formato estruturado, sem redação de campos sensíveis — inviável de consultar em agregador.
- **Recomendação:** `pino` (ou `winston`) com nível por env, saída JSON e lista de campos redigidos; substituir as três chamadas.

#### [código morto] Configuração e acumulador nunca usados — `src/utils.js:2-3,5,10,25`, `src/AppManager.js:2`
- **O que:** `dbUser` (`utils.js:2`), `dbPass` (`:3`) e `smtpUser` (`:5`) não são referenciados em lugar algum — o banco é `:memory:` (`AppManager.js:7`), que não usa credencial, e não há envio de e-mail. `totalRevenue` (`utils.js:10`) é exportado (`:25`) e importado (`AppManager.js:2`) mas nunca lido nem incrementado; como é primitivo, o export é uma cópia por valor e jamais refletiria mutação.
- **Impacto:** segredos expostos (ver AP-02) sem sequer contrapartida funcional; o import morto sugere uma feature de receita acumulada que não existe, enganando quem lê.
- **Recomendação:** remover as chaves não usadas em vez de migrá-las para env; deletar `totalRevenue` e seu import.

#### [AP-07/AP-14] Sem error handler central, sem `NODE_ENV` e contrato de erro inconsistente — `src/app.js:5-10`, `src/AppManager.js:35,38,41,48,51,55,84,135`
- **O que:** `app.js` registra apenas `express.json()` (`:6`) e as rotas (`:10`) — nenhum middleware de erro, nenhum 404 handler, nenhuma leitura de `NODE_ENV`. Os erros são devolvidos como `text/plain` improvisado (`"Bad Request"` em `:35`, `"Erro DB"` em `:41`, `"Erro Matrícula"` em `:51`), enquanto o sucesso é JSON (`:60`, `:121`). Sem `NODE_ENV=production`, o handler padrão do Express inclui o stack trace na resposta.
- **Impacto:** o cliente precisa de dois parsers; mensagens em português cru não são internacionalizáveis nem mapeáveis a códigos; um JSON malformado no corpo cai no handler padrão e devolve caminhos internos do servidor.
- **Recomendação:** middleware de erro central emitindo `{ error: { code, message } }` com status apropriado, 404 handler, e `NODE_ENV` vindo do ambiente.

#### [contrato] Nomes crípticos no payload e mensagem confessional na resposta — `src/AppManager.js:29-33, 135`
- **O que:** o corpo do checkout usa `usr`, `eml`, `pwd`, `c_id`, `card` (`:29-33`), mapeados para variáveis de uma letra `u`, `e`, `p`, `cid`, `cc`. A resposta do DELETE é `"Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco."` (`:135`) — documentação de um defeito entregue ao cliente final.
- **Impacto:** contrato público ilegível e inconsistente com `users`/`courses` do resto da API; a mensagem revela fragilidade interna a quem chama.
- **Recomendação:** renomear para `name`, `email`, `password`, `courseId`, `card` — mudança de contrato, então versionar ou aceitar ambos temporariamente; resposta do DELETE em `204 No Content`.

#### [determinismo] Ordem do relatório depende da conclusão dos callbacks — `src/AppManager.js:96, 119`
- **O que:** `report.push(courseData)` acontece quando o último callback daquele curso termina (`:96` para cursos sem matrícula, `:119` para os demais), não na ordem de `courses.forEach` (`:89`). O array `report` (`:81`) e os contadores (`:86`, `:93`) são estado compartilhado entre callbacks de uma mesma requisição.
- **Impacto:** a mesma base pode gerar ordens diferentes entre chamadas; cursos sem matrícula tendem a aparecer primeiro. Quebra snapshot tests e qualquer consumidor que assuma ordenação.
- **Recomendação:** `ORDER BY` explícito na consulta agregada (ver AP-13) — a reescrita com `JOIN` elimina o problema junto com os contadores manuais.

---

## APIs deprecated

| API | Local | Substituir por |
|---|---|---|
| `express@4.x` (linha em manutenção; 5.x é a atual) | `package.json:10` | `express@5` — conferir breaking changes de roteamento e de `res.status().send()` |
| `sqlite3` callback-only (binding nativo legado) | `package.json:11`, `src/AppManager.js:1` | `node:sqlite` (Node 22+) ou `better-sqlite3`; alternativamente `util.promisify` atrás dos repositórios |
| `.verbose()` habilitado incondicionalmente | `src/AppManager.js:1` | remover, ou condicionar a `NODE_ENV !== 'production'` |

Não detectadas: `new Buffer(...)` (o código já usa `Buffer.from` em `utils.js:20`), `body-parser` como dependência separada (já usa `express.json()` nativo em `app.js:6`), `crypto.createCipher`, `url.parse`, `request`, `moment`.

## Categorias do catálogo sem ocorrência

Varredura completa das 16 categorias; estas não produziram achado:

- **AP-01 (SQL injection):** todas as 11 queries usam parâmetros vinculados (`?`) — `AppManager.js:37, 40, 50, 54, 57, 69, 83, 92, 104, 106, 133`. Nenhuma concatenação de input em string SQL.
- **AP-05 (endpoint que executa entrada arbitrária):** não há rota de query/eval/exec.
- **AP-07 (DEBUG ligado):** não existe flag de debug explícita — o risco correlato (ausência de `NODE_ENV`) está registrado em LOW.
- **AP-12 (duplicação WET):** a repetição existente (blocos `res.status(500).send(...)`) é pequena e fica coberta pela recomendação de error handler central.
- **AP-16 (CORS aberto):** nenhum middleware de CORS configurado.

## Recomendação de refatoração

Ordem sugerida para a Fase 3 — fecha risco antes de organizar:

1. **Segurança CRITICAL:** extrair `config/` lendo `process.env` (+ `.env.example`, `.gitignore`); remover o log do cartão/chave (`AppManager.js:45`); trocar `badCrypto` por bcrypt/argon2 e renomear a coluna para `password_hash`. *As chaves já expostas precisam ser rotatividade fora do código — o Git guarda o histórico.*
2. **HIGH:** middleware de autenticação/autorização nas rotas admin e no DELETE; persistência real com migrations; exigir senha no checkout; transação única no fluxo de cobrança; FKs com enforcement; tratamento de `err` em todo callback.
3. **Reestruturação MVC (MEDIUM arquiteturais):** quebrar `AppManager` em `controllers/`, `services/`, `repositories/`, `models/`, `routes/`, `config/`, `middlewares/`; extrair o `PaymentGateway` como porta; substituir o N+1 por consulta agregada; eliminar o cache global.
4. **LOW:** logger estruturado, remoção de código morto, error handler central, normalização do contrato de entrada/saída.

Restrição de comportamento a preservar: os três endpoints de `api.http` — `POST /api/checkout`, `GET /api/admin/financial-report`, `DELETE /api/users/:id` — continuam respondendo nos mesmos caminhos e métodos.

> **Fase 2 completa. Prosseguir com a refatoração (Fase 3)? [y/n]**
