"""
Persistent queue for meeting log entries (offline support)
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class MeetingLogQueue:
    def __init__(self, queue_file: str = "logs/meeting_log_queue.json"):
        self.queue_file = queue_file
        os.makedirs(os.path.dirname(queue_file), exist_ok=True)

    def _load(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.queue_file):
            return []
        try:
            with open(self.queue_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load queue: {e}")
            return []

    def _save(self, items: List[Dict[str, Any]]) -> None:
        try:
            with open(self.queue_file, "w", encoding="utf-8") as f:
                json.dump(items, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save queue: {e}")

    def enqueue(self, item: Dict[str, Any]) -> None:
        items = self._load()
        items.append(item)
        self._save(items)
        logger.info("Queued meeting log item for later publishing")

    def dequeue_all(self) -> List[Dict[str, Any]]:
        items = self._load()
        if items:
            self._save([])
        return items
