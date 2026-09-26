"""Validadores de entrada, um por entidade, compartilhados entre criar e atualizar.

Fecha duas coisas de uma vez:
  - AP-12: o bloco de validação de produto estava colado em `criar_produto`
    (`controllers.py:28-54`) e `atualizar_produto` (`controllers.py:72-90`), e as
    cópias já tinham divergido -- o PUT não checava tamanho de nome nem
    categoria. Agora há um validador só, usado pelos dois caminhos.
  - Validação sem checagem de tipo: `if preco < 0` sobre um valor de JSON
    levantava TypeError e virava 500. Aqui o tipo é verificado antes da
    comparação e o retorno é 400 com o campo problemático.

As mensagens de erro são idênticas às do código original, para não alterar o
corpo das respostas que os clientes já consomem.
"""

from .constants import (
    CATEGORIAS_VALIDAS,
    CATEGORIA_PADRAO,
    NOME_PRODUTO_TAMANHO_MAXIMO,
    NOME_PRODUTO_TAMANHO_MINIMO,
    STATUS_VALIDOS,
)
from .errors import ErroDeValidacao


def _numero(valor, campo, rotulo):
    # bool é subclasse de int em Python: `True` passaria por número válido.
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise ErroDeValidacao(rotulo + " deve ser um número", campo)
    return valor


def validar_produto(dados):
    """Valida o payload de produto e devolve os campos normalizados.

    A ordem das checagens (e as mensagens) segue o handler original.
    """
    if not dados:
        raise ErroDeValidacao("Dados inválidos")
    if "nome" not in dados:
        raise ErroDeValidacao("Nome é obrigatório", "nome")
    if "preco" not in dados:
        raise ErroDeValidacao("Preço é obrigatório", "preco")
    if "estoque" not in dados:
        raise ErroDeValidacao("Estoque é obrigatório", "estoque")

    nome = dados["nome"]
    if not isinstance(nome, str):
        raise ErroDeValidacao("Nome deve ser texto", "nome")

    descricao = dados.get("descricao", "")
    if descricao is None:
        descricao = ""
    if not isinstance(descricao, str):
        raise ErroDeValidacao("Descrição deve ser texto", "descricao")

    preco = _numero(dados["preco"], "preco", "Preço")
    estoque = _numero(dados["estoque"], "estoque", "Estoque")

    categoria = dados.get("categoria") or CATEGORIA_PADRAO
    if not isinstance(categoria, str):
        raise ErroDeValidacao("Categoria deve ser texto", "categoria")

    if preco < 0:
        raise ErroDeValidacao("Preço não pode ser negativo", "preco")
    if estoque < 0:
        raise ErroDeValidacao("Estoque não pode ser negativo", "estoque")
    if len(nome) < NOME_PRODUTO_TAMANHO_MINIMO:
        raise ErroDeValidacao("Nome muito curto", "nome")
    if len(nome) > NOME_PRODUTO_TAMANHO_MAXIMO:
        raise ErroDeValidacao("Nome muito longo", "nome")
    if categoria not in CATEGORIAS_VALIDAS:
        raise ErroDeValidacao(
            "Categoria inválida. Válidas: " + str(list(CATEGORIAS_VALIDAS)), "categoria"
        )

    return {
        "nome": nome,
        "descricao": descricao,
        "preco": preco,
        "estoque": estoque,
        "categoria": categoria,
    }


def validar_usuario(dados):
    if not dados:
        raise ErroDeValidacao("Dados inválidos")

    nome = dados.get("nome", "")
    email = dados.get("email", "")
    senha = dados.get("senha", "")

    for valor in (nome, email, senha):
        if not isinstance(valor, str) or not valor:
            raise ErroDeValidacao("Nome, email e senha são obrigatórios")

    # O e-mail é gravado exatamente como recebido -- normalizar aqui mudaria o
    # que `GET /usuarios` devolve.
    if not _email_parece_valido(email):
        raise ErroDeValidacao("E-mail inválido", "email")

    return {"nome": nome, "email": email, "senha": senha}


def validar_credenciais(dados):
    email = (dados or {}).get("email", "")
    senha = (dados or {}).get("senha", "")
    if not isinstance(email, str) or not isinstance(senha, str) or not email or not senha:
        raise ErroDeValidacao("Email e senha são obrigatórios")
    return {"email": email, "senha": senha}


def validar_status_de_pedido(dados):
    status = (dados or {}).get("status", "")
    if status not in STATUS_VALIDOS:
        raise ErroDeValidacao("Status inválido", "status")
    return status


def validar_itens_de_pedido(dados):
    if not dados:
        raise ErroDeValidacao("Dados inválidos")

    usuario_id = dados.get("usuario_id")
    itens = dados.get("itens", [])

    if not usuario_id:
        raise ErroDeValidacao("Usuario ID é obrigatório", "usuario_id")
    if not itens or not isinstance(itens, list):
        raise ErroDeValidacao("Pedido deve ter pelo menos 1 item", "itens")

    itens_normalizados = []
    for item in itens:
        if not isinstance(item, dict):
            raise ErroDeValidacao("Item de pedido inválido", "itens")
        produto_id = item.get("produto_id")
        if produto_id is None:
            raise ErroDeValidacao("produto_id é obrigatório em cada item", "itens")
        quantidade = _numero(item.get("quantidade"), "itens", "Quantidade")
        if quantidade <= 0:
            raise ErroDeValidacao("Quantidade deve ser maior que zero", "itens")
        itens_normalizados.append({"produto_id": produto_id, "quantidade": quantidade})

    return {"usuario_id": usuario_id, "itens": itens_normalizados}


def validar_paginacao(limite, deslocamento, limite_padrao, limite_maximo):
    """Paginação opcional (`?limit=&offset=`).

    Sem parâmetro e sem `LISTAGEM_LIMITE_PADRAO` configurado o comportamento é o
    original: retorna tudo. Quando um limite é informado, ele é aparado pelo
    teto de configuração.
    """
    if limite is None:
        limite_efetivo = limite_padrao
    else:
        try:
            limite_efetivo = int(limite)
        except (TypeError, ValueError):
            raise ErroDeValidacao("limit deve ser um número inteiro", "limit")
        if limite_efetivo < 0:
            raise ErroDeValidacao("limit não pode ser negativo", "limit")
        if limite_maximo is not None:
            limite_efetivo = min(limite_efetivo, limite_maximo)

    if deslocamento is None:
        deslocamento_efetivo = 0
    else:
        try:
            deslocamento_efetivo = int(deslocamento)
        except (TypeError, ValueError):
            raise ErroDeValidacao("offset deve ser um número inteiro", "offset")
        if deslocamento_efetivo < 0:
            raise ErroDeValidacao("offset não pode ser negativo", "offset")

    return limite_efetivo, deslocamento_efetivo


def validar_preco_de_filtro(valor, campo):
    """`is not None` em vez de veracidade: `preco_max=0` passa a valer (era ignorado)."""
    if valor is None:
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        raise ErroDeValidacao(campo + " deve ser um número", campo)


def _email_parece_valido(email):
    if email.count("@") != 1:
        return False
    local, _, dominio = email.partition("@")
    if not local or "." not in dominio:
        return False
    return not dominio.startswith(".") and not dominio.endswith(".")
