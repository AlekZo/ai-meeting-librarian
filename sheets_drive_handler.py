"""
Google Sheets and Drive integration helpers
Supports queuing Sheets operations for batch processing
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, List, Tuple, Optional, Dict

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]


class SheetsDriveHandler:
    def __init__(self, credentials_file: str, token_file: str, sheets_queue: Optional[Any] = None):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.creds = None
        self.sheets_service = None
        self.drive_service = None
        self.sheets_queue = sheets_queue  # Optional SheetsQueue instance

    def authenticate(self, retry_attempts: int = 3, retry_delay: int = 5) -> None:
        self.creds = None

        for attempt in range(retry_attempts):
            try:
                if os.path.exists(self.token_file):
                    try:
                        self.creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
                        logger.info("Loaded existing Sheets/Drive credentials")
                    except Exception as e:
                        logger.warning(f"Failed to load token file: {e}")

                if not self.creds or not self.creds.valid:
                    if self.creds and self.creds.expired and self.creds.refresh_token:
                        logger.info("Refreshing expired credentials for Sheets/Drive")
                        self.creds.refresh(Request())
                    else:
                        if not os.path.exists(self.credentials_file):
                            raise FileNotFoundError(
                                f"Credentials file not found: {self.credentials_file}"
                            )
                        logger.info("Initiating OAuth 2.0 flow for Sheets/Drive")
                        flow = InstalledAppFlow.from_client_secrets_file(
                            self.credentials_file, SCOPES
                        )
                        self.creds = flow.run_local_server(port=0, open_browser=True)

                with open(self.token_file, "w") as token:
                    token.write(self.creds.to_json())
                logger.info("Saved Sheets/Drive credentials")

                self.sheets_service = build("sheets", "v4", credentials=self.creds, cache_discovery=False)
                self.drive_service = build("drive", "v3", credentials=self.creds, cache_discovery=False)
                logger.info("Sheets and Drive services initialized")
                return
            except Exception as e:
                if attempt < retry_attempts - 1:
                    logger.warning(
                        f"Sheets/Drive auth failed (attempt {attempt + 1}/{retry_attempts}): {e}. "
                        f"Retrying in {retry_delay}s..."
                    )
                    time.sleep(retry_delay)
                else:
                    logger.error(f"Sheets/Drive auth failed after {retry_attempts} attempts: {e}")
                    raise

    def _ensure_services(self) -> None:
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                logger.info("Refreshing expired credentials for Sheets/Drive automatically")
                try:
                    self.creds.refresh(Request())
                    with open(self.token_file, "w") as token:
                        token.write(self.creds.to_json())
                    # Force re-build services after refresh
                    self.sheets_service = None
                    self.drive_service = None
                except Exception as e:
                    logger.error(f"Failed to refresh Sheets/Drive token: {e}")
                    self.authenticate()
            else:
                self.authenticate()

        if not self.sheets_service or not self.drive_service:
            self.sheets_service = build("sheets", "v4", credentials=self.creds, cache_discovery=False)
            self.drive_service = build("drive", "v3", credentials=self.creds, cache_discovery=False)

    def append_meeting_log(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        row: List[Any],
        queue_if_failed: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Append a meeting log row to Google Sheets
        
        Args:
            spreadsheet_id: Google Sheets ID
            sheet_name: Sheet name/tab
            row: Row data to append
            queue_if_failed: Queue the operation if it fails
            metadata: Optional metadata for queuing
            
        Returns:
            True if successful, False if queued or failed
        """
        try:
            self._ensure_services()
            body = {"values": [row]}
            self.sheets_service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=sheet_name,
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body=body,
            ).execute()
            logger.info(f"Successfully appended meeting log to {sheet_name}")
            return True
        except Exception as e:
            if "insufficient authentication scopes" in str(e).lower() or (hasattr(e, 'resp') and e.resp.status == 403):
                logger.warning("Insufficient permissions for Sheets/Drive. Deleting token and re-authenticating...")
                if os.path.exists(self.token_file):
                    os.remove(self.token_file)
                self.authenticate()
                # Retry the operation once
                return self.append_meeting_log(spreadsheet_id, sheet_name, row, queue_if_failed, metadata)

            logger.error(f"Failed to append meeting log: {e}")
            if queue_if_failed and self.sheets_queue:
                self.sheets_queue.enqueue_append(
                    spreadsheet_id,
                    sheet_name,
                    row,
                    metadata=metadata
                )
                logger.info("Meeting log queued for later publishing")
                return False
            raise

    def read_project_config(self, spreadsheet_id: str, sheet_name: str) -> List[Tuple[str, str]]:
        self._ensure_services()
        range_name = f"{sheet_name}!A2:B"
        result = (
            self.sheets_service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=range_name)
            .execute()
        )
        values = result.get("values", [])
        projects = []
        for row in values:
            if not row:
                continue
            name = row[0].strip() if len(row) > 0 else ""
            keywords = row[1].strip() if len(row) > 1 else ""
            if name:
                projects.append((name, keywords))
        return projects

    def read_meeting_types_config(self, spreadsheet_id: str, sheet_name: str) -> List[Tuple[str, str]]:
        self._ensure_services()
        range_name = f"{sheet_name}!A2:B"
        result = (
            self.sheets_service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=range_name)
            .execute()
        )
        values = result.get("values", [])
        types = []
        for row in values:
            if not row:
                continue
            name = row[0].strip() if len(row) > 0 else ""
            desc = row[1].strip() if len(row) > 1 else ""
            if name:
                types.append((name, desc))
        return types

    def ensure_tabs_and_headers(
        self,
        spreadsheet_id: str,
        meeting_tab: str,
        project_tab: str,
        type_tab: str,
    ) -> None:
        """Ensure required tabs exist with headers."""
        self._ensure_services()
        spreadsheet = self.sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        existing_tabs = {s["properties"]["title"] for s in spreadsheet.get("sheets", [])}

        requests = []
        if meeting_tab not in existing_tabs:
            requests.append({"addSheet": {"properties": {"title": meeting_tab}}})
        if project_tab not in existing_tabs:
            requests.append({"addSheet": {"properties": {"title": project_tab}}})
        if type_tab not in existing_tabs:
            requests.append({"addSheet": {"properties": {"title": type_tab}}})

        if requests:
            self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={"requests": requests},
            ).execute()

        meeting_headers = [[
            "Date & Time",
            "Meeting Name",
            "Meeting Type",
            "Speakers",
            "Summary",
            "Project Tag",
            "Video Source Link",
            "Scribber Link",
            "Transcript Drive Doc",
            "Status",
        ]]
        project_headers = [["Project Name", "Keywords / Context"]]
        type_headers = [["Type Name", "Description / AI Prompt"]]

        self.sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{meeting_tab}!A1:J1",
            valueInputOption="RAW",
            body={"values": meeting_headers},
        ).execute()

        self.sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{project_tab}!A1:B1",
            valueInputOption="RAW",
            body={"values": project_headers},
        ).execute()

        self.sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{type_tab}!A1:B1",
            valueInputOption="RAW",
            body={"values": type_headers},
        ).execute()

    def upload_transcript(self, file_path: str, folder_id: str | None) -> str:
        self._ensure_services()
        
        # Убираем расширение .txt из имени файла для Google Doc
        file_name = os.path.basename(file_path)
        if file_name.lower().endswith('.txt'):
            file_name = file_name[:-4]

        # Указываем MIME-тип Google Doc для конвертации
        file_metadata = {
            "name": file_name,
            "mimeType": "application/vnd.google-apps.document"
        }
        
        if folder_id:
            file_metadata["parents"] = [folder_id]

        media = MediaFileUpload(file_path, mimetype="text/plain", resumable=False)
        
        # Запрашиваем webViewLink сразу в ответе
        file = (
            self.drive_service.files()
            .create(body=file_metadata, media_body=media, fields="id, webViewLink")
            .execute()
        )
        file_id = file.get("id")
        web_view_link = file.get("webViewLink")

        if not file_id:
            raise RuntimeError("Drive upload failed: no file id returned")

        # Делаем файл доступным по ссылке (reader)
        self.drive_service.permissions().create(
            fileId=file_id,
            body={"role": "reader", "type": "anyone"},
        ).execute()

        # Возвращаем ссылку на Google Doc
        return web_view_link or f"https://docs.google.com/document/d/{file_id}/edit"
