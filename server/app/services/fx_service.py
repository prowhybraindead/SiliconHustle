import httpx
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Tuple
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entities import ExchangeRate

SUPPORTED_CURRENCIES = {
    "VND": {"name": "Vietnamese Dong", "symbol": "₫", "country": "Vietnam"},
    "USD": {"name": "US Dollar", "symbol": "$", "country": "United States"},
    "EUR": {"name": "Euro", "symbol": "€", "country": "Eurozone"},
    "JPY": {"name": "Japanese Yen", "symbol": "¥", "country": "Japan"},
    "CNY": {"name": "Chinese Yuan", "symbol": "¥", "country": "China"},
    "TWD": {"name": "New Taiwan Dollar", "symbol": "NT$", "country": "Taiwan"},
    "HKD": {"name": "Hong Kong Dollar", "symbol": "HK$", "country": "Hong Kong"},
    "KRW": {"name": "South Korean Won", "symbol": "₩", "country": "South Korea"},
    "SGD": {"name": "Singapore Dollar", "symbol": "S$", "country": "Singapore"},
    "THB": {"name": "Thai Baht", "symbol": "฿", "country": "Thailand"}
}

STATIC_FALLBACK_RATES = {
    "USD": 25400.0,
    "EUR": 27500.0,
    "JPY": 160.0,
    "CNY": 3500.0,
    "TWD": 780.0,
    "HKD": 3250.0,
    "KRW": 18.5,
    "SGD": 18800.0,
    "THB": 690.0,
    "VND": 1.0
}

FRANKFURTER_SUPPORTED = {"USD", "EUR", "JPY", "CNY", "HKD", "KRW", "SGD", "THB"}


def get_supported_currencies() -> List[Dict[str, str]]:
    return [
        {"code": code, "name": info["name"], "symbol": info["symbol"], "country": info["country"]}
        for code, info in SUPPORTED_CURRENCIES.items()
    ]


def _upsert_rate(db: Session, base_currency: str, quote_currency: str, rate: float, provider: str, source: str, is_fallback: bool, raw_json: Any) -> ExchangeRate:
    now = datetime.now(timezone.utc)
    stmt = select(ExchangeRate).where(
        ExchangeRate.base_currency == base_currency,
        ExchangeRate.quote_currency == quote_currency
    )
    existing = db.scalar(stmt)
    if existing:
        existing.rate = rate
        existing.provider = provider
        existing.source = source
        existing.is_fallback = is_fallback
        existing.raw_json = raw_json
        existing.fetched_at = now
        db.commit()
        db.refresh(existing)
        return existing
    else:
        new_rate = ExchangeRate(
            base_currency=base_currency,
            quote_currency=quote_currency,
            rate=rate,
            provider=provider,
            source=source,
            is_fallback=is_fallback,
            raw_json=raw_json,
            fetched_at=now
        )
        db.add(new_rate)
        db.commit()
        db.refresh(new_rate)
        return new_rate


def get_rate_to_vnd(db: Session, currency: str, force_refresh=False) -> Tuple[float, str, str, datetime, bool, Any]:
    currency = currency.upper()
    if currency not in SUPPORTED_CURRENCIES:
        raise ValueError(f"Currency {currency} is not supported.")

    now = datetime.now(timezone.utc)
    if currency == "VND":
        return (1.0, "identity", "Static Identity", now, False, None)

    settings = get_settings()

    # 1. Check DB Cache
    if not force_refresh:
        stmt = select(ExchangeRate).where(
            ExchangeRate.base_currency == currency,
            ExchangeRate.quote_currency == "VND"
        ).order_by(ExchangeRate.fetched_at.desc())
        cached = db.scalar(stmt)
        if cached:
            ttl = settings.fx_cache_ttl_seconds
            # Make sure we handle tzinfo safely
            fetched_at_utc = cached.fetched_at.replace(tzinfo=timezone.utc) if cached.fetched_at.tzinfo is None else cached.fetched_at
            if fetched_at_utc + timedelta(seconds=ttl) > now:
                return (
                    cached.rate,
                    cached.provider,
                    cached.source or "",
                    cached.fetched_at,
                    cached.is_fallback,
                    cached.raw_json
                )

    # 2. Try external call if enabled and fx_enabled is true
    if settings.fx_enabled and settings.fx_external_calls_enabled:
        timeout = settings.fx_request_timeout_seconds
        
        # Try Frankfurter first (if supported)
        if settings.fx_primary_provider == "frankfurter" and currency in FRANKFURTER_SUPPORTED:
            try:
                url = f"https://api.frankfurter.app/latest?from={currency}&to=VND"
                response = httpx.get(url, timeout=timeout)
                if response.status_code == 200:
                    data = response.json()
                    rate = data.get("rates", {}).get("VND")
                    if rate is not None:
                        cached_rate = _upsert_rate(db, currency, "VND", float(rate), "frankfurter", "Frankfurter API", False, data)
                        return (cached_rate.rate, cached_rate.provider, cached_rate.source, cached_rate.fetched_at, cached_rate.is_fallback, cached_rate.raw_json)
            except Exception:
                pass

        # Try ExchangeRate-API Open Access
        try:
            url = f"https://open.er-api.com/v6/latest/{currency}"
            response = httpx.get(url, timeout=timeout)
            if response.status_code == 200:
                data = response.json()
                if data.get("result") == "success":
                    rate = data.get("rates", {}).get("VND")
                    if rate is not None:
                        cached_rate = _upsert_rate(db, currency, "VND", float(rate), "exchangerate_api_open_access", "ExchangeRate-API Open Access", False, data)
                        return (cached_rate.rate, cached_rate.provider, cached_rate.source, cached_rate.fetched_at, cached_rate.is_fallback, cached_rate.raw_json)
        except Exception:
            pass

    # 3. Fallback to latest cached DB rate (even if expired)
    stmt = select(ExchangeRate).where(
        ExchangeRate.base_currency == currency,
        ExchangeRate.quote_currency == "VND"
    ).order_by(ExchangeRate.fetched_at.desc())
    expired_cached = db.scalar(stmt)
    if expired_cached:
        return (
            expired_cached.rate,
            expired_cached.provider,
            expired_cached.source or "",
            expired_cached.fetched_at,
            True,
            expired_cached.raw_json
        )

    # 4. Fallback to static rates
    if settings.fx_static_fallback_enabled:
        static_rate = STATIC_FALLBACK_RATES.get(currency, 1.0)
        cached_rate = _upsert_rate(db, currency, "VND", static_rate, "static_fallback", "Static Fallback", True, None)
        return (cached_rate.rate, cached_rate.provider, cached_rate.source, cached_rate.fetched_at, cached_rate.is_fallback, cached_rate.raw_json)

    # Absolute fallback
    return (1.0, "static_fallback", "Static Fallback Default", now, True, None)


def get_latest_rate(db: Session, base_currency: str, quote_currency: str, force_refresh=False) -> Tuple[float, str, str, datetime, bool]:
    base_currency = base_currency.upper()
    quote_currency = quote_currency.upper()

    if base_currency == quote_currency:
        return (1.0, "identity", "Static Identity", datetime.now(timezone.utc), False)

    # If quote_currency is VND (direct conversion to base accounting)
    if quote_currency == "VND":
        rate, provider, source, fetched_at, is_fallback, _ = get_rate_to_vnd(db, base_currency, force_refresh)
        return (rate, provider, source, fetched_at, is_fallback)

    # If base_currency is VND (reverse conversion)
    if base_currency == "VND":
        rate, provider, source, fetched_at, is_fallback, _ = get_rate_to_vnd(db, quote_currency, force_refresh)
        return (1.0 / rate if rate != 0 else 0.0, provider, source, fetched_at, is_fallback)

    # Both are foreign currencies, e.g., USD -> EUR
    rate_base, provider_base, source_base, fetched_at_base, fallback_base, _ = get_rate_to_vnd(db, base_currency, force_refresh)
    rate_quote, provider_quote, source_quote, fetched_at_quote, fallback_quote, _ = get_rate_to_vnd(db, quote_currency, force_refresh)

    rate = rate_base / rate_quote if rate_quote != 0 else 0.0
    provider = f"{provider_base}/{provider_quote}"
    source = f"{source_base} / {source_quote}"
    fetched_at = min(fetched_at_base, fetched_at_quote)
    is_fallback = fallback_base or fallback_quote

    return (rate, provider, source, fetched_at, is_fallback)


def convert_to_vnd(db: Session, amount: float, currency: str, spread_percent: float = 0.0, force_refresh=False) -> Tuple[float, float, str, datetime, bool, float, int]:
    currency = currency.upper()
    if currency == "VND":
        return (amount, 1.0, "identity", datetime.now(timezone.utc), False, 0.0, int(amount))

    rate, provider, source, fetched_at, is_fallback, _ = get_rate_to_vnd(db, currency, force_refresh)
    
    # Apply spread
    rate_with_spread = rate * (1.0 + spread_percent / 100.0)
    converted_amount = amount * rate_with_spread
    final_amount_vnd = round(converted_amount)

    return (converted_amount, rate, provider, fetched_at, is_fallback, spread_percent, final_amount_vnd)


def list_latest_rates(db: Session) -> List[Dict[str, Any]]:
    rates = []
    for cur in SUPPORTED_CURRENCIES:
        if cur == "VND":
            continue
        try:
            rate, provider, source, fetched_at, is_fallback, _ = get_rate_to_vnd(db, cur)
            rates.append({
                "base_currency": cur,
                "quote_currency": "VND",
                "rate": rate,
                "provider": provider,
                "source": source,
                "fetched_at": fetched_at,
                "is_fallback": is_fallback
            })
        except Exception:
            pass
    return rates


def refresh_rates(db: Session, force=False) -> List[Dict[str, Any]]:
    rates = []
    for cur in SUPPORTED_CURRENCIES:
        if cur == "VND":
            continue
        try:
            rate, provider, source, fetched_at, is_fallback, _ = get_rate_to_vnd(db, cur, force_refresh=True)
            rates.append({
                "base_currency": cur,
                "quote_currency": "VND",
                "rate": rate,
                "provider": provider,
                "source": source,
                "fetched_at": fetched_at,
                "is_fallback": is_fallback
            })
        except Exception:
            pass
    return rates
