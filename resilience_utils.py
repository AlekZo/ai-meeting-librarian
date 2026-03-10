"""
Resilience utilities for network operations and retries
Provides exponential backoff, connection recovery, and graceful degradation
"""

import logging
import time
import random
import functools
import threading
from typing import Callable, Any, Optional, TypeVar, Tuple, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

# Type for decorated functions
F = TypeVar('F', bound=Callable[..., Any])

class ResilienceConfig:
    """Configuration for resilience behavior"""
    def __init__(self):
        # Exponential backoff settings
        self.initial_delay = 1  # seconds
        self.max_delay = 300    # 5 minutes
        self.backoff_factor = 2  # exponential factor
        self.jitter_factor = 0.1  # 10% jitter to avoid thundering herd
        
        # Retry settings
        self.default_max_retries = 3
        self.connection_timeout = 10  # seconds
        self.read_timeout = 30  # seconds
        
        # Circuit breaker settings
        self.circuit_breaker_threshold = 5  # failures before breaking
        self.circuit_breaker_reset_time = 60  # seconds


# Global instance
_resilience_config = ResilienceConfig()


def set_resilience_config(config: ResilienceConfig) -> None:
    """Set the global resilience configuration"""
    global _resilience_config
    _resilience_config = config


def get_resilience_config() -> ResilienceConfig:
    """Get the global resilience configuration"""
    return _resilience_config


class CircuitBreaker:
    """
    Simple circuit breaker for failing endpoints
    Prevents cascading failures by temporarily stopping requests to failing services
    """
    def __init__(self, failure_threshold: int = 5, reset_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failures = 0
        self.last_failure_time = None
        self.is_open = False
        self.lock = threading.RLock()
    
    def record_success(self):
        """Record a successful call"""
        with self.lock:
            self.failures = 0
            self.is_open = False
    
    def record_failure(self):
        """Record a failed call"""
        with self.lock:
            self.failures += 1
            self.last_failure_time = datetime.now()
            
            if self.failures >= self.failure_threshold:
                self.is_open = True
                logger.warning(
                    f"Circuit breaker opened after {self.failures} failures. "
                    f"Will attempt reset in {self.reset_timeout}s"
                )
    
    def can_execute(self) -> bool:
        """Check if execution is allowed"""
        with self.lock:
            if not self.is_open:
                return True
            
            # Check if reset timeout has passed
            if self.last_failure_time:
                elapsed = (datetime.now() - self.last_failure_time).total_seconds()
                if elapsed >= self.reset_timeout:
                    logger.info("Circuit breaker attempting reset...")
                    self.is_open = False
                    self.failures = 0
                    return True
            
            return False


class RetryContext:
    """Context for a single retry operation"""
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.attempt = 0
        self.last_exception = None
    
    def should_retry(self) -> bool:
        """Check if we should retry"""
        return self.attempt < self.max_retries
    
    def increment(self):
        """Increment attempt counter"""
        self.attempt += 1


def calculate_backoff_delay(attempt: int, config: Optional[ResilienceConfig] = None) -> float:
    """
    Calculate delay with exponential backoff and jitter
    
    Args:
        attempt: The retry attempt number (0-based)
        config: Optional resilience config (uses global if not provided)
    
    Returns:
        Delay in seconds
    """
    if config is None:
        config = get_resilience_config()
    
    # Exponential backoff: initial_delay * (backoff_factor ^ attempt)
    delay = config.initial_delay * (config.backoff_factor ** attempt)
    
    # Cap at max delay
    delay = min(delay, config.max_delay)
    
    # Add jitter to avoid thundering herd
    jitter = delay * config.jitter_factor * random.uniform(-1, 1)
    delay = max(0.1, delay + jitter)  # Ensure at least 0.1 seconds
    
    return delay


def retry_with_backoff(
    max_retries: int = 3,
    operation_name: str = "operation",
    config: Optional[ResilienceConfig] = None,
    on_retry: Optional[Callable[[int, float, Exception], None]] = None
) -> Callable[[F], F]:
    """
    Decorator for functions that should retry with exponential backoff
    
    Args:
        max_retries: Maximum number of attempts
        operation_name: Name for logging purposes
        config: Optional resilience config
        on_retry: Optional callback when retry happens
    
    Returns:
        Decorated function
    """
    if config is None:
        config = get_resilience_config()
    
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    logger.debug(f"Executing {operation_name} (attempt {attempt + 1}/{max_retries})")
                    result = func(*args, **kwargs)
                    
                    if attempt > 0:
                        logger.info(f"✓ {operation_name} succeeded on retry attempt {attempt + 1}")
                    
                    return result
                    
                except Exception as e:
                    last_exception = e
                    
                    if attempt < max_retries - 1:
                        delay = calculate_backoff_delay(attempt, config)
                        logger.warning(
                            f"{operation_name} failed (attempt {attempt + 1}/{max_retries}): {str(e)}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        
                        if on_retry:
                            on_retry(attempt, delay, e)
                        
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"{operation_name} failed after {max_retries} attempts: {str(e)}"
                        )
            
            # Raise the last exception if all retries failed
            raise last_exception
        
        return wrapper  # type: ignore
    
    return decorator


def retry_operation(
    func: Callable[[], Any],
    max_retries: int = 3,
    operation_name: str = "operation",
    on_retry: Optional[Callable[[int, float, Exception], None]] = None
) -> Tuple[bool, Any]:
    """
    Execute a function with retry logic (non-decorator version)
    
    Args:
        func: Function to execute
        max_retries: Maximum number of attempts
        operation_name: Name for logging
        on_retry: Optional callback on retry
    
    Returns:
        Tuple of (success, result/exception)
    """
    config = get_resilience_config()
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            logger.debug(f"Executing {operation_name} (attempt {attempt + 1}/{max_retries})")
            result = func()
            
            if attempt > 0:
                logger.info(f"✓ {operation_name} succeeded on retry attempt {attempt + 1}")
            
            return True, result
            
        except Exception as e:
            last_exception = e
            
            if attempt < max_retries - 1:
                delay = calculate_backoff_delay(attempt, config)
                logger.warning(
                    f"{operation_name} failed (attempt {attempt + 1}/{max_retries}): {str(e)}. "
                    f"Retrying in {delay:.1f}s..."
                )
                
                if on_retry:
                    on_retry(attempt, delay, e)
                
                time.sleep(delay)
            else:
                logger.error(
                    f"{operation_name} failed after {max_retries} attempts: {str(e)}"
                )
    
    return False, last_exception


def is_retryable_error(exception: Exception) -> bool:
    """
    Determine if an error is retryable
    
    Args:
        exception: The exception to check
    
    Returns:
        True if the error is temporary/retryable
    """
    error_str = str(exception).lower()
    
    # Network errors are retryable
    retryable_patterns = [
        "connection",
        "timeout",
        "temporarily unavailable",
        "too many requests",
        "service unavailable",
        "bad gateway",
        "gateway timeout",
        "remote end closed",
        "forcibly closed",
        "connection reset",
        "connection refused",
        "connection aborted",
    ]
    
    return any(pattern in error_str for pattern in retryable_patterns)


class HealthChecker:
    """
    Periodically checks the health of connections and services
    """
    def __init__(self, check_interval: int = 60):
        self.check_interval = check_interval
        self.checks = {}  # name -> (last_check_time, is_healthy, error_msg)
        self.lock = threading.RLock()
    
    def record_check(self, name: str, is_healthy: bool, error_msg: str = ""):
        """Record the result of a health check"""
        with self.lock:
            self.checks[name] = {
                "last_check": datetime.now(),
                "is_healthy": is_healthy,
                "error": error_msg
            }
    
    def is_healthy(self, name: str) -> bool:
        """Check if a service is currently healthy"""
        with self.lock:
            if name not in self.checks:
                return True  # Assume healthy if not yet checked
            
            return self.checks[name]["is_healthy"]
    
    def get_status(self, name: Optional[str] = None) -> Dict[str, Any]:
        """Get health status of services"""
        with self.lock:
            if name:
                return self.checks.get(name, {})
            return dict(self.checks)


# Global circuit breakers
_circuit_breakers = {}


def get_circuit_breaker(name: str, config: Optional[ResilienceConfig] = None) -> CircuitBreaker:
    """Get or create a circuit breaker for a service"""
    if name not in _circuit_breakers:
        if config is None:
            config = get_resilience_config()
        _circuit_breakers[name] = CircuitBreaker(
            config.circuit_breaker_threshold,
            config.circuit_breaker_reset_time
        )
    return _circuit_breakers[name]


# Global health checker
_health_checker = HealthChecker()


def get_health_checker() -> HealthChecker:
    """Get the global health checker"""
    return _health_checker
