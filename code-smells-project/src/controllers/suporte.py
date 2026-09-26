"""Helpers compartilhados pelos controllers.

`container()` é o único ponto onde a camada HTTP alcança as dependências
montadas no composition root -- os controllers não instanciam service nem
repository, e nunca importam a camada de banco.
"""

from flask import current_app, request

from ..models.validators import validar_paginacao


def container():
    return current_app.extensions["container"]


def corpo_json():
    """Corpo JSON ou None.

    `silent=True` evita o que acontecia antes: um POST sem `Content-Type:
    application/json` levantava HTTPException dentro do `try` gigante e voltava
    como 500. Agora cai no caminho normal de validação (400 "Dados inválidos").
    """
    return request.get_json(silent=True)


def parametros_de_pagina():
    settings = container().settings
    return validar_paginacao(
        request.args.get("limit"),
        request.args.get("offset"),
        settings.listagem_limite_padrao,
        settings.listagem_limite_maximo,
    )
