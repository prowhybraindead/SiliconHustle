from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.enums import TestType
from app.schemas.game import InventoryUnitCreate, InventoryUnitRead, InventoryUnitUpdate, TestActionResponse, TestResultRead
from app.services import inventory_service, test_bench_service

router = APIRouter(prefix="/api/save-games/{save_game_id}/inventory", tags=["inventory"])


@router.get("", response_model=list[InventoryUnitRead])
def list_inventory(save_game_id: int, db: Session = Depends(get_db)):
    return inventory_service.list_inventory(db, save_game_id)


@router.post("", response_model=InventoryUnitRead)
def create_inventory(save_game_id: int, payload: InventoryUnitCreate, db: Session = Depends(get_db)):
    return inventory_service.create_inventory_unit(db, save_game_id, payload)


@router.get("/{inventory_unit_id}", response_model=InventoryUnitRead)
def get_inventory(save_game_id: int, inventory_unit_id: int, db: Session = Depends(get_db)):
    return inventory_service.get_inventory_unit(db, save_game_id, inventory_unit_id)


@router.patch("/{inventory_unit_id}", response_model=InventoryUnitRead)
def update_inventory(save_game_id: int, inventory_unit_id: int, payload: InventoryUnitUpdate, db: Session = Depends(get_db)):
    return inventory_service.update_inventory_unit(db, save_game_id, inventory_unit_id, payload)


def _run_test(db: Session, save_game_id: int, inventory_unit_id: int, test_type: TestType) -> dict[str, object]:
    unit, result = test_bench_service.run_test(db, save_game_id, inventory_unit_id, test_type)
    return {"unit": unit, "result": result}


@router.post("/{inventory_unit_id}/tests/basic-check", response_model=TestActionResponse)
def basic_check(save_game_id: int, inventory_unit_id: int, db: Session = Depends(get_db)):
    return _run_test(db, save_game_id, inventory_unit_id, TestType.BASIC_CHECK)


@router.post("/{inventory_unit_id}/tests/benchmark", response_model=TestActionResponse)
def benchmark(save_game_id: int, inventory_unit_id: int, db: Session = Depends(get_db)):
    return _run_test(db, save_game_id, inventory_unit_id, TestType.BENCHMARK)


@router.post("/{inventory_unit_id}/tests/stress-test", response_model=TestActionResponse)
def stress_test(save_game_id: int, inventory_unit_id: int, db: Session = Depends(get_db)):
    return _run_test(db, save_game_id, inventory_unit_id, TestType.STRESS_TEST)


@router.post("/{inventory_unit_id}/tests/full-inspection", response_model=TestActionResponse)
def full_inspection(save_game_id: int, inventory_unit_id: int, db: Session = Depends(get_db)):
    return _run_test(db, save_game_id, inventory_unit_id, TestType.FULL_INSPECTION)


@router.get("/{inventory_unit_id}/tests", response_model=list[TestResultRead])
def list_tests(save_game_id: int, inventory_unit_id: int, db: Session = Depends(get_db)):
    return test_bench_service.list_tests(db, save_game_id, inventory_unit_id)
