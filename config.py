from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
WAREHOUSE_DIR = DATA_DIR / "warehouse"
DATABASE_PATH = WAREHOUSE_DIR / "ecommerce.duckdb"
API_BASE_URL = "https://dummyjson.com"
