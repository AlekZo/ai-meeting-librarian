"""
Progress tracking and statistics collection
Tracks file processing, errors, and performance metrics
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List
from collections import defaultdict

logger = logging.getLogger(__name__)


class ProgressTracker:
    """Track application progress and statistics"""
    
    def __init__(self):
        self.start_time = datetime.now()
        
        # File processing stats
        self.files_processed = 0
        self.files_failed = 0
        self.files_pending = 0
        self.files_queued = 0
        
        # Performance metrics
        self.total_processing_time = 0.0
        self.total_retry_count = 0
        self.total_errors = 0
        
        # Status tracking
        self.internet_available = True
        self.last_activity = datetime.now()
        self.restart_count = 0
        self.health_status = "Healthy"
        
        # Detailed tracking
        self.processing_times = []  # List of processing times
        self.error_log = []  # List of errors
        self.activity_log = []  # List of activities
        
        # Performance by file type
        self.stats_by_type = defaultdict(lambda: {
            "count": 0,
            "total_time": 0.0,
            "errors": 0
        })
    
    def record_file_processed(self, filename: str, processing_time: float, file_type: str = "video"):
        """Record a successfully processed file"""
        self.files_processed += 1
        self.total_processing_time += processing_time
        self.processing_times.append(processing_time)
        self.last_activity = datetime.now()
        
        # Update stats by type
        self.stats_by_type[file_type]["count"] += 1
        self.stats_by_type[file_type]["total_time"] += processing_time
        
        logger.info(f"File processed: {filename} ({processing_time:.2f}s)")
    
    def record_file_failed(self, filename: str, error: str, file_type: str = "video"):
        """Record a failed file"""
        self.files_failed += 1
        self.total_errors += 1
        self.last_activity = datetime.now()
        
        # Update stats by type
        self.stats_by_type[file_type]["errors"] += 1
        
        # Log error
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "filename": filename,
            "error": error,
            "type": file_type
        }
        self.error_log.append(error_entry)
        
        logger.error(f"File failed: {filename} - {error}")
    
    def record_file_queued(self, filename: str, reason: str = "offline"):
        """Record a queued file"""
        self.files_queued += 1
        self.files_pending += 1
        self.last_activity = datetime.now()
        
        activity = {
            "timestamp": datetime.now().isoformat(),
            "action": "queued",
            "filename": filename,
            "reason": reason
        }
        self.activity_log.append(activity)
        
        logger.info(f"File queued: {filename} ({reason})")
    
    def record_file_dequeued(self, filename: str):
        """Record a dequeued file"""
        if self.files_pending > 0:
            self.files_pending -= 1
        
        activity = {
            "timestamp": datetime.now().isoformat(),
            "action": "dequeued",
            "filename": filename
        }
        self.activity_log.append(activity)
        
        logger.info(f"File dequeued: {filename}")
    
    def record_retry(self, filename: str, attempt: int, reason: str = "network"):
        """Record a retry attempt"""
        self.total_retry_count += 1
        self.last_activity = datetime.now()
        
        activity = {
            "timestamp": datetime.now().isoformat(),
            "action": "retry",
            "filename": filename,
            "attempt": attempt,
            "reason": reason
        }
        self.activity_log.append(activity)
        
        logger.debug(f"Retry {attempt}: {filename} ({reason})")
    
    def record_internet_status(self, available: bool):
        """Record internet status change"""
        self.internet_available = available
        self.last_activity = datetime.now()
        
        status = "online" if available else "offline"
        activity = {
            "timestamp": datetime.now().isoformat(),
            "action": "internet_status",
            "status": status
        }
        self.activity_log.append(activity)
        
        logger.info(f"Internet status: {status}")
    
    def record_restart(self):
        """Record application restart"""
        self.restart_count += 1
        self.last_activity = datetime.now()
        
        activity = {
            "timestamp": datetime.now().isoformat(),
            "action": "restart",
            "count": self.restart_count
        }
        self.activity_log.append(activity)
        
        logger.info(f"Application restart #{self.restart_count}")
    
    def set_health_status(self, status: str):
        """Set health status"""
        self.health_status = status
        self.last_activity = datetime.now()
    
    def get_uptime(self) -> timedelta:
        """Get application uptime"""
        return datetime.now() - self.start_time
    
    def get_average_processing_time(self) -> float:
        """Get average file processing time"""
        if not self.processing_times:
            return 0.0
        return sum(self.processing_times) / len(self.processing_times)
    
    def get_success_rate(self) -> float:
        """Get file processing success rate"""
        total = self.files_processed + self.files_failed
        if total == 0:
            return 0.0
        return (self.files_processed / total) * 100
    
    def get_stats(self) -> Dict[str, Any]:
        """Get all statistics"""
        uptime = self.get_uptime()
        hours = uptime.total_seconds() // 3600
        minutes = (uptime.total_seconds() % 3600) // 60
        
        return {
            "files_processed": self.files_processed,
            "files_failed": self.files_failed,
            "files_pending": self.files_pending,
            "files_queued": self.files_queued,
            "total_errors": self.total_errors,
            "total_retries": self.total_retry_count,
            "success_rate": f"{self.get_success_rate():.1f}%",
            "avg_processing_time": f"{self.get_average_processing_time():.2f}s",
            "total_processing_time": f"{self.total_processing_time:.1f}s",
            "uptime": f"{int(hours)}h {int(minutes)}m",
            "internet_status": "Online" if self.internet_available else "Offline",
            "health_status": self.health_status,
            "restart_count": self.restart_count,
            "last_activity": self.last_activity.strftime("%H:%M:%S")
        }
    
    def get_detailed_stats(self) -> Dict[str, Any]:
        """Get detailed statistics including by-type breakdown"""
        stats = self.get_stats()
        
        # Add by-type stats
        stats["by_type"] = {}
        for file_type, type_stats in self.stats_by_type.items():
            if type_stats["count"] > 0:
                avg_time = type_stats["total_time"] / type_stats["count"]
                stats["by_type"][file_type] = {
                    "processed": type_stats["count"],
                    "errors": type_stats["errors"],
                    "avg_time": f"{avg_time:.2f}s"
                }
        
        # Add recent errors
        stats["recent_errors"] = self.error_log[-5:] if self.error_log else []
        
        # Add recent activities
        stats["recent_activities"] = self.activity_log[-10:] if self.activity_log else []
        
        return stats
    
    def print_summary(self):
        """Print statistics summary"""
        stats = self.get_stats()
        
        print("\n" + "="*60)
        print("STATISTICS SUMMARY")
        print("="*60)
        
        for key, value in stats.items():
            key_display = key.replace("_", " ").title()
            print(f"  {key_display:<30} : {value}")
        
        print("="*60 + "\n")
    
    def reset(self):
        """Reset all statistics"""
        self.__init__()
        logger.info("Statistics reset")
