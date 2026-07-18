"""enforce membership roles

Revision ID: 0013_membership_roles
Revises: 0012_schema_contract_alignment
Create Date: 2026-07-18
"""

from alembic import op


revision = "0013_membership_roles"
down_revision = "0012_schema_contract_alignment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE memberships SET role = 'viewer' "
        "WHERE role NOT IN ('owner', 'admin', 'sales_manager', 'sales_rep', 'viewer')"
    )
    op.create_check_constraint(
        "ck_memberships_role",
        "memberships",
        "role IN ('owner', 'admin', 'sales_manager', 'sales_rep', 'viewer')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_memberships_role", "memberships", type_="check")
