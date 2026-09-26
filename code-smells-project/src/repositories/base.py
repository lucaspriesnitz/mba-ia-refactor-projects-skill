"""Base das repositories.

A conexão chega por injeção de dependência (um callable), não por import de um
global mutável -- fecha AP-11 e permite trocar o escopo da conexão sem tocar em
nenhuma query.

Regra desta camada: nenhuma repository dá `commit`. O limite da transação é do
service (`database.unit_of_work.transacao`).
"""


def montar_clausula_de_paginacao(limite, deslocamento):
    """Devolve o sufixo `LIMIT/OFFSET` e seus parâmetros.

    SQLite exige um LIMIT para aceitar OFFSET; -1 significa "sem limite".
    """
    if limite is None and not deslocamento:
        return "", []
    if limite is None:
        return " LIMIT -1 OFFSET ?", [deslocamento]
    return " LIMIT ? OFFSET ?", [limite, deslocamento or 0]


class RepositoryBase:
    def __init__(self, provedor_conexao):
        self._provedor_conexao = provedor_conexao

    @property
    def conexao(self):
        return self._provedor_conexao()

    def _cursor(self):
        return self.conexao.cursor()
