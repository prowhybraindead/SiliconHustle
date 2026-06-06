from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    brands,
    customers,
    fx,
    hardware,
    health,
    inventory,
    orders,
    quotes,
    save_games,
    suppliers,
    warranty,
    product_prices,
    market,
    player_profiles,
    progression,
    compatibility,
    used_market,
    refurbish,
    resale,
    reviews,
    staff,
    customer_personas,
    customer_conversations,
)
from app.core.config import get_settings
from app.core.database import SessionLocal, init_db
from app.seed.initial_data import seed_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with SessionLocal() as db:
        seed_database(db)
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(save_games.router)
app.include_router(brands.router)
app.include_router(hardware.router)
app.include_router(inventory.router)
app.include_router(suppliers.router)
app.include_router(customers.router)
app.include_router(orders.router)
app.include_router(quotes.router)
app.include_router(warranty.router)
app.include_router(fx.router)
app.include_router(product_prices.router)
app.include_router(market.router)
app.include_router(player_profiles.router)
app.include_router(progression.router)
app.include_router(compatibility.router)
app.include_router(used_market.router)
app.include_router(refurbish.router)
app.include_router(resale.router)
app.include_router(reviews.router)
app.include_router(staff.router)
app.include_router(customer_personas.router)
app.include_router(customer_conversations.router)
