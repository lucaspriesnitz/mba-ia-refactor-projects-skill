"""Logging central, no lugar dos 13 `print` (AP-15).

Nível vindo da configuração; os módulos só fazem `logging.getLogger(__name__)`.
"""

import logging

LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def configure_logging(level="INFO"):
    logging.basicConfig(level=getattr(logging, level, logging.INFO), format=LOG_FORMAT, force=True)
