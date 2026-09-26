"""Autenticação e autorização como decorators reutilizáveis (AP-06 / T-05).

Antes não havia mecanismo algum: o login validava a senha e devolvia o usuário,
mas não emitia credencial -- nenhuma rota posterior tinha como saber quem chamava.
Agora o login emite um token assinado (`AuthService`) e as rotas sensíveis o
exigem via `Authorization: Bearer <token>`.

Escopo aplicado nesta refatoração: as rotas administrativas. As rotas de negócio
(`GET /usuarios`, `GET /pedidos`, `DELETE /produtos/<id>`...) continuam abertas
porque protegê-las mudaria a resposta de endpoints que a Fase 2 homologou como
preservados -- a decisão de fechá-las está registrada no README como próximo
passo, e o mecanismo já está pronto para isso (basta aplicar o decorator).
"""

from functools import wraps

from flask import current_app, g, request

from ..models.errors import NaoAutenticado, NaoAutorizado

PREFIXO_BEARER = "Bearer "
CHAVE_USUARIO = "usuario_autenticado"


def usuario_autenticado():
    """Dados do portador da credencial na requisição atual, ou None."""
    return g.get(CHAVE_USUARIO)


def _autenticar():
    cabecalho = request.headers.get("Authorization", "")
    if not cabecalho.startswith(PREFIXO_BEARER):
        raise NaoAutenticado("Credencial ausente")

    token = cabecalho[len(PREFIXO_BEARER):].strip()
    if not token:
        raise NaoAutenticado("Credencial ausente")

    dados = current_app.extensions["container"].auth_service.validar_token(token)
    setattr(g, CHAVE_USUARIO, dados)
    return dados


def requer_autenticacao(funcao):
    @wraps(funcao)
    def envelope(*args, **kwargs):
        _autenticar()
        return funcao(*args, **kwargs)

    return envelope


def requer_papel(papel):
    def decorador(funcao):
        @wraps(funcao)
        def envelope(*args, **kwargs):
            dados = _autenticar()
            if dados.get("papel") != papel:
                raise NaoAutorizado("Permissão insuficiente")
            return funcao(*args, **kwargs)

        return envelope

    return decorador
