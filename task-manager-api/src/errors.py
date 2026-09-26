"""Erros de domínio. O error handler central traduz cada um no status HTTP.

Substitui os `return jsonify({'error': ...}), 4xx` espalhados nos handlers e os
11 `except:` nus (AP-14): services levantam o erro com a mensagem de negócio e
ninguém mais precisa decidir status code no meio da regra.
"""


class DomainError(Exception):
    status_code = 500

    def __init__(self, message):
        super().__init__(message)
        self.message = message


class InvalidInput(DomainError):
    status_code = 400


class Unauthenticated(DomainError):
    status_code = 401


class Forbidden(DomainError):
    status_code = 403


class NotFound(DomainError):
    status_code = 404


class Conflict(DomainError):
    status_code = 409
