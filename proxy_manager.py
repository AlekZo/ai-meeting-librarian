"""
Proxy manager for Clash Verge integration
Handles proxy configuration and routing through Clash Verge
"""

from __future__ import annotations

import logging
import os
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class ProxyManager:
    """Manages proxy configuration for Clash Verge"""
    
    def __init__(self, clash_verge_port: int = 7890, enable_proxy: bool = False):
        """
        Initialize proxy manager
        
        Args:
            clash_verge_port: Port where Clash Verge is running (default: 7890)
            enable_proxy: Whether to enable proxy routing
        """
        self.clash_verge_port = clash_verge_port
        self.enable_proxy = enable_proxy
        self.proxy_url = f"http://127.0.0.1:{clash_verge_port}"
        self.proxies = None
        
        if self.enable_proxy:
            self._setup_proxies()
    
    def _setup_proxies(self) -> None:
        """Setup proxy configuration for requests library"""
        self.proxies = {
            "http": self.proxy_url,
            "https": self.proxy_url,
        }
        logger.info(f"Proxy configured: {self.proxy_url}")
    
    def get_proxies(self) -> Optional[Dict[str, str]]:
        """Get proxy configuration for requests"""
        return self.proxies if self.enable_proxy else None
    
    def is_enabled(self) -> bool:
        """Check if proxy is enabled"""
        return self.enable_proxy
    
    def enable(self) -> None:
        """Enable proxy routing"""
        self.enable_proxy = True
        self._setup_proxies()
        logger.info("Proxy enabled")
    
    def disable(self) -> None:
        """Disable proxy routing"""
        self.enable_proxy = False
        self.proxies = None
        logger.info("Proxy disabled")
    
    def set_port(self, port: int) -> None:
        """Change Clash Verge port"""
        self.clash_verge_port = port
        self.proxy_url = f"http://127.0.0.1:{port}"
        if self.enable_proxy:
            self._setup_proxies()
        logger.info(f"Proxy port changed to: {port}")
    
    def test_connection(self) -> bool:
        """Test if Clash Verge is accessible"""
        if not self.enable_proxy:
            logger.warning("Proxy is not enabled")
            return False
        
        try:
            import requests
            response = requests.get(
                "http://127.0.0.1:9090/api/version",
                proxies=self.proxies,
                timeout=5
            )
            if response.status_code == 200:
                logger.info("Clash Verge connection successful")
                return True
        except Exception as e:
            logger.error(f"Failed to connect to Clash Verge: {e}")
        
        return False
