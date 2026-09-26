"""Agregações de vendas.

As cinco queries sequenciais de `models.py:239-254` viram uma só. A regra de
negócio (faixas de desconto, ticket médio) NÃO mora aqui -- foi para
`services/relatorio_service.py`, onde é testável sem banco.
"""

from ..models.constants import STATUS_APROVADO, STATUS_CANCELADO, STATUS_PENDENTE
from .base import RepositoryBase


class RelatorioRepository(RepositoryBase):
    def agregados_de_pedidos(self):
        cursor = self._cursor()
        cursor.execute(
            "SELECT COUNT(*) AS total_pedidos,"
            "       COALESCE(SUM(total), 0) AS faturamento,"
            "       SUM(CASE WHEN status = ? THEN 1 ELSE 0 END) AS pendentes,"
            "       SUM(CASE WHEN status = ? THEN 1 ELSE 0 END) AS aprovados,"
            "       SUM(CASE WHEN status = ? THEN 1 ELSE 0 END) AS cancelados"
            "  FROM pedidos",
            (STATUS_PENDENTE, STATUS_APROVADO, STATUS_CANCELADO),
        )
        row = cursor.fetchone()
        return {
            "total_pedidos": row["total_pedidos"],
            "faturamento": row["faturamento"] or 0,
            "pendentes": row["pendentes"] or 0,
            "aprovados": row["aprovados"] or 0,
            "cancelados": row["cancelados"] or 0,
        }
