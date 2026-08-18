from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    base_url: str = os.getenv(
        "HF_OPENAI_BASE_URL",
        "https://g9hnto0u7lvbu837.us-east-2.aws.endpoints.huggingface.cloud/v1",
    )
    api_key: str = os.getenv("HF_OPENAI_API_KEY", "none")
    model: str = os.getenv("HF_MODEL", "Qwen/Qwen3.8-27B")
    dry_run: bool = os.getenv("KALI_DRY_RUN", "true").lower() == "true"
    workdir: str = os.getenv("KALI_WORKDIR", ".")
    timeout_seconds: int = int(os.getenv("KALI_TIMEOUT_SECONDS", "60"))


settings = Settings()
