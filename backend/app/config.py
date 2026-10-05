import os
from pathlib import Path
from pydantic_settings import BaseSettings

# Prevent joblib physical-cores warning on Windows
os.environ.setdefault("LOKY_MAX_CPU_COUNT", "4")

BASE_DIR = Path(__file__).resolve().parent.parent          # …/backend/
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models_saved"

# Auto-create essential directories
DATA_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    """All environment-backed settings with defaults."""

    # Security
    admin_token: str = "change_me"

    # Database — always resolves to backend/ldce_enquiries.db
    database_url: str = f"sqlite:///{(BASE_DIR / 'ldce_enquiries.db').as_posix()}"

    # CORS
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Classifier
    confidence_threshold: float = 0.35       # ~0.35 default for Naive Bayes
    classifier_algorithm: str = "naive_bayes"  # naive_bayes | decision_tree | knn

    # KDD / Apriori — lowered defaults so planted co-occurrences produce rules
    min_support: float = 0.02
    min_confidence: float = 0.25
    min_lift: float = 1.1

    model_config = {"env_file": str(BASE_DIR / ".env"), "env_file_encoding": "utf-8"}


settings = Settings()
