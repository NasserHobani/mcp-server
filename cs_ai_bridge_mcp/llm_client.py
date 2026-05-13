"""HTTP client for the FastAPI LLM proxy."""

from __future__ import annotations

from typing import Any

import httpx

from . import config


def chat_completion(payload: dict[str, Any]) -> dict[str, Any]:
    base_url = config.get_llm_api_base_url()
    timeout_seconds = config.get_llm_api_timeout_seconds()

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    with httpx.Client(timeout=timeout_seconds) as client:
        response = client.post(
            f"{base_url}/v1/chat/completions",
            json=payload,
            headers=headers,
        )

    try:
        data = response.json()
    except ValueError as exc:
        raise ValueError(
            f"LLM API returned non-JSON ({response.status_code}): "
            f"{response.text[:500]}"
        ) from exc

    if response.is_error:
        detail: Any = data.get("detail") if isinstance(data, dict) else data
        raise ValueError(f"LLM API request failed ({response.status_code}): {detail}")

    if not isinstance(data, dict):
        raise ValueError("LLM API response must be a JSON object.")
    return data
