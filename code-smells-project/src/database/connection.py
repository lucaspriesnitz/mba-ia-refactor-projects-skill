"""Fabrica de conexoes SQLite.

Substitui o singleton global mutavel com `check_same_thread=False`
(AP-08/AP-11): aqui nao existe estado de modulo -- cada chamada a `conectar`
devolve uma conexao nova, e o escopo de vida dela e decidido por quem pede
(uma por requisicao no caminho HTTP, ver `request_scope.py`).
"""

import sqlite3


class Database:
    def __init__(self, db_path):
        self._db_path = db_path

    @property
    def db_path(self):
        return self._db_path

    def conectar(self):
        conexao = sqlite3.connect(self._db_path)
        conexao.row_factory = sqlite3.Row
        return conexao
