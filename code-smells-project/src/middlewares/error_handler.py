"""Tratamento de erro central (fecha AP-14).

Antes: 17 handlers com `try` gigante terminando em
`return jsonify({"erro": str(e)}), 500` -- mensagens do SQLite (nomes de tabela e
coluna, SQL malformado) iam direto para o cliente, entregando o schema a quem
sondava injeção.

Agora: os controllers não têm `try/except`. Erro de domínio vira o status
correspondente com a mensagem de negócio; qualquer outra exceção é registrada com
stack trace no log e responde uma mensagem genérica.
"""

import logging

from werkzeug.exceptions import HTTPException

from ..controllers.envelope import resposta_de_erro
from ..models.errors import ErroDeDominio

logger = logging.getLogger(__name__)

MENSAGEM_GENERICA = "Erro interno do servidor"


def registrar_tratamento_de_erros(app):
    @app.errorhandler(ErroDeDominio)
    def tratar_erro_de_dominio(erro):
        logger.info(
            "Requisição rejeitada (%s): %s", erro.status_http, erro.mensagem
        )
        return resposta_de_erro(erro.mensagem, erro.status_http, erro.campo)

    @app.errorhandler(HTTPException)
    def tratar_erro_http(erro):
        # Preserva o status que o Flask escolheu (404 de rota inexistente, 405,
        # 415...), mas responde JSON com a descrição padrão -- nunca detalhe interno.
        return resposta_de_erro(erro.description, erro.code or 500)

    @app.errorhandler(Exception)
    def tratar_erro_inesperado(erro):
        logger.exception("Erro não tratado: %s", erro)
        return resposta_de_erro(MENSAGEM_GENERICA, 500)
