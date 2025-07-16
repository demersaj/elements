import io
import json
import logging
import mimetypes
import tempfile
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload


class GoogleDriveService:
    """Service class for interacting with Google Drive API"""
    
    # Scopes required for reading files from Google Drive
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
    
    # Supported file types for OCR processing
    SUPPORTED_MIME_TYPES = {
        'application/pdf': '.pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
        'application/msword': '.doc',
        'text/plain': '.txt'
    }
    
    def __init__(self, credentials_path: Optional[str] = None, credentials_json: Optional[str] = None):
        """
        Initialize Google Drive service
        
        Args:
            credentials_path: Path to service account credentials JSON file
            credentials_json: Service account credentials as JSON string
        """
        self.logger = logging.getLogger(__name__)
        self.service = None
        self.credentials_path = credentials_path
        self.credentials_json = credentials_json
        
    def authenticate(self) -> bool:
        """
        Authenticate with Google Drive API using service account credentials
        
        Returns:
            bool: True if authentication successful, False otherwise
        """
        try:
            creds = None
            
            if self.credentials_json:
                # Use credentials from JSON string
                credentials_info = json.loads(self.credentials_json)
                creds = ServiceAccountCredentials.from_service_account_info(
                    credentials_info, scopes=self.SCOPES
                )
            elif self.credentials_path and Path(self.credentials_path).exists():
                # Use credentials from file
                creds = ServiceAccountCredentials.from_service_account_file(
                    self.credentials_path, scopes=self.SCOPES
                )
            else:
                self.logger.error("No valid credentials provided")
                return False
            
            self.service = build('drive', 'v3', credentials=creds)
            self.logger.info("Successfully authenticated with Google Drive")
            return True
            
        except Exception as e:
            self.logger.error(f"Authentication failed: {str(e)}")
            return False
    
    def list_files_in_folder(self, folder_id: str, file_types: Optional[List[str]] = None) -> List[Dict]:
        """
        List files in a specific Google Drive folder
        
        Args:
            folder_id: Google Drive folder ID
            file_types: List of file extensions to filter (e.g., ['.pdf', '.docx'])
        
        Returns:
            List of file dictionaries with id, name, mimeType, and size
        """
        if not self.service:
            raise Exception("Not authenticated. Call authenticate() first.")
        
        try:
            # Build query to get files in folder
            query = f"'{folder_id}' in parents and trashed=false"
            
            if file_types:
                # Convert file extensions to MIME types
                mime_types = []
                for ext in file_types:
                    mime_type = mimetypes.guess_type(f"file{ext}")[0]
                    if mime_type:
                        mime_types.append(mime_type)
                
                if mime_types:
                    mime_query = " or ".join([f"mimeType='{mt}'" for mt in mime_types])
                    query += f" and ({mime_query})"
            
            results = self.service.files().list(
                q=query,
                fields="nextPageToken, files(id, name, mimeType, size, modifiedTime)"
            ).execute()
            
            files = results.get('files', [])
            self.logger.info(f"Found {len(files)} files in folder {folder_id}")
            
            return files
            
        except Exception as e:
            self.logger.error(f"Failed to list files: {str(e)}")
            return []
    
    def download_file(self, file_id: str, file_name: str, download_path: Path) -> Optional[Path]:
        """
        Download a file from Google Drive
        
        Args:
            file_id: Google Drive file ID
            file_name: Name of the file
            download_path: Local path to save the file
        
        Returns:
            Path to downloaded file if successful, None otherwise
        """
        if not self.service:
            raise Exception("Not authenticated. Call authenticate() first.")
        
        try:
            request = self.service.files().get_media(fileId=file_id)
            
            # Ensure download directory exists
            download_path.mkdir(parents=True, exist_ok=True)
            
            # Create file path
            file_path = download_path / file_name
            
            # Download file
            with io.BytesIO() as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                    self.logger.debug(f"Download {int(status.progress() * 100)}%")
                
                # Write to file
                with open(file_path, 'wb') as f:
                    f.write(fh.getvalue())
            
            self.logger.info(f"Downloaded {file_name} to {file_path}")
            return file_path
            
        except Exception as e:
            self.logger.error(f"Failed to download file {file_name}: {str(e)}")
            return None
    
    def get_file_info(self, file_id: str) -> Optional[Dict]:
        """
        Get metadata for a specific file
        
        Args:
            file_id: Google Drive file ID
        
        Returns:
            File metadata dictionary if successful, None otherwise
        """
        if not self.service:
            raise Exception("Not authenticated. Call authenticate() first.")
        
        try:
            file_info = self.service.files().get(
                fileId=file_id,
                fields="id, name, mimeType, size, modifiedTime, createdTime"
            ).execute()
            
            return file_info
            
        except Exception as e:
            self.logger.error(f"Failed to get file info for {file_id}: {str(e)}")
            return None
    
    def is_supported_file_type(self, mime_type: str) -> bool:
        """
        Check if file type is supported for OCR processing
        
        Args:
            mime_type: MIME type of the file
        
        Returns:
            bool: True if supported, False otherwise
        """
        return mime_type in self.SUPPORTED_MIME_TYPES
    
    def batch_download_folder(self, folder_id: str, download_path: Path, 
                            file_types: Optional[List[str]] = None) -> Tuple[List[Path], List[Dict]]:
        """
        Download all files from a folder
        
        Args:
            folder_id: Google Drive folder ID
            download_path: Local path to save files
            file_types: List of file extensions to filter
        
        Returns:
            Tuple of (successfully_downloaded_paths, failed_downloads)
        """
        files = self.list_files_in_folder(folder_id, file_types)
        
        downloaded_files = []
        failed_downloads = []
        
        for file_info in files:
            # Check if file type is supported
            if not self.is_supported_file_type(file_info.get('mimeType', '')):
                self.logger.warning(f"Skipping unsupported file type: {file_info.get('name', 'Unknown')}")
                continue
            
            file_path = self.download_file(
                file_info['id'], 
                file_info['name'], 
                download_path
            )
            
            if file_path:
                downloaded_files.append(file_path)
            else:
                failed_downloads.append(file_info)
        
        self.logger.info(f"Successfully downloaded {len(downloaded_files)} files")
        if failed_downloads:
            self.logger.warning(f"Failed to download {len(failed_downloads)} files")
        
        return downloaded_files, failed_downloads 