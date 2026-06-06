from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.game import CustomerRead, CustomerRequestRead, GeneratedCustomerResponse
from app.services import customer_service

router = APIRouter(prefix="/api/save-games/{save_game_id}", tags=["customers"])


@router.post("/customers/generate-sample", response_model=GeneratedCustomerResponse)
def generate_sample_customer(save_game_id: int, db: Session = Depends(get_db)):
    customer, request = customer_service.generate_sample_customer(db, save_game_id)
    return {"customer": customer, "request": request}


@router.get("/customers", response_model=list[CustomerRead])
def list_customers(save_game_id: int, db: Session = Depends(get_db)):
    return customer_service.list_customers(db, save_game_id)


@router.get("/customer-requests", response_model=list[CustomerRequestRead])
def list_requests(save_game_id: int, db: Session = Depends(get_db)):
    return customer_service.list_requests(db, save_game_id)
