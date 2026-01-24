"""
File renaming logic module
"""

import os
import logging
import re
import shutil
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Pattern to match timestamps in filenames like: 2026-01-22_14-26-31
TIMESTAMP_PATTERN = r'(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})'

class FileRenamer:
    """Handles file renaming logic"""
    
    # Windows-illegal characters
    ILLEGAL_CHARS = r'[<>:"/\\|?*]'
    
    @staticmethod
    def sanitize_filename(filename):
        """
        Remove Windows-illegal characters from filename
        
        Args:
            filename: Original filename string
        
        Returns:
            str: Sanitized filename
        """
        # Replace illegal characters with underscores
        sanitized = re.sub(FileRenamer.ILLEGAL_CHARS, '_', filename)
        # Remove trailing dots and spaces (also illegal in Windows)
        sanitized = sanitized.rstrip('. ')
        return sanitized
    
    @staticmethod
    def extract_timestamp_from_filename(filename):
        """
        Extract timestamp from filename pattern like: 2026-01-22_14-26-31.mp4
        
        Args:
            filename: Filename to extract timestamp from
        
        Returns:
            tuple: (datetime object, timestamp_string) or (None, None) if not found
        """
        match = re.search(TIMESTAMP_PATTERN, filename)
        if match:
            year, month, day, hour, minute, second = map(int, match.groups())
            try:
                dt = datetime(year, month, day, hour, minute, second)
                timestamp_str = f"{year:04d}-{month:02d}-{day:02d}_{hour:02d}-{minute:02d}-{second:02d}"
                logger.info(f"Extracted timestamp from filename: {timestamp_str}")
                return dt, timestamp_str
            except ValueError as e:
                logger.warning(f"Invalid timestamp in filename: {e}")
                return None, None
        return None, None
    
    @staticmethod
    def generate_new_filename_from_timestamp(meeting_title, original_file_path, timestamp_str, dry_run=False):
        """
        Generate new filename based on meeting title and existing timestamp from file
        
        Args:
            meeting_title: Title of the meeting
            original_file_path: Path to the original file
            timestamp_str: Timestamp string extracted from original filename (format: YYYY-MM-DD_HH-MM-SS)
            dry_run: If True, don't actually rename the file
        
        Returns:
            str: New filename with full path
        """
        if not meeting_title:
            logger.warning("No meeting title provided, keeping original filename")
            return original_file_path
        
        file_path = Path(original_file_path)
        sanitized_title = FileRenamer.sanitize_filename(meeting_title)
        return FileRenamer._build_unique_filename(file_path, f"{sanitized_title}_{timestamp_str}")
    
    @staticmethod
    def generate_new_filename(meeting_title, original_file_path, dry_run=False):
        """
        Generate new filename based on meeting title
        
        Args:
            meeting_title: Title of the meeting
            original_file_path: Path to the original file
            dry_run: If True, don't actually rename the file
        
        Returns:
            str: New filename with full path
        """
        if not meeting_title:
            logger.warning("No meeting title provided, keeping original filename")
            return original_file_path
        
        file_path = Path(original_file_path)
        sanitized_title = FileRenamer.sanitize_filename(meeting_title)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        return FileRenamer._build_unique_filename(file_path, f"{sanitized_title}_{timestamp}")

    @staticmethod
    def _build_unique_filename(file_path: Path, base_name: str):
        """Build a unique filename in the same directory using a base name."""
        file_ext = file_path.suffix
        parent_dir = file_path.parent
        new_filename = f"{base_name}{file_ext}"
        new_filepath = parent_dir / new_filename

        counter = 1
        while new_filepath.exists():
            new_filename = f"{base_name}_{counter:02d}{file_ext}"
            new_filepath = parent_dir / new_filename
            counter += 1
            if counter > 100:
                logger.error("Too many duplicate filenames, unable to rename")
                return None

        logger.info(f"Generated new filename: {new_filename}")
        return str(new_filepath)
    
    @staticmethod
    def is_file_ready(file_path, check_delay=2, check_attempts=5):
        """
        Check if a file is ready to be renamed (not being written to)
        
        Args:
            file_path: Path to the file
            check_delay: Delay in seconds between checks
            check_attempts: Number of checks to perform
        
        Returns:
            bool: True if file is ready, False otherwise
        """
        import time
        
        for attempt in range(check_attempts):
            try:
                # Try to open the file exclusively
                with open(file_path, 'rb') as f:
                    f.seek(0, 2)  # Seek to end
                    file_size = f.tell()
                
                # Small delay between checks
                if attempt < check_attempts - 1:
                    time.sleep(check_delay)
                    # Verify size hasn't changed
                    with open(file_path, 'rb') as f:
                        f.seek(0, 2)
                        new_size = f.tell()
                    
                    if file_size != new_size:
                        logger.debug(f"File is still being written (size changed: {file_size} -> {new_size})")
                        continue
                
                logger.info(f"File is ready: {file_path} ({file_size} bytes)")
                return True
            
            except (IOError, OSError) as e:
                logger.debug(f"File not ready (attempt {attempt + 1}/{check_attempts}): {e}")
                if attempt < check_attempts - 1:
                    time.sleep(check_delay)
        
        logger.warning(f"File did not become ready after {check_attempts} attempts: {file_path}")
        return False
    
    @staticmethod
    def rename_file(original_path, new_path, dry_run=False):
        """
        Rename a file from original path to new path
        
        Args:
            original_path: Current file path
            new_path: New file path
            dry_run: If True, don't actually rename
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not os.path.exists(original_path):
                logger.error(f"Original file does not exist: {original_path}")
                return False
            
            if dry_run:
                logger.info(f"[DRY RUN] Would rename: {original_path} -> {new_path}")
                return True
            
            os.rename(original_path, new_path)
            logger.info(f"Successfully renamed: {original_path} -> {new_path}")
            return True
        
        except Exception as e:
            logger.error(f"Error renaming file: {e}")
            return False
    
    @staticmethod
    def copy_file(source_path, destination_path, dry_run=False):
        """
        Copy a file from source to destination
        
        Args:
            source_path: Path to the source file
            destination_path: Path to the destination file
            dry_run: If True, don't actually copy
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not os.path.exists(source_path):
                logger.error(f"Source file does not exist: {source_path}")
                return False
            
            # Ensure destination directory exists
            dest_dir = os.path.dirname(destination_path)
            if not os.path.exists(dest_dir):
                if dry_run:
                    logger.info(f"[DRY RUN] Would create directory: {dest_dir}")
                else:
                    os.makedirs(dest_dir, exist_ok=True)
                    logger.info(f"Created destination directory: {dest_dir}")
            
            if dry_run:
                logger.info(f"[DRY RUN] Would copy: {source_path} -> {destination_path}")
                return True
            
            shutil.copy2(source_path, destination_path)
            logger.info(f"Successfully copied: {source_path} -> {destination_path}")
            return True
        
        except Exception as e:
            logger.error(f"Error copying file: {e}")
            return False
    
    @staticmethod
    def delete_file(file_path, dry_run=False):
        """
        Delete a file
        
        Args:
            file_path: Path to the file to delete
            dry_run: If True, don't actually delete
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"File does not exist: {file_path}")
                return False
            
            if dry_run:
                logger.info(f"[DRY RUN] Would delete: {file_path}")
                return True
            
            os.remove(file_path)
            logger.info(f"Successfully deleted: {file_path}")
            return True
        
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False
    
    @staticmethod
    def rename_file_with_calendar_lookup(file_path, calendar_handler, config=None, dry_run=False):
        """
        Complete workflow: Extract timestamp from filename, lookup meeting on Google Calendar,
        and rename file with meeting title + original timestamp
        
        Args:
            file_path: Path to the file to rename
            calendar_handler: GoogleCalendarHandler instance for querying meetings
            config: Config object to get timezone offset (optional)
            dry_run: If True, don't actually rename
        
        Returns:
            dict: Result with keys:
                - 'success': bool indicating if rename was successful
                - 'timestamp': extracted timestamp (YYYY-MM-DD_HH-MM-SS)
                - 'meeting_title': found meeting title or None
                - 'new_path': new file path or None
                - 'message': descriptive message
        """
        filename = os.path.basename(file_path)
        
        # Step 1: Extract timestamp from filename
        dt, timestamp_str = FileRenamer.extract_timestamp_from_filename(filename)
        if not dt or not timestamp_str:
            message = f"Could not extract timestamp from filename: {filename}"
            logger.warning(message)
            return {
                'success': False,
                'timestamp': None,
                'meeting_title': None,
                'new_path': None,
                'message': message
            }
        
        # Step 2: Convert local time to UTC for Google Calendar query
        # The filename timestamp is in LOCAL time, but Google Calendar uses UTC
        timezone_offset = 0
        if config:
            timezone_offset = config.get("timezone_offset_hours", 0)
        
        # Convert local time to UTC by subtracting the offset
        dt_utc = dt - timedelta(hours=timezone_offset)
        
        logger.info(f"Local time from file: {timestamp_str}")
        logger.info(f"Timezone offset: GMT+{timezone_offset}")
        logger.info(f"Converting to UTC for calendar query: {dt_utc.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Step 3: Query Google Calendar for meeting at that UTC time
        try:
            meeting = calendar_handler.get_meeting_at_time(dt_utc)
            if not meeting:
                message = f"No meeting found at {timestamp_str} (local) / {dt_utc.strftime('%Y-%m-%d %H:%M:%S')} (UTC) for file: {filename}"
                logger.info(message)
                return {
                    'success': False,
                    'timestamp': timestamp_str,
                    'meeting_title': None,
                    'new_path': None,
                    'message': message
                }
            
            meeting_title = meeting.get('summary', 'Unknown')
            logger.info(f"Found meeting: '{meeting_title}' at {timestamp_str} (local time)")
        
        except Exception as e:
            message = f"Error querying Google Calendar: {e}"
            logger.error(message)
            return {
                'success': False,
                'timestamp': timestamp_str,
                'meeting_title': None,
                'new_path': None,
                'message': message
            }
        
        # Step 4: Generate new filename with meeting title + original timestamp
        new_path = FileRenamer.generate_new_filename_from_timestamp(
            meeting_title, 
            file_path, 
            timestamp_str, 
            dry_run
        )
        
        if not new_path:
            message = f"Failed to generate new filename for: {filename}"
            logger.error(message)
            return {
                'success': False,
                'timestamp': timestamp_str,
                'meeting_title': meeting_title,
                'new_path': None,
                'message': message
            }
        
        # Step 5: Perform the rename
        if FileRenamer.rename_file(file_path, new_path, dry_run):
            message = f"Successfully renamed '{filename}' to '{os.path.basename(new_path)}' (meeting: {meeting_title})"
            logger.info(message)
            return {
                'success': True,
                'timestamp': timestamp_str,
                'meeting_title': meeting_title,
                'new_path': new_path,
                'message': message
            }
        else:
            message = f"Failed to rename file: {filename}"
            logger.error(message)
            return {
                'success': False,
                'timestamp': timestamp_str,
                'meeting_title': meeting_title,
                'new_path': new_path,
                'message': message
            }
