"""
Google Sheets and Drive integration helpers
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, List, Tuple

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
    def __init__(self, credentials_file: str, token_file: str):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.creds = None
        self.sheets_service = None
        self.drive_service = None

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

                self.sheets_service = build("sheets", "v4", credentials=self.creds)
                self.drive_service = build("drive", "v3", credentials=self.creds)
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
        if not self.sheets_service or not self.drive_service:
            self.authenticate()

    def append_meeting_log(self, spreadsheet_id: str, sheet_name: str, row: List[Any]) -> None:
        self._ensure_services()
        body = {"values": [row]}
        self.sheets_service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=sheet_name,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body=body,
        ).execute()

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

    def ensure_tabs_and_headers(
        self,
        spreadsheet_id: str,
        meeting_tab: str,
        project_tab: str,
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

        if requests:
            self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={"requests": requests},
            ).execute()

        meeting_headers = [[
            "Date & Time",
            "Meeting Name",
            "Project Tag",
            "Video Source Link",
            "Scribber Link",
            "Transcript Drive Link",
            "Status",
        ]]
        project_headers = [["Project Name", "Keywords / Context"]]

        self.sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{meeting_tab}!A1:G1",
            valueInputOption="RAW",
            body={"values": meeting_headers},
        ).execute()

        self.sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{project_tab}!A1:B1",
            valueInputOption="RAW",
            body={"values": project_headers},
        ).execute()

    def upload_transcript(self, file_path: str, folder_id: str | None) -> str:
        self._ensure_services()
        file_metadata = {"name": os.path.basename(file_path)}
        if folder_id:
            file_metadata["parents"] = [folder_id]

        media = MediaFileUpload(file_path, mimetype="text/plain", resumable=False)
        file = (
            self.drive_service.files()
            .create(body=file_metadata, media_body=media, fields="id")
            .execute()
        )
        file_id = file.get("id")
        if not file_id:
            raise RuntimeError("Drive upload failed: no file id returned")

        # Make the file shareable
        self.drive_service.permissions().create(
            fileId=file_id,
            body={"role": "reader", "type": "anyone"},
        ).execute()

        return f"https://drive.google.com/file/d/{file_id}/view"
