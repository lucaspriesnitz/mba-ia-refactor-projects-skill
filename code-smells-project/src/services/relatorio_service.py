"""Regra de negócio do relatório de vendas.

As faixas de desconto e o ticket médio estavam no meio das queries
(`models.py:256-272`), impossíveis de testar sem banco. Aqui a repository devolve
os agregados e o cálculo é uma função pura sobre eles.
"""

from ..models.constants import FAIXAS_DE_DESCONTO


class RelatorioService:
    def __init__(self, relatorio_repository):
        self._relatorios = relatorio_repository

    def vendas(self):
        agregados = self._relatorios.agregados_de_pedidos()
        return self.montar_relatorio(agregados)

    @staticmethod
    def calcular_desconto(faturamento):
        for minimo, percentual in FAIXAS_DE_DESCONTO:
            if faturamento > minimo:
                return faturamento * percentual
        return 0

    @classmethod
    def montar_relatorio(cls, agregados):
        faturamento = agregados["faturamento"]
        total_pedidos = agregados["total_pedidos"]
        desconto = cls.calcular_desconto(faturamento)
        return {
            "total_pedidos": total_pedidos,
            "faturamento_bruto": round(faturamento, 2),
            "desconto_aplicavel": round(desconto, 2),
            "faturamento_liquido": round(faturamento - desconto, 2),
            "pedidos_pendentes": agregados["pendentes"],
            "pedidos_aprovados": agregados["aprovados"],
            "pedidos_cancelados": agregados["cancelados"],
            "ticket_medio": round(faturamento / total_pedidos, 2) if total_pedidos > 0 else 0,
        }
