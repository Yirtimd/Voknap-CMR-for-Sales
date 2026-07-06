"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-07-05
"""

from alembic import op

from app.core.database import Base
from app.modules.accounts import models as accounts_models
from app.modules.activity import models as activity_models
from app.modules.ai_agent import models as ai_agent_models
from app.modules.connectors import models as connectors_models
from app.modules.knowledge import models as knowledge_models
from app.modules.production import models as production_models
from app.modules.sales import models as sales_models
from app.modules.templates import models as templates_models


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)

