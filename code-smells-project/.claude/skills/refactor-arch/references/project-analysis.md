# Referência — Análise de Projeto (Fase 1)

Heurísticas **agnósticas** para descobrir a stack e mapear a arquitetura atual.
A ideia é decidir por **sinais concretos** (arquivos-marcador, imports, padrões),
não por chute.

## 1. Linguagem e gerenciador de pacotes

Detecte pelo arquivo-marcador presente na raiz (ou subpasta de código):

| Arquivo-marcador | Linguagem | Ecossistema |
|---|---|---|
| `requirements.txt`, `pyproject.toml`, `Pipfile`, `setup.py` | Python | pip/poetry |
| `package.json` | JavaScript/TypeScript | npm/yarn/pnpm |
| `go.mod` | Go | go modules |
| `pom.xml`, `build.gradle` | Java/Kotlin | maven/gradle |
| `Gemfile` | Ruby | bundler |
| `composer.json` | PHP | composer |
| `*.csproj` | C# | dotnet |

Confirme pela extensão dominante dos fontes (`.py`, `.js`/`.ts`, `.go`, …).

## 2. Framework web

Olhe as **dependências** do arquivo-marcador e os **imports** dos fontes:

| Sinais | Framework |
|---|---|
| `flask` / `from flask import` | Flask (Python) |
| `fastapi` / `from fastapi import` | FastAPI (Python) |
| `django` / `settings.py`, `urls.py` | Django (Python) |
| `express` / `require('express')` / `import express` | Express (Node) |
| `@nestjs/*` | NestJS (Node) |
| `koa`, `fastify`, `hapi` | Koa/Fastify/Hapi (Node) |
| `gin-gonic`, `net/http`, `echo` | Gin/Echo (Go) |
| `spring-boot-starter-web` | Spring Boot (Java) |
| `rails`, `sinatra` | Rails/Sinatra (Ruby) |

Anote a **versão** quando o lockfile/manifest declarar.

## 3. Banco de dados e camada de acesso

Procure por:

- **Driver/ORM nas deps ou imports:** `sqlite3`, `psycopg2`, `mysql`,
  `sqlalchemy`, `flask_sqlalchemy`, `sequelize`, `prisma`, `mongoose`,
  `better-sqlite3`, `pg`, `knex`, `typeorm`.
- **Definição de schema:** `CREATE TABLE ...` em strings, classes de modelo
  (`class X(db.Model)`, `@Entity`), migrations.
- **String de conexão:** caminho de arquivo (`sqlite:///x.db`, `loja.db`),
  `:memory:` (banco volátil — perde dados no restart), URL de host, env var.

Liste as **tabelas/modelos** detectados (nome + campos principais). Isso vira a
linha `DB tables:` do resumo e orienta os `models/` da Fase 3.

## 4. Domínio da aplicação

Infira o que a app faz a partir de: nomes de rotas/endpoints, nomes de tabelas,
mensagens, seeds. Descreva em uma frase — ex.: "API de e-commerce (produtos,
usuários, pedidos)", "LMS com checkout de cursos", "gerenciador de tarefas".

## 5. Arquitetura atual — classifique o ponto de partida

Isto decide o **tamanho** da refatoração na Fase 3. Enquadre em um dos níveis:

- **N0 — Monólito plano:** tudo em poucos arquivos, sem camadas; acesso a
  dados + regra de negócio + rota misturados. Sinais: 1 "God module/class",
  SQL inline nas rotas, um arquivo de centenas de linhas.
- **N1 — Separação parcial nominal:** existem pastas (`models/`, `routes/`,
  `utils/`) mas as responsabilidades vazam — regra de negócio dentro das rotas,
  sem camada de service, helpers/serviços mortos.
- **N2 — Em camadas mas com defeitos pontuais:** MVC presente; problemas são
  localizados (um N+1, um segredo hardcoded).

Como distinguir rápido:
- Conte arquivos-fonte e a maior contagem de linhas por arquivo.
- Há uma pasta `services/` **usada** (importada pelas rotas)? Se não, provável N0/N1.
- As rotas chamam o banco **diretamente** ou via camada? Direto → N0/N1.
- Há blueprints/routers registrando rotas separadas do handler? Sinal de N1+.

Registre o nível — a Fase 3 adapta a estrutura-alvo a ele (ver
`mvc-guidelines.md` › "Adaptação ao ponto de partida").

## 6. Saída da fase

Preencha o bloco `PHASE 1: PROJECT ANALYSIS` do `SKILL.md` com o que foi
detectado. Nenhuma escrita em disco nesta fase.
