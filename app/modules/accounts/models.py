from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    memberships: Mapped[list["Membership"]] = relationship(back_populates="tenant")


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    memberships: Mapped[list["Membership"]] = relationship(
        back_populates="user", foreign_keys="Membership.user_id"
    )


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", name="uq_membership_tenant_user"),
        UniqueConstraint("tenant_id", "id", name="uq_memberships_tenant_id"),
        CheckConstraint(
            "role IN ('owner', 'admin', 'sales_manager', 'sales_rep', 'viewer')",
            name="ck_memberships_role",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "team_id"],
            ["sales_teams.tenant_id", "sales_teams.id"],
            name="fk_memberships_tenant_team_id",
            use_alter=True,
        ),
        ForeignKeyConstraint(
            ["tenant_id", "manager_membership_id"],
            ["memberships.tenant_id", "memberships.id"],
            name="fk_memberships_tenant_manager_membership_id",
            use_alter=True,
        ),
        ForeignKeyConstraint(
            ["tenant_id", "deactivated_by_id"],
            ["memberships.tenant_id", "memberships.user_id"],
            name="fk_memberships_tenant_deactivated_by_id",
            use_alter=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(40), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    team_id: Mapped[UUID | None] = mapped_column(index=True)
    manager_membership_id: Mapped[UUID | None] = mapped_column(index=True)
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deactivated_by_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    tenant: Mapped[Tenant] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(back_populates="memberships", foreign_keys=[user_id])


class SalesTeam(Base):
    __tablename__ = "sales_teams"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_sales_teams_tenant_id"),
        UniqueConstraint("tenant_id", "name", name="uq_sales_teams_tenant_name"),
        ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_sales_teams_tenant"),
        ForeignKeyConstraint(
            ["tenant_id", "manager_membership_id"],
            ["memberships.tenant_id", "memberships.id"],
            name="fk_sales_teams_tenant_manager_membership_id",
            use_alter=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    manager_membership_id: Mapped[UUID | None] = mapped_column(index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class TeamInvitation(Base):
    __tablename__ = "team_invitations"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_team_invitations_tenant_id"),
        UniqueConstraint("token_hash", name="uq_team_invitations_token_hash"),
        CheckConstraint(
            "role IN ('owner', 'admin', 'sales_manager', 'sales_rep', 'viewer')",
            name="ck_team_invitations_role",
        ),
        ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_team_invitations_tenant"),
        ForeignKeyConstraint(
            ["tenant_id", "team_id"],
            ["sales_teams.tenant_id", "sales_teams.id"],
            name="fk_team_invitations_tenant_team_id",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "manager_membership_id"],
            ["memberships.tenant_id", "memberships.id"],
            name="fk_team_invitations_tenant_manager_membership_id",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "invited_by_id"],
            ["memberships.tenant_id", "memberships.user_id"],
            name="fk_team_invitations_tenant_invited_by_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(40), nullable=False)
    team_id: Mapped[UUID | None] = mapped_column(index=True)
    manager_membership_id: Mapped[UUID | None] = mapped_column(index=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    invited_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class LeadQueue(Base):
    __tablename__ = "lead_queues"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_lead_queues_tenant_id"),
        UniqueConstraint("tenant_id", "name", name="uq_lead_queues_tenant_name"),
        ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_lead_queues_tenant"),
        ForeignKeyConstraint(
            ["tenant_id", "team_id"],
            ["sales_teams.tenant_id", "sales_teams.id"],
            name="fk_lead_queues_tenant_team_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    team_id: Mapped[UUID | None] = mapped_column(index=True)
    strategy: Mapped[str] = mapped_column(String(40), default="round_robin", nullable=False)
    routing_cursor: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class LeadQueueMember(Base):
    __tablename__ = "lead_queue_members"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_lead_queue_members_tenant_id"),
        UniqueConstraint(
            "tenant_id", "queue_id", "membership_id", name="uq_lead_queue_members_member"
        ),
        ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_lead_queue_members_tenant"),
        ForeignKeyConstraint(
            ["tenant_id", "queue_id"],
            ["lead_queues.tenant_id", "lead_queues.id"],
            name="fk_lead_queue_members_tenant_queue_id",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "membership_id"],
            ["memberships.tenant_id", "memberships.id"],
            name="fk_lead_queue_members_tenant_membership_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    queue_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    membership_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Territory(Base):
    __tablename__ = "territories"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_territories_tenant_id"),
        UniqueConstraint("tenant_id", "name", name="uq_territories_tenant_name"),
        ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_territories_tenant"),
        ForeignKeyConstraint(
            ["tenant_id", "owner_membership_id"],
            ["memberships.tenant_id", "memberships.id"],
            name="fk_territories_tenant_owner_membership_id",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "team_id"],
            ["sales_teams.tenant_id", "sales_teams.id"],
            name="fk_territories_tenant_team_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    country_code: Mapped[str | None] = mapped_column(String(2))
    region: Mapped[str | None] = mapped_column(String(120))
    industry: Mapped[str | None] = mapped_column(String(120))
    owner_membership_id: Mapped[UUID | None] = mapped_column(index=True)
    team_id: Mapped[UUID | None] = mapped_column(index=True)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AssignmentRule(Base):
    __tablename__ = "assignment_rules"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_assignment_rules_tenant_id"),
        CheckConstraint("entity_type IN ('lead', 'company')", name="ck_assignment_rules_entity"),
        CheckConstraint(
            "target_type IN ('member', 'team', 'queue', 'territory')",
            name="ck_assignment_rules_target",
        ),
        CheckConstraint(
            "(target_type = 'member' AND assignee_id IS NOT NULL AND team_id IS NULL "
            "AND queue_id IS NULL AND territory_id IS NULL) OR "
            "(target_type = 'team' AND assignee_id IS NULL AND team_id IS NOT NULL "
            "AND queue_id IS NULL AND territory_id IS NULL) OR "
            "(target_type = 'queue' AND assignee_id IS NULL AND team_id IS NULL "
            "AND queue_id IS NOT NULL AND territory_id IS NULL) OR "
            "(target_type = 'territory' AND assignee_id IS NULL AND team_id IS NULL "
            "AND queue_id IS NULL AND territory_id IS NOT NULL)",
            name="ck_assignment_rules_target_reference",
        ),
        ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_assignment_rules_tenant"),
        ForeignKeyConstraint(
            ["tenant_id", "assignee_id"],
            ["memberships.tenant_id", "memberships.user_id"],
            name="fk_assignment_rules_tenant_assignee_id",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "team_id"],
            ["sales_teams.tenant_id", "sales_teams.id"],
            name="fk_assignment_rules_tenant_team_id",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "queue_id"],
            ["lead_queues.tenant_id", "lead_queues.id"],
            name="fk_assignment_rules_tenant_queue_id",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "territory_id"],
            ["territories.tenant_id", "territories.id"],
            name="fk_assignment_rules_tenant_territory_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    criteria_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    target_type: Mapped[str] = mapped_column(String(20), nullable=False)
    assignee_id: Mapped[UUID | None] = mapped_column(index=True)
    team_id: Mapped[UUID | None] = mapped_column(index=True)
    queue_id: Mapped[UUID | None] = mapped_column(index=True)
    territory_id: Mapped[UUID | None] = mapped_column(index=True)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
