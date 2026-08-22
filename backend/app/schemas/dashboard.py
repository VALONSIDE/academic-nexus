"""Compact, role-aware metrics for the workspace overview."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class DashboardMetric(BaseModel):
    code: str
    value: int
    total: int | None = None


class DashboardBreakdown(BaseModel):
    code: str
    value: int = Field(ge=0)


class DashboardSelectionActivity(BaseModel):
    id: str
    student_name: str
    mentor_name: str
    status: str
    updated_at: datetime


class DashboardResponse(BaseModel):
    role: Literal["student", "mentor", "admin"]
    metrics: list[DashboardMetric]
    profile_completion: list[DashboardBreakdown]
    resource_distribution: list[DashboardBreakdown]
    selection_statistics: list[DashboardBreakdown] = Field(default_factory=list)
    recent_selection_activity: list[DashboardSelectionActivity] = Field(default_factory=list)
