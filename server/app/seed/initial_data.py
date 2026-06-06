from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import HardwareProduct, Supplier, SupplierOffer
from app.models.enums import HardwareCategory, SupplierType


PRODUCTS = [
    ("Intel Core i5-14400", "Intel", HardwareCategory.CPU, 2024, 78, 65, 55, 88, 5_200_000, 78, 8, 18, {"cores": 10, "socket": "LGA1700"}),
    ("AMD Ryzen 5 5600", "AMD", HardwareCategory.CPU, 2022, 68, 65, 48, 86, 3_100_000, 86, 7, 28, {"cores": 6, "socket": "AM4"}),
    ("NVIDIA GeForce RTX 4060 8GB", "NVIDIA", HardwareCategory.GPU, 2023, 76, 115, 58, 82, 8_200_000, 82, 46, 24, {"vram_gb": 8}),
    ("NVIDIA GeForce RTX 3060 12GB", "NVIDIA", HardwareCategory.GPU, 2021, 70, 170, 66, 78, 7_400_000, 88, 58, 34, {"vram_gb": 12}),
    ("NVIDIA GeForce RTX 3070 8GB", "NVIDIA", HardwareCategory.GPU, 2020, 84, 220, 76, 74, 11_000_000, 84, 72, 38, {"vram_gb": 8}),
    ("AMD Radeon RX 6600 8GB", "AMD", HardwareCategory.GPU, 2021, 64, 132, 56, 80, 5_600_000, 80, 38, 33, {"vram_gb": 8}),
    ("16GB DDR4 RAM", "Kingston", HardwareCategory.RAM, 2020, 42, 8, 24, 91, 950_000, 88, 2, 18, {"capacity_gb": 16}),
    ("32GB DDR5 RAM", "Corsair", HardwareCategory.RAM, 2023, 62, 10, 30, 89, 2_400_000, 82, 2, 20, {"capacity_gb": 32}),
    ("1TB NVMe SSD", "Samsung", HardwareCategory.SSD, 2022, 67, 8, 34, 90, 1_900_000, 86, 1, 24, {"capacity_tb": 1}),
    ("650W 80+ Bronze PSU", "Cooler Master", HardwareCategory.PSU, 2021, 40, 650, 46, 78, 1_350_000, 76, 0, 25, {"watts": 650}),
    ("750W 80+ Gold PSU", "Seasonic", HardwareCategory.PSU, 2022, 55, 750, 42, 91, 2_450_000, 82, 0, 22, {"watts": 750}),
    ("Intel B660 Motherboard", "ASUS", HardwareCategory.MOTHERBOARD, 2022, 48, 35, 38, 84, 2_700_000, 76, 0, 26, {"socket": "LGA1700", "memory_type": "DDR4"}),
    ("AMD B550 Motherboard", "MSI", HardwareCategory.MOTHERBOARD, 2020, 46, 32, 36, 83, 2_250_000, 84, 0, 28, {"socket": "AM4", "memory_type": "DDR4"}),
    ("Mid Tower Case", "DeepCool", HardwareCategory.CASE, 2022, 25, 0, 28, 92, 1_200_000, 70, 0, 15, {"size": "mid_tower"}),
    ("240mm AIO Cooler", "NZXT", HardwareCategory.COOLER, 2022, 58, 8, 36, 77, 2_200_000, 74, 0, 30, {"radiator_mm": 240}),
]

SUPPLIERS = [
    ("VN Official Components", SupplierType.OFFICIAL_DISTRIBUTOR, 92, 50, 2, "Reliable new stock with manufacturer warranty."),
    ("Cho Tot Used Bench", SupplierType.USED_MARKET, 58, 25, 1, "Cheap used market lots, higher uncertainty."),
    ("Saigon Wholesale Rack", SupplierType.WHOLESALE, 78, 38, 4, "Better prices at higher quantities."),
    ("Global Tech Import", SupplierType.WHOLESALE, 85, 40, 7, "Imported premium brands. Invoices in USD. Extra customs processing time."),
    ("Shenzhen Parts Depot", SupplierType.USED_MARKET, 60, 20, 10, "Bulk used lots directly from China. Invoices in CNY. High risk, high reward."),
]


import re

def normalize_slug(value: str) -> str:
    text = str(value).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def seed_database(db: Session) -> None:
    for name, brand, category, year, perf, watts, heat, reliability, msrp, demand, mining, dep, specs in PRODUCTS:
        slug = normalize_slug(name)
        existing = db.scalar(select(HardwareProduct).where(HardwareProduct.name == name))
        if not existing:
            db.add(
                HardwareProduct(
                    name=name,
                    slug=slug,
                    brand=brand,
                    category=category,
                    release_year=year,
                    base_performance_score=perf,
                    base_power_watts=watts,
                    base_heat_score=heat,
                    base_reliability_score=reliability,
                    msrp_vnd=msrp,
                    used_demand_score=demand,
                    mining_popularity_score=mining,
                    depreciation_rate=dep,
                    specs_json=specs,
                )
            )
        else:
            if not existing.slug:
                existing.slug = slug
    db.commit()

    for name, supplier_type, trust, relationship, days, notes in SUPPLIERS:
        existing = db.scalar(select(Supplier).where(Supplier.name == name))
        if not existing:
            country_code = "VN"
            invoice_currency = "VND"
            fx_spread = None
            import_fee = None
            payment_fee = None
            
            if name == "Global Tech Import":
                country_code = "US"
                invoice_currency = "USD"
                fx_spread = 2.0
                import_fee = 5.0
                payment_fee = 250_000
            elif name == "Shenzhen Parts Depot":
                country_code = "CN"
                invoice_currency = "CNY"
                fx_spread = 1.5
                import_fee = 8.0
                payment_fee = 150_000
                
            db.add(
                Supplier(
                    name=name,
                    type=supplier_type,
                    trust_score=trust,
                    relationship_score=relationship,
                    delivery_days=days,
                    notes=notes,
                    country_code=country_code,
                    invoice_currency=invoice_currency,
                    fx_spread_percent=fx_spread,
                    import_fee_percent=import_fee,
                    payment_fee_flat_vnd=payment_fee,
                )
            )
    db.commit()

    suppliers = {supplier.name: supplier for supplier in db.scalars(select(Supplier))}
    products = {product.name: product for product in db.scalars(select(HardwareProduct))}
    offer_specs = [
        ("VN Official Components", "Intel Core i5-14400", 4_750_000, 1, 12, 36),
        ("VN Official Components", "NVIDIA GeForce RTX 4060 8GB", 7_600_000, 1, 8, 36),
        ("VN Official Components", "750W 80+ Gold PSU", 2_150_000, 2, 10, 36),
        ("Saigon Wholesale Rack", "16GB DDR4 RAM", 720_000, 4, 30, 24),
        ("Saigon Wholesale Rack", "1TB NVMe SSD", 1_520_000, 3, 18, 24),
        ("Cho Tot Used Bench", "NVIDIA GeForce RTX 3060 12GB", 4_900_000, 1, 3, 3),
        ("Cho Tot Used Bench", "AMD Radeon RX 6600 8GB", 3_600_000, 1, 4, 3),
        ("Global Tech Import", "Intel Core i5-14400", 185, 1, 15, 36),
        ("Global Tech Import", "NVIDIA GeForce RTX 4060 8GB", 295, 1, 10, 36),
        ("Shenzhen Parts Depot", "NVIDIA GeForce RTX 3060 12GB", 1350, 2, 20, 3),
        ("Shenzhen Parts Depot", "AMD Radeon RX 6600 8GB", 1000, 2, 25, 3),
    ]

    for supplier_name, product_name, price, min_qty, available, warranty in offer_specs:
        supplier = suppliers[supplier_name]
        product = products[product_name]
        existing = db.scalar(
            select(SupplierOffer).where(
                SupplierOffer.supplier_id == supplier.id,
                SupplierOffer.product_id == product.id,
                SupplierOffer.unit_price_vnd == price,
            )
        )
        if not existing:
            db.add(
                SupplierOffer(
                    supplier_id=supplier.id,
                    product_id=product.id,
                    unit_price_vnd=price,
                    min_order_quantity=min_qty,
                    available_quantity=available,
                    warranty_months=warranty,
                    expires_at=datetime.now(timezone.utc) + timedelta(days=14),
                )
            )
    db.commit()
