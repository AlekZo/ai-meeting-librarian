"""
Enhanced UI Dashboard for Auto Meeting Video Renamer
Provides real-time status, statistics, and controls
"""

import threading
import logging
import os
import json
from datetime import datetime
from typing import Dict, Any, Callable, Optional
from pathlib import Path

try:
    from PIL import Image, ImageDraw
    import pystray
    from pystray import MenuItem as item
    HAS_PYSTRAY = True
except ImportError:
    HAS_PYSTRAY = False

logger = logging.getLogger(__name__)


class EnhancedDashboard:
    """Enhanced dashboard with real-time status and statistics"""
    
    def __init__(self, on_quit_callback: Optional[Callable] = None):
        self.on_quit = on_quit_callback
        self.icon = None
        self.status = "Starting..."
        self.status_color = "yellow"
        self._thread = None
        
        # Statistics
        self.stats = {
            "files_processed": 0,
            "files_pending": 0,
            "errors": 0,
            "uptime_seconds": 0,
            "internet_status": "Unknown",
            "last_activity": "None",
            "restart_count": 0,
            "health_status": "Unknown"
        }
        
        self.start_time = datetime.now()
    
    def update_stats(self, stats_dict: Dict[str, Any]):
        """Update dashboard statistics"""
        self.stats.update(stats_dict)
        self._update_display()
    
    def update_status(self, status: str, color: str = "green"):
        """Update status message and color"""
        self.status = status
        self.status_color = color
        self.stats["last_activity"] = datetime.now().strftime("%H:%M:%S")
        self._update_display()
    
    def _update_display(self):
        """Update the display (tray icon and menu)"""
        if self.icon and HAS_PYSTRAY:
            try:
                self.icon.icon = self._create_icon(self.status_color)
            except Exception as e:
                logger.debug(f"Could not update icon: {e}")
    
    def _create_icon(self, color: str) -> Image.Image:
        """Create a colored icon with status indicator"""
        if not HAS_PYSTRAY:
            return None
        
        width, height = 64, 64
        image = Image.new('RGB', (width, height), (255, 255, 255))
        draw = ImageDraw.Draw(image)
        
        # Color mapping
        color_map = {
            "green": (0, 200, 0),
            "yellow": (255, 200, 0),
            "red": (255, 0, 0),
            "orange": (255, 140, 0),
            "blue": (0, 100, 255)
        }
        
        rgb_color = color_map.get(color, (100, 100, 100))
        
        # Draw main circle
        draw.ellipse((8, 8, 56, 56), fill=rgb_color, outline="black", width=2)
        
        # Draw status indicator
        if color == "green":
            draw.text((20, 20), "✓", fill="white")
        elif color == "yellow":
            draw.text((20, 18), "⚙", fill="black")
        elif color == "red":
            draw.text((20, 20), "✗", fill="white")
        elif color == "orange":
            draw.text((18, 18), "⚠", fill="white")
        
        return image
    
    def _get_status_text(self) -> str:
        """Get formatted status text"""
        uptime = (datetime.now() - self.start_time).total_seconds()
        hours = int(uptime // 3600)
        minutes = int((uptime % 3600) // 60)
        
        return (
            f"Status: {self.status}\n"
            f"Internet: {self.stats['internet_status']}\n"
            f"Health: {self.stats['health_status']}\n"
            f"Uptime: {hours}h {minutes}m\n"
            f"Files Processed: {self.stats['files_processed']}\n"
            f"Pending: {self.stats['files_pending']}\n"
            f"Errors: {self.stats['errors']}\n"
            f"Restarts: {self.stats['restart_count']}\n"
            f"Last Activity: {self.stats['last_activity']}"
        )
    
    def _setup_menu(self):
        """Setup system tray menu"""
        if not HAS_PYSTRAY:
            return None
        
        return pystray.Menu(
            item(self._get_status_text, lambda: None, enabled=False),
            pystray.Menu.SEPARATOR,
            item("📊 Show Statistics", self._show_stats),
            item("🔄 Restart", self._restart_app),
            item("⏸️ Pause", self._pause_app),
            item("▶️ Resume", self._resume_app),
            pystray.Menu.SEPARATOR,
            item("❌ Quit", self._on_quit_clicked)
        )
    
    def _show_stats(self, icon=None, item=None):
        """Show detailed statistics"""
        stats_text = json.dumps(self.stats, indent=2)
        logger.info(f"Dashboard Stats:\n{stats_text}")
    
    def _restart_app(self, icon=None, item=None):
        """Request app restart"""
        logger.info("Restart requested from dashboard")
        self.update_status("Restarting...", "yellow")
    
    def _pause_app(self, icon=None, item=None):
        """Pause app processing"""
        logger.info("Pause requested from dashboard")
        self.update_status("Paused", "orange")
    
    def _resume_app(self, icon=None, item=None):
        """Resume app processing"""
        logger.info("Resume requested from dashboard")
        self.update_status("Resumed", "green")
    
    def _on_quit_clicked(self, icon, item):
        """Handle quit from menu"""
        logger.info("Quit clicked from dashboard")
        if icon:
            icon.stop()
        if self.on_quit:
            self.on_quit()
    
    def run(self):
        """Run the dashboard"""
        if not HAS_PYSTRAY:
            logger.warning("pystray not available, dashboard disabled")
            return
        
        try:
            self.icon = pystray.Icon(
                "AutoMeetingVideoRenamer",
                self._create_icon(self.status_color),
                "Auto-Meeting Video Renamer",
                self._setup_menu()
            )
            self.icon.run()
        except Exception as e:
            logger.error(f"Dashboard error: {e}")
    
    def start(self):
        """Start dashboard in background thread"""
        if not HAS_PYSTRAY:
            logger.debug("Dashboard disabled (pystray not available)")
            return
        
        self._thread = threading.Thread(target=self.run, daemon=True)
        self._thread.start()
        logger.info("Dashboard started")
    
    def stop(self):
        """Stop dashboard"""
        if self.icon:
            try:
                self.icon.stop()
            except Exception as e:
                logger.debug(f"Error stopping dashboard: {e}")


class ConsoleUI:
    """Console-based UI for terminal output"""
    
    def __init__(self):
        self.last_update = datetime.now()
        self.update_interval = 5  # seconds
    
    def print_header(self):
        """Print application header"""
        print("\n" + "="*60)
        print("  AUTO MEETING VIDEO RENAMER - RESILIENCE EDITION")
        print("="*60 + "\n")
    
    def print_status(self, status: str, color: str = "green"):
        """Print status with color"""
        colors = {
            "green": "\033[92m",
            "yellow": "\033[93m",
            "red": "\033[91m",
            "orange": "\033[33m",
            "blue": "\033[94m",
            "reset": "\033[0m"
        }
        
        color_code = colors.get(color, colors["reset"])
        reset_code = colors["reset"]
        
        print(f"{color_code}[{status}]{reset_code}")
    
    def print_stats(self, stats: Dict[str, Any]):
        """Print statistics table"""
        print("\n" + "-"*60)
        print("STATISTICS")
        print("-"*60)
        
        for key, value in stats.items():
            key_display = key.replace("_", " ").title()
            print(f"  {key_display:<25} : {value}")
        
        print("-"*60 + "\n")
    
    def print_progress(self, current: int, total: int, label: str = "Progress"):
        """Print progress bar"""
        if total == 0:
            percentage = 0
        else:
            percentage = (current / total) * 100
        
        bar_length = 40
        filled = int(bar_length * current / total) if total > 0 else 0
        bar = "█" * filled + "░" * (bar_length - filled)
        
        print(f"\r{label}: [{bar}] {percentage:.1f}% ({current}/{total})", end="", flush=True)
    
    def print_error(self, error: str):
        """Print error message"""
        print(f"\n\033[91m[ERROR] {error}\033[0m\n")
    
    def print_success(self, message: str):
        """Print success message"""
        print(f"\n\033[92m[SUCCESS] {message}\033[0m\n")
    
    def print_warning(self, message: str):
        """Print warning message"""
        print(f"\n\033[93m[WARNING] {message}\033[0m\n")


class UIManager:
    """Unified UI manager combining dashboard and console"""
    
    def __init__(self, on_quit_callback: Optional[Callable] = None):
        self.dashboard = EnhancedDashboard(on_quit_callback)
        self.console = ConsoleUI()
        self.enabled = True
    
    def start(self):
        """Start UI components"""
        self.console.print_header()
        self.dashboard.start()
    
    def update_status(self, status: str, color: str = "green"):
        """Update status in all UI components"""
        self.dashboard.update_status(status, color)
        self.console.print_status(status, color)
    
    def update_stats(self, stats: Dict[str, Any]):
        """Update statistics"""
        self.dashboard.update_stats(stats)
    
    def print_stats(self, stats: Dict[str, Any]):
        """Print statistics to console"""
        self.console.print_stats(stats)
    
    def print_progress(self, current: int, total: int, label: str = "Progress"):
        """Print progress bar"""
        self.console.print_progress(current, total, label)
    
    def print_error(self, error: str):
        """Print error"""
        self.console.print_error(error)
        self.dashboard.update_status(f"Error: {error[:30]}", "red")
    
    def print_success(self, message: str):
        """Print success"""
        self.console.print_success(message)
        self.dashboard.update_status(message, "green")
    
    def print_warning(self, message: str):
        """Print warning"""
        self.console.print_warning(message)
        self.dashboard.update_status(message, "orange")
    
    def stop(self):
        """Stop UI"""
        self.dashboard.stop()
