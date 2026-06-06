import hashlib
import secrets
import re
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import not_found, bad_request, forbidden
from app.models.entities import PlayerProfile, ProfileUnlockSession, SaveGame


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _is_future(dt: Optional[datetime]) -> bool:
    if not dt:
        return False
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        now = now.replace(tzinfo=None)
    return dt > now


def _is_past(dt: Optional[datetime]) -> bool:
    if not dt:
        return False
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        now = now.replace(tzinfo=None)
    return dt < now


def _remaining_seconds(dt: datetime) -> int:
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        now = now.replace(tzinfo=None)
    return int((dt - now).total_seconds())


def _slugify(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    return s.strip("-")


def hash_pin(pin: str, salt: str) -> str:
    hashed = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt.encode("utf-8"), 100000)
    return hashed.hex()


def list_profiles(db: Session) -> List[PlayerProfile]:
    return list(db.scalars(select(PlayerProfile).order_by(PlayerProfile.display_name)))


def create_profile(db: Session, display_name: str, pin: Optional[str] = None) -> PlayerProfile:
    settings = get_settings()
    slug_base = _slugify(display_name)
    if not slug_base:
        slug_base = "player"
        
    slug = slug_base
    counter = 1
    while db.scalar(select(PlayerProfile).where(PlayerProfile.slug == slug)):
        slug = f"{slug_base}-{counter}"
        counter += 1
        
    profile = PlayerProfile(
        display_name=display_name,
        slug=slug,
        pin_enabled=False
    )
    
    if pin:
        if len(pin) < settings.profile_pin_min_length or len(pin) > settings.profile_pin_max_length:
            raise bad_request(f"PIN must be between {settings.profile_pin_min_length} and {settings.profile_pin_max_length} characters")
        salt = secrets.token_hex(16)
        profile.pin_salt = salt
        profile.pin_hash = hash_pin(pin, salt)
        profile.pin_enabled = True
        
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def get_profile(db: Session, profile_id: int) -> PlayerProfile:
    profile = db.get(PlayerProfile, profile_id)
    if not profile:
        raise not_found("Player profile not found")
    return profile


def set_profile_pin(db: Session, profile_id: int, pin: str, current_pin: Optional[str] = None) -> PlayerProfile:
    profile = get_profile(db, profile_id)
    settings = get_settings()
    
    # If PIN is currently enabled, verify current pin first
    if profile.pin_enabled and current_pin is not None:
        # Check lockout
        if _is_future(profile.locked_until):
            remaining = _remaining_seconds(profile.locked_until)
            raise forbidden(f"Profile temporarily locked. Try again in {remaining} seconds.")
            
        expected = hash_pin(current_pin, profile.pin_salt)
        if profile.pin_hash != expected:
            # Increment failed attempts on pin-change failure too
            profile.failed_unlock_attempts += 1
            profile.last_failed_unlock_at = now_utc()
            if profile.failed_unlock_attempts >= 5:
                profile.locked_until = now_utc() + timedelta(minutes=5)
            db.commit()
            raise bad_request("Invalid current PIN")
            
    if len(pin) < settings.profile_pin_min_length or len(pin) > settings.profile_pin_max_length:
        raise bad_request(f"PIN must be between {settings.profile_pin_min_length} and {settings.profile_pin_max_length} characters")
        
    salt = secrets.token_hex(16)
    profile.pin_salt = salt
    profile.pin_hash = hash_pin(pin, salt)
    profile.pin_enabled = True
    profile.failed_unlock_attempts = 0
    profile.locked_until = None
    
    db.commit()
    db.refresh(profile)
    return profile


def disable_profile_pin(db: Session, profile_id: int, current_pin: Optional[str] = None) -> PlayerProfile:
    profile = get_profile(db, profile_id)
    
    if profile.pin_enabled:
        if current_pin is None:
            raise bad_request("Current PIN is required to disable PIN lock")
            
        if _is_future(profile.locked_until):
            remaining = _remaining_seconds(profile.locked_until)
            raise forbidden(f"Profile temporarily locked. Try again in {remaining} seconds.")
            
        expected = hash_pin(current_pin, profile.pin_salt)
        if profile.pin_hash != expected:
            profile.failed_unlock_attempts += 1
            profile.last_failed_unlock_at = now_utc()
            if profile.failed_unlock_attempts >= 5:
                profile.locked_until = now_utc() + timedelta(minutes=5)
            db.commit()
            raise bad_request("Invalid current PIN")
            
    profile.pin_enabled = False
    profile.pin_hash = None
    profile.pin_salt = None
    profile.failed_unlock_attempts = 0
    profile.locked_until = None
    
    # Revoke all unlock sessions for this profile
    db.execute(
        select(ProfileUnlockSession)
        .where(ProfileUnlockSession.profile_id == profile_id)
    )
    sessions = db.scalars(select(ProfileUnlockSession).where(ProfileUnlockSession.profile_id == profile_id))
    for s in sessions:
        s.is_revoked = True
        
    db.commit()
    db.refresh(profile)
    return profile


def verify_profile_pin(db: Session, profile_id: int, pin: str) -> bool:
    profile = get_profile(db, profile_id)
    
    if not profile.pin_enabled:
        return True
        
    if _is_future(profile.locked_until):
        remaining = _remaining_seconds(profile.locked_until)
        raise forbidden(f"Profile temporarily locked. Try again in {remaining} seconds.")
        
    expected = hash_pin(pin, profile.pin_salt)
    if profile.pin_hash == expected:
        profile.failed_unlock_attempts = 0
        profile.locked_until = None
        profile.last_unlocked_at = now_utc()
        db.commit()
        return True
    else:
        profile.failed_unlock_attempts += 1
        profile.last_failed_unlock_at = now_utc()
        if profile.failed_unlock_attempts >= 5:
            profile.locked_until = now_utc() + timedelta(minutes=5)
        db.commit()
        return False


def create_unlock_session(db: Session, profile_id: int) -> tuple[str, datetime]:
    settings = get_settings()
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    expires_at = now_utc() + timedelta(hours=settings.profile_unlock_ttl_hours)
    
    session = ProfileUnlockSession(
        profile_id=profile_id,
        token_hash=token_hash,
        expires_at=expires_at
    )
    db.add(session)
    db.commit()
    return token, expires_at


def validate_unlock_session(db: Session, profile_id: int, token: str) -> bool:
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    session = db.scalar(
        select(ProfileUnlockSession).where(
            ProfileUnlockSession.profile_id == profile_id,
            ProfileUnlockSession.token_hash == token_hash
        )
    )
    if not session or session.is_revoked or _is_past(session.expires_at):
        return False
        
    session.last_used_at = now_utc()
    db.commit()
    return True


def revoke_unlock_session(db: Session, profile_id: int, token: str) -> None:
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    session = db.scalar(
        select(ProfileUnlockSession).where(
            ProfileUnlockSession.profile_id == profile_id,
            ProfileUnlockSession.token_hash == token_hash
        )
    )
    if session:
        session.is_revoked = True
        db.commit()


def attach_save_to_profile(db: Session, save_game_id: int, profile_id: int) -> SaveGame:
    save_game = db.get(SaveGame, save_game_id)
    if not save_game:
        raise not_found("Save game not found")
        
    profile = get_profile(db, profile_id)
    save_game.player_profile_id = profile.id
    save_game.pin_required = profile.pin_enabled
    db.commit()
    db.refresh(save_game)
    return save_game


def require_profile_access(db: Session, save_game_id: int, token: Optional[str] = None) -> None:
    save_game = db.get(SaveGame, save_game_id)
    if not save_game:
        raise not_found("Save game not found")
        
    if save_game.player_profile_id is None:
        return
        
    profile = db.get(PlayerProfile, save_game.player_profile_id)
    if not profile or not profile.pin_enabled:
        return
        
    if not token:
        raise forbidden("PIN lock is enabled on this profile. Please provide X-Profile-Unlock-Token header.")
        
    if not validate_unlock_session(db, profile.id, token):
        raise forbidden("Invalid or expired profile unlock token.")
        
    # Update last accessed
    save_game.last_accessed_at = now_utc()
    db.commit()
