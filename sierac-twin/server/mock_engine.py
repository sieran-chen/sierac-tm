from __future__ import annotations

import random
import uuid
from datetime import datetime, timezone
from enum import Enum

from models import (
    Alarm,
    AlarmLevel,
    Equipment,
    EquipmentStatus,
    EquipmentSummary,
    HighlightValue,
    TelemetryValue,
)


TRANSITION_MATRIX: dict[EquipmentStatus, dict[EquipmentStatus, float]] = {
    EquipmentStatus.RUNNING: {
        EquipmentStatus.RUNNING: 0.96,
        EquipmentStatus.IDLE: 0.02,
        EquipmentStatus.FAULT: 0.01,
        EquipmentStatus.MAINTENANCE: 0.01,
    },
    EquipmentStatus.IDLE: {
        EquipmentStatus.RUNNING: 0.30,
        EquipmentStatus.IDLE: 0.65,
        EquipmentStatus.MAINTENANCE: 0.05,
    },
    EquipmentStatus.FAULT: {
        EquipmentStatus.FAULT: 0.70,
        EquipmentStatus.MAINTENANCE: 0.30,
    },
    EquipmentStatus.MAINTENANCE: {
        EquipmentStatus.MAINTENANCE: 0.80,
        EquipmentStatus.IDLE: 0.20,
    },
}


def _weighted_choice(options: dict[EquipmentStatus, float]) -> EquipmentStatus:
    r = random.random()
    cumulative = 0.0
    for state, prob in options.items():
        cumulative += prob
        if r <= cumulative:
            return state
    return list(options.keys())[-1]


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _walk(current: float, step: float, lo: float, hi: float) -> float:
    return _clamp(current + random.gauss(0, step), lo, hi)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class MockEngine:
    def __init__(self, equipment_id: str = "roller-001") -> None:
        self.equipment = Equipment(
            id=equipment_id,
            name="1号滚筒剔除装置",
            model="滚筒剔除机",
            location="A车间-1号线",
            status=EquipmentStatus.IDLE,
        )

        self.roller_speed: float = 120.0  # rpm
        self.belt_speed: float = 25.0  # m/min
        self.motor_current: float = 4.2  # A
        self.temperature: float = 42.0  # °C 滚筒/轴承温
        self.today_pass: float = 0.0  # 通过数
        self.today_reject: float = 0.0  # 剔除数
        self.today_target: float = 30000.0  # 目标通过数
        self.runtime_seconds: int = 0
        self.oee: float = 85.0
        self.availability_rate: float = 0.92
        self.performance_rate: float = 0.95
        self.quality_rate: float = 0.98

        self.alarms: dict[str, Alarm] = {}
        self.tick_count: int = 0

    def tick(self) -> None:
        self.tick_count += 1
        prev_status = self.equipment.status

        new_status = _weighted_choice(TRANSITION_MATRIX[prev_status])
        self.equipment.status = new_status

        if new_status == EquipmentStatus.RUNNING:
            self.roller_speed = _walk(self.roller_speed, 3.0, 80.0, 180.0)
            self.belt_speed = _walk(self.belt_speed, 0.5, 15.0, 35.0)
            self.motor_current = _walk(self.motor_current, 0.2, 2.0, 8.0)
            self.temperature = _walk(self.temperature, 0.5, 30.0, 65.0)
            self.today_pass += self.belt_speed * 0.5  # 模拟通过数
            self.runtime_seconds += 1
            if random.random() < 0.008:
                self.today_reject += 1
            self.oee = _walk(self.oee, 0.3, 70.0, 95.0)
            self.availability_rate = _walk(self.availability_rate, 0.01, 0.85, 0.99)
            self.performance_rate = _walk(self.performance_rate, 0.01, 0.85, 0.99)
            self.quality_rate = _clamp(self.oee / (self.availability_rate * self.performance_rate or 0.01), 0.8, 1.0)

        elif new_status == EquipmentStatus.IDLE:
            self.roller_speed = max(0, self.roller_speed - 15)
            self.belt_speed = max(0, self.belt_speed - 5)
            self.temperature = _walk(self.temperature, 0.5, 20.0, 55.0)
            self.oee = _walk(self.oee, 0.5, 60.0, self.oee)

        elif new_status == EquipmentStatus.FAULT:
            self.roller_speed = max(0, self.roller_speed - 30)
            self.belt_speed = 0
            self.temperature = _walk(self.temperature, 1.0, 35.0, 80.0)
            self.oee = _walk(self.oee, 1.0, 40.0, self.oee)

        elif new_status == EquipmentStatus.MAINTENANCE:
            self.roller_speed = 0
            self.belt_speed = 0
            self.temperature = _walk(self.temperature, 0.3, 25.0, 50.0)

        self._check_alarms()

    def _check_alarms(self) -> None:
        self._check_threshold(
            "temp_high", "temperature", self.temperature,
            warning_hi=55.0, critical_hi=70.0,
            msg_warning="滚筒/轴承温度偏高 ({val:.1f}°C)",
            msg_critical="滚筒/轴承温度过高 ({val:.1f}°C)",
        )
        self._check_threshold(
            "current_high", "motor_current", self.motor_current,
            warning_hi=6.0, critical_hi=7.5,
            msg_warning="电机电流偏高 ({val:.2f} A)",
            msg_critical="电机电流过高 ({val:.2f} A)",
        )
        self._check_threshold(
            "speed_low", "roller_speed", self.roller_speed,
            warning_lo=60.0, critical_lo=40.0,
            msg_warning="滚筒转速偏低 ({val:.1f} rpm)",
            msg_critical="滚筒转速过低 ({val:.1f} rpm)",
        )

        if self.equipment.status == EquipmentStatus.FAULT:
            if "fault_alarm" not in self.alarms:
                self.alarms["fault_alarm"] = Alarm(
                    id=f"alarm-{uuid.uuid4().hex[:8]}",
                    equipment_id=self.equipment.id,
                    level=AlarmLevel.CRITICAL,
                    message="设备故障停机",
                    start_time=_now_iso(),
                )
        else:
            self.alarms.pop("fault_alarm", None)

    def _check_threshold(
        self,
        alarm_key: str,
        point_id: str,
        value: float,
        warning_lo: float | None = None,
        critical_lo: float | None = None,
        warning_hi: float | None = None,
        critical_hi: float | None = None,
        msg_warning: str = "",
        msg_critical: str = "",
    ) -> None:
        is_critical = False
        is_warning = False

        if critical_hi is not None and value > critical_hi:
            is_critical = True
        elif critical_lo is not None and value < critical_lo:
            is_critical = True
        elif warning_hi is not None and value > warning_hi:
            is_warning = True
        elif warning_lo is not None and value < warning_lo:
            is_warning = True

        if is_critical:
            if alarm_key not in self.alarms or self.alarms[alarm_key].level != AlarmLevel.CRITICAL:
                self.alarms[alarm_key] = Alarm(
                    id=f"alarm-{uuid.uuid4().hex[:8]}",
                    equipment_id=self.equipment.id,
                    point_id=point_id,
                    level=AlarmLevel.CRITICAL,
                    message=msg_critical.format(val=value),
                    start_time=_now_iso(),
                )
        elif is_warning:
            if alarm_key not in self.alarms or self.alarms[alarm_key].level != AlarmLevel.WARNING:
                self.alarms[alarm_key] = Alarm(
                    id=f"alarm-{uuid.uuid4().hex[:8]}",
                    equipment_id=self.equipment.id,
                    point_id=point_id,
                    level=AlarmLevel.WARNING,
                    message=msg_warning.format(val=value),
                    start_time=_now_iso(),
                )
        else:
            self.alarms.pop(alarm_key, None)

    def get_summary(self, equipment_id: str) -> EquipmentSummary | None:
        if equipment_id != self.equipment.id:
            return None
        return EquipmentSummary(
            equipment=self.equipment,
            highlights={
                "roller_speed": HighlightValue(value=round(self.roller_speed, 1), unit="rpm"),
                "today_pass": HighlightValue(value=round(self.today_pass), unit="件"),
                "today_reject": HighlightValue(value=round(self.today_reject), unit="件"),
                "today_target": HighlightValue(value=round(self.today_target), unit="件"),
                "oee": HighlightValue(value=round(self.oee, 1), unit="%"),
            },
            active_alarms=len(self.alarms),
            updated_at=_now_iso(),
        )

    def get_telemetry(self, equipment_id: str) -> list[TelemetryValue] | None:
        if equipment_id != self.equipment.id:
            return None
        now = _now_iso()
        return [
            TelemetryValue(point_id="status", name="运行状态", value=self.equipment.status.value, timestamp=now),
            TelemetryValue(point_id="roller_speed", name="滚筒转速", value=round(self.roller_speed, 1), unit="rpm", min=80, max=180, timestamp=now),
            TelemetryValue(point_id="belt_speed", name="皮带速度", value=round(self.belt_speed, 1), unit="m/min", min=15, max=35, timestamp=now),
            TelemetryValue(point_id="motor_current", name="电机电流", value=round(self.motor_current, 2), unit="A", min=2.0, max=6.0, timestamp=now),
            TelemetryValue(point_id="temperature", name="滚筒/轴承温度", value=round(self.temperature, 1), unit="°C", min=30, max=55, timestamp=now),
            TelemetryValue(point_id="today_pass", name="当日通过数", value=round(self.today_pass), unit="件", min=0, max=50000, timestamp=now),
            TelemetryValue(point_id="today_reject", name="当日剔除数", value=round(self.today_reject), unit="件", min=0, max=5000, timestamp=now),
            TelemetryValue(point_id="today_target", name="当日目标", value=round(self.today_target), unit="件", timestamp=now),
            TelemetryValue(point_id="runtime_today", name="当日运行时长", value=round(self.runtime_seconds / 3600, 2), unit="小时", min=0, max=24, timestamp=now),
            TelemetryValue(point_id="oee", name="设备综合效率", value=round(self.oee, 1), unit="%", min=70, max=95, timestamp=now),
            TelemetryValue(point_id="availability_rate", name="可用率", value=round(self.availability_rate * 100, 1), unit="%", timestamp=now),
            TelemetryValue(point_id="performance_rate", name="性能率", value=round(self.performance_rate * 100, 1), unit="%", timestamp=now),
            TelemetryValue(point_id="quality_rate", name="良品率", value=round(self.quality_rate * 100, 1), unit="%", timestamp=now),
        ]

    def get_alarms(self, equipment_id: str, active_only: bool = True) -> list[Alarm] | None:
        if equipment_id != self.equipment.id:
            return None
        alarms = list(self.alarms.values())
        if active_only:
            alarms = [a for a in alarms if a.end_time is None]
        return alarms
