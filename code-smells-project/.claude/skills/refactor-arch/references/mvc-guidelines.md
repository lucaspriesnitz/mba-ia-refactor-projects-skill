# Referência — Guidelines de Arquitetura MVC em Camadas (Fase 3)

Define a **estrutura-alvo** e como adaptá-la ao ponto de partida detectado na
Fase 1. Princípio único: **cada camada tem uma responsabilidade e só depende da
de baixo.** A refatoração é mecânica quando as fronteiras estão claras.

## As camadas

```
HTTP  →  Controller  →  Service  →  Repository  →  Banco
              ↑             ↑            ↑
           Router        Model      (driver/ORM)
                       (entidade)
```

| Camada | Responsabilidade | NÃO faz |
|---|---|---|
| **Router** | Mapeia rota+método → controller. | Regra de negócio. |
| **Controller** | Traduz HTTP↔domínio: lê request, chama service, formata response/status. | SQL, cálculo de negócio. |
| **Service** | Regra de negócio, orquestração, transação. Reutilizável fora do HTTP. | Conhecer `request`/`response`, montar SQL. |
| **Repository / Model** | Acesso a dados: CRUD, queries, mapeamento linha↔entidade. | Regra de negócio, HTTP. |
| **Config** | Lê ambiente (segredos, porta, DB URL). Fonte única. | Valores hardcoded. |

Transversais (uma vez, no lugar certo): **config** (env), **tratamento de erro
central**, **logging**, **entry point / composition root** que monta o grafo de
dependências e sobe o servidor.

## Estrutura de diretórios alvo (agnóstica)

Adapte os nomes à convenção da linguagem, mantenha os papéis:

```
src/  (ou raiz do pacote)
├── config/            # leitura de ambiente, sem segredo no código
├── routers/           # registro de rotas → controllers
├── controllers/       # um por recurso (produtos, usuarios, pedidos)
├── services/          # regra de negócio por domínio
├── repositories/      # acesso a dados por entidade (ou models/ no ORM)
├── models/            # entidades/schema
├── middlewares/       # auth, error handler, logging
└── app entrypoint     # compõe tudo e sobe o servidor (app.py / app.js)
```

Regra de dependência: **de fora pra dentro**. Controller importa service;
service importa repository; ninguém de baixo importa de cima. Nada de import
circular.

## Adaptação ao ponto de partida

A Fase 1 classificou o projeto em N0/N1/N2. A refatoração muda de tamanho:

### N0 — Monólito plano (ex.: `code-smells-project`, `ecommerce-api-legacy`)
Tudo misturado num punhado de arquivos. Refatoração **completa**:
1. Criar as pastas de camada.
2. Extrair schema/seed para `models/` + init de banco isolado.
3. Mover cada query para um `repository` (parametrizando — mata AP-01).
4. Mover regra de negócio dos handlers para `services`.
5. Reduzir controllers a HTTP↔service.
6. Extrair `config` do ambiente (mata AP-02).
7. Adicionar middleware de auth e error handler central.

### N1 — Separação parcial nominal (pastas existem, responsabilidades vazam)
Pastas já existem mas regra vaza pra rota / não há service usado:
1. Introduzir/adotar a camada `services` de fato (rotas param de falar com o
   banco direto).
2. Puxar regra de negócio das rotas para os services.
3. Remover helpers/serviços mortos; consolidar duplicação.

### N2 — Em camadas com defeitos pontuais (ex.: `task-manager-api`)
MVC presente, problemas localizados. **Não reescreva** — corrija cirurgicamente:
1. Fechar os achados pontuais (um N+1, um segredo, um endpoint sem auth).
2. Preencher a lacuna de camada específica (ex.: um `config/` ausente).
3. Não mover o que já está no lugar — mudança mínima que fecha o achado.

> Regra de ouro: **o tamanho da refatoração é ditado pelo ponto de partida, não
> por um template fixo.** Ler o código antes de desenhar a estrutura-alvo.

## Preservação de comportamento (invariante da Fase 3)

- Os **endpoints originais** (rota, método, formato de resposta) continuam
  idênticos após a refatoração — a mudança é interna.
- Se um endpoint precisar mudar de contrato (ex.: parava de vazar `str(e)`),
  registre no relatório como mudança intencional.
- Ao terminar, a árvore de diretórios resultante e o checklist de validação vão
  no bloco `PHASE 3: REFACTORING COMPLETE` do `SKILL.md`.
