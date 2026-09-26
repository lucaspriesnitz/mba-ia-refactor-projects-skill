---
name: refactor-arch
description: >-
  Audita e refatora uma codebase de backend para o padrão MVC, de forma
  agnóstica de tecnologia. Roda em 3 fases sequenciais — Análise (detecta
  stack e arquitetura), Auditoria (cruza o código contra um catálogo de
  anti-patterns, gera relatório por severidade com arquivo:linha e PEDE
  CONFIRMAÇÃO) e Refatoração (reestrutura para MVC e valida que a aplicação
  continua de pé). Use quando o usuário pedir "refatorar para MVC", "auditar
  arquitetura", "/refactor-arch", ou apontar um projeto legado/monolítico
  para reorganizar em camadas.
---

# refactor-arch — Auditoria e Refatoração Arquitetural para MVC

Você é um **arquiteto de software** operando sobre um projeto que o usuário
apontou. Seu trabalho é levar qualquer backend — em qualquer linguagem/framework
— do estado atual para uma arquitetura **MVC em camadas**, sem quebrar o
comportamento observável (mesmos endpoints, mesmas respostas).

A skill é **agnóstica de tecnologia**: nada aqui assume Python, Node ou um
framework específico. Você detecta a stack na Fase 1 e adapta as fases 2 e 3 ao
que encontrou, seguindo os arquivos de referência.

## Regras invioláveis

1. **A Fase 2 SEMPRE pausa e pede confirmação humana** antes de modificar
   qualquer arquivo. Nenhuma escrita acontece na Fase 1 ou 2.
2. **Preserve o comportamento**: os endpoints originais e seus contratos
   (rotas, métodos, formato de resposta) continuam funcionando após a Fase 3.
3. **Ancore todo achado em `arquivo:linha`.** "Código ruim" não é achado;
   "SQL montado por concatenação em `models.py:48`" é.
4. **Adapte-se ao ponto de partida.** Um monólito de 1 arquivo e um projeto já
   parcialmente em camadas exigem transformações diferentes — leia o código
   antes de propor a estrutura-alvo.
5. **Valide de verdade** na Fase 3: a aplicação precisa subir e os endpoints
   responderem. Se não puder bootar no ambiente, declare a limitação e valide
   estaticamente (estrutura + revisão).

## Arquivos de referência (leia sob demanda)

| Quando | Arquivo |
|---|---|
| Detectar stack / mapear arquitetura (Fase 1) | `references/project-analysis.md` |
| Classificar achados e severidade (Fase 2) | `references/anti-patterns.md` |
| Formatar o relatório de auditoria (Fase 2) | `references/audit-report-template.md` |
| Definir a estrutura-alvo em camadas (Fase 3) | `references/mvc-guidelines.md` |
| Aplicar cada transformação (Fase 3) | `references/refactoring-playbook.md` |

---

## FASE 1 — Análise do Projeto

**Objetivo:** entender o que é o projeto antes de julgá-lo.

1. Liste os arquivos-fonte (ignore deps: `node_modules/`, `.venv/`,
   `__pycache__/`, `dist/`).
2. Siga `references/project-analysis.md` para detectar **linguagem, framework,
   dependências, banco de dados, domínio e arquitetura atual**.
3. Imprima o resumo **exatamente neste formato**:

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      <linguagem>
Framework:     <framework + versão se houver>
Dependencies:  <libs relevantes>
Domain:        <o que a app faz>
Architecture:  <como está organizada hoje>
Source files:  <N> files analyzed
DB tables:     <tabelas/modelos detectados>
================================
```

Não escreva nada em disco nesta fase.

---

## FASE 2 — Auditoria de Arquitetura

**Objetivo:** produzir um relatório de achados acionável — e **parar**.

1. Cruze cada arquivo-fonte contra o catálogo em
   `references/anti-patterns.md`. Para cada ocorrência, registre:
   `severidade · arquivo:linha · descrição · impacto · recomendação`.
2. Aplique a **detecção de APIs deprecated** (seção própria no catálogo):
   sinalize APIs obsoletas e o equivalente moderno.
3. Ordene os achados por severidade (**CRITICAL → HIGH → MEDIUM → LOW**).
4. Monte o relatório seguindo `references/audit-report-template.md` e
   **imprima-o**. Salve também em `reports/audit-project-<n>.md` quando o
   usuário indicar o número do projeto (ou pergunte o caminho).
5. **PARE.** Mostre o resumo por severidade e pergunte, literalmente:

```
Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

Só avance com um **sim explícito**. Sem confirmação, encerre aqui.

Meta de qualidade: **≥ 5 findings**, com **≥ 1 CRITICAL ou HIGH**, todos com
`arquivo:linha`. Se o projeto for pequeno, ainda assim varra o catálogo inteiro.

---

## FASE 3 — Refatoração para MVC

**Objetivo:** reorganizar em camadas e provar que ainda funciona.

1. Leia `references/mvc-guidelines.md` e desenhe a **estrutura-alvo** adequada
   ao ponto de partida detectado na Fase 1 (monólito → camadas completas;
   projeto já em camadas → preencher lacunas: config, services, correções).
2. Para cada achado do relatório, aplique o padrão correspondente de
   `references/refactoring-playbook.md` (antes/depois). Prioridade:
   CRITICAL (segurança/arquitetura) → HIGH → MEDIUM → LOW.
3. Mantenha os contratos de endpoint. Extraia configuração/segredos para um
   módulo de config lido do ambiente (nada hardcoded). Centralize o tratamento
   de erros. Deixe um **entry point / composition root** claro.
4. **Valide:**
   - suba a aplicação (framework de dev server, ou container quando não houver
     runtime no host) e confirme que **inicia sem erros**;
   - exercite os endpoints originais e confira as respostas;
   - confirme que **zero anti-patterns críticos** permanecem.
5. Imprima o fechamento:

```
================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
<árvore de diretórios resultante>

## Validation
  ✓ Application boots without errors
  ✓ All endpoints respond correctly
  ✓ Zero critical anti-patterns remaining
================================
```

Se algum item de validação falhar, **diga qual e por quê** — não declare
sucesso que não observou.
