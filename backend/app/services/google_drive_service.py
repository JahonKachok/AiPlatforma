import logging
import os
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)


class GoogleDriveService:
    def __init__(self):
        self.service = None
        self.enabled = False

    def initialize(self):
        if not settings.GOOGLE_DRIVE_CREDENTIALS_FILE:
            return
        if not os.path.exists(settings.GOOGLE_DRIVE_CREDENTIALS_FILE):
            logger.info("Google Drive credentials file not found, skipping initialization")
            return

        try:
            from googleapiclient.discovery import build
            from google.oauth2 import service_account

            credentials = service_account.Credentials.from_service_account_file(
                settings.GOOGLE_DRIVE_CREDENTIALS_FILE,
                scopes=["https://www.googleapis.com/auth/drive"],
            )
            self.service = build("drive", "v3", credentials=credentials)
            self.enabled = True
            logger.info("Google Drive service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Google Drive: {e}")

    def create_project_folder(self, project_name: str, parent_folder_id: Optional[str] = None) -> Optional[str]:
        if not self.enabled:
            return None
        try:
            parent = parent_folder_id or settings.GOOGLE_DRIVE_FOLDER_ID
            file_metadata = {
                "name": project_name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent] if parent else [],
            }
            folder = self.service.files().create(body=file_metadata, fields="id").execute()
            return folder.get("id")
        except Exception as e:
            logger.error(f"Failed to create Google Drive folder: {e}")
            return None

    def upload_file(self, file_path: str, filename: str, parent_folder_id: Optional[str] = None) -> Optional[str]:
        if not self.enabled:
            return None
        try:
            from googleapiclient.http import MediaFileUpload
            import mimetypes

            mime_type, _ = mimetypes.guess_type(file_path)
            file_metadata = {
                "name": filename,
                "parents": [parent_folder_id] if parent_folder_id else [],
            }
            media = MediaFileUpload(file_path, mimetype=mime_type or "application/octet-stream")
            file = self.service.files().create(body=file_metadata, media_body=media, fields="id").execute()
            return file.get("id")
        except Exception as e:
            logger.error(f"Failed to upload file to Google Drive: {e}")
            return None

    def get_file_url(self, file_id: str) -> str:
        return f"https://drive.google.com/file/d/{file_id}/view"

    def set_permissions(self, file_id: str, email: str, role: str = "reader") -> bool:
        if not self.enabled:
            return False
        try:
            permission = {"type": "user", "role": role, "emailAddress": email}
            self.service.permissions().create(fileId=file_id, body=permission).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to set permissions: {e}")
            return False


google_drive_service = GoogleDriveService()
