from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

ALLOWED_CATEGORIES = {
    "CPU",
    "GPU",
    "MOTHERBOARD",
    "RAM",
    "STORAGE",
    "PSU",
    "CASE",
    "COOLER",
    "WATER_COOLING",
    "MONITOR",
    "OTHER",
}
ALLOWED_ORIGIN_CODES = {"US", "CN", "TW", "HK", "KR", "JP", "DE", "AT", "NL", "SI", "VN", "SG", "SE", "ZA"}
ALLOWED_BRAND_TYPES = {"CHIP_VENDOR", "BOARD_PARTNER", "MEMORY_STORAGE", "PSU_CASE_COOLING", "CASE_COOLING", "RETAILER", "OTHER"}
ALLOWED_MARKET_TIERS = {"PREMIUM", "MAINSTREAM", "VALUE", "BUDGET", "GRAY_MARKET", "INDUSTRIAL", "UNKNOWN"}

BRANDS_CANDIDATES = ("brands_normalized.csv", "silicon_hustle_brands_normalized.csv")
CATEGORIES_CANDIDATES = ("brand_categories.csv", "silicon_hustle_brand_categories.csv")
SHEET_ROWS_CANDIDATES = ("brand_sheet_normalized_rows.csv", "silicon_hustle_brand_sheet_normalized_rows.csv")

CATEGORY_ALIASES = {
    "SSD": "STORAGE",
    "HDD": "STORAGE",
    "MAINBOARD": "MOTHERBOARD",
    "MOTHER BOARD": "MOTHERBOARD",
    "WATER COOLING": "WATER_COOLING",
    "WATERCOOLING": "WATER_COOLING",
    "AIO": "WATER_COOLING",
}

BRAND_NAME_OVERRIDES = {
    "amd": "AMD",
    "adata": "ADATA",
    "hp": "HP",
    "ibm": "IBM",
    "lg": "LG",
    "msi": "MSI",
    "nvidia": "NVIDIA",
}


@dataclass
class ParsedBrand:
    name: str
    slug: str
    origin_name_vi: str | None
    origin_code: str | None
    logo_url: str | None
    website_url: str | None
    brand_type: str
    market_tier: str
    base_trust_score: int
    used_market_risk_modifier: int
    categories: list[str] = field(default_factory=list)
    notes: str | None = None


@dataclass
class ParsedCategory:
    brand_slug: str
    category: str
    brand_name: str | None = None


@dataclass
class ParseReport:
    brands: list[ParsedBrand]
    categories: list[ParsedCategory]
    warnings: list[str]
    errors: list[str]
    brands_path: Path | None
    categories_path: Path | None


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def server_root() -> Path:
    return Path(__file__).resolve().parents[1]


def imports_dir() -> Path:
    return server_root() / "data" / "imports"


def resolve_csv(candidates: Iterable[str]) -> Path | None:
    base = imports_dir()
    for name in candidates:
        path = base / name
        if path.exists():
            return path
    return None


def read_csv_rows(path: Path | None) -> list[dict[str, str]]:
    if not path:
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def parse_brand_csv() -> ParseReport:
    warnings: list[str] = []
    errors: list[str] = []
    brands_path = resolve_csv(BRANDS_CANDIDATES)
    categories_path = resolve_csv(CATEGORIES_CANDIDATES)
    if not brands_path:
        errors.append("Missing brands CSV. Expected brands_normalized.csv or silicon_hustle_brands_normalized.csv.")
    if not categories_path:
        warnings.append("Missing brand categories CSV. Falling back to categories field in brands CSV if present.")

    brands: list[ParsedBrand] = []
    for row_number, row in enumerate(read_csv_rows(brands_path), start=2):
        brand = parse_brand_row(row, row_number, warnings, errors)
        if brand:
            brands.append(brand)

    categories: list[ParsedCategory] = []
    if categories_path:
        for row_number, row in enumerate(read_csv_rows(categories_path), start=2):
            category = parse_category_row(row, row_number, warnings, errors)
            if category:
                categories.append(category)
    else:
        for brand in brands:
            for category in brand.categories:
                categories.append(ParsedCategory(brand_slug=brand.slug, brand_name=brand.name, category=category))

    return ParseReport(brands=brands, categories=categories, warnings=warnings, errors=errors, brands_path=brands_path, categories_path=categories_path)


def parse_brand_row(row: dict[str, str], row_number: int, warnings: list[str], errors: list[str]) -> ParsedBrand | None:
    raw_slug = clean_text(row.get("slug"))
    name = normalize_brand_name(clean_text(row.get("name")), raw_slug)
    slug = normalize_slug(raw_slug or name)
    if not name:
        errors.append(f"brands row {row_number}: missing brand name")
    if not slug:
        errors.append(f"brands row {row_number}: missing brand slug")
    if not name or not slug:
        return None

    origin_code = clean_text(row.get("origin_code"))
    origin_code = origin_code.upper() if origin_code else None
    if origin_code and origin_code not in ALLOWED_ORIGIN_CODES:
        errors.append(f"brands row {row_number} ({slug}): unknown origin_code {origin_code}")

    brand_type = normalize_choice(row.get("brand_type"), ALLOWED_BRAND_TYPES, "OTHER", f"brands row {row_number} ({slug}) brand_type", warnings)
    market_tier = normalize_choice(row.get("market_tier"), ALLOWED_MARKET_TIERS, "UNKNOWN", f"brands row {row_number} ({slug}) market_tier", warnings)
    trust = parse_int(row.get("base_trust_score"), 50, f"brands row {row_number} ({slug}) base_trust_score", errors)
    risk = parse_int(row.get("used_market_risk_modifier"), 0, f"brands row {row_number} ({slug}) used_market_risk_modifier", errors)
    logo_url = clean_text(row.get("logo_url"))
    website_url = clean_text(row.get("website_url"))
    if not website_url:
        warnings.append(f"brands row {row_number} ({slug}): website_url missing")
    warn_missing_logo(logo_url, slug, warnings)

    return ParsedBrand(
        name=name,
        slug=slug,
        origin_name_vi=clean_text(row.get("origin_name_vi")),
        origin_code=origin_code,
        logo_url=logo_url,
        website_url=website_url,
        brand_type=brand_type,
        market_tier=market_tier,
        base_trust_score=trust,
        used_market_risk_modifier=risk,
        categories=parse_categories_field(row.get("categories"), f"brands row {row_number} ({slug}) categories", warnings, errors),
        notes=clean_text(row.get("notes")),
    )


def parse_category_row(row: dict[str, str], row_number: int, warnings: list[str], errors: list[str]) -> ParsedCategory | None:
    slug = normalize_slug(row.get("brand_slug"))
    category = normalize_category(row.get("category"))
    if not slug:
        errors.append(f"brand_categories row {row_number}: missing brand_slug")
    if not category:
        errors.append(f"brand_categories row {row_number} ({slug or 'unknown'}): missing category")
    if category and category not in ALLOWED_CATEGORIES:
        errors.append(f"brand_categories row {row_number} ({slug}): unknown category {category}")
    if not slug or not category or category not in ALLOWED_CATEGORIES:
        return None
    return ParsedCategory(brand_slug=slug, brand_name=clean_text(row.get("brand_name")), category=category)


def validate_report(report: ParseReport) -> tuple[list[str], list[str]]:
    warnings = list(report.warnings)
    errors = list(report.errors)
    slugs = [brand.slug for brand in report.brands]
    duplicates = sorted({slug for slug in slugs if slugs.count(slug) > 1})
    for slug in duplicates:
        errors.append(f"Duplicate brand slug in brands CSV: {slug}")
    known_slugs = set(slugs)
    for category in report.categories:
        if category.brand_slug not in known_slugs:
            errors.append(f"brand_categories references unknown brand_slug: {category.brand_slug}")
    for brand in report.brands:
        if not 0 <= brand.base_trust_score <= 100:
            errors.append(f"{brand.slug}: base_trust_score must be 0-100")
        if not -100 <= brand.used_market_risk_modifier <= 100:
            errors.append(f"{brand.slug}: used_market_risk_modifier must be -100 to 100")
    return warnings, errors


def parse_categories_field(value: str | None, label: str, warnings: list[str], errors: list[str]) -> list[str]:
    text = clean_text(value)
    if not text:
        return []
    categories: list[str] = []
    for part in re.split(r"[,;|]", text):
        category = normalize_category(part)
        if not category:
            continue
        if category not in ALLOWED_CATEGORIES:
            errors.append(f"{label}: unknown category {category}")
            continue
        categories.append(category)
    return unique_preserve_order(categories)


def normalize_category(value: str | None) -> str | None:
    text = clean_text(value)
    if not text:
        return None
    text = re.sub(r"[\-/]+", " ", text.upper()).strip()
    text = re.sub(r"\s+", " ", text)
    text = CATEGORY_ALIASES.get(text, text.replace(" ", "_"))
    return text


def normalize_choice(value: str | None, allowed: set[str], fallback: str, label: str, warnings: list[str]) -> str:
    text = clean_text(value)
    normalized = text.upper().replace(" ", "_") if text else fallback
    if normalized not in allowed:
        warnings.append(f"{label}: unknown value {text!r}; falling back to {fallback}")
        return fallback
    return normalized


def parse_int(value: str | None, default: int, label: str, errors: list[str]) -> int:
    text = clean_text(value)
    if not text:
        return default
    try:
        return int(text)
    except ValueError:
        errors.append(f"{label}: invalid integer {text!r}")
        return default


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value).strip())
    return text or None


def normalize_slug(value: str | None) -> str:
    text = clean_text(value)
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def normalize_brand_name(value: str | None, slug: str | None) -> str:
    name = clean_text(value) or ""
    slug_value = normalize_slug(slug or name)
    if slug_value in BRAND_NAME_OVERRIDES:
        return BRAND_NAME_OVERRIDES[slug_value]
    if name.isupper() and len(name) > 4:
        return name.title()
    return name


def warn_missing_logo(logo_url: str | None, slug: str, warnings: list[str]) -> None:
    if not logo_url:
        warnings.append(f"{slug}: logo_url missing")
        return
    if logo_url.startswith("http://") or logo_url.startswith("https://"):
        warnings.append(f"{slug}: logo_url is external; prefer local /assets/brands/{slug}.svg")
        return
    if logo_url.startswith("/"):
        path = project_root() / "public" / logo_url.lstrip("/")
    else:
        path = project_root() / "public" / "assets" / "brands" / logo_url
    if not path.exists():
        fallback = project_root() / "public" / "assets" / "brands" / f"{slug}.svg"
        if not fallback.exists():
            warnings.append(f"{slug}: logo file missing at {logo_url}")


def unique_preserve_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
