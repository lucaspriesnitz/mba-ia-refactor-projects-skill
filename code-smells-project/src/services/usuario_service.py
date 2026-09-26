"""Regra de negócio de usuários e autenticação.

Fecha AP-03 (hash na escrita, verificação em código na leitura) e o achado de
e-mail sem unicidade (checagem prévia -> 409). O login passa a emitir uma
credencial assinada, que é o que faltava para as rotas saberem quem chama
(AP-06).
"""

import logging

from ..database.unit_of_work import transacao
from ..models.constants import PAPEL_CLIENTE
from ..models.errors import ConflitoDeRecurso, CredenciaisInvalidas, RecursoNaoEncontrado
from ..models.serializers import (
    serializar_usuario,
    serializar_usuario_autenticado,
    serializar_usuarios,
)
from ..models.validators import validar_credenciais, validar_usuario

logger = logging.getLogger(__name__)


class UsuarioService:
    def __init__(self, usuario_repository, auth_service, provedor_conexao):
        self._usuarios = usuario_repository
        self._auth = auth_service
        self._provedor_conexao = provedor_conexao

    def listar(self, limite=None, deslocamento=0):
        return serializar_usuarios(self._usuarios.listar(limite, deslocamento))

    def buscar_por_id(self, usuario_id):
        row = self._usuarios.buscar_por_id(usuario_id)
        if row is None:
            raise RecursoNaoEncontrado("Usuário não encontrado")
        return serializar_usuario(row)

    def criar(self, dados):
        campos = validar_usuario(dados)
        if self._usuarios.existe_email(campos["email"]):
            raise ConflitoDeRecurso("E-mail já cadastrado", "email")

        senha_hash = self._auth.gerar_hash_de_senha(campos["senha"])
        with transacao(self._provedor_conexao):
            usuario_id = self._usuarios.criar(
                campos["nome"], campos["email"], senha_hash, PAPEL_CLIENTE
            )
        # Sem PII no log (antes: `print("Usuário criado: " + email)`).
        logger.info("Usuário criado id=%s", usuario_id)
        return usuario_id

    def autenticar(self, dados):
        campos = validar_credenciais(dados)
        row = self._usuarios.buscar_credencial_por_email(campos["email"])

        if row is None or not self._auth.senha_confere(campos["senha"], row["senha"]):
            # Mesma resposta para e-mail inexistente e senha errada, e sem
            # identificador no log: antes as duas linhas de `print` formavam um
            # oráculo de enumeração de contas.
            logger.info("Tentativa de login recusada")
            raise CredenciaisInvalidas("Email ou senha inválidos")

        usuario = serializar_usuario_autenticado(row)
        usuario["token"] = self._auth.emitir_token(row["id"], row["tipo"])
        logger.info("Login bem-sucedido usuario_id=%s", row["id"])
        return usuario
