"""Token de acesso assinado (fecha o achado "token falso e forjável").

Antes: `'fake-jwt-token-' + str(user.id)` (`routes/user_routes.py:210`) --
previsível, sem assinatura, sem expiração. Agora: JWT HS256 assinado com a
`SECRET_KEY` do ambiente, com `exp`.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt

from ..errors import Unauthenticated

ALGORITHM = "HS256"


@dataclass(frozen=True)
class Actor:
    """Quem está chamando, segundo o token. O papel efetivo é relido do banco."""

    user_id: int


class TokenService:
    def __init__(self, secret_key, ttl_seconds):
        self._secret_key = secret_key
        self._ttl = timedelta(seconds=ttl_seconds)

    def issue(self, user):
        now = datetime.now(UTC)
        claims = {"sub": str(user.id), "role": user.role, "iat": now, "exp": now + self._ttl}
        return jwt.encode(claims, self._secret_key, algorithm=ALGORITHM)

    def decode(self, token):
        try:
            claims = jwt.decode(
                token, self._secret_key, algorithms=[ALGORITHM], options={"require": ["exp", "sub"]}
            )
            return Actor(user_id=int(claims["sub"]))
        except jwt.ExpiredSignatureError:
            raise Unauthenticated("Token expirado")
        except (jwt.InvalidTokenError, ValueError):
            raise Unauthenticated("Token inválido")
