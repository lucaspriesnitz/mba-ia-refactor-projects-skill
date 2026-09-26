"""Constantes de dominio nomeadas -- fim dos numeros e listas magicas.

Antes: categorias validas literais em `controllers.py:52`, status validos em
`controllers.py:242` (sem relacao com o DEFAULT do schema) e as faixas de
desconto embutidas em `models.py:256-262`.
"""

CATEGORIAS_VALIDAS = (
    "informatica",
    "moveis",
    "vestuario",
    "geral",
    "eletronicos",
    "livros",
)
CATEGORIA_PADRAO = "geral"

STATUS_PENDENTE = "pendente"
STATUS_APROVADO = "aprovado"
STATUS_ENVIADO = "enviado"
STATUS_ENTREGUE = "entregue"
STATUS_CANCELADO = "cancelado"

STATUS_VALIDOS = (
    STATUS_PENDENTE,
    STATUS_APROVADO,
    STATUS_ENVIADO,
    STATUS_ENTREGUE,
    STATUS_CANCELADO,
)
STATUS_PADRAO = STATUS_PENDENTE

NOME_PRODUTO_TAMANHO_MINIMO = 2
NOME_PRODUTO_TAMANHO_MAXIMO = 200

# (faturamento minimo, percentual de desconto) -- avaliadas da faixa mais alta
# para a mais baixa, preservando o resultado do relatorio original.
FAIXAS_DE_DESCONTO = (
    (10000, 0.10),
    (5000, 0.05),
    (1000, 0.02),
)

PAPEL_ADMIN = "admin"
PAPEL_CLIENTE = "cliente"
