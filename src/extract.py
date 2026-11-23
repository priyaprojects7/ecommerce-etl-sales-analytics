"""Extract paginated data from the DummyJSON demo API."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests

from config import API_BASE_URL, RAW_DIR


class SourceAPIError(RuntimeError):
    """Raised when the source API returns invalid or incomplete data."""


def _get_json(session: requests.Session, url: str, params: dict, timeout: int) -> dict:
    try:
        response = session.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise SourceAPIError(f"Could not retrieve {url}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SourceAPIError(f"Unexpected response from {url}")
    return payload


def fetch_resource(resource: str, *, base_url: str = API_BASE_URL,
                   session: requests.Session | None = None,
                   timeout: int = 20) -> dict[str, Any]:
    """Fetch all pages for one DummyJSON resource."""
    client = session or requests.Session()
    url = f"{base_url.rstrip('/')}/{resource.lstrip('/')}"
    first = _get_json(client, url, {"limit": 100, "skip": 0}, timeout)
    items = first.get(resource)
    if not isinstance(items, list):
        raise SourceAPIError(f"Response for {resource!r} has no list")
    all_items = list(items)
    total = int(first.get("total", len(all_items)))
    while len(all_items) < total:
        page = _get_json(client, url, {"limit": 100, "skip": len(all_items)}, timeout)
        batch = page.get(resource)
        if not isinstance(batch, list) or not batch:
            raise SourceAPIError(f"Pagination stopped early for {resource!r}")
        all_items.extend(batch)
    return {resource: all_items, "total": len(all_items)}


def extract_all(output_dir: Path = RAW_DIR, *, base_url: str = API_BASE_URL) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    results = {}
    for resource in ("products", "users", "carts"):
        payload = fetch_resource(resource, base_url=base_url)
        (output_dir / f"{resource}.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )
        results[resource] = payload
    return results
