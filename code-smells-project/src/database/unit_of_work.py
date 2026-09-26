"""Fronteira de transacao explicita, com rollback.

As repositories nunca dao `commit`: quem decide o limite da transacao e o
service. Fecha o achado HIGH "criacao de pedido sem transacao nem rollback".
"""

from contextlib import contextmanager


@contextmanager
def transacao(provedor_conexao):
    conexao = provedor_conexao()
    try:
        yield conexao
    except Exception:
        conexao.rollback()
        raise
    else:
        conexao.commit()
