"""
Persistent queue for Google Sheets requests (batch processing)
Allows queuing Sheets operations and sending them in batches when ready
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional
from datetime import datetime

from storage_utils import locked_load_json, locked_save_json

logger = logging.getLogger(__name__)


class SheetsQueue:
    """Queue for batching Google Sheets requests"""
    
    def __init__(self, queue_file: str = "logs/sheets_queue.json"):
        self.queue_file = queue_file
        os.makedirs(os.path.dirname(queue_file), exist_ok=True)
    
    def _load(self) -> List[Dict[str, Any]]:
        """Load queue from file"""
        return locked_load_json(self.queue_file, [])
    
    def _save(self, items: List[Dict[str, Any]]) -> None:
        """Save queue to file"""
        try:
            locked_save_json(self.queue_file, items, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save sheets queue: {e}")
    
    def enqueue_append(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        row: List[Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Queue an append operation
        
        Args:
            spreadsheet_id: Google Sheets ID
            sheet_name: Sheet name/tab
            row: Row data to append
            metadata: Optional metadata (e.g., meeting_id, timestamp)
        """
        items = self._load()
        item = {
            "operation": "append",
            "spreadsheet_id": spreadsheet_id,
            "sheet_name": sheet_name,
            "row": row,
            "metadata": metadata or {},
            "queued_at": datetime.now().isoformat(),
            "status": "pending"
        }
        items.append(item)
        self._save(items)
        logger.info(f"Queued append operation for {sheet_name}")
    
    def enqueue_update(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        range_name: str,
        values: List[List[Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Queue an update operation
        
        Args:
            spreadsheet_id: Google Sheets ID
            sheet_name: Sheet name/tab
            range_name: Range to update (e.g., "A1:C10")
            values: Values to update
            metadata: Optional metadata
        """
        items = self._load()
        item = {
            "operation": "update",
            "spreadsheet_id": spreadsheet_id,
            "sheet_name": sheet_name,
            "range_name": range_name,
            "values": values,
            "metadata": metadata or {},
            "queued_at": datetime.now().isoformat(),
            "status": "pending"
        }
        items.append(item)
        self._save(items)
        logger.info(f"Queued update operation for {sheet_name}")
    
    def enqueue_batch_update(
        self,
        spreadsheet_id: str,
        requests: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Queue a batch update operation
        
        Args:
            spreadsheet_id: Google Sheets ID
            requests: List of batch update requests
            metadata: Optional metadata
        """
        items = self._load()
        item = {
            "operation": "batch_update",
            "spreadsheet_id": spreadsheet_id,
            "requests": requests,
            "metadata": metadata or {},
            "queued_at": datetime.now().isoformat(),
            "status": "pending"
        }
        items.append(item)
        self._save(items)
        logger.info(f"Queued batch update operation with {len(requests)} requests")
    
    def dequeue_all(self) -> List[Dict[str, Any]]:
        """Get all queued items and clear queue"""
        items = self._load()
        if items:
            self._save([])
            logger.info(f"Dequeued {len(items)} items from sheets queue")
        return items
    
    def dequeue_by_spreadsheet(self, spreadsheet_id: str) -> List[Dict[str, Any]]:
        """Get queued items for specific spreadsheet"""
        items = self._load()
        matching = [item for item in items if item.get("spreadsheet_id") == spreadsheet_id]
        remaining = [item for item in items if item.get("spreadsheet_id") != spreadsheet_id]
        self._save(remaining)
        if matching:
            logger.info(f"Dequeued {len(matching)} items for spreadsheet {spreadsheet_id}")
        return matching
    
    def dequeue_by_operation(self, operation: str) -> List[Dict[str, Any]]:
        """Get queued items of specific operation type"""
        items = self._load()
        matching = [item for item in items if item.get("operation") == operation]
        remaining = [item for item in items if item.get("operation") != operation]
        self._save(remaining)
        if matching:
            logger.info(f"Dequeued {len(matching)} {operation} operations")
        return matching
    
    def get_queue_size(self) -> int:
        """Get number of items in queue"""
        return len(self._load())
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        items = self._load()
        stats = {
            "total_items": len(items),
            "by_operation": {},
            "by_spreadsheet": {},
            "oldest_item": None
        }
        
        for item in items:
            op = item.get("operation", "unknown")
            stats["by_operation"][op] = stats["by_operation"].get(op, 0) + 1
            
            sheet_id = item.get("spreadsheet_id", "unknown")
            stats["by_spreadsheet"][sheet_id] = stats["by_spreadsheet"].get(sheet_id, 0) + 1
        
        if items:
            stats["oldest_item"] = items[0].get("queued_at")
        
        return stats
    
    def clear_queue(self) -> None:
        """Clear all queued items"""
        self._save([])
        logger.warning("Sheets queue cleared")
    
    def mark_as_processed(self, item_index: int) -> None:
        """Mark item as processed (for tracking)"""
        items = self._load()
        if 0 <= item_index < len(items):
            items[item_index]["status"] = "processed"
            items[item_index]["processed_at"] = datetime.now().isoformat()
            self._save(items)
