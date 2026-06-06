from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Silicon Hustle API"
    environment: str = "local"
    database_url: str = "sqlite:///./silicon_hustle.db"
    frontend_origin: str = "http://localhost:5173"
    nestyai_base_url: str | None = None
    nestyai_api_key: str | None = None
    nestyai_model_default: str = "nestyai-default"

    # FX Settings
    base_currency: str = "VND"
    fx_enabled: bool = True
    fx_external_calls_enabled: bool = True
    fx_primary_provider: str = "frankfurter"
    fx_fallback_provider: str = "exchangerate_api_open_access"
    fx_cache_ttl_seconds: int = 21600
    fx_request_timeout_seconds: int = 8
    fx_static_fallback_enabled: bool = True
    fx_spread_percent_default: float = 1.5
    fx_attribution_text: str = "Exchange rates provided by Frankfurter / ExchangeRate-API where available."

    # Market Events settings
    ai_market_events_enabled: bool = False
    ai_market_events_model: str = "nesty-flash-1.0"
    ai_market_events_max_active_context: int = 5
    market_random_event_chance: float = 0.20
    market_max_active_events: int = 5
    market_min_multiplier: float = 0.35
    market_max_multiplier: float = 3.5

    # Player Profile PIN settings
    profile_pin_enabled: bool = True
    profile_unlock_ttl_hours: int = 168
    profile_pin_min_length: int = 4
    profile_pin_max_length: int = 12

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
