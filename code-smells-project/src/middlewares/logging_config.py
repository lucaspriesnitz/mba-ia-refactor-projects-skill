"""Logging central, no lugar dos 17 `print` espalhados (AP-15).

Nível vindo da configuração, timestamp e origem no formato. Nenhum módulo
configura logging por conta própria: todos apenas pegam `logging.getLogger(__name__)`.
"""

import logging

FORMATO = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def configurar_logging(nivel="INFO"):
    logging.basicConfig(
        level=getattr(logging, nivel, logging.INFO),
        format=FORMATO,
        force=True,
    )
