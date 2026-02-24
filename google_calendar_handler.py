"""
Google Calendar API integration module
"""

import os
import pickle
import logging
import time
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# Google API scopes (Calendar + Sheets + Drive)
SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

class GoogleCalendarHandler:
    """Handles Google Calendar API interactions"""
    
    def __init__(self, credentials_file="credentials.json", token_file="token.json"):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        self.creds = None
    
    def authenticate(self, retry_attempts=3, retry_delay=5):
        """
        Authenticate with Google Calendar API
        
        Args:
            retry_attempts: Number of times to retry on network error
            retry_delay: Seconds to wait between retries
        """
        self.creds = None
        
        for attempt in range(retry_attempts):
            try:
                # Load existing token if available
                if os.path.exists(self.token_file):
                    try:
                        self.creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
                        logger.info("Loaded existing credentials from token file")
                    except Exception as e:
                        logger.warning(f"Failed to load token file: {e}")
                
                # If no valid credentials, get new ones
                if not self.creds or not self.creds.valid:
                    if self.creds and self.creds.expired and self.creds.refresh_token:
                        logger.info("Refreshing expired credentials")
                        try:
                            self.creds.refresh(Request())
                        except Exception as e:
                            error_str = str(e).lower()
                            if "network" in error_str or "connection" in error_str:
                                if attempt < retry_attempts - 1:
                                    logger.warning(f"Network error refreshing credentials (attempt {attempt + 1}/{retry_attempts}). Retrying in {retry_delay}s...")
                                    time.sleep(retry_delay)
                                    continue
                            elif "invalid_grant" in error_str:
                                # Token has been revoked or expired, need to re-authenticate
                                logger.warning("Token has been revoked or expired. Forcing re-authentication...")
                                self.creds = None
                                # Delete the token file to force new OAuth flow
                                if os.path.exists(self.token_file):
                                    try:
                                        os.remove(self.token_file)
                                        logger.info(f"Deleted expired token file: {self.token_file}")
                                    except Exception as del_err:
                                        logger.warning(f"Could not delete token file: {del_err}")
                                # Continue to OAuth flow below
                                continue
                            raise
                    else:
                        if not os.path.exists(self.credentials_file):
                            raise FileNotFoundError(
                                f"Credentials file not found: {self.credentials_file}\n"
                                "Please download it from Google Cloud Console and place it in the project root."
                            )
                        
                        logger.info("Initiating OAuth 2.0 flow")
                        flow = InstalledAppFlow.from_client_secrets_file(
                            self.credentials_file, SCOPES
                        )
                        # Open browser and display URL clearly
                        import webbrowser
                        try:
                            self.creds = flow.run_local_server(port=0, open_browser=True)
                        except Exception as e:
                            logger.warning(f"Browser auto-open failed: {e}. Please open the URL manually.")
                            self.creds = flow.run_local_server(port=0, open_browser=False)
                
                # Save credentials for future use
                try:
                    with open(self.token_file, 'w') as token:
                        token.write(self.creds.to_json())
                    logger.info("Saved credentials to token file")
                except Exception as e:
                    logger.error(f"Failed to save token file: {e}")
                
                # Build the service
                self.service = build('calendar', 'v3', credentials=self.creds)
                logger.info("Google Calendar service initialized")
                return  # Success
            
            except Exception as e:
                error_str = str(e).lower()
                if "network" in error_str or "connection" in error_str or "timeout" in error_str:
                    if attempt < retry_attempts - 1:
                        logger.warning(f"Network error during authentication (attempt {attempt + 1}/{retry_attempts}): {e}. Retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                        continue
                    else:
                        logger.error(f"Network error during authentication after {retry_attempts} attempts: {e}")
                        raise
                elif "invalid_grant" in error_str:
                    # Token has been revoked, force re-authentication
                    logger.warning("Token has been revoked or expired. Will require new authentication on next attempt.")
                    if os.path.exists(self.token_file):
                        try:
                            os.remove(self.token_file)
                            logger.info(f"Deleted expired token file: {self.token_file}")
                        except Exception as del_err:
                            logger.warning(f"Could not delete token file: {del_err}")
                    raise
                else:
                    # Non-network error, don't retry
                    raise
    
    def get_current_meeting(self, time_threshold_minutes=10):
        """
        Get the current active meeting from Google Calendar
        
        Args:
            time_threshold_minutes: How many minutes before/after the current time to search
        
        Returns:
            dict: Meeting event or None if no meeting found
        """
        if not self.service:
            self.authenticate()
        
        try:
            now = datetime.utcnow().isoformat() + 'Z'
            
            # Query for events in the time window
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=now,
                maxResults=10,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            if events:
                # Return the first (earliest) event
                meeting = events[0]
                logger.info(f"Found meeting: {meeting.get('summary', 'Unknown')}")
                return meeting
            else:
                logger.info("No current/upcoming meetings found")
                return None
        
        except Exception as e:
            logger.error(f"Error querying Google Calendar: {e}")
            return None
    
    def get_meetings_at_time(self, check_time, retry_attempts=3, retry_delay=2):
        """
        Get all meetings that are active at a specific time
        
        Args:
            check_time: datetime object or ISO format string
            retry_attempts: Number of times to retry on network error
            retry_delay: Seconds to wait between retries
        
        Returns:
            list: List of meeting events or empty list if no meeting found
        """
        if not self.service:
            self.authenticate()
        
        for attempt in range(retry_attempts):
            try:
                if isinstance(check_time, datetime):
                    # Create a window for the entire day of the check_time
                    # to find meetings that were active during the recording
                    from datetime import timedelta
                    start_of_day = check_time.replace(hour=0, minute=0, second=0, microsecond=0)
                    end_of_day = start_of_day + timedelta(days=1)
                    time_min = start_of_day.isoformat() + 'Z'
                    time_max = end_of_day.isoformat() + 'Z'
                else:
                    time_min = check_time
                    time_max = None
                
                # Query for events around the given time
                logger.debug(f"Querying Google Calendar: timeMin={time_min}, timeMax={time_max}")
                events_result = self.service.events().list(
                    calendarId='primary',
                    timeMin=time_min,
                    timeMax=time_max,
                    maxResults=20,
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                
                events = events_result.get('items', [])
                logger.debug(f"API returned {len(events)} events")
                
                # Filter events to find those that actually overlap with check_time
                active_meetings = []
                for event in events:
                    summary = event.get('summary', 'No Title')
                    start = event['start'].get('dateTime', event['start'].get('date'))
                    end = event['end'].get('dateTime', event['end'].get('date'))
                    
                    logger.debug(f"Checking event: '{summary}' ({start} to {end})")
                    
                    # Convert to datetime objects for comparison
                    from dateutil import parser
                    start_dt = parser.parse(start)
                    end_dt = parser.parse(end)
                    
                    # Check if check_time is between start and end
                    # We need to handle timezone-aware vs naive datetimes
                    is_active = False
                    
                    # Ensure check_time is timezone-aware for proper comparison
                    if start_dt.tzinfo and not check_time.tzinfo:
                        # check_time is naive, start_dt is aware
                        # Assume check_time is in UTC (since it comes from file timestamp converted to UTC)
                        from datetime import timezone
                        check_time_aware = check_time.replace(tzinfo=timezone.utc)
                        logger.debug(f"Converted naive check_time to UTC-aware: {check_time_aware}")
                    elif start_dt.tzinfo and check_time.tzinfo:
                        # Both are aware, use as-is
                        check_time_aware = check_time
                    else:
                        # Both are naive
                        check_time_aware = check_time
                    
                    if start_dt <= check_time_aware <= end_dt:
                        is_active = True
                    
                    if is_active:
                        logger.debug(f"MATCH: Event '{summary}' ({start_dt} to {end_dt}) is active at {check_time_aware}")
                        active_meetings.append(event)
                    else:
                        logger.debug(f"NO MATCH: Event '{summary}' ({start_dt} to {end_dt}) is NOT active at {check_time_aware}")
                
                if active_meetings:
                    logger.info(f"Found {len(active_meetings)} active meetings at {check_time}")
                    return active_meetings
                else:
                    logger.info(f"No active meetings found at {check_time}")
                    return []
            
            except HttpError as e:
                # ... existing error handling ...
                error_code = e.resp.status
                if error_code in [403, 429, 500, 502, 503, 504]:
                    if attempt < retry_attempts - 1:
                        logger.warning(f"Google Calendar API error (attempt {attempt + 1}/{retry_attempts}): {e.resp.reason}. Retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                        continue
                logger.error(f"Google Calendar API error: {e}")
                return []
            except Exception as e:
                if attempt < retry_attempts - 1:
                    logger.warning(f"Error querying Google Calendar (attempt {attempt + 1}/{retry_attempts}): {e}. Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    continue
                logger.error(f"Error querying Google Calendar after {retry_attempts} attempts: {e}")
                return []
        
        return []

    def get_meeting_at_time(self, check_time, retry_attempts=3, retry_delay=2):
        """
        Get the meeting that is active at a specific time
        
        Args:
            check_time: datetime object or ISO format string
            retry_attempts: Number of times to retry on network error
            retry_delay: Seconds to wait between retries
        
        Returns:
            dict: Meeting event or None if no meeting found at that time
        """
        meetings = self.get_meetings_at_time(check_time, retry_attempts, retry_delay)
        return meetings[0] if meetings else None

    def _ensure_authenticated(self):
        """Ensure credentials are valid and refresh if necessary"""
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                logger.info("Refreshing expired credentials automatically")
                try:
                    self.creds.refresh(Request())
                    with open(self.token_file, 'w') as token:
                        token.write(self.creds.to_json())
                except Exception as e:
                    logger.error(f"Failed to refresh token: {e}")
                    self.authenticate()
            else:
                self.authenticate()
        
        if not self.service:
            self.service = build('calendar', 'v3', credentials=self.creds)

    def get_all_meetings_on_date(self, check_date, retry_attempts=3, retry_delay=2):
        """
        Get all meetings on a specific date (regardless of time overlap)
        
        Args:
            check_date: datetime object representing the date
            retry_attempts: Number of times to retry on network error
            retry_delay: Seconds to wait between retries
        
        Returns:
            list: List of all meeting events on that date or empty list if none found
        """
        self._ensure_authenticated()
        
        for attempt in range(retry_attempts):
            try:
                if isinstance(check_date, datetime):
                    # Create a window for the entire day
                    from datetime import timedelta
                    start_of_day = check_date.replace(hour=0, minute=0, second=0, microsecond=0)
                    end_of_day = start_of_day + timedelta(days=1)
                    time_min = start_of_day.isoformat() + 'Z'
                    time_max = end_of_day.isoformat() + 'Z'
                else:
                    time_min = check_date
                    time_max = None
                
                # Query for all events on the given date
                logger.debug(f"Querying Google Calendar for all meetings on date: timeMin={time_min}, timeMax={time_max}")
                events_result = self.service.events().list(
                    calendarId='primary',
                    timeMin=time_min,
                    timeMax=time_max,
                    maxResults=50,
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                
                events = events_result.get('items', [])
                logger.info(f"Found {len(events)} meetings on date {check_date.date() if isinstance(check_date, datetime) else check_date}")
                return events
            
            except HttpError as e:
                error_code = e.resp.status
                if error_code == 403 and "insufficient authentication scopes" in str(e).lower():
                    logger.warning("Insufficient permissions detected. Deleting token and re-authenticating...")
                    if os.path.exists(self.token_file):
                        os.remove(self.token_file)
                    self.authenticate()
                    return self.get_all_meetings_on_date(check_date, retry_attempts, retry_delay)
                
                if error_code in [403, 429, 500, 502, 503, 504]:
                    if attempt < retry_attempts - 1:
                        logger.warning(f"Google Calendar API error (attempt {attempt + 1}/{retry_attempts}): {e.resp.reason}. Retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                        continue
                logger.error(f"Google Calendar API error: {e}")
                return []
            except Exception as e:
                if attempt < retry_attempts - 1:
                    logger.warning(f"Error querying Google Calendar (attempt {attempt + 1}/{retry_attempts}): {e}. Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    continue
                logger.error(f"Error querying Google Calendar after {retry_attempts} attempts: {e}")
                return []
        
        return []

    def close(self):
        """Close the service connection"""
        if self.service:
            self.service.close()
            logger.info("Google Calendar service closed")
