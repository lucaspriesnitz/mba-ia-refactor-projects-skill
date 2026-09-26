"""Conexao com escopo de requisicao (AP-08).

O provedor devolvido aqui e injetado nas repositories. Todas as repositories de
uma mesma requisicao recebem a MESMA conexao, o que permite ao service abrir uma
transacao unica sobre varias repositories (ver `unit_of_work.transacao`).
"""

from flask import g

CHAVE_CONEXAO = "conexao_db"


def criar_provedor_de_conexao(database):
    def provedor():
        conexao = g.get(CHAVE_CONEXAO)
        if conexao is None:
            conexao = database.conectar()
            setattr(g, CHAVE_CONEXAO, conexao)
        return conexao

    return provedor


def registrar_encerramento(app):
    @app.teardown_appcontext
    def fechar_conexao(_excecao):
        conexao = g.pop(CHAVE_CONEXAO, None)
        if conexao is not None:
            conexao.close()
