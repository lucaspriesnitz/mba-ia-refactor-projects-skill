from ..database import db
from .domain import DEFAULT_CATEGORY_COLOR, utc_now


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(300), nullable=True)
    color = db.Column(db.String(7), default=DEFAULT_CATEGORY_COLOR)
    created_at = db.Column(db.DateTime, default=utc_now)

    tasks = db.relationship("Task", back_populates="category", passive_deletes=True)
