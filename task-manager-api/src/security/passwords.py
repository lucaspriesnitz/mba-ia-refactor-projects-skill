"""Hash de senha (fecha AP-04).

Antes: `hashlib.md5(pwd.encode()).hexdigest()` sem salt em `models/user.py:29,32`.
Agora: scrypt com salt por registro via `werkzeug.security` (já vem com o Flask,
nenhuma dependência nova).

Hashes MD5 gravados antes da refatoração não são recuperáveis. Em vez de forçar
reset de todo mundo, o login aceita o formato legado uma última vez e o service
regrava a senha no formato novo (`needs_rehash`).
"""

import hashlib
import hmac
import re

from werkzeug.security import check_password_hash, generate_password_hash

HASH_METHOD = "scrypt"
_LEGACY_MD5 = re.compile(r"[0-9a-f]{32}")


def hash_password(password):
    return generate_password_hash(password, method=HASH_METHOD)


def verify_password(password, stored_hash):
    """Retorna `(confere, precisa_regravar)`."""
    if not stored_hash:
        return False, False
    if _LEGACY_MD5.fullmatch(stored_hash):
        legacy = hashlib.md5(password.encode()).hexdigest()
        matches = hmac.compare_digest(legacy, stored_hash)
        return matches, matches
    return check_password_hash(stored_hash, password), False
