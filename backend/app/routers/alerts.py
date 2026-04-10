from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models.alert import Alert
from ..schemas.alert import AlertCreate, AlertOut, AlertUpdate

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut])
async def list_alerts(db: AsyncSession = Depends(get_db)) -> list[Alert]:
    res = await db.execute(select(Alert).order_by(Alert.created_at.desc()))
    return list(res.scalars().all())


@router.post("", response_model=AlertOut, status_code=201)
async def create_alert(
    payload: AlertCreate, request: Request, db: AsyncSession = Depends(get_db)
) -> Alert:
    alert = Alert(
        symbol=payload.symbol.upper().strip(),
        condition=payload.condition,
        threshold=Decimal(str(payload.threshold)),
        active=True,
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    await request.app.state.alert_engine.add(alert)
    return alert


@router.patch("/{alert_id}", response_model=AlertOut)
async def update_alert(
    alert_id: int, payload: AlertUpdate, request: Request, db: AsyncSession = Depends(get_db)
) -> Alert:
    alert = await db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(404, "Not found")
    if payload.active is not None and payload.active != alert.active:
        alert.active = payload.active
        await db.commit()
        await db.refresh(alert)
        await request.app.state.alert_engine.set_active(alert_id, alert.active)
    return alert


@router.delete("/{alert_id}", status_code=204)
async def delete_alert(
    alert_id: int, request: Request, db: AsyncSession = Depends(get_db)
) -> None:
    alert = await db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(404, "Not found")
    await db.delete(alert)
    await db.commit()
    await request.app.state.alert_engine.remove(alert_id)
