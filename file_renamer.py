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

# Pattern to match timestamps in filenames:
# - 2026-01-22_14-26-31 (date with time)
# - 2026-01-22 (date only)
# - 2026-01-23T10:01:46Z (ISO 8601 format with timezone)
# - 2026-01-23T10:01:46 (ISO 8601 format without timezone)
# - 2602061401 (YYMMDDHHMM format)
# - 18_Feb_26 (DD_Mon_YY format)
TIMESTAMP_PATTERN = r'(\d{4})-(\d{2})-(\d{2})(?:[T_](\d{2}):(\d{2}):(\d{2})|_(\d{2})-(\d{2})-(\d{2}))?'
SHORT_TIMESTAMP_PATTERN = r'(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})'
DATE_MON_YY_PATTERN = r'(\d{1,2})_(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)_(\d{2})'

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
    def extract_original_timestamp_string(filename):
        """
        Extract the ORIGINAL timestamp string from filename, preserving its format.
        
        Args:
            filename: Filename to extract timestamp from
        
        Returns:
            str: Original timestamp string as it appears in filename, or None if not found
        """
        match = re.search(TIMESTAMP_PATTERN, filename)
        if match:
            # Return the matched string exactly as it appears in the filename
            return match.group(0)
        
        # Try short pattern
        match_short = re.search(SHORT_TIMESTAMP_PATTERN, filename)
        if match_short:
            return match_short.group(0)
        
        # Try DD_Mon_YY pattern
        match_mon_yy = re.search(DATE_MON_YY_PATTERN, filename, re.IGNORECASE)
        if match_mon_yy:
            return match_mon_yy.group(0)
            
        return None

    @staticmethod
    def extract_timestamp_from_filename(filename):
        """
        Extract timestamp from filename pattern like:
        - 2026-01-22_14-26-31.mp4 (date with time, hyphens)
        - 2026-01-22_DION Video.mp4 (date only)
        - Ердакова Надежда_2026-01-23T10:01:46Z.mp4 (ISO 8601 with timezone)
        - Ердакова Надежда_2026-01-23T10:01:46.mp4 (ISO 8601 without timezone)
        - Кирилл Хаустов ПСБ-2602061401.mp3 (YYMMDDHHMM)
        - Meeting_Notes_18_Feb_26.mp4 (DD_Mon_YY format)
        
        Args:
            filename: Filename to extract timestamp from
        
        Returns:
            tuple: (datetime object, timestamp_string, format_type) or (None, None, None) if not found
        """
        match = re.search(TIMESTAMP_PATTERN, filename)
        if match:
            groups = match.groups()
            year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
            
            # Check for ISO 8601 format with colons (groups 3, 4, 5)
            if groups[3] is not None and groups[4] is not None and groups[5] is not None:
                hour, minute, second = int(groups[3]), int(groups[4]), int(groups[5])
                format_type = "ISO 8601"
            # Check for underscore format with hyphens (groups 6, 7, 8)
            elif groups[6] is not None and groups[7] is not None and groups[8] is not None:
                hour, minute, second = int(groups[6]), int(groups[7]), int(groups[8])
                format_type = "underscore with hyphens"
            else:
                # No time component, use midnight (00:00:00)
                hour, minute, second = 0, 0, 0
                format_type = "date-only"
            
            try:
                dt = datetime(year, month, day, hour, minute, second)
                timestamp_str = f"{year:04d}-{month:02d}-{day:02d}_{hour:02d}-{minute:02d}-{second:02d}"
                logger.info(f"Extracted timestamp from filename: {timestamp_str} ({format_type} format)")
                return dt, timestamp_str, format_type
            except ValueError as e:
                logger.warning(f"Invalid timestamp in filename: {e}")
                return None, None, None

        # Try short pattern (YYMMDDHHMM)
        match_short = re.search(SHORT_TIMESTAMP_PATTERN, filename)
        if match_short:
            groups = match_short.groups()
            try:
                # Assume 20xx for the year
                year = 2000 + int(groups[0])
                month, day = int(groups[1]), int(groups[2])
                hour, minute = int(groups[3]), int(groups[4])
                second = 0
                
                dt = datetime(year, month, day, hour, minute, second)
                timestamp_str = f"{year:04d}-{month:02d}-{day:02d}_{hour:02d}-{minute:02d}-{second:02d}"
                logger.info(f"Extracted short timestamp from filename: {timestamp_str} (YYMMDDHHMM format)")
                return dt, timestamp_str, "YYMMDDHHMM"
            except ValueError as e:
                logger.warning(f"Invalid short timestamp in filename: {e}")
                return None, None, None

        # Try DD_Mon_YY pattern (e.g., 18_Feb_26)
        match_mon_yy = re.search(DATE_MON_YY_PATTERN, filename, re.IGNORECASE)
        if match_mon_yy:
            groups = match_mon_yy.groups()
            try:
                day = int(groups[0])
                month_name = groups[1]
                year = 2000 + int(groups[2])
                
                # Convert month name to month number
                month_map = {
                    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
                }
                month = month_map.get(month_name.lower())
                if not month:
                    logger.warning(f"Unknown month name in filename: {month_name}")
                    return None, None, None
                
                hour, minute, second = 0, 0, 0  # No time component in this format
                dt = datetime(year, month, day, hour, minute, second)
                timestamp_str = f"{year:04d}-{month:02d}-{day:02d}_{hour:02d}-{minute:02d}-{second:02d}"
                logger.info(f"Extracted DD_Mon_YY timestamp from filename: {timestamp_str} (DD_Mon_YY format)")
                return dt, timestamp_str, "DD_Mon_YY"
            except ValueError as e:
                logger.warning(f"Invalid DD_Mon_YY timestamp in filename: {e}")
                return None, None, None

        return None, None, None
    
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
    def generate_new_filename_preserve_timestamp_format(meeting_title, original_file_path, dry_run=False):
        """
        Generate new filename based on meeting title while preserving the ORIGINAL timestamp format.
        This extracts the timestamp exactly as it appears in the original filename.
        
        Args:
            meeting_title: Title of the meeting
            original_file_path: Path to the original file
            dry_run: If True, don't actually rename the file
        
        Returns:
            str: New filename with full path, or None if timestamp cannot be extracted
        """
        if not meeting_title:
            logger.warning("No meeting title provided, keeping original filename")
            return original_file_path
        
        filename = os.path.basename(original_file_path)
        original_timestamp = FileRenamer.extract_original_timestamp_string(filename)
        
        if not original_timestamp:
            logger.warning(f"Could not extract original timestamp from {filename}, using standard format")
            return FileRenamer.generate_new_filename(meeting_title, original_file_path, dry_run)
        
        file_path = Path(original_file_path)
        sanitized_title = FileRenamer.sanitize_filename(meeting_title)
        logger.info(f"Preserving original timestamp format: {original_timestamp}")
        return FileRenamer._build_unique_filename(file_path, f"{sanitized_title}_{original_timestamp}")
    
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
    def is_file_ready(file_path, check_delay=3, check_attempts=10):
        """
        Check if a file is ready to be renamed (not being written to)
        Optimized for Nextcloud-synced files
        
        Args:
            file_path: Path to the file
            check_delay: Delay in seconds between checks
            check_attempts: Number of checks to perform
        
        Returns:
            bool: True if file is ready, False otherwise
        """
        import time
        import os
        
        last_size = -1
        stable_count = 0
        required_stable_checks = 2  # Require 2 consecutive size checks to be stable
        
        for attempt in range(check_attempts):
            try:
                if not os.path.exists(file_path):
                    logger.debug(f"File does not exist: {file_path}")
                    return False

                # Get current file size
                current_size = os.path.getsize(file_path)
                logger.debug(f"File size check (attempt {attempt + 1}/{check_attempts}): {current_size} bytes, last_size={last_size}")
                
                # Windows specific check: Try to rename the file to itself
                # If this fails, the file is likely locked (e.g., still recording)
                rename_ok = True
                if os.name == 'nt':
                    try:
                        os.rename(file_path, file_path)
                        logger.debug("Windows rename check passed")
                    except (IOError, OSError) as e:
                        logger.debug(f"Windows rename check failed (file locked?): {e}")
                        rename_ok = False
                
                # Standard check: Try to open for reading (less restrictive than appending)
                # This checks if file is accessible without modifying it
                append_ok = True
                try:
                    with open(file_path, 'rb') as f:
                        # Try to read a small amount to verify accessibility
                        f.read(1)
                    logger.debug(f"File read check passed")
                except (IOError, OSError) as e:
                    logger.debug(f"File read check failed (still being written?): {e}")
                    append_ok = False
                
                # Size stability check
                if current_size == last_size:
                    stable_count += 1
                    logger.debug(f"Size stable: {current_size} bytes (stable_count={stable_count}/{required_stable_checks})")
                else:
                    stable_count = 0
                    logger.debug(f"Size changed: {last_size} -> {current_size} bytes (resetting stable count)")
                
                last_size = current_size
                
                # File is ready if:
                # 1. Size is stable (not currently being written to)
                # 2. We can read it (accessible)
                # 3. Windows rename-to-self check passed (not locked)
                # 4. File has some content OR it's a Nextcloud file that might be legitimately empty
                if stable_count >= required_stable_checks and append_ok and current_size >= 0 and (rename_ok or os.name != 'nt'):
                    logger.info(f"✓ File is ready: {file_path} ({current_size} bytes, stable={stable_count} checks)")
                    return True
                
                time.sleep(check_delay)
            
            except Exception as e:
                logger.debug(f"Unexpected error in readiness check (attempt {attempt + 1}/{check_attempts}): {e}")
                time.sleep(check_delay)
        
        logger.warning(f"File did not become ready after {check_attempts} attempts ({check_attempts * check_delay}s total): {file_path}")
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
        import time
        try:
            if not os.path.exists(original_path):
                logger.error(f"Original file does not exist: {original_path}")
                return False
            
            if dry_run:
                logger.info(f"[DRY RUN] Would rename: {original_path} -> {new_path}")
                return True
            
            # Try to rename with retries if file is locked
            # Increased retries for Nextcloud file locks (can take 30-60+ seconds)
            max_retries = 20
            retry_delay = 2
            for i in range(max_retries):
                try:
                    os.rename(original_path, new_path)
                    logger.info(f"Successfully renamed: {original_path} -> {new_path}")
                    return True
                except (IOError, OSError) as e:
                    if i < max_retries - 1:
                        logger.warning(f"Rename attempt {i+1}/{max_retries} failed (file locked?), retrying in {retry_delay}s...: {e}")
                        time.sleep(retry_delay)
                    else:
                        raise e
            return False
        except Exception as e:
            logger.error(f"Error renaming file: {e}")
            return False
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
        import time
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
            
            # Try to copy with retries if file is locked
            max_retries = 10
            retry_delay = 2
            for i in range(max_retries):
                try:
                    shutil.copy2(source_path, destination_path)
                    logger.info(f"Successfully copied: {source_path} -> {destination_path}")
                    return True
                except (IOError, OSError) as e:
                    if i < max_retries - 1:
                        logger.warning(f"Copy attempt {i+1}/{max_retries} failed (file locked?), retrying in {retry_delay}s...: {e}")
                        time.sleep(retry_delay)
                    else:
                        raise e
        
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
        import time
        try:
            if not os.path.exists(file_path):
                logger.error(f"File does not exist: {file_path}")
                return False
            
            if dry_run:
                logger.info(f"[DRY RUN] Would delete: {file_path}")
                return True
            
            # Try to delete with retries if file is locked
            max_retries = 10
            retry_delay = 2
            for i in range(max_retries):
                try:
                    os.remove(file_path)
                    logger.info(f"Successfully deleted: {file_path}")
                    return True
                except (IOError, OSError) as e:
                    if i < max_retries - 1:
                        logger.warning(f"Delete attempt {i+1}/{max_retries} failed (file locked?), retrying in {retry_delay}s...: {e}")
                        time.sleep(retry_delay)
                    else:
                        raise e
        
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
        dt, timestamp_str, _ = FileRenamer.extract_timestamp_from_filename(filename)
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
