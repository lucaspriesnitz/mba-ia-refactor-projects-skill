# Referência — Template de Relatório de Auditoria (Fase 2)

O relatório é o **entregável** da Fase 2 e a evidência do desafio. Ele é impresso
na tela E salvo em `reports/audit-project-<n>.md`. Preencha o esqueleto abaixo
com os achados reais — **não invente números**, cada linha aponta `arquivo:linha`.

Regras de forma:
- Achados **ordenados por severidade**: CRITICAL → HIGH → MEDIUM → LOW.
- Cada achado usa o ID do catálogo (`AP-NN`) quando aplicável.
- O resumo traz a **contagem por severidade** (é o que o avaliador confere rápido).
- Linguagem do relatório: a mesma do projeto/usuário.

---

## Esqueleto (copie e preencha)

```markdown
# Relatório de Auditoria Arquitetural — <nome-do-projeto>

- **Data:** <YYYY-MM-DD>
- **Stack:** <linguagem> / <framework + versão>
- **Arquitetura de partida:** <N0 monólito | N1 separação parcial | N2 em camadas>
- **Arquivos analisados:** <N>

## Resumo por severidade

| Severidade | Qtd |
|---|---|
| CRITICAL | <n> |
| HIGH | <n> |
| MEDIUM | <n> |
| LOW | <n> |
| **Total** | **<n>** |

APIs deprecated detectadas: <n> (ou "nenhuma").

## Achados

### 🔴 CRITICAL

#### [AP-01] Injeção de SQL por concatenação — `models.py:28`
- **O que:** a query `SELECT * FROM produtos WHERE id = " + str(id)` interpola
  input direto na string SQL.
- **Impacto:** leitura/escrita arbitrária no banco a partir da rede.
- **Recomendação:** query parametrizada (`WHERE id = ?`, `(id,)`).

<repita um bloco por achado CRITICAL>

### 🟠 HIGH

#### [AP-07] DEBUG ligado em código — `app.py:8`
- **O que:** `app.config["DEBUG"] = True` fixo no fonte.
- **Impacto:** stack traces expostos + console de debug remoto em Flask.
- **Recomendação:** controlar por env var; produção com `DEBUG=False`.

<repita por achado HIGH>

### 🟡 MEDIUM

<blocos MEDIUM>

### 🔵 LOW

<blocos LOW>

## APIs deprecated

| API | Local | Substituir por |
|---|---|---|
| <api> | `<arquivo:linha>` | <moderna> |

## Recomendação de refatoração

Ordem sugerida para a Fase 3 (fecha risco antes de organizar):
1. CRITICAL de segurança (SQLi, segredo, senha, crypto).
2. HIGH (config de produção, auth, persistência).
3. Reestruturação em camadas MVC (MEDIUM arquiteturais).
4. LOW (logging, código morto).

> **Fase 2 completa. Prosseguir com a refatoração (Fase 3)? [y/n]**
```

---

## Exemplo de bloco de achado (formato canônico)

Cada achado é auto-contido — dá pra corrigir só lendo o bloco:

```
#### [<AP-ID>] <título curto> — `<arquivo:linha>`
- **O que:** <o padrão observado, citando o trecho>
- **Impacto:** <consequência concreta>
- **Recomendação:** <a correção, acionável>
```

Não misture achados de severidades diferentes na mesma seção. Se um achado se
repete em vários arquivos, liste os locais numa linha só (`arquivo:linha,
arquivo:linha`) em vez de duplicar o bloco.
