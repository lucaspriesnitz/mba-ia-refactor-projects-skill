"""Checagem de saúde do banco.

Antes, `health_check` abria cursor e rodava SQL direto dentro do controller
(`controllers.py:266-274`), furando a fronteira de camadas. O SQL agora está
aqui; o controller só chama o service.
"""

from .base import RepositoryBase


class HealthRepository(RepositoryBase):
    def contagens(self):
        cursor = self._cursor()
        cursor.execute("SELECT 1")
        cursor.execute(
            "SELECT (SELECT COUNT(*) FROM produtos) AS produtos,"
            "       (SELECT COUNT(*) FROM usuarios) AS usuarios,"
            "       (SELECT COUNT(*) FROM pedidos) AS pedidos"
        )
        row = cursor.fetchone()
        return {
            "produtos": row["produtos"],
            "usuarios": row["usuarios"],
            "pedidos": row["pedidos"],
        }

    def apagar_todos_os_dados(self):
        """Usada apenas pela rota administrativa de reset (protegida por auth).

        Os quatro comandos são literais, na ordem filho -> pai. Nome de tabela
        não pode ser parâmetro em SQL, então aqui não há nem concatenação: não
        existe caminho por onde um identificador vindo de fora entre na query.
        """
        cursor = self._cursor()
        cursor.execute("DELETE FROM itens_pedido")
        cursor.execute("DELETE FROM pedidos")
        cursor.execute("DELETE FROM produtos")
        cursor.execute("DELETE FROM usuarios")
