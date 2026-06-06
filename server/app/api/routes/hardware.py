from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.enums import HardwareCategory
from app.schemas.game import HardwareProductRead
from app.services import hardware_service

router = APIRouter(prefix="/api/hardware-products", tags=["hardware"])


@router.get("", response_model=list[HardwareProductRead])
def list_products(
    category: HardwareCategory | None = None,
    brand_id: int | None = None,
    brand_slug: str | None = None,
    chip_vendor_slug: str | None = None,
    q: str | None = None,
    data_confidence: str | None = None,
    origin_code: str | None = None,
    min_performance_score: int | None = None,
    max_power_watts: int | None = None,
    save_game_id: int | None = None,
    db: Session = Depends(get_db),
):
    return hardware_service.list_products(
        db,
        category=category,
        brand_id=brand_id,
        brand_slug=brand_slug,
        chip_vendor_slug=chip_vendor_slug,
        q=q,
        data_confidence=data_confidence,
        origin_code=origin_code,
        min_performance_score=min_performance_score,
        max_power_watts=max_power_watts,
        save_game_id=save_game_id,
    )


@router.get("/{product_id}", response_model=HardwareProductRead)
def get_product(product_id: int, save_game_id: int | None = None, db: Session = Depends(get_db)):
    return hardware_service.get_product(db, product_id, save_game_id=save_game_id)
