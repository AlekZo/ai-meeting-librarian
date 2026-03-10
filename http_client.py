"""
HTTP client helpers for consistent requests handling
Supports proxy routing through Clash Verge
Includes resilience features: retries, exponential backoff, circuit breakers
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional, Tuple, Dict, Callable

import requests

from resilience_utils import (
    get_circuit_breaker,
    calculate_backoff_delay,
    is_retryable_error,
    get_health_checker,
    ResilienceConfig
)

logger = logging.getLogger(__name__)

# Global proxy configuration
_proxy_config: Optional[Dict[str, str]] = None

# Resilience settings
_max_retries = 3
_connection_timeout = 10
_read_timeout = 30


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


def set_resilience_settings(max_retries: int = 3, connection_timeout: int = 10, read_timeout: int = 30) -> None:
    """Configure HTTP client resilience settings"""
    global _max_retries, _connection_timeout, _read_timeout
    _max_retries = max_retries
    _connection_timeout = connection_timeout
    _read_timeout = read_timeout


def _get_timeout() -> Tuple[float, float]:
    """Get connection and read timeouts"""
    return (_connection_timeout, _read_timeout)


def _should_retry_for_url(url: str) -> bool:
    """Determine if URL should use retry logic"""
    # Don't retry long-polling endpoints
    if "getUpdates" in url and "api.telegram.org" in url:
        return False
    return True


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
    max_retries: Optional[int] = None,
) -> Tuple[Optional[requests.Response], Optional[Any]]:
    """Send an HTTP request and attempt to parse JSON response with retries."""
    
    # Use provided max_retries or global setting
    retries = max_retries if max_retries is not None else _max_retries
    
    # Check if this URL should use retries
    should_retry = _should_retry_for_url(url)
    if not should_retry:
        retries = 1  # Single attempt for long-polling
    
    # Get circuit breaker for this service
    service_name = _extract_service_name(url)
    circuit_breaker = get_circuit_breaker(service_name)
    health_checker = get_health_checker()
    
    # Check if circuit breaker is open
    if not circuit_breaker.can_execute():
        logger.warning(f"Circuit breaker open for {service_name}. Skipping request to {url}")
        return None, None
    
    last_exception = None
    
    for attempt in range(retries):
        try:
            # Use provided proxies or fall back to global config
            request_proxies = proxies if proxies is not None else _proxy_config
            
            # Use provided timeout or calculate default
            request_timeout = timeout if timeout is not None else _get_timeout()
            
            response = requests.request(
                method,
                url,
                headers=headers,
                params=params,
                json=json_body,
                data=data,
                files=files,
                timeout=request_timeout,
                proxies=request_proxies,
            )
            
            try:
                payload = response.json()
            except ValueError:
                payload = None
            
            # Record success
            circuit_breaker.record_success()
            health_checker.record_check(service_name, True)
            
            return response, payload
            
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
            last_exception = exc
            
            # Log appropriately based on URL
            if "api.telegram.org" in url and "getUpdates" in url:
                logger.debug(f"Telegram long-polling timeout/connection (attempt {attempt + 1}/{retries}): {exc}")
            else:
                logger.warning(f"HTTP {method} request failed (attempt {attempt + 1}/{retries}): {url} - {exc}")
            
            # Record as transient failure (don't open circuit breaker yet)
            if attempt == retries - 1:
                circuit_breaker.record_failure()
                health_checker.record_check(service_name, False, str(exc))
            
            # Retry with backoff if applicable
            if attempt < retries - 1 and should_retry:
                delay = calculate_backoff_delay(attempt)
                logger.debug(f"Retrying in {delay:.1f}s...")
                time.sleep(delay)
            elif attempt < retries - 1:
                # No backoff for non-retryable URLs, just fail fast
                break
        
        except Exception as exc:
            last_exception = exc
            logger.error(f"HTTP {method} request failed: {url} - {exc}")
            circuit_breaker.record_failure()
            health_checker.record_check(service_name, False, str(exc))
            # Don't retry on non-network errors
            break
    
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
    max_retries: Optional[int] = None,
) -> Tuple[Optional[requests.Response], Optional[str]]:
    """Send an HTTP request and return text response with retries."""
    
    # Use provided max_retries or global setting
    retries = max_retries if max_retries is not None else _max_retries
    
    # Check if this URL should use retries
    should_retry = _should_retry_for_url(url)
    if not should_retry:
        retries = 1
    
    # Get circuit breaker for this service
    service_name = _extract_service_name(url)
    circuit_breaker = get_circuit_breaker(service_name)
    health_checker = get_health_checker()
    
    # Check if circuit breaker is open
    if not circuit_breaker.can_execute():
        logger.warning(f"Circuit breaker open for {service_name}. Skipping request to {url}")
        return None, None
    
    last_exception = None
    
    for attempt in range(retries):
        try:
            # Use provided proxies or fall back to global config
            request_proxies = proxies if proxies is not None else _proxy_config
            
            # Use provided timeout or calculate default
            request_timeout = timeout if timeout is not None else _get_timeout()
            
            response = requests.request(
                method,
                url,
                headers=headers,
                params=params,
                json=json_body,
                data=data,
                files=files,
                timeout=request_timeout,
                proxies=request_proxies,
            )
            
            # Record success
            circuit_breaker.record_success()
            health_checker.record_check(service_name, True)
            
            return response, response.text
            
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
            last_exception = exc
            logger.warning(f"HTTP {method} request failed (attempt {attempt + 1}/{retries}): {url} - {exc}")
            
            # Record failure
            if attempt == retries - 1:
                circuit_breaker.record_failure()
                health_checker.record_check(service_name, False, str(exc))
            
            # Retry with backoff if applicable
            if attempt < retries - 1 and should_retry:
                delay = calculate_backoff_delay(attempt)
                logger.debug(f"Retrying in {delay:.1f}s...")
                time.sleep(delay)
            elif attempt < retries - 1:
                break
        
        except Exception as exc:
            last_exception = exc
            logger.error(f"HTTP {method} request failed: {url} - {exc}")
            circuit_breaker.record_failure()
            health_checker.record_check(service_name, False, str(exc))
            # Don't retry on non-network errors
            break
    
    return None, None


def _extract_service_name(url: str) -> str:
    """Extract service name from URL for circuit breaker tracking"""
    if "api.telegram.org" in url:
        return "telegram"
    elif "googleapis.com" in url:
        return "google_api"
    elif "api.openrouter.ai" in url:
        return "openrouter"
    else:
        # Extract domain
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc or "unknown"
        except:
            return "unknown"
