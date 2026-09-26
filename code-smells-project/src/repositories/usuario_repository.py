"""Acesso a dados de usuários.

Duas mudanças estruturais em relação a `models.py`:
  - as colunas são projetadas explicitamente, e as listagens NÃO trazem a
    credencial (fecha AP-03: `SELECT *` + serializer com `senha`);
  - o login não recebe mais a senha: busca-se pelo e-mail e a verificação do
    hash acontece em código (fecha o bypass de autenticação de `models.py:109-111`).
"""

from .base import RepositoryBase, montar_clausula_de_paginacao

COLUNAS_PUBLICAS = "id, nome, email, tipo, criado_em"
# Usada somente pelo fluxo de autenticação, nunca por uma listagem.
COLUNAS_COM_CREDENCIAL = "id, nome, email, tipo, criado_em, senha"


class UsuarioRepository(RepositoryBase):
    def listar(self, limite=None, deslocamento=0):
        sufixo, parametros = montar_clausula_de_paginacao(limite, deslocamento)
        cursor = self._cursor()
        cursor.execute(
            "SELECT " + COLUNAS_PUBLICAS + " FROM usuarios ORDER BY id" + sufixo,
            parametros,
        )
        return cursor.fetchall()

    def buscar_por_id(self, usuario_id):
        cursor = self._cursor()
        cursor.execute(
            "SELECT " + COLUNAS_PUBLICAS + " FROM usuarios WHERE id = ?", (usuario_id,)
        )
        return cursor.fetchone()

    def buscar_credencial_por_email(self, email):
        cursor = self._cursor()
        cursor.execute(
            "SELECT " + COLUNAS_COM_CREDENCIAL + " FROM usuarios WHERE email = ?",
            (email,),
        )
        return cursor.fetchone()

    def existe_email(self, email):
        cursor = self._cursor()
        cursor.execute("SELECT 1 FROM usuarios WHERE email = ? LIMIT 1", (email,))
        return cursor.fetchone() is not None

    def criar(self, nome, email, senha_hash, tipo):
        cursor = self._cursor()
        cursor.execute(
            "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
            (nome, email, senha_hash, tipo),
        )
        return cursor.lastrowid
