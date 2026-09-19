"""
LLM Client — Phase 10

Thin wrapper that returns a configured OpenAI-compatible client
pointed at AvalAI's gateway. Kept deliberately minimal: this module's
only job is authentication/configuration. Prompt construction and
output validation belong in higher-level modules (Modularity
principle, Master Instruction section 23).
"""

from __future__ import annotations

import os
from typing import Tuple

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


def get_llm_client() -> Tuple[OpenAI, str]:
    """Returns (client, model_name) configured from environment
    variables. Fails loudly and clearly if config is missing, rather
    than surfacing a confusing API error later."""
    api_key = os.getenv("AVALAI_API_KEY")
    base_url = os.getenv("AVALAI_BASE_URL")
    model_name = os.getenv("AVALAI_MODEL_NAME")

    missing = [
        name for name, value in [
            ("AVALAI_API_KEY", api_key),
            ("AVALAI_BASE_URL", base_url),
            ("AVALAI_MODEL_NAME", model_name),
        ]
        if not value
    ]
    if missing:
        raise RuntimeError(
            f"Missing environment variable(s): {', '.join(missing)}. "
            "Check your .env file exists and is filled in."
        )

    client = OpenAI(api_key=api_key, base_url=base_url)
    return client, model_name