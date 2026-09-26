from ..database import db
from .domain import UserRole, utc_now


class User(db.Model):
    """Entidade. Hash de senha e serialização saíram daqui.

    `set_password`/`check_password` com MD5 (AP-04) foram para
    `security/passwords.py`; `to_dict` (que devolvia o hash, AP-03) foi
    substituído por `schemas/user.py`, com allowlist de campos.
    """

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default=UserRole.USER.value)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    tasks = db.relationship("Task", back_populates="user", passive_deletes=True)

    @property
    def is_admin(self):
        return self.role == UserRole.ADMIN
