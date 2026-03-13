from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from history_buffer import HistoryBuffer
from mock_engine import MockEngine
from models import (
    Alarm,
    EquipmentSummary,
    HistoryDataPoint,
    HistoryResponse,
    TelemetryValue,
)

engine = MockEngine()
history_buffer = HistoryBuffer(max_seconds=86400)  # 24h
TICK_INTERVAL = float(os.getenv("TWIN_TICK_INTERVAL", "1"))


def _append_telemetry_to_history(equipment_id: str) -> None:
    telemetry = engine.get_telemetry(equipment_id)
    if not telemetry:
        return
    now = datetime.now(timezone.utc)
    for t in telemetry:
        if isinstance(t.value, (int, float)):
            history_buffer.append(t.point_id, float(t.value), now)


async def _tick_loop() -> None:
    while True:
        try:
            engine.tick()
            _append_telemetry_to_history(engine.equipment.id)
        except Exception as exc:
            print(f"[MockEngine] tick error: {exc}")
        await asyncio.sleep(TICK_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_tick_loop())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="Sierac Twin API", version="0.1.0", lifespan=lifespan)

cors_origins = os.getenv("TWIN_CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get(
    "/api/twin/equipment/{equipment_id}/summary",
    response_model=EquipmentSummary,
)
async def get_summary(equipment_id: str) -> EquipmentSummary:
    result = engine.get_summary(equipment_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Equipment not found: {equipment_id}")
    return result


@app.get(
    "/api/twin/equipment/{equipment_id}/telemetry",
    response_model=list[TelemetryValue],
)
async def get_telemetry(equipment_id: str) -> list[TelemetryValue]:
    result = engine.get_telemetry(equipment_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Equipment not found: {equipment_id}")
    return result


@app.get(
    "/api/twin/equipment/{equipment_id}/alarms",
    response_model=list[Alarm],
)
async def get_alarms(equipment_id: str, active: bool = True) -> list[Alarm]:
    result = engine.get_alarms(equipment_id, active_only=active)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Equipment not found: {equipment_id}")
    return result


@app.get(
    "/api/twin/equipment/{equipment_id}/history",
    response_model=HistoryResponse,
)
async def get_history(
    equipment_id: str,
    point_id: str,
    hours: float = 4.0,
    interval: int = 10,
) -> HistoryResponse:
    telemetry = engine.get_telemetry(equipment_id)
    if telemetry is None:
        raise HTTPException(status_code=404, detail=f"Equipment not found: {equipment_id}")
    meta = next((t for t in telemetry if t.point_id == point_id), None)
    point_name = meta.name if meta else point_id
    unit = meta.unit if meta else None
    min_val = meta.min if meta else None
    max_val = meta.max if meta else None
    data = history_buffer.query(point_id, hours=hours, interval_seconds=max(0, interval))
    return HistoryResponse(
        point_id=point_id,
        point_name=point_name,
        unit=unit,
        min=min_val,
        max=max_val,
        data=[HistoryDataPoint(timestamp=d["timestamp"], value=d["value"]) for d in data],
    )


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("TWIN_HOST", "0.0.0.0")
    port = int(os.getenv("TWIN_PORT", "8100"))
    uvicorn.run("main:app", host=host, port=port, reload=True)
