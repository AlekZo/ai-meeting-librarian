"""
State recovery module for resilient application restart
Tracks application state and enables recovery after crashes or terminations
"""

import os
import json
import logging
from typing import Any, Dict, List
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class AppState:
    """Persistent application state for crash recovery"""
    
    def __init__(self, state_file: str = "logs/app_state.json"):
        self.state_file = state_file
        os.makedirs(os.path.dirname(state_file), exist_ok=True)
        self._load()
    
    def _load(self):
        """Load state from disk"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    self.state = json.load(f)
                logger.info("✓ Loaded application state from disk")
            except Exception as e:
                logger.warning(f"Failed to load app state: {e}. Starting fresh.")
                self.state = self._create_default_state()
        else:
            self.state = self._create_default_state()
    
    def _create_default_state(self) -> Dict[str, Any]:
        """Create default state"""
        return {
            "last_startup": None,
            "last_shutdown": None,
            "initialization_complete": False,
            "last_internet_check": None,
            "internet_available": False,
            "pending_files": [],
            "in_progress_operations": {},
            "error_count": 0,
            "last_error": None,
            "restart_count": 0,
            "crash_recovery_mode": False
        }
    
    def _save(self):
        """Save state to disk"""
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save app state: {e}")
    
    def mark_startup(self):
        """Mark application startup"""
        self.state["last_startup"] = datetime.now().isoformat()
        self.state["error_count"] = 0
        self.state["last_error"] = None
        self.state["restart_count"] = self.state.get("restart_count", 0) + 1
        self._save()
        logger.info(f"Application restart #{self.state['restart_count']}")
    
    def mark_shutdown(self):
        """Mark graceful shutdown"""
        self.state["last_shutdown"] = datetime.now().isoformat()
        self.state["restart_count"] = 0  # Reset on graceful shutdown
        self.state["crash_recovery_mode"] = False
        self._save()
    
    def mark_initialization_complete(self):
        """Mark when initialization is fully complete"""
        self.state["initialization_complete"] = True
        self._save()
        logger.info("✓ Application initialization complete")
    
    def set_internet_status(self, available: bool):
        """Update internet availability status"""
        self.state["last_internet_check"] = datetime.now().isoformat()
        self.state["internet_available"] = available
        self._save()
    
    def record_error(self, error: str):
        """Record an error"""
        self.state["error_count"] = self.state.get("error_count", 0) + 1
        self.state["last_error"] = error
        self.state["last_error_time"] = datetime.now().isoformat()
        
        # If too many errors, mark crash recovery mode
        if self.state["error_count"] > 10:
            self.state["crash_recovery_mode"] = True
            logger.warning("⚠️ ERROR COUNT HIGH: Entering crash recovery mode")
        
        self._save()
    
    def should_enter_recovery_mode(self) -> bool:
        """Determine if we should enter recovery mode"""
        # Check for repeated crashes
        if self.state.get("restart_count", 0) > 5:
            return True
        
        # Check if last startup was recent but app seems to be crashing
        if self.state.get("last_startup"):
            try:
                last_start = datetime.fromisoformat(self.state["last_startup"])
                time_since_start = (datetime.now() - last_start).total_seconds()
                if time_since_start < 30:  # Crashed within 30 seconds of startup
                    return True
            except:
                pass
        
        return self.state.get("crash_recovery_mode", False)
    
    def get_pending_files(self) -> List[str]:
        """Get list of pending files"""
        return self.state.get("pending_files", [])
    
    def set_pending_files(self, files: List[str]):
        """Update pending files list"""
        self.state["pending_files"] = files
        self._save()
    
    def add_in_progress_operation(self, op_id: str, op_data: Dict[str, Any]):
        """Track an in-progress operation"""
        self.state["in_progress_operations"][op_id] = {
            "started_at": datetime.now().isoformat(),
            **op_data
        }
        self._save()
    
    def finish_in_progress_operation(self, op_id: str):
        """Mark operation as complete"""
        if op_id in self.state["in_progress_operations"]:
            del self.state["in_progress_operations"][op_id]
            self._save()
    
    def get_in_progress_operations(self) -> Dict[str, Any]:
        """Get all in-progress operations"""
        return self.state.get("in_progress_operations", {})
    
    def get_state(self) -> Dict[str, Any]:
        """Get full state dictionary"""
        return dict(self.state)
    
    def set_state(self, state: Dict[str, Any]):
        """Set full state dictionary"""
        self.state = state
        self._save()


class StateMonitor:
    """Monitors application state and detects issues"""
    
    def __init__(self, app_state: AppState):
        self.app_state = app_state
        self.warnings = []
        self.errors = []
    
    def check_health(self) -> Dict[str, Any]:
        """Perform health check and return status"""
        health = {
            "timestamp": datetime.now().isoformat(),
            "is_healthy": True,
            "warnings": [],
            "errors": []
        }
        
        state = self.app_state.get_state()
        
        # Check error count
        error_count = state.get("error_count", 0)
        if error_count > 5:
            health["warnings"].append(f"High error count: {error_count}")
        if error_count > 10:
            health["is_healthy"] = False
            health["errors"].append(f"Critical error count: {error_count}")
        
        # Check restart count
        restart_count = state.get("restart_count", 0)
        if restart_count > 3:
            health["warnings"].append(f"Frequent restarts: {restart_count}")
        if restart_count > 10:
            health["is_healthy"] = False
            health["errors"].append(f"Too many restarts: {restart_count}")
        
        # Check pending files
        pending = state.get("pending_files", [])
        if len(pending) > 100:
            health["warnings"].append(f"Large pending queue: {len(pending)} files")
        
        # Check in-progress operations
        in_progress = state.get("in_progress_operations", {})
        stuck_ops = 0
        for op_id, op_data in in_progress.items():
            try:
                started = datetime.fromisoformat(op_data.get("started_at", ""))
                elapsed = (datetime.now() - started).total_seconds()
                if elapsed > 3600:  # Operation stuck for >1 hour
                    stuck_ops += 1
                    health["warnings"].append(f"Stuck operation: {op_id} running for {elapsed:.0f}s")
            except:
                pass
        
        if stuck_ops > 0:
            health["errors"].append(f"{stuck_ops} operations appear to be stuck")
        
        return health


def enable_auto_restart(command: str, max_restarts: int = 5, restart_delay: int = 5) -> bool:
    """
    Create a wrapper script that auto-restarts the application on crash
    
    Args:
        command: Full command to run the application
        max_restarts: Maximum number of consecutive restarts before giving up
        restart_delay: Seconds to wait before restarting
    
    Returns:
        True if wrapper created successfully
    """
    import platform
    import sys
    
    if platform.system() == "Windows":
        bat_content = f"""@echo off
setlocal enabledelayedexpansion

set "MAX_RESTARTS={max_restarts}"
set "RESTART_DELAY={restart_delay}"
set "RESTART_COUNT=0"

:start_app
set /a RESTART_COUNT+=1

if !RESTART_COUNT! gtr !MAX_RESTARTS! (
    echo.
    echo ERROR: Application has restarted %MAX_RESTARTS% times. Giving up.
    pause
    exit /b 1
)

echo.
echo Starting application (attempt !RESTART_COUNT!/%MAX_RESTARTS%)...
cd /d "%~dp0"

{command}

echo.
echo Application crashed or exited with error code !ERRORLEVEL!
echo Waiting %RESTART_DELAY% seconds before restart...
timeout /t %RESTART_DELAY%

goto start_app
"""
        wrapper_file = "start_with_auto_restart.bat"
        try:
            with open(wrapper_file, 'w', encoding='utf-8') as f:
                f.write(bat_content)
            logger.info(f"✓ Created auto-restart wrapper: {wrapper_file}")
            logger.info(f"  Run it with: {wrapper_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to create restart wrapper: {e}")
            return False
    
    else:  # Linux/Mac
        sh_content = f"""#!/bin/bash

MAX_RESTARTS={max_restarts}
RESTART_DELAY={restart_delay}
RESTART_COUNT=0
SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"

while true; do
    RESTART_COUNT=$((RESTART_COUNT + 1))
    
    if [ $RESTART_COUNT -gt $MAX_RESTARTS ]; then
        echo ""
        echo "ERROR: Application has restarted $MAX_RESTARTS times. Giving up."
        exit 1
    fi
    
    echo ""
    echo "Starting application (attempt $RESTART_COUNT/$MAX_RESTARTS)..."
    cd "$SCRIPT_DIR"
    
    {command}
    EXIT_CODE=$?
    
    echo ""
    echo "Application crashed or exited with code $EXIT_CODE"
    echo "Waiting $RESTART_DELAY seconds before restart..."
    sleep $RESTART_DELAY
done
"""
        wrapper_file = "start_with_auto_restart.sh"
        try:
            with open(wrapper_file, 'w', encoding='utf-8') as f:
                f.write(sh_content)
            # Make executable
            os.chmod(wrapper_file, 0o755)
            logger.info(f"✓ Created auto-restart wrapper: {wrapper_file}")
            logger.info(f"  Run it with: bash {wrapper_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to create restart wrapper: {e}")
            return False
