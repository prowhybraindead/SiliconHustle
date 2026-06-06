from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.game import PurchaseOrderCreate, PurchaseOrderRead, SupplierOfferRead, SupplierRead
from app.services import supplier_service

router = APIRouter(tags=["suppliers"])


@router.get("/api/suppliers", response_model=list[SupplierRead])
def list_suppliers(db: Session = Depends(get_db)):
    return supplier_service.list_suppliers(db)


@router.get("/api/supplier-offers", response_model=list[SupplierOfferRead])
def list_offers(
    category: str | None = Query(None, description="Filter by hardware category"),
    brand_slug: str | None = Query(None, description="Filter by brand slug"),
    supplier_id: int | None = Query(None, description="Filter by supplier ID"),
    q: str | None = Query(None, description="Search product or supplier name"),
    currency: str | None = Query(None, description="Filter by currency"),
    save_game_id: int | None = Query(None, description="Optional save game ID"),
    db: Session = Depends(get_db)
):
    return supplier_service.list_offers(
        db,
        category=category,
        brand_slug=brand_slug,
        supplier_id=supplier_id,
        q=q,
        currency=currency,
        save_game_id=save_game_id,
    )


@router.get("/api/save-games/{save_game_id}/purchase-orders", response_model=list[PurchaseOrderRead])
def list_purchase_orders(save_game_id: int, db: Session = Depends(get_db)):
    return supplier_service.list_purchase_orders(db, save_game_id)


@router.post("/api/save-games/{save_game_id}/purchase-orders", response_model=PurchaseOrderRead)
def create_purchase_order(save_game_id: int, payload: PurchaseOrderCreate, db: Session = Depends(get_db)):
    return supplier_service.create_purchase_order(db, save_game_id, payload)


@router.post("/api/save-games/{save_game_id}/purchase-orders/{purchase_order_id}/receive", response_model=PurchaseOrderRead)
def receive_purchase_order(save_game_id: int, purchase_order_id: int, db: Session = Depends(get_db)):
    return supplier_service.receive_purchase_order(db, save_game_id, purchase_order_id)
