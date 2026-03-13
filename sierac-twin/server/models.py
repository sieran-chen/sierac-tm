from __future__ import annotations

from enum import Enum
from pydantic import BaseModel


class EquipmentStatus(str, Enum):
    RUNNING = "running"
    IDLE = "idle"
    FAULT = "fault"
    MAINTENANCE = "maintenance"


class Equipment(BaseModel):
    id: str
    name: str
    model: str
    location: str
    status: EquipmentStatus


class HighlightValue(BaseModel):
    value: float
    unit: str


class EquipmentSummary(BaseModel):
    equipment: Equipment
    highlights: dict[str, HighlightValue]
    active_alarms: int
    updated_at: str


class TelemetryValue(BaseModel):
    point_id: str
    name: str
    value: float | str | bool
    unit: str | None = None
    min: float | None = None
    max: float | None = None
    quality: str = "good"
    timestamp: str


class AlarmLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Alarm(BaseModel):
    id: str
    equipment_id: str
    point_id: str | None = None
    level: AlarmLevel
    message: str
    start_time: str
    end_time: str | None = None
    acknowledged: bool = False


class HistoryDataPoint(BaseModel):
    timestamp: str
    value: float


class HistoryResponse(BaseModel):
    point_id: str
    point_name: str
    unit: str | None
    min: float | None
    max: float | None
    data: list[HistoryDataPoint]
