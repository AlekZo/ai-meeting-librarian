"""
Configuration module for Auto-Meeting Video Renamer
"""

import os
import json
from pathlib import Path

# Default configuration values
DEFAULT_CONFIG = {
    "watch_folder": r"D:\Nextcloud\Videos\ScreenRecordings\JustRecorded",
    "to_transcribe_folder": r"D:\Nextcloud\Videos\ScreenRecordings\ToTranscribe",
    "transcribed_folder": r"D:\Nextcloud\Videos\ScreenRecordings\Transcribed",
    "google_credentials_path": "credentials.json",
    "google_token_path": "token.json",
    "video_extensions": [".mp4", ".mkv", ".mov", ".avi", ".flv", ".wmv"],
    "file_lock_check_delay": 2,  # seconds
    "file_lock_check_attempts": 5,
    "log_level": "INFO",
    "enable_logging": True,
    "log_file": "logs/auto_renamer.log",
    "dry_run": False,  # Set to True to test without actually renaming files
    "timezone_offset_hours": 3,  # Local timezone offset from UTC (e.g., 3 for GMT+3)
    "enable_upload": True,  # Enable uploading videos to transcription service
    "enable_speaker_identification": False,  # Enable automatic speaker identification using AI
    "api_base_url": "http://localhost:8080",
    "api_key": "FXlyaUoaTTYgR5fr1SDQGp8JKSAKgcF3",
    "google_sheets_id": "",
    "google_sheets_meeting_tab": "Meeting_Logs",
    "google_sheets_project_tab": "Project_Config",
    "drive_transcript_folder_id": "",
    "openrouter_max_tokens": 80000,
    "openrouter_api_key": "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",
    "openrouter_model": "google/gemini-2.5-flash-lite",
    "telegram_bot_token": "8251779884:AAGLq3w8Vker8N3HrYegTBVg92lClpm07ug",
    "telegram_chat_id": "376661128",
}

class Config:
    """Configuration handler"""
    
    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        self.config = self._load_config()
    
    def _load_config(self):
        """Load configuration from file or use defaults"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    user_config = json.load(f)
                # Merge with defaults
                config = {**DEFAULT_CONFIG, **user_config}
                return config
            except Exception as e:
                print(f"Error loading config file: {e}. Using defaults.")
                return DEFAULT_CONFIG.copy()
        else:
            # Create default config file
            self._save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG.copy()
    
    def _save_config(self, config):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Error saving config file: {e}")
    
    def get(self, key, default=None):
        """Get a configuration value"""
        return self.config.get(key, default)
    
    def set(self, key, value):
        """Set a configuration value"""
        self.config[key] = value
        self._save_config(self.config)
    
    def validate(self):
        """Validate configuration"""
        watch_folder = self.get("watch_folder")
        if not os.path.exists(watch_folder):
            raise ValueError(f"Watch folder does not exist: {watch_folder}")
        
        if not os.path.isdir(watch_folder):
            raise ValueError(f"Watch path is not a directory: {watch_folder}")
        
        to_transcribe_folder = self.get("to_transcribe_folder")
        if not os.path.exists(to_transcribe_folder):
            raise ValueError(f"To transcribe folder does not exist: {to_transcribe_folder}")
        
        if not os.path.isdir(to_transcribe_folder):
            raise ValueError(f"To transcribe path is not a directory: {to_transcribe_folder}")
        
        transcribed_folder = self.get("transcribed_folder")
        if not os.path.exists(transcribed_folder):
            raise ValueError(f"Transcribed folder does not exist: {transcribed_folder}")
        
        if not os.path.isdir(transcribed_folder):
            raise ValueError(f"Transcribed path is not a directory: {transcribed_folder}")
        
        # Validate API settings if upload is enabled
        if self.get("enable_upload"):
            if not self.get("api_base_url"):
                raise ValueError("API base URL is required when upload is enabled")
            if not self.get("api_key"):
                raise ValueError("API key is required when upload is enabled")
        
        return True

# Global config instance
config = Config()
