#!/usr/bin/env python3
"""
Auto-Meeting Video Renamer
Main application entry point

This script monitors a folder for new video recordings and automatically
renames them based on the current Google Calendar meeting title.
"""

import sys
import os
import logging
import signal
import time
import socket
import threading
from datetime import datetime, timedelta
try:
    from setproctitle import setproctitle
except ImportError:
    setproctitle = None
from pathlib import Path
import requests

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from logger import setup_logging
from config.config import config
from google_calendar_handler import GoogleCalendarHandler
from file_monitor import FileMonitor
from file_renamer import FileRenamer
from video_uploader import VideoUploader
from http_client import request_json, request_text
from sheets_drive_handler import SheetsDriveHandler
from meeting_log_queue import MeetingLogQueue
from callback_persistence import CallbackPersistence
from system_tray import SystemTrayIcon

logger = logging.getLogger(__name__)

class AutoMeetingVideoRenamer:
    """Main application class"""
    
    def __init__(self):
        if setproctitle:
            setproctitle("AutoMeetingVideoRenamer")
        self.config = config
        self.monitor = None
        self.calendar = None
        self.uploader = VideoUploader(self.config)
        self.uploader.main_app = self # Allow uploader to access callback_map
        self.running = False
        
        self.tray = SystemTrayIcon(on_quit_callback=self.shutdown)
        self.tray.start()
        self.tray.update_status("Initializing...", "yellow")
        
        # Send startup notification
        self.uploader._send_telegram_notification("🚀 Auto-Meeting Video Renamer started and monitoring folders...")
        
        self.pending_files = []  # Queue for files detected while offline
        self.internet_available = False
        
        self.callback_persistence = CallbackPersistence()
        self.callback_map = self.callback_persistence.load() # Map short IDs to full data for Telegram buttons
        self.user_states = {} # Track user states for ForceReply (e.g., renaming speaker)
        self.active_mappings = {} # Track all speaker renames per job_id: {job_id: {orig: custom}}
        self.initial_speaker_mappings = {} # Track AI-detected names per job_id

        self.sheets_handler = SheetsDriveHandler(
            self.config.get("google_credentials_path"),
            self.config.get("google_token_path")
        )
        self.meeting_queue = MeetingLogQueue()
    
    @staticmethod
    def check_internet_connection(timeout=5):
        """
        Check if internet connection is available
        
        Args:
            timeout: Timeout in seconds for the connection check
        
        Returns:
            bool: True if internet is available, False otherwise
        """
        try:
            # Try to connect to Google's DNS server
            socket.create_connection(("8.8.8.8", 53), timeout=timeout)
            return True
        except (socket.timeout, socket.error):
            return False
    
    def wait_for_internet(self, check_interval=10):
        """
        Wait for internet connection to become available
        
        Args:
            check_interval: Seconds to wait between connection checks
        """
        logger.warning("No internet connection detected. Waiting for internet...")
        
        while self.running:
            if self.check_internet_connection():
                logger.info("✓ Internet connection restored!")
                self.internet_available = True
                self.tray.update_status("Monitoring (Online)", "green")
                return True
            
            logger.debug(f"Still waiting for internet... (checking again in {check_interval}s)")
            time.sleep(check_interval)
        
        return False
    
    def initialize(self):
        """Initialize the application"""
        logger.info("=" * 50)
        logger.info("Auto-Meeting Video Renamer - Initializing")
        logger.info("=" * 50)
        
        # Telegram polling is handled by _handle_telegram_updates in run()
        
        # Validate configuration
        try:
            self.config.validate()
            logger.info("Configuration validated successfully")
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            return False
        
        # Initialize file monitor first (doesn't require internet)
        try:
            watch_folder = self.config.get("watch_folder")
            video_extensions = self.config.get("video_extensions")
            
            self.monitor = FileMonitor(
                watch_folder,
                video_extensions,
                self.on_video_created
            )
            logger.info(f"File monitor initialized for: {watch_folder}")
        except Exception as e:
            logger.error(f"Failed to initialize file monitor: {e}")
            return False
        
        # Initialize Google Calendar handler (requires internet)
        # Keep trying until internet is available
        while self.running:
            try:
                # Check internet first
                if not self.check_internet_connection():
                    logger.warning("No internet connection. Waiting for internet before authenticating with Google Calendar...")
                    if not self.wait_for_internet():
                        return False
                
                creds_path = self.config.get("google_credentials_path")
                token_path = self.config.get("google_token_path")
                
                self.calendar = GoogleCalendarHandler(creds_path, token_path)
                self.calendar.authenticate()
                logger.info("✓ Google Calendar authenticated successfully")
                self.internet_available = True
                break
            
            except Exception as e:
                logger.error(f"Failed to authenticate with Google Calendar: {e}")
                logger.error("Please ensure credentials.json is in the project root")
                
                # If it's a network error, wait for internet
                if "network" in str(e).lower() or "connection" in str(e).lower():
                    if not self.wait_for_internet():
                        return False
                else:
                    # For other errors, return False
                    return False
        
        return True

    def _initialize_sheets_tabs(self):
        sheet_id = self.config.get("google_sheets_id")
        if not sheet_id:
            return
        meeting_tab = self.config.get("google_sheets_meeting_tab", "Meeting_Logs")
        project_tab = self.config.get("google_sheets_project_tab", "Project_Config")
        type_tab = self.config.get("google_sheets_type_tab", "Meeting_Types")
        try:
            self.sheets_handler.ensure_tabs_and_headers(sheet_id, meeting_tab, project_tab, type_tab)
        except Exception as e:
            logger.error(f"Failed to ensure Sheets tabs/headers: {e}")
    
    def on_video_created(self, file_path):
        """
        Callback when a new video file is created
        
        Args:
            file_path: Path to the newly created video file
        """
        logger.info(f"Processing video file: {file_path}")

        if not self._is_file_ready(file_path):
            return

        if self._queue_if_offline(file_path):
            return

        filename = os.path.basename(file_path)
        dt, timestamp_str = FileRenamer.extract_timestamp_from_filename(filename)
        if not dt or not timestamp_str:
            logger.warning(f"Could not process file {file_path} automatically.")
            return

        meetings = self._get_meetings_for_timestamp(dt)
        if not meetings:
            self._notify_no_meeting(file_path, filename)
            return

        if len(meetings) > 1:
            self._prompt_meeting_selection(file_path, filename, meetings)
            return

        meeting_title = meetings[0].get('summary', 'Unknown')
        meeting_start = meetings[0].get('start', {}).get('dateTime') or meetings[0].get('start', {}).get('date')
        logger.info(f"Found meeting: {meeting_title}")
        self._rename_with_title(file_path, meeting_title, timestamp_str, meeting_start)

    def _is_file_ready(self, file_path):
        file_lock_delay = self.config.get("file_lock_check_delay", 2)
        file_lock_attempts = self.config.get("file_lock_check_attempts", 5)
        if not FileRenamer.is_file_ready(file_path, file_lock_delay, file_lock_attempts):
            logger.warning(f"File not ready after checks, skipping: {file_path}")
            return False
        return True

    def _queue_if_offline(self, file_path):
        if not self.internet_available:
            logger.warning(f"Internet not available. Queueing file for later processing: {file_path}")
            if file_path not in self.pending_files:
                self.pending_files.append(file_path)
            return True
        return False

    def _get_meetings_for_timestamp(self, dt):
        timezone_offset = self.config.get("timezone_offset_hours", 0)
        dt_utc = dt - timedelta(hours=timezone_offset)
        return self.calendar.get_meetings_at_time(dt_utc)

    def _notify_no_meeting(self, file_path, filename):
        logger.warning(f"No meetings found for {filename}. Sending Telegram notification.")
        cb_id = f"retry_{int(time.time())}"
        self.callback_map[cb_id] = {"action": "retry", "file_path": file_path}
        cancel_id = f"skip_{int(time.time())}"
        self.callback_map[cancel_id] = {"action": "skip", "file_path": file_path}
        self.callback_persistence.save(self.callback_map)

        self.uploader._send_telegram_notification(
            f"❓ No meeting found for: {filename}\n\nPlease add it to Google Calendar and click Retry.",
            reply_markup={
                "inline_keyboard": [[
                    {"text": "🔄 Retry", "callback_data": cb_id},
                    {"text": "❌ Cancel", "callback_data": cancel_id}
                ]]
            }
        )

    def _prompt_meeting_selection(self, file_path, filename, meetings):
        logger.info(f"Multiple meetings found for {filename}. Asking user to select via Telegram.")
        buttons = []
        for i, meeting in enumerate(meetings[:5]):
            title = meeting.get('summary', 'Unknown')
            cb_id = f"sel_{int(time.time())}_{i}"
            self.callback_map[cb_id] = {"action": "select", "title": title, "file_path": file_path}
            buttons.append([{"text": title, "callback_data": cb_id}])

        cancel_id = f"skip_{int(time.time())}"
        self.callback_map[cancel_id] = {"action": "skip", "file_path": file_path}
        self.callback_persistence.save(self.callback_map)
        buttons.append([{"text": "❌ Cancel", "callback_data": cancel_id}])

        self.uploader._send_telegram_notification(
            f"📂 Multiple meetings found for: {filename}\nWhich one should I use?",
            reply_markup={"inline_keyboard": buttons}
        )

    def _rename_with_title(self, file_path, meeting_title, timestamp_str, meeting_time=None):
        dry_run = self.config.get("dry_run", False)
        new_path = FileRenamer.generate_new_filename_from_timestamp(
            meeting_title,
            file_path,
            timestamp_str,
            dry_run
        )

        if new_path:
            if FileRenamer.rename_file(file_path, new_path, dry_run):
                result = {
                    'success': True,
                    'new_path': new_path,
                    'meeting_title': meeting_title,
                    'meeting_time': meeting_time or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'message': f"Successfully renamed to {os.path.basename(new_path)}"
                }
                self.handle_successful_rename(result, file_path)
            else:
                logger.error(f"Failed to rename file: {file_path}")
    
    def process_existing_files(self):
        """Process all existing video files in the watch folder"""
        watch_folder = self.config.get("watch_folder")
        video_extensions = self.config.get("video_extensions", [])
        
        if not os.path.exists(watch_folder):
            logger.warning(f"Watch folder does not exist: {watch_folder}")
            return
        
        logger.info("=" * 50)
        logger.info("Processing existing files in watch folder...")
        logger.info("=" * 50)
        
        # Get all video files in the watch folder
        video_files = []
        for ext in video_extensions:
            video_files.extend(Path(watch_folder).glob(f"*{ext}"))
        
        if not video_files:
            logger.info("No existing video files found in watch folder")
            return
        
        logger.info(f"Found {len(video_files)} existing video file(s) to process")
        
        # Process each file
        for video_file in sorted(video_files):
            try:
                logger.info(f"Processing existing file: {video_file}")
                self.on_video_created(str(video_file))
                # Small delay between files to avoid overwhelming the API
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error processing file {video_file}: {e}", exc_info=True)
        
        logger.info("=" * 50)
        logger.info("Finished processing existing files")
        logger.info("=" * 50)
    
    def process_pending_files(self):
        """Process any files that were queued while internet was unavailable"""
        if not self.pending_files:
            return
        
        logger.info("=" * 50)
        logger.info(f"Processing {len(self.pending_files)} pending file(s) from offline period...")
        logger.info("=" * 50)
        
        pending_copy = self.pending_files.copy()
        self.pending_files.clear()
        
        for file_path in pending_copy:
            try:
                if os.path.exists(file_path):
                    logger.info(f"Processing pending file: {file_path}")
                    self.on_video_created(file_path)
                    time.sleep(1)
                else:
                    logger.warning(f"Pending file no longer exists: {file_path}")
            except Exception as e:
                logger.error(f"Error processing pending file {file_path}: {e}", exc_info=True)
        
        logger.info("=" * 50)
        logger.info("Finished processing pending files")
        logger.info("=" * 50)
    
    def _handle_telegram_updates(self):
        """Poll Telegram for button clicks"""
        token = self.config.get("telegram_bot_token")
        if not token:
            return
            
        last_update_id = 0
        logger.info("Telegram update poller started")
        
        while self.running:
            try:
                url = f"https://api.telegram.org/bot{token}/getUpdates"
                params = {"offset": last_update_id + 1, "timeout": 30}
                # Use a slightly longer timeout for the request than the API timeout
                response, payload = request_json("GET", url, params=params, timeout=40)
                
                if response and response.status_code == 200 and payload:
                    updates = payload.get("result", [])
                    for update in updates:
                        last_update_id = update["update_id"]
                        
                        if "callback_query" in update:
                            self._process_callback(update["callback_query"])
                        elif "message" in update and "text" in update["message"]:
                            self.handle_telegram_message(update["message"])
                elif response and response.status_code == 409:
                    logger.warning("Telegram: Another instance of the bot is running. Waiting 10s...")
                    time.sleep(10)
                elif response:
                    logger.error(f"Telegram API error: {response.status_code}")
                    time.sleep(5)
                else:
                    # If response is None, it means request_json caught an exception
                    # and already logged it. We just wait before retrying.
                    time.sleep(5)
                    
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                # These are common during long-polling, log as debug/warning instead of error
                logger.debug(f"Telegram connection hiccup (expected during long-polling): {str(e)}")
                time.sleep(2) # Short wait before retrying
            except Exception as e:
                logger.error(f"Unexpected error polling Telegram: {str(e)}")
                time.sleep(5)

    def _process_callback(self, callback):
        data = callback["data"]
        chat_id = callback["message"]["chat"]["id"]
        message_id = callback["message"]["message_id"]
        token = self.config.get("telegram_bot_token")
        
        logger.info(f"Received Telegram callback: {data}")
        
        # Answer callback to remove loading state
        request_json(
            "POST",
            f"https://api.telegram.org/bot{token}/answerCallbackQuery",
            json_body={"callback_query_id": callback["id"]}
        )

        # Look up full data from short ID
        cb_data = self.callback_map.get(data)
        if not cb_data:
            # Try reloading from disk in case it was updated by another process or just restarted
            self.callback_map = self.callback_persistence.load()
            cb_data = self.callback_map.get(data)
            
        if not cb_data:
            logger.warning(f"Unknown or expired callback ID: {data}. Current map keys: {list(self.callback_map.keys())}")
            self.uploader._send_telegram_notification("⚠️ This button has expired or the app was restarted. Please try again with a new file.")
            return

        if cb_data["action"] == "select":
            meeting_title = cb_data["title"]
            file_path = cb_data["file_path"]
            logger.info(f"User selected meeting via Telegram: {meeting_title} for {file_path}")
            self.uploader._send_telegram_notification(f"✅ Selected: {meeting_title}. Processing...")
            
            # Remove buttons from the original message to show it's processed
            request_json(
                "POST",
                f"https://api.telegram.org/bot{token}/editMessageReplyMarkup",
                json_body={"chat_id": chat_id, "message_id": message_id, "reply_markup": {"inline_keyboard": []}}
            )
            
            threading.Thread(target=self._process_file_with_title, args=(file_path, meeting_title)).start()
            
        elif cb_data["action"] == "retry":
            file_path = cb_data["file_path"]
            logger.info(f"User requested retry via Telegram for: {file_path}")
            self.uploader._send_telegram_notification("🔄 Retrying calendar lookup...")
            
            # Remove buttons
            request_json(
                "POST",
                f"https://api.telegram.org/bot{token}/editMessageReplyMarkup",
                json_body={"chat_id": chat_id, "message_id": message_id, "reply_markup": {"inline_keyboard": []}}
            )
            
            threading.Thread(target=self.on_video_created, args=(file_path,)).start()

        elif cb_data["action"] == "skip":
            file_path = cb_data.get("file_path")
            logger.info(f"User canceled meeting selection for: {file_path}")

            # Remove buttons
            request_json(
                "POST",
                f"https://api.telegram.org/bot{token}/editMessageReplyMarkup",
                json_body={"chat_id": chat_id, "message_id": message_id, "reply_markup": {"inline_keyboard": []}}
            )

            self.uploader._send_telegram_notification(
                f"❌ Canceled for: {os.path.basename(file_path) if file_path else 'Unknown'}"
            )

        elif cb_data["action"] == "cancel":
            job_id = cb_data.get("job_id")
            file_path = cb_data.get("file_path")
            logger.info(f"User requested cancellation for job {job_id}")
            
            # Remove buttons
            request_json(
                "POST",
                f"https://api.telegram.org/bot{token}/editMessageReplyMarkup",
                json_body={"chat_id": chat_id, "message_id": message_id, "reply_markup": {"inline_keyboard": []}}
            )
            
            if job_id:
                # Attempt to stop the job on the server
                try:
                    url = f"{self.uploader.base_url}/api/v1/transcription/{job_id}/cancel"
                    headers = {"X-API-Key": self.uploader.api_key}
                    request_text("POST", url, headers=headers, timeout=10)
                    logger.info(f"Sent cancel request for job {job_id}")
                except Exception as e:
                    logger.error(f"Failed to send cancel request: {e}")
            
            self.uploader._send_telegram_notification(f"🛑 Process stopped for: {os.path.basename(file_path) if file_path else 'Unknown'}")

        elif cb_data["action"] == "assign_speaker":
            job_id = cb_data["job_id"]
            speaker_id = cb_data["speaker_id"]
            file_name = cb_data["file_name"]
            current_name = cb_data.get("current_name", speaker_id)
            
            # Set state for this user
            self.user_states[chat_id] = {
                "state": "awaiting_name",
                "job_id": job_id,
                "speaker_id": speaker_id,
                "file_name": file_name,
                "current_name": current_name,
                "all_speakers": cb_data.get("all_speakers", [])
            }

            # Ask for the new name using ForceReply
            self.uploader._send_telegram_notification(
                f"What is the real name for **{speaker_id}** (currently '{current_name}')?",
                reply_markup={"force_reply": True, "selective": True}
            )

        elif cb_data["action"] == "confirm_rename":
            job_id = cb_data["job_id"]
            speaker_id = cb_data["speaker_id"]
            new_name = cb_data["new_name"]
            
            # Persist the mapping in the session
            if job_id not in self.active_mappings:
                self.active_mappings[job_id] = {}
            self.active_mappings[job_id][speaker_id] = new_name

            # UI Cleanup: Edit the confirmation message
            request_json(
                "POST",
                f"https://api.telegram.org/bot{token}/editMessageText",
                json_body={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": f"✅ Confirmed: Updated **{speaker_id}** to **{new_name}**"
                }
            )
            
            # Update Scriberr with ALL current mappings for this job
            success = self.uploader._update_scriberr_speakers(job_id, self.active_mappings[job_id])
            
            if not success:
                self.uploader._send_telegram_notification(f"❌ Failed to update speaker for job {job_id}")
            else:
                # REFRESH MENU: Show the list again so user can continue editing
                all_speakers = cb_data.get("all_speakers", [])
                file_name = cb_data.get("file_name", "Meeting")
                dummy_transcript = {"title": file_name}
                self.uploader._offer_manual_speaker_assignment(job_id, all_speakers, dummy_transcript)

        elif cb_data["action"] == "offer_swap":
            job_id = cb_data["job_id"]
            speakers = cb_data["speakers"]
            display_map = cb_data["display_map"]
            file_name = cb_data["file_name"]
            
            # Create buttons for each pair
            keyboard = []
            import itertools
            for s1, s2 in itertools.combinations(speakers, 2):
                name1 = display_map.get(s1, s1)
                name2 = display_map.get(s2, s2)
                cb_id = f"swp_{int(time.time())}_{s1}_{s2}"
                self.callback_map[cb_id] = {
                    "action": "confirm_swap",
                    "job_id": job_id,
                    "s1": s1,
                    "s2": s2,
                    "name1": name1,
                    "name2": name2,
                    "all_speakers": speakers,  # Pass the full list to restore menu later
                    "file_name": file_name     # Pass filename to restore menu later
                }
                keyboard.append([{"text": f"🔄 {name1} ↔️ {name2}", "callback_data": cb_id}])
            
            self.uploader._send_telegram_notification(
                f"Select two speakers to swap names for {file_name}:",
                reply_markup={"inline_keyboard": keyboard}
            )

        elif cb_data["action"] == "confirm_swap":
            job_id = cb_data["job_id"]
            s1, s2 = cb_data["s1"], cb_data["s2"]
            name1, name2 = cb_data["name1"], cb_data["name2"]
            
            # Persist the swapped mappings
            if job_id not in self.active_mappings:
                self.active_mappings[job_id] = {}
            self.active_mappings[job_id][s1] = name2
            self.active_mappings[job_id][s2] = name1

            # UI Cleanup: Edit the confirmation message
            request_json(
                "POST",
                f"https://api.telegram.org/bot{token}/editMessageText",
                json_body={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": f"✅ Swapped names: **{s1}** is now **{name2}**, **{s2}** is now **{name1}**"
                }
            )
            
            # Update Scriberr with ALL current mappings for this job
            success = self.uploader._update_scriberr_speakers(job_id, self.active_mappings[job_id])
            
            if not success:
                self.uploader._send_telegram_notification(f"❌ Failed to swap speakers for job {job_id}")
            else:
                # REFRESH MENU: Show the list again so user can continue editing or finalize
                all_speakers = cb_data.get("all_speakers", [])
                file_name = cb_data.get("file_name", "Meeting")
                # Create a dummy transcript data object just to pass the title
                dummy_transcript = {"title": file_name}
                
                # Re-trigger the menu
                self.uploader._offer_manual_speaker_assignment(job_id, all_speakers, dummy_transcript)

        elif cb_data["action"] == "speaker_assignment_done":
            job_id = cb_data["job_id"]
            file_name = cb_data["file_name"]
            transcript_data = cb_data.get("transcript_data")
            
            # UI Cleanup: Replace the button menu with a processing message
            request_json(
                "POST",
                f"https://api.telegram.org/bot{token}/editMessageText",
                json_body={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": f"⏳ Processing final transcript for {file_name}..."
                }
            )
            
            # Ensure ALL mappings (AI + Manual) are pushed to Scriberr one last time
            final_mappings = {}
            if job_id in self.initial_speaker_mappings:
                final_mappings.update(self.initial_speaker_mappings[job_id])
            if job_id in self.active_mappings:
                final_mappings.update(self.active_mappings[job_id])
            
            if final_mappings:
                logger.info(f"Applying final speaker mappings for job {job_id} before finalization")
                self.uploader._update_scriberr_speakers(job_id, final_mappings)
                time.sleep(1) # Give Scriberr a moment to process

            # Use local session data to show the final summary
            if job_id in self.active_mappings:
                table_lines = [f"📊 **Final Speaker Mapping for {file_name}:**"]
                for orig, custom in self.active_mappings[job_id].items():
                    table_lines.append(f"• {orig} ➔ **{custom}**")
                self.uploader._send_telegram_notification("\n".join(table_lines))

            self.uploader._send_telegram_notification(f"✅ Finalizing transcript for {file_name}...")
            
            # Trigger transcript re-download and processing with finalize=True
            if transcript_data:
                # We need to re-fetch the transcript from Scriberr to get updated names
                threading.Thread(target=self.uploader._download_transcript, args=(job_id, "manual_refresh", transcript_data, True)).start()
            else:
                self.uploader._send_telegram_notification("⚠️ Could not refresh transcript automatically. Please check Scriberr.")

    def _process_file_with_title(self, file_path, meeting_title):
        """Process file when title is manually selected"""
        filename = os.path.basename(file_path)
        _, timestamp_str = FileRenamer.extract_timestamp_from_filename(filename)
        
        dry_run = self.config.get("dry_run", False)
        new_path = FileRenamer.generate_new_filename_from_timestamp(
            meeting_title, file_path, timestamp_str, dry_run
        )
        
        if FileRenamer.rename_file(file_path, new_path, dry_run):
            result = {
                'success': True,
                'new_path': new_path,
                'message': f"Manually renamed to {meeting_title}"
            }
            self.handle_successful_rename(result, file_path)

    def monitor_internet_connection(self):
        """Monitor internet connection and handle reconnection"""
        check_interval = 30  # Check every 30 seconds
        
        while self.running:
            try:
                current_status = self.check_internet_connection()
                
                if current_status and not self.internet_available:
                    # Internet just came back online
                    logger.info("✓ Internet connection detected!")
                    self.internet_available = True
                    self.tray.update_status("Monitoring (Online)", "green")
                    
                    # Process any pending files
                    if self.pending_files:
                        self.process_pending_files()

                    # Flush any queued meeting logs
                    self.flush_meeting_queue()
                
                elif not current_status and self.internet_available:
                    # Internet just went offline
                    logger.warning("✗ Internet connection lost!")
                    self.internet_available = False
                    self.tray.update_status("Offline (Queuing)", "orange")
                
                time.sleep(check_interval)
            
            except Exception as e:
                logger.error(f"Error monitoring internet connection: {e}")
                time.sleep(check_interval)
    
    def run(self):
        """Run the application"""
        self.running = True
        
        if not self.initialize():
            logger.error("Failed to initialize application")
            return False

        self._initialize_sheets_tabs()
        
        try:
            # Process any existing files first
            self.process_existing_files()

            # Flush any queued meeting logs on startup
            self.flush_meeting_queue()
            
            # Start file monitoring
            self.monitor.start()
            
            # Start internet monitoring in a separate thread
            import threading
            internet_monitor_thread = threading.Thread(
                target=self.monitor_internet_connection,
                daemon=True
            )
            internet_monitor_thread.start()

            # Start Telegram update poller
            telegram_thread = threading.Thread(
                target=self._handle_telegram_updates,
                daemon=True
            )
            telegram_thread.start()
            
            logger.info("Auto-Meeting Video Renamer is running...")
            logger.info("Press Ctrl+C to exit")
            
            # Keep the application running
            while self.running:
                time.sleep(1)
        
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
        finally:
            self.shutdown()
        
        return True
    
    def shutdown(self):
        """Shutdown the application"""
        logger.info("Shutting down application...")
        
        if self.monitor:
            self.monitor.stop()
        
        if self.calendar:
            self.calendar.close()
        
        self.running = False
        logger.info("Application shutdown complete")
    
    def run_telegram_bot(self):
        """Listen for Telegram callback queries"""
        token = self.config.get("telegram_bot_token")
        if not token:
            logger.warning("Telegram bot token not configured, interactive features disabled")
            return

        offset = 0
        while self.running:
            try:
                url = f"https://api.telegram.org/bot{token}/getUpdates?offset={offset}&timeout=30"
                response = requests.get(url, timeout=35)
                if response.status_code == 200:
                    updates = response.json().get("result", [])
                    for update in updates:
                        offset = update["update_id"] + 1
                        if "callback_query" in update:
                            self.handle_telegram_callback(update["callback_query"])
                        elif "message" in update and "text" in update["message"]:
                            self.handle_telegram_message(update["message"])
            except Exception as e:
                logger.error(f"Error in Telegram bot listener: {e}")
                time.sleep(5)

    def handle_telegram_message(self, message):
        """Handle text messages from Telegram"""
        text = message.get("text", "")
        chat_id = message["chat"]["id"]
        
        # Check if user is in a state
        user_state = self.user_states.get(chat_id)
        if user_state and user_state["state"] == "awaiting_name":
            job_id = user_state["job_id"]
            speaker_id = user_state["speaker_id"]
            new_name = text.strip()
            
            logger.info(f"State-based speaker rename: Job {job_id}, {speaker_id} -> {new_name}")
            
            # Clear state
            del self.user_states[chat_id]
            
            # Requirement 3: Confirmation Prompt
            cb_id_yes = f"conf_y_{int(time.time())}"
            cb_id_no = f"conf_n_{int(time.time())}"
            
            self.callback_map[cb_id_yes] = {
                "action": "confirm_rename",
                "job_id": job_id,
                "speaker_id": speaker_id,
                "new_name": new_name,
                "file_name": user_state.get("file_name"),
                "all_speakers": user_state.get("all_speakers", [])
            }
            self.callback_map[cb_id_no] = {"action": "skip", "file_path": "rename_cancel"}
            self.callback_persistence.save(self.callback_map)

            self.uploader._send_telegram_notification(
                f"I will update **{speaker_id}** to **{new_name}**. Is this correct?",
                reply_markup={
                    "inline_keyboard": [[
                        {"text": "✅ Yes", "callback_data": cb_id_yes},
                        {"text": "❌ No", "callback_data": cb_id_no}
                    ]]
                }
            )
            return

        if text.startswith("/name "):
            # Format: /name job_id speaker_id Real Name
            parts = text.split(" ", 3)
            if len(parts) >= 4:
                job_id = parts[1]
                speaker_id = parts[2]
                new_name = parts[3]
                
                logger.info(f"Manual speaker rename request: Job {job_id}, {speaker_id} -> {new_name}")
                
                # Update session storage
                if job_id not in self.active_mappings:
                    self.active_mappings[job_id] = {}
                self.active_mappings[job_id][speaker_id] = new_name
                
                # Send the COMPLETE list of mappings
                success = self.uploader._update_scriberr_speakers(job_id, self.active_mappings[job_id])
                
                if success:
                    self.uploader._send_telegram_notification(f"✅ Updated {speaker_id} to **{new_name}** for job {job_id}")
                else:
                    self.uploader._send_telegram_notification(f"❌ Failed to update speaker for job {job_id}")
            else:
                self.uploader._send_telegram_notification("⚠️ Invalid format. Use: `/name job_id speaker_id Real Name`")

    def handle_telegram_callback(self, callback_query):
        """Handle button clicks from Telegram"""
        data = callback_query.get("data", "")
        chat_id = callback_query["message"]["chat"]["id"]
        token = self.config.get("telegram_bot_token")
        
        # Answer callback to remove loading state
        requests.post(f"https://api.telegram.org/bot{token}/answerCallbackQuery", 
                     json={"callback_query_id": callback_query["id"]})

        if data.startswith("retry:"):
            file_path = data.replace("retry:", "")
            self.uploader._send_telegram_notification(f"🔄 Retrying processing for: {os.path.basename(file_path)}")
            # Run in a separate thread to not block the bot
            threading.Thread(target=self.on_video_created, args=(file_path,)).start()
            
        elif data.startswith("select:"):
            parts = data.split(":")
            meeting_id = parts[1]
            file_path = parts[2]
            
            # Fetch specific meeting
            try:
                meeting = self.calendar.service.events().get(calendarId='primary', eventId=meeting_id).execute()
                meeting_title = meeting.get('summary', 'Unknown')
                self.uploader._send_telegram_notification(f"✅ Selected meeting: {meeting_title}. Processing...")
                
                # Extract timestamp from filename
                filename = os.path.basename(file_path)
                _, timestamp_str = FileRenamer.extract_timestamp_from_filename(filename)
                
                # Manually trigger rename with this title
                dry_run = self.config.get("dry_run", False)
                new_path = FileRenamer.generate_new_filename_from_timestamp(meeting_title, file_path, timestamp_str, dry_run)
                
                if new_path and FileRenamer.rename_file(file_path, new_path, dry_run):
                    # Trigger the rest of the flow (copy, upload, etc)
                    # We simulate a successful result from rename_file_with_calendar_lookup
                    result = {
                        'success': True,
                        'new_path': new_path,
                        'meeting_title': meeting_title,
                        'meeting_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'message': 'Manual selection successful'
                    }
                    self.handle_successful_rename(result, file_path)
            except Exception as e:
                logger.error(f"Error processing manual selection: {e}")
                self.uploader._send_telegram_notification(f"❌ Error: {str(e)}")

    def handle_successful_rename(self, result, original_file_path):
        """Helper to handle the post-rename logic (copy, upload, delete)"""
        logger.info(f"✓ {result['message']}")
        new_path = result['new_path']
        output_folder = self.config.get("output_folder")
        dry_run = self.config.get("dry_run", False)
        
        if new_path and output_folder:
            filename = os.path.basename(new_path)
            destination_path = os.path.join(output_folder, filename)
            
            logger.info(f"Copying renamed file to output folder: {destination_path}")
            if FileRenamer.copy_file(new_path, destination_path, dry_run):
                logger.info(f"✓ File copied to output folder: {destination_path}")
                
                if self.config.get("enable_upload", False):
                    logger.info(f"Uploading file to transcription service: {destination_path}")
                    meeting_info = {
                        "meeting_name": result.get("meeting_title"),
                        "meeting_time": result.get("meeting_time"),
                        "video_source_link": f"file:///{destination_path}",
                    }
                    self.uploader.upload_video(destination_path, meeting_info=meeting_info)
                
                logger.info(f"Deleting renamed file from watch folder: {new_path}")
                if FileRenamer.delete_file(new_path, dry_run):
                    logger.info(f"✓ Renamed file deleted: {new_path}")
                else:
                    logger.warning(f"✗ Failed to delete renamed file: {new_path}")
            else:
                logger.warning(f"✗ Failed to copy file to output folder: {destination_path}")
        else:
            logger.warning("Output folder not configured, skipping copy operation")

    def flush_meeting_queue(self):
        items = self.meeting_queue.dequeue_all()
        if not items:
            return

        logger.info(f"Flushing {len(items)} queued meeting log item(s)")
        for item in items:
            try:
                self._publish_meeting_log(item)
            except Exception as e:
                logger.error(f"Failed to publish queued item: {e}")
                self.meeting_queue.enqueue(item)

    def _publish_meeting_log(self, item):
        sheet_id = self.config.get("google_sheets_id")
        meeting_tab = self.config.get("google_sheets_meeting_tab", "Meeting_Logs")

        if not sheet_id:
            logger.error("google_sheets_id is not configured")
            return

        # Обновленный порядок колонок:
        # Date | Name | Type | Speakers | Summary | Project | Video Link | Scriberr Link | Doc Link | Status
        row = [
            item.get("meeting_time", ""),
            item.get("meeting_name", ""),
            item.get("meeting_type", ""),
            item.get("speakers", ""),
            item.get("summary", ""),
            item.get("project_tag", ""),
            item.get("video_source_link", ""),
            item.get("scribber_link", ""),
            item.get("transcript_drive_link", ""),
            item.get("status", ""),
        ]
        self.sheets_handler.append_meeting_log(sheet_id, meeting_tab, row)

    def on_transcript_ready(self, job_id, original_file_path, transcript_data, transcript_path, meeting_info=None, is_final=False):
        """Called by uploader when transcript is ready."""
        if not is_final:
            logger.info(f"Transcript for job {job_id} is not final yet. Skipping Sheets logging.")
            return

        try:
            sheet_id = self.config.get("google_sheets_id")
            meeting_tab = self.config.get("google_sheets_meeting_tab", "Meeting_Logs")
            project_tab = self.config.get("google_sheets_project_tab", "Project_Config")
            drive_folder_id = self.config.get("drive_transcript_folder_id", "")

            if not sheet_id or not transcript_path:
                logger.warning("Sheet ID or transcript path missing; skipping meeting log publish")
                return

            # 1. Загрузка транскрипта (теперь создает Google Doc)
            transcript_drive_link = self.sheets_handler.upload_transcript(transcript_path, drive_folder_id)

            # Подготовка текста для AI
            full_transcript_text = self._build_full_transcript_text(transcript_data)
            trimmed_text = self._trim_transcript_for_openrouter(full_transcript_text)

            # 2. Извлечение Спикеров
            speakers = self.uploader._extract_speakers(transcript_data)
            speakers_str = ", ".join(sorted(list(speakers))) if speakers else ""

            # 3. Определение Типа Встречи (ДИНАМИЧЕСКИ ИЗ ТАБЛИЦЫ)
            type_tab = self.config.get("google_sheets_type_tab", "Meeting_Types")
            meeting_types_config = self.sheets_handler.read_meeting_types_config(sheet_id, type_tab)
            
            meeting_name = (meeting_info or {}).get("meeting_name", "")
            meeting_type = "General"
            if trimmed_text:
                if meeting_types_config:
                    types_desc = "\n".join([f"- {t[0]}: {t[1]}" for t in meeting_types_config])
                    type_prompt = (
                        "Classify this meeting into one of the following categories based on their descriptions:\n"
                        f"{types_desc}\n\n"
                        f"Meeting Name: {meeting_name}\n\n"
                        "Return ONLY the category name exactly as listed above.\n"
                        "If none match perfectly, choose the closest one.\n\n"
                        f"Transcript Start:\n{trimmed_text[:2000]}"
                    )
                else:
                    type_prompt = (
                        "Classify this meeting: Daily Standup, Sprint Planning, Retrospective, "
                        "Client Meeting, Technical Discussion, 1:1, Demo, Webinar.\n"
                        f"Meeting Name: {meeting_name}\n\n"
                        "Return ONLY the category name.\n\n"
                        f"Transcript Start:\n{trimmed_text[:2000]}"
                    )
                
                meeting_type = self.uploader._get_openrouter_response(type_prompt)
                meeting_type = str(meeting_type).strip(" .")

            # 4. Генерация Summary (кратко)
            summary = ""
            if trimmed_text:
                summary_prompt = (
                    "Summarize the following meeting transcript in 3-5 concise sentences. "
                    "Focus on key decisions, action items, and the main topic.\n\n"
                    f"Transcript:\n{trimmed_text}"
                )
                summary = self.uploader._get_openrouter_response(summary_prompt)

            # Определение проекта (существующая логика)
            projects = self.sheets_handler.read_project_config(sheet_id, project_tab)
            project_tag = self._identify_project_tag(projects, trimmed_text)

            # Подготовка данных для таблицы
            meeting_time = (meeting_info or {}).get("meeting_time", "")
            
            # Format meeting_time to M/D/YYYY HH:MM:SS with +3 TZ offset
            if meeting_time:
                try:
                    # Google Calendar returns ISO format: 2026-01-22T20:00:00+03:00 or 2026-01-22T20:00:00Z
                    # We want to ensure it's in +3 and format it as M/D/YYYY HH:MM:SS
                    from dateutil import parser
                    dt = parser.parse(meeting_time)
                    
                    # If it has timezone info, convert to +3. If not, assume it's already local or UTC.
                    # The user specifically asked for +3.
                    from datetime import timezone, timedelta
                    target_tz = timezone(timedelta(hours=3))
                    dt_target = dt.astimezone(target_tz)
                    
                    # Format: M/D/YYYY HH:MM:SS (e.g., 1/22/2026 20:00:00)
                    # %m/%d/%Y includes leading zeros (01/22/2026). 
                    # To remove leading zeros on Windows, use %#m/%#d/%Y.
                    meeting_time = dt_target.strftime("%#m/%#d/%Y %H:%M:%S")
                except Exception as e:
                    logger.error(f"Error formatting meeting_time '{meeting_time}': {e}")

            # meeting_name already extracted above
            video_source_link = (meeting_info or {}).get("video_source_link", "")
            if video_source_link:
                video_source_link = f'=HYPERLINK("{video_source_link}", "Link")'
            scribber_link = f"{self.uploader.base_url}/audio/{job_id}"

            item = {
                "meeting_time": meeting_time,
                "meeting_name": meeting_name,
                "meeting_type": meeting_type,
                "speakers": speakers_str,
                "summary": summary,
                "project_tag": project_tag,
                "video_source_link": video_source_link,
                "scribber_link": scribber_link,
                "transcript_drive_link": transcript_drive_link,
                "status": "Processed",
            }

            if not self.internet_available:
                self.meeting_queue.enqueue(item)
                return

            self._publish_meeting_log(item)
        except Exception as e:
            logger.error(f"Failed to publish meeting log: {e}")
            if meeting_info:
                item = {
                    "meeting_time": meeting_info.get("meeting_time", ""),
                    "meeting_name": meeting_info.get("meeting_name", ""),
                    "speakers": "",
                    "summary": "",
                    "project_tag": "",
                    "video_source_link": meeting_info.get("video_source_link", ""),
                    "scribber_link": f"{self.uploader.base_url}/audio/{job_id}",
                    "transcript_drive_link": "",
                    "status": "Failed",
                }
                self.meeting_queue.enqueue(item)

    def _build_full_transcript_text(self, transcript_data):
        segments = []
        if isinstance(transcript_data, dict):
            segments = self.uploader._find_segments(transcript_data) or []
        lines = []
        for segment in segments:
            speaker = segment.get("speaker", "Unknown")
            text = segment.get("text", "").strip()
            start = segment.get("start", 0.0)
            if text:
                minutes = int(start) // 60
                seconds = int(start) % 60
                lines.append(f"[{minutes:02d}:{seconds:02d}] {speaker}: {text}")
        return "\n\n".join(lines)

    def _trim_transcript_for_openrouter(self, text: str) -> str:
        max_tokens = int(self.config.get("openrouter_max_tokens", 80000))
        # Rough char limit: 4 chars per token
        max_chars = max_tokens * 4
        if len(text) <= max_chars:
            return text
        return text[:max_chars]

    def _identify_project_tag(self, projects, transcript_text):
        # Build prompt for OpenRouter
        if not projects:
            return ""

        project_lines = [f"- {name}: {keywords}" for name, keywords in projects]
        prompt = (
            "You are an expert meeting classifier. Your task is to assign the most relevant project tag "
            "to the provided transcript based on the listed projects and their context keywords.\n\n"
            "Rules:\n"
            "1. Return ONLY the exact project name.\n"
            "2. If no project clearly matches, return 'Uncategorized'.\n"
            "3. Base your decision on the technical topics and clients mentioned.\n\n"
            "Available Projects:\n" + "\n".join(project_lines) +
            "\n\nTranscript Content:\n" + transcript_text
        )

        result = self.uploader._get_openrouter_response(prompt)
        if not result:
            return ""
        
        # Basic cleanup
        tag = str(result).strip().splitlines()[0]
        
        # Validation: Ensure the tag exists in projects or is 'Uncategorized'
        project_names = {name for name, _ in projects}
        if tag in project_names or tag == "Uncategorized":
            return tag
            
        return "Uncategorized"

def signal_handler(signum, frame):
    """Handle system signals"""
    logger.info("Signal received, initiating shutdown...")
    sys.exit(0)

def main():
    """Main entry point"""
    # Setup logging
    log_file = os.path.join(PROJECT_ROOT, "logs", "auto_renamer.log")
    setup_logging(log_file)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and run application
    app = AutoMeetingVideoRenamer()
    success = app.run()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
