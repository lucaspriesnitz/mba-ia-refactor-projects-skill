from .category_controller import category_bp
from .health_controller import health_bp
from .report_controller import report_bp
from .task_controller import task_bp
from .user_controller import user_bp

BLUEPRINTS = (health_bp, task_bp, user_bp, category_bp, report_bp)

__all__ = ["BLUEPRINTS"]
