"""
Persistent storage for Telegram callback data
"""

import json
import logging
import os
from typing import Any, Dict

from storage_utils import locked_load_json, locked_save_json

logger = logging.getLogger(__name__)

class CallbackPersistence:
    def __init__(self, storage_file: str = "logs/callback_map.json"):
        self.storage_file = storage_file
        os.makedirs(os.path.dirname(storage_file), exist_ok=True)

    def load(self) -> Dict[str, Any]:
        """Load the callback map from disk"""
        return locked_load_json(self.storage_file, {})

    def save(self, callback_map: Dict[str, Any]) -> None:
        """Save the callback map to disk"""
        try:
            locked_save_json(self.storage_file, callback_map, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save callback map: {e}")

    def update(self, cb_id: str, data: Dict[str, Any]) -> None:
        """Update a single callback entry and persist"""
        callback_map = self.load()
        callback_map[cb_id] = data
        self.save(callback_map)
