"""
Portfolio: a user's saved listings, each with notes and the cash-flow
assumptions they analysed it with.
"""
import json
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.security import CurrentUser, current_user
from shared import House, SavedHouse, get_db
from shared.models.schemas import HouseResponse

router = APIRouter(prefix="/api/v1/portfolio", tags=["portfolio"])


class SaveHouseRequest(BaseModel):
    house_id: int
    notes: Optional[str] = None
    assumptions: Optional[dict[str, Any]] = None


class UpdateSavedRequest(BaseModel):
    notes: Optional[str] = None
    assumptions: Optional[dict[str, Any]] = None


def _entry(saved: SavedHouse) -> dict:
    return {
        "id": saved.id,
        "house_id": saved.house_id,
        "saved_at": saved.created_at.isoformat(),
        "notes": saved.notes,
        "assumptions": json.loads(saved.assumptions) if saved.assumptions else None,
        "house": HouseResponse.model_validate(saved.house).model_dump(mode="json"),
    }


async def _owned(db: AsyncSession, user_id: int, house_id: int) -> Optional[SavedHouse]:
    return (await db.execute(
        select(SavedHouse).where(SavedHouse.user_id == user_id, SavedHouse.house_id == house_id)
    )).unique().scalar_one_or_none()


@router.get("/saved")
async def get_saved_houses(
    user: CurrentUser = Depends(current_user), db: AsyncSession = Depends(get_db)
):
    """All saved listings for the current user, newest first."""
    result = await db.execute(
        select(SavedHouse).where(SavedHouse.user_id == user.id).order_by(SavedHouse.created_at.desc())
    )
    return [_entry(s) for s in result.unique().scalars().all()]


@router.post("/save")
async def save_house(
    body: SaveHouseRequest,
    user: CurrentUser = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    if not (await db.execute(select(House.id).where(House.id == body.house_id))).scalar():
        raise HTTPException(status_code=404, detail="House not found")
    existing = await _owned(db, user.id, body.house_id)
    if existing:
        return {"message": "House already saved", "id": existing.id}

    saved = SavedHouse(
        user_id=user.id,
        house_id=body.house_id,
        notes=body.notes,
        assumptions=json.dumps(body.assumptions) if body.assumptions else None,
    )
    db.add(saved)
    await db.commit()
    await db.refresh(saved)
    return {"message": "House saved successfully", "id": saved.id, "house_id": saved.house_id}


@router.patch("/saved/{house_id}")
async def update_saved(
    house_id: int,
    body: UpdateSavedRequest,
    user: CurrentUser = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update notes or the saved cash-flow assumptions."""
    saved = await _owned(db, user.id, house_id)
    if not saved:
        raise HTTPException(status_code=404, detail="House not found in portfolio")
    changes = body.model_dump(exclude_unset=True)
    if "notes" in changes:
        saved.notes = changes["notes"]
    if "assumptions" in changes:
        saved.assumptions = json.dumps(changes["assumptions"]) if changes["assumptions"] else None
    await db.commit()
    await db.refresh(saved)
    return _entry(saved)


@router.delete("/saved/{house_id}")
async def remove_house(
    house_id: int,
    user: CurrentUser = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    saved = await _owned(db, user.id, house_id)
    if not saved:
        raise HTTPException(status_code=404, detail="House not found in portfolio")
    await db.delete(saved)
    await db.commit()
    return {"message": "House removed from portfolio"}
