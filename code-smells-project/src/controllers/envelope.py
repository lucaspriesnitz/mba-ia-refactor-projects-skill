"""Envelope de resposta único (fecha o achado de contrato inconsistente).

Antes, alguns erros traziam `sucesso: False` e outros só `erro`; alguns sucessos
tinham `mensagem`, outros não. Agora existe um só lugar que monta o corpo -- e o
error handler central usa o mesmo helper.

Os campos de sucesso são exatamente os que cada endpoint já devolvia; a
padronização é **aditiva** (`sucesso: False` passa a estar presente em todos os
erros, inclusive nos que antes o omitiam).
"""

from flask import jsonify


def resposta_de_sucesso(dados=None, mensagem=None, status=200, extra=None):
    corpo = {}
    if dados is not None:
        corpo["dados"] = dados
    if extra:
        corpo.update(extra)
    corpo["sucesso"] = True
    if mensagem is not None:
        corpo["mensagem"] = mensagem
    return jsonify(corpo), status


def resposta_de_erro(mensagem, status, campo=None):
    corpo = {"erro": mensagem, "sucesso": False}
    if campo:
        corpo["campo"] = campo
    return jsonify(corpo), status
