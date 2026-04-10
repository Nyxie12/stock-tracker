from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..deps import get_current_user
from ..models.alert import Alert
from ..models.user import User
from ..schemas.alert import AlertCreate, AlertOut, AlertUpdate

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut])
async def list_alerts(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Alert]:
    res = await db.execute(
        select(Alert).where(Alert.user_id == user.id).order_by(Alert.created_at.desc())
    )
    return list(res.scalars().all())


@router.post("", response_model=AlertOut, status_code=201)
async def create_alert(
    payload: AlertCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Alert:
    alert = Alert(
        user_id=user.id,
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
    alert_id: int,
    payload: AlertUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Alert:
    alert = await db.get(Alert, alert_id)
    if not alert or alert.user_id != user.id:
        raise HTTPException(404, "Not found")
    if payload.active is not None and payload.active != alert.active:
        alert.active = payload.active
        await db.commit()
        await db.refresh(alert)
        await request.app.state.alert_engine.set_active(alert_id, alert.active)
    return alert


@router.delete("/{alert_id}", status_code=204)
async def delete_alert(
    alert_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    alert = await db.get(Alert, alert_id)
    if not alert or alert.user_id != user.id:
        raise HTTPException(404, "Not found")
    await db.delete(alert)
    await db.commit()
    await request.app.state.alert_engine.remove(alert_id)
