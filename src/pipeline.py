"""Run the complete sample-data ETL pipeline."""
from config import DATABASE_PATH, RAW_DIR
from src.extract import extract_all
from src.transform import transform_payloads
from src.warehouse import load_warehouse


def run_pipeline() -> None:
    print("Extracting products, users, and carts...")
    payloads = extract_all(RAW_DIR)
    print("Transforming and validating...")
    tables = transform_payloads(payloads)
    print("Loading DuckDB...")
    load_warehouse(tables, DATABASE_PATH)
    print("Pipeline complete: " + ", ".join(
        f"{name}={len(frame)}" for name, frame in tables.items()
    ))
    print(f"Warehouse: {DATABASE_PATH}")


if __name__ == "__main__":
    run_pipeline()
