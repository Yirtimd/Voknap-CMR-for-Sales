from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ForecastSummary(BaseModel):
    currency: str = "RUB"
    period_days: int
    open_pipeline: float
    due_in_period: float
    weighted_revenue: float
    commit_revenue: float
    best_case_revenue: float
    pipeline_revenue: float
    overdue_revenue: float
    won_revenue: float
    open_deals: int


class StageConversion(BaseModel):
    pipeline_id: UUID
    pipeline_name: str
    stage_id: UUID
    stage_name: str
    sort_order: int
    deal_count: int
    reached_count: int
    amount: float
    weighted_amount: float
    conversion_from_first: float
    conversion_from_previous: float
    stuck_count: int


class StuckDeal(BaseModel):
    deal_id: UUID
    title: str
    company_id: UUID
    company_name: str
    stage_name: str
    owner_name: str | None = None
    amount: float
    weighted_amount: float
    days_in_stage: int
    last_activity_at: datetime | None = None
    risk_level: str


class OwnerTaskSLA(BaseModel):
    owner_id: UUID
    owner_name: str
    total: int
    completed: int
    overdue: int
    sla_rate: float


class TaskSLASummary(BaseModel):
    total: int
    open: int
    completed: int
    overdue: int
    completed_on_time: int
    completion_rate: float
    sla_rate: float
    average_resolution_hours: float | None = None
    by_owner: list[OwnerTaskSLA] = Field(default_factory=list)


class ManagerActivity(BaseModel):
    manager_id: UUID
    manager_name: str
    activities: int
    calls: int
    emails: int
    meetings: int
    notes: int
    tasks_completed: int
    tasks_overdue: int
    open_deals: int
    pipeline_amount: float
    weighted_revenue: float


class CompanyHealthItem(BaseModel):
    company_id: UUID
    company_name: str
    score: int
    label: str
    trend: str | None = None
    open_deals: int
    pipeline_amount: float
    overdue_tasks: int
    days_since_activity: int | None = None
    risk_level: str
    reasons: list[str] = Field(default_factory=list)


class DealRiskItem(BaseModel):
    deal_id: UUID
    title: str
    company_id: UUID
    company_name: str
    stage_name: str
    owner_name: str | None = None
    amount: float
    weighted_amount: float
    score: int
    level: str
    reasons: list[str]


class RiskMap(BaseModel):
    high: int
    medium: int
    low: int
    revenue_at_risk: float
    deals: list[DealRiskItem]


class AnalyticsOverview(BaseModel):
    generated_at: datetime
    forecast: ForecastSummary
    stage_conversion: list[StageConversion]
    stuck_deals: list[StuckDeal]
    task_sla: TaskSLASummary
    manager_activity: list[ManagerActivity]
    company_health: list[CompanyHealthItem]
    risk_map: RiskMap
