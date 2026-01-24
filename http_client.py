"""
HTTP client helpers for consistent requests handling
"""

from __future__ import annotations

import logging
from typing import Any, Optional, Tuple

import requests

logger = logging.getLogger(__name__)


def request_json(
    method: str,
    url: str,
    *,
    headers: Optional[dict[str, str]] = None,
    params: Optional[dict[str, Any]] = None,
    json_body: Optional[dict[str, Any]] = None,
    data: Any = None,
    files: Any = None,
    timeout: Optional[float] = None,
) -> Tuple[Optional[requests.Response], Optional[Any]]:
    """Send an HTTP request and attempt to parse JSON response."""
    try:
        response = requests.request(
            method,
            url,
            headers=headers,
            params=params,
            json=json_body,
            data=data,
            files=files,
            timeout=timeout,
        )
        try:
            payload = response.json()
        except ValueError:
            payload = None
        return response, payload
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
        logger.warning(f"HTTP {method} request failed (Connection/Timeout): {url} - {exc}")
        return None, None
    except Exception as exc:
        logger.error(f"HTTP {method} request failed: {url} - {exc}")
        return None, None


def request_text(
    method: str,
    url: str,
    *,
    headers: Optional[dict[str, str]] = None,
    params: Optional[dict[str, Any]] = None,
    json_body: Optional[dict[str, Any]] = None,
    data: Any = None,
    files: Any = None,
    timeout: Optional[float] = None,
) -> Tuple[Optional[requests.Response], Optional[str]]:
    """Send an HTTP request and return text response."""
    try:
        response = requests.request(
            method,
            url,
            headers=headers,
            params=params,
            json=json_body,
            data=data,
            files=files,
            timeout=timeout,
        )
        return response, response.text
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
        logger.warning(f"HTTP {method} request failed (Connection/Timeout): {url} - {exc}")
        return None, None
    except Exception as exc:
        logger.error(f"HTTP {method} request failed: {url} - {exc}")
        return None, None
