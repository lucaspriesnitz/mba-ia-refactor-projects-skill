"""Excecoes de dominio tipadas.

Substituem os 17 blocos `except Exception as e: return jsonify({"erro": str(e)}), 500`
(AP-14). O service levanta o erro semantico; o error handler central traduz para
status HTTP. Nenhuma mensagem interna do SQLite chega ao cliente.
"""


class ErroDeDominio(Exception):
    status_http = 400

    def __init__(self, mensagem, campo=None):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.campo = campo


class ErroDeValidacao(ErroDeDominio):
    status_http = 400


class RegraDeNegocioViolada(ErroDeDominio):
    status_http = 400


class RecursoNaoEncontrado(ErroDeDominio):
    status_http = 404


class ConflitoDeRecurso(ErroDeDominio):
    status_http = 409


class NaoAutenticado(ErroDeDominio):
    status_http = 401


class NaoAutorizado(ErroDeDominio):
    status_http = 403


class CredenciaisInvalidas(ErroDeDominio):
    status_http = 401
