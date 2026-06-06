from __future__ import annotations

from brand_data import parse_brand_csv, validate_report


def main() -> int:
    report = parse_brand_csv()
    warnings, errors = validate_report(report)
    print("Brand validation report")
    print(f"- brands CSV: {report.brands_path or 'missing'}")
    print(f"- categories CSV: {report.categories_path or 'missing'}")
    print(f"- brands parsed: {len(report.brands)}")
    print(f"- category mappings parsed: {len(report.categories)}")
    print(f"- warnings: {len(warnings)}")
    print(f"- hard errors: {len(errors)}")
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
