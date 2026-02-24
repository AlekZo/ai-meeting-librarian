"""
HTTP client helpers for consistent requests handling
Supports proxy routing through Clash Verge
"""

from __future__ import annotations

import logging
from typing import Any, Optional, Tuple, Dict

import requests

logger = logging.getLogger(__name__)

# Global proxy configuration
_proxy_config: Optional[Dict[str, str]] = None


def set_proxy(proxies: Optional[Dict[str, str]]) -> None:
    """Set global proxy configuration"""
    global _proxy_config
    _proxy_config = proxies
    if proxies:
        logger.info(f"HTTP proxy configured: {proxies.get('http', 'N/A')}")
    else:
        logger.info("HTTP proxy disabled")


def get_proxy() -> Optional[Dict[str, str]]:
    """Get current proxy configuration"""
    return _proxy_config


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
    proxies: Optional[Dict[str, str]] = None,
) -> Tuple[Optional[requests.Response], Optional[Any]]:
    """Send an HTTP request and attempt to parse JSON response."""
    try:
        # Use provided proxies or fall back to global config
        request_proxies = proxies if proxies is not None else _proxy_config
        
        response = requests.request(
            method,
            url,
            headers=headers,
            params=params,
            json=json_body,
            data=data,
            files=files,
            timeout=timeout,
            proxies=request_proxies,
        )
        try:
            payload = response.json()
        except ValueError:
            payload = None
        return response, payload
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
        # Log as debug for Telegram getUpdates to avoid cluttering logs during long-polling
        if "api.telegram.org" in url and "getUpdates" in url:
            logger.debug(f"Telegram long-polling timeout/connection issue: {url} - {exc}")
        else:
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
    proxies: Optional[Dict[str, str]] = None,
) -> Tuple[Optional[requests.Response], Optional[str]]:
    """Send an HTTP request and return text response."""
    try:
        # Use provided proxies or fall back to global config
        request_proxies = proxies if proxies is not None else _proxy_config
        
        response = requests.request(
            method,
            url,
            headers=headers,
            params=params,
            json=json_body,
            data=data,
            files=files,
            timeout=timeout,
            proxies=request_proxies,
        )
        return response, response.text
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
        logger.warning(f"HTTP {method} request failed (Connection/Timeout): {url} - {exc}")
        return None, None
    except Exception as exc:
        logger.error(f"HTTP {method} request failed: {url} - {exc}")
        return None, None
