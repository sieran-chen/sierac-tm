"""Unit tests for MockEngine: state machine, telemetry gradient, alarms, output accumulation."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from mock_engine import MockEngine
from models import EquipmentStatus


def test_initial_state_is_idle() -> None:
    engine = MockEngine()
    assert engine.equipment.status == EquipmentStatus.IDLE


def test_state_transitions_follow_matrix() -> None:
    engine = MockEngine()
    engine.equipment.status = EquipmentStatus.RUNNING
    counts: dict[EquipmentStatus, int] = {
        EquipmentStatus.RUNNING: 0,
        EquipmentStatus.IDLE: 0,
        EquipmentStatus.FAULT: 0,
        EquipmentStatus.MAINTENANCE: 0,
    }
    for _ in range(500):
        engine.tick()
        counts[engine.equipment.status] += 1
    assert sum(counts.values()) == 500
    assert counts[EquipmentStatus.RUNNING] > 300


def test_telemetry_gradual_change() -> None:
    engine = MockEngine()
    engine.equipment.status = EquipmentStatus.RUNNING
    engine.roller_speed = 120.0
    prev_speed = engine.roller_speed
    with patch("mock_engine._weighted_choice", return_value=EquipmentStatus.RUNNING):
        for _ in range(10):
            engine.tick()
            assert abs(engine.roller_speed - prev_speed) <= 30
            prev_speed = engine.roller_speed


def test_alarm_on_fault() -> None:
    engine = MockEngine()
    engine.equipment.status = EquipmentStatus.RUNNING
    for _ in range(5):
        engine.tick()
    engine.equipment.status = EquipmentStatus.FAULT
    engine._check_alarms()
    assert "fault_alarm" in engine.alarms
    assert engine.alarms["fault_alarm"].level.value == "critical"


def test_alarm_recovery() -> None:
    engine = MockEngine()
    engine.equipment.status = EquipmentStatus.RUNNING
    engine.temperature = 60.0
    engine._check_alarms()
    assert "temp_high" in engine.alarms
    engine.temperature = 45.0
    engine._check_alarms()
    assert "temp_high" not in engine.alarms


def test_output_accumulation_only_when_running() -> None:
    engine = MockEngine()
    engine.equipment.status = EquipmentStatus.RUNNING
    engine.belt_speed = 25.0
    out_before = engine.today_pass
    for _ in range(60):
        engine.tick()
    assert engine.today_pass > out_before

    engine.equipment.status = EquipmentStatus.IDLE
    out_idle = engine.today_pass
    with patch("mock_engine._weighted_choice", return_value=EquipmentStatus.IDLE):
        for _ in range(60):
            engine.tick()
    assert engine.today_pass == out_idle


def test_get_summary_returns_none_for_unknown_id() -> None:
    engine = MockEngine()
    assert engine.get_summary("other-001") is None
    assert engine.get_summary("roller-001") is not None


def test_get_telemetry_returns_all_points() -> None:
    engine = MockEngine()
    telemetry = engine.get_telemetry("roller-001")
    assert telemetry is not None
    point_ids = {t.point_id for t in telemetry}
    assert "roller_speed" in point_ids
    assert "temperature" in point_ids
    assert "oee" in point_ids
    assert "availability_rate" in point_ids
