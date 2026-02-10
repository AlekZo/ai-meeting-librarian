#!/usr/bin/env python3
"""
Example: How to integrate Clash Verge proxy and Sheets queue into your application

This file demonstrates the complete integration pattern.
Copy the relevant parts into your main.py
"""

import logging
from typing import Optional

from proxy_manager import ProxyManager
from sheets_queue import SheetsQueue
from sheets_drive_handler import SheetsDriveHandler
from http_client import set_proxy
from config.config import config

logger = logging.getLogger(__name__)


class ApplicationWithProxyAndQueue:
    """Example application with proxy and queue support"""
    
    def __init__(self):
        """Initialize application with proxy and queue"""
        
        # ============================================================
        # 1. INITIALIZE PROXY MANAGER
        # ============================================================
        self.proxy_manager = ProxyManager(
            clash_verge_port=config.get("clash_verge_port", 7890),
            enable_proxy=config.get("enable_proxy", False)
        )
        
        # Test and enable proxy if available
        if self.proxy_manager.is_enabled():
            if self.proxy_manager.test_connection():
                logger.info("✓ Clash Verge proxy connected successfully")
                # Set global proxy for all HTTP requests
                set_proxy(self.proxy_manager.get_proxies())
            else:
                logger.warning("✗ Clash Verge not responding, continuing without proxy")
                self.proxy_manager.disable()
        else:
            logger.info("Proxy is disabled in configuration")
        
        # ============================================================
        # 2. INITIALIZE SHEETS QUEUE
        # ============================================================
        self.sheets_queue = SheetsQueue(
            queue_file=config.get("sheets_queue_file", "logs/sheets_queue.json")
        )
        
        queue_size = self.sheets_queue.get_queue_size()
        if queue_size > 0:
            logger.info(f"Found {queue_size} items in Sheets queue")
        
        # ============================================================
        # 3. INITIALIZE SHEETS HANDLER WITH QUEUE
        # ============================================================
        self.sheets_handler = SheetsDriveHandler(
            credentials_file=config.get("google_credentials_path"),
            token_file=config.get("google_token_path"),
            sheets_queue=self.sheets_queue  # Pass queue for automatic queuing
        )
        
        logger.info("Application initialized with proxy and queue support")
    
    def publish_meeting_log(self, row_data: list) -> bool:
        """
        Publish meeting log to Google Sheets with automatic queuing on failure
        
        Args:
            row_data: List of values for the row
            
        Returns:
            True if published successfully, False if queued
        """
        try:
            # This will automatically queue if it fails
            success = self.sheets_handler.append_meeting_log(
                spreadsheet_id=config.get("google_sheets_id"),
                sheet_name=config.get("google_sheets_meeting_tab"),
                row=row_data,
                queue_if_failed=True,  # Enable automatic queuing
                metadata={
                    "source": "video_upload",
                    "timestamp": str(__import__('datetime').datetime.now())
                }
            )
            
            if success:
                logger.info("✓ Meeting log published to Google Sheets")
                return True
            else:
                logger.info("⏳ Meeting log queued for later publishing")
                return False
        
        except Exception as e:
            logger.error(f"✗ Failed to publish meeting log: {e}")
            return False
    
    def process_queued_sheets_operations(self) -> int:
        """
        Process all queued Google Sheets operations
        
        Returns:
            Number of successfully processed items
        """
        # Get all queued items
        items = self.sheets_queue.dequeue_all()
        
        if not items:
            logger.info("No queued Sheets operations to process")
            return 0
        
        logger.info(f"Processing {len(items)} queued Sheets operations")
        
        processed_count = 0
        failed_items = []
        
        for idx, item in enumerate(items, 1):
            try:
                operation = item.get("operation", "unknown")
                
                if operation == "append":
                    # Process append operation
                    self.sheets_handler.append_meeting_log(
                        spreadsheet_id=item["spreadsheet_id"],
                        sheet_name=item["sheet_name"],
                        row=item["row"],
                        queue_if_failed=False  # Don't re-queue
                    )
                    logger.info(f"✓ Processed append operation ({idx}/{len(items)})")
                    processed_count += 1
                
                elif operation == "update":
                    # Process update operation
                    self.sheets_handler.sheets_service.spreadsheets().values().update(
                        spreadsheetId=item["spreadsheet_id"],
                        range=item["range_name"],
                        valueInputOption="USER_ENTERED",
                        body={"values": item["values"]}
                    ).execute()
                    logger.info(f"✓ Processed update operation ({idx}/{len(items)})")
                    processed_count += 1
                
                elif operation == "batch_update":
                    # Process batch update operation
                    self.sheets_handler.sheets_service.spreadsheets().batchUpdate(
                        spreadsheetId=item["spreadsheet_id"],
                        body={"requests": item["requests"]}
                    ).execute()
                    logger.info(f"✓ Processed batch update operation ({idx}/{len(items)})")
                    processed_count += 1
                
                else:
                    logger.warning(f"Unknown operation type: {operation}")
                    failed_items.append(item)
            
            except Exception as e:
                logger.error(f"✗ Failed to process queued item: {e}")
                failed_items.append(item)
        
        # Re-queue failed items
        if failed_items:
            logger.warning(f"Re-queuing {len(failed_items)} failed items")
            for item in failed_items:
                if item["operation"] == "append":
                    self.sheets_queue.enqueue_append(
                        item["spreadsheet_id"],
                        item["sheet_name"],
                        item["row"],
                        item.get("metadata")
                    )
                elif item["operation"] == "update":
                    self.sheets_queue.enqueue_update(
                        item["spreadsheet_id"],
                        item["sheet_name"],
                        item["range_name"],
                        item["values"],
                        item.get("metadata")
                    )
        
        logger.info(f"Processed {processed_count}/{len(items)} queued operations")
        return processed_count
    
    def get_queue_status(self) -> dict:
        """Get current queue status"""
        stats = self.sheets_queue.get_queue_stats()
        return {
            "total_items": stats["total_items"],
            "by_operation": stats["by_operation"],
            "by_spreadsheet": stats["by_spreadsheet"],
            "oldest_item": stats["oldest_item"],
            "proxy_enabled": self.proxy_manager.is_enabled()
        }
    
    def enable_proxy(self) -> bool:
        """Enable proxy and test connection"""
        self.proxy_manager.enable()
        if self.proxy_manager.test_connection():
            logger.info("✓ Proxy enabled and connected")
            set_proxy(self.proxy_manager.get_proxies())
            return True
        else:
            logger.warning("✗ Proxy not available")
            self.proxy_manager.disable()
            return False
    
    def disable_proxy(self) -> None:
        """Disable proxy"""
        self.proxy_manager.disable()
        set_proxy(None)
        logger.info("Proxy disabled")


# ============================================================
# USAGE EXAMPLES
# ============================================================

def example_basic_usage():
    """Example 1: Basic usage"""
    app = ApplicationWithProxyAndQueue()
    
    # Publish a meeting log
    row_data = [
        "2026-02-03 22:30:00",
        "Team Meeting",
        "Standup",
        "John, Jane",
        "Discussed Q1 goals",
        "Project A",
        "https://example.com/video",
        "https://example.com/scribber",
        "https://docs.google.com/document/d/...",
        "Completed"
    ]
    
    success = app.publish_meeting_log(row_data)
    if not success:
        print("Meeting log was queued")


def example_process_queue():
    """Example 2: Process queued operations"""
    app = ApplicationWithProxyAndQueue()
    
    # Check queue status
    status = app.get_queue_status()
    print(f"Queue status: {status}")
    
    # Process queued items
    processed = app.process_queued_sheets_operations()
    print(f"Processed {processed} items")


def example_proxy_management():
    """Example 3: Manage proxy"""
    app = ApplicationWithProxyAndQueue()
    
    # Enable proxy
    if app.enable_proxy():
        print("Proxy is now enabled")
    
    # Do some work...
    
    # Disable proxy
    app.disable_proxy()
    print("Proxy is now disabled")


def example_periodic_processing():
    """Example 4: Periodic queue processing (for main loop)"""
    import time
    
    app = ApplicationWithProxyAndQueue()
    
    # In your main loop, periodically process queue
    while True:
        try:
            # Do main work...
            
            # Every 5 minutes, process queued operations
            time.sleep(300)
            app.process_queued_sheets_operations()
        
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}")


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run examples
    print("=" * 60)
    print("Example 1: Basic Usage")
    print("=" * 60)
    # example_basic_usage()
    
    print("\n" + "=" * 60)
    print("Example 2: Process Queue")
    print("=" * 60)
    # example_process_queue()
    
    print("\n" + "=" * 60)
    print("Example 3: Proxy Management")
    print("=" * 60)
    # example_proxy_management()
    
    print("\nUncomment the examples you want to run in the __main__ block")
