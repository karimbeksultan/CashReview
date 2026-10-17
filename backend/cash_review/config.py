"""Runtime settings. Secrets are read only by the server process."""

from dataclasses import dataclass, field
import os
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent


@dataclass(frozen=True)
class Settings:
    data_dir: Path = field(default_factory=lambda: Path(os.getenv("CASH_REVIEW_DATA_DIR", str(PROJECT_DIR / "runtime"))).resolve())
    api_key: str = field(default_factory=lambda: os.getenv("CASH_REVIEW_API_KEY", ""))
    origins: tuple[str, ...] = field(default_factory=lambda: tuple(v.strip().rstrip("/") for v in os.getenv("CASH_REVIEW_ALLOWED_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173").split(",") if v.strip()))
    max_upload_bytes: int = field(default_factory=lambda: int(os.getenv("CASH_REVIEW_MAX_UPLOAD_BYTES", str(64 * 1024 * 1024))))
    deadline_seconds: float = field(default_factory=lambda: min(300.0, float(os.getenv("CASH_REVIEW_DEADLINE_SECONDS", "300"))))
    retention_seconds: float = field(default_factory=lambda: float(os.getenv("CASH_REVIEW_RETENTION_SECONDS", "86400")))
    token_ttl_seconds: float = field(default_factory=lambda: min(86400.0, float(os.getenv("CASH_REVIEW_TOKEN_TTL_SECONDS", "7200"))))
    queue_capacity: int = field(default_factory=lambda: int(os.getenv("CASH_REVIEW_QUEUE_CAPACITY", "8")))
    worker_concurrency: int = field(default_factory=lambda: int(os.getenv("CASH_REVIEW_WORKERS", "1")))
    lease_seconds: float = 30.0
    upload_rate_limit: int = 6
    poll_rate_limit: int = 240
    start_worker: bool = True
    frontend_dir: Path = PROJECT_DIR / "frontend" / "dist"
    rules_path: Path = BACKEND_DIR / "rules" / "registry.json"

    def __post_init__(self) -> None:
        if self.max_upload_bytes <= 0 or not 0 < self.deadline_seconds <= 300:
            raise ValueError("Upload limit and deadline must be positive; deadline cannot exceed 300 seconds.")
        if not 1 <= self.worker_concurrency <= 8 or not 1 <= self.queue_capacity <= 100:
            raise ValueError("Invalid worker concurrency or queue capacity.")
        if self.retention_seconds <= 0 or self.token_ttl_seconds <= 0:
            raise ValueError("Retention and token lifetime must be positive.")
