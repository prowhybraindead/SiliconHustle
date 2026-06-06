from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Union, Dict, Any

from app.core.database import get_db
from app.core.config import get_settings
from app.schemas.game import ExchangeRateRead, CurrencyConversionResult, SupportedCurrency
from app.services import fx_service

router = APIRouter(prefix="/api/fx", tags=["fx"])


@router.get("/supported-currencies", response_model=List[SupportedCurrency])
def get_supported_currencies():
    return fx_service.get_supported_currencies()


@router.get("/rates")
def get_rates(
    base: str = Query(None, description="Base currency code"),
    quote: str = Query(None, description="Quote currency code"),
    db: Session = Depends(get_db)
):
    if base and quote:
        # Get specific rate
        rate, provider, source, fetched_at, is_fallback = fx_service.get_latest_rate(db, base, quote)
        return {
            "base_currency": base.upper(),
            "quote_currency": quote.upper(),
            "rate": rate,
            "provider": provider,
            "source": source,
            "fetched_at": fetched_at,
            "is_fallback": is_fallback
        }
    else:
        # Get all rates to VND
        return fx_service.list_latest_rates(db)


@router.post("/rates/refresh")
def refresh_rates(
    force: bool = Query(False, description="Force refresh from external providers"),
    db: Session = Depends(get_db)
):
    return fx_service.refresh_rates(db, force=force)


@router.get("/convert", response_model=CurrencyConversionResult)
def convert_currency(
    amount: float = Query(..., description="Amount to convert"),
    from_currency: str = Query(..., description="Currency to convert from"),
    to_currency: str = Query("VND", description="Currency to convert to (optional, defaults to VND)"),
    spread_percent: float = Query(0.0, description="Spread percent to apply (optional, defaults to 0.0)"),
    db: Session = Depends(get_db)
):
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()
    
    # We always convert via VND. First convert from_currency to VND.
    converted_amount, rate, provider, fetched_at, is_fallback, spread_applied, final_amount_vnd = fx_service.convert_to_vnd(
        db, amount, from_currency, spread_percent
    )
    
    if to_currency == "VND":
        return CurrencyConversionResult(
            amount=amount,
            from_currency=from_currency,
            to_currency=to_currency,
            converted_amount=converted_amount,
            rate=rate,
            provider=provider,
            fetched_at=fetched_at,
            is_fallback=is_fallback,
            spread_applied=spread_applied,
            final_amount_vnd=final_amount_vnd
        )
    
    # If converting to another foreign currency, e.g. from USD to EUR:
    # We first got final_amount_vnd. Now convert VND to to_currency.
    rate_to_quote, _, _, _, _ = fx_service.get_latest_rate(db, "VND", to_currency)
    converted_foreign = converted_amount * rate_to_quote
    
    # Calculate overall cross rate
    cross_rate, cross_provider, _, _, _ = fx_service.get_latest_rate(db, from_currency, to_currency)
    
    return CurrencyConversionResult(
        amount=amount,
        from_currency=from_currency,
        to_currency=to_currency,
        converted_amount=converted_foreign,
        rate=cross_rate,
        provider=cross_provider,
        fetched_at=fetched_at,
        is_fallback=is_fallback,
        spread_applied=spread_applied,
        final_amount_vnd=final_amount_vnd
    )


@router.get("/attribution")
def get_attribution():
    settings = get_settings()
    return {"attribution": settings.fx_attribution_text}
