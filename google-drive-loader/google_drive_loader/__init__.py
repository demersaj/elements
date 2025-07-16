import json
import os
from uuid import UUID
from typing import Optional, List, Dict, Any

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from webai_element_sdk.comms.messages import Frame
from webai_element_sdk.element import Context, Element
from webai_element_sdk.element.variables import ElementOutputs, Output, Input, ElementInputs
from webai_element_sdk.element.settings import ElementSettings, TextSetting, BoolSetting, NumberSetting


class Inputs(ElementInputs):
    """
    This element doesn't require any inputs - it fetches data directly from Google Drive.
    """
    
    def setup(self, callback: Any):
        # Override to do nothing since this element doesn't need input handling
        pass
    
    async def receive(self, callback: Any):
        # Override to immediately call the callback since no inputs are expected
        await callback()

  
class Outputs(ElementOutputs):
    """
    Each output can be either a single frame or a stream of frames.
    Outputs are how your element sends data to other elements.
    """
    documents = Output[Frame]()


class Settings(ElementSettings):
    """
    Settings allow users to configure your element's behavior.
    You can create Text, Number, or Boolean settings with validation rules.
    """
    # Google Drive API credentials (JSON file upload)
    credentials_json = TextSetting(
        name="credentials_json",
        display_name="Credentials JSON File",
        description="Upload your Google Drive API service account credentials JSON file (from Google Cloud Console)",
        default='',
        required=True,
        hints=["file", "json"],
        sensitive=True
    )
    
    # Folder ID to search for documents (optional)
    folder_id = TextSetting(
        name="folder_id",
        display_name="Folder ID", 
        description="Specific Google Drive folder ID to search in (optional - leave empty to search all accessible files)",
        default="",
        required=False
    )
    
    # File types to include
    file_types = TextSetting(
        name="file_types",
        display_name="File Types",
        description="Comma-separated list of MIME types to include (e.g., 'application/vnd.google-apps.document,application/pdf')",
        default="application/vnd.google-apps.document,application/pdf,text/plain",
        required=False
    )
    
    # Maximum number of files to retrieve
    max_files = NumberSetting(
        name="max_files",
        display_name="Max Files",
        description="Maximum number of files to retrieve",
        default=10,
        min_value=1,
        max_value=100,
        required=False
    )


element: Element = Element(
    id=UUID("07b6538d-a205-4ba1-b4b1-5fc35e070b48"),
    name="google_drive_loader",
    display_name="Google Drive Loader",
    description="Load documents from Google Drive with configurable filters and output document metadata and content",
    version="0.2.2",
    settings=Settings(),
    inputs=Inputs(),
    outputs=Outputs(),
)


class GoogleDriveService:
    def __init__(self, credentials_json: str):
        self.credentials_json = credentials_json
        self.service = None
        
    async def authenticate(self):
        """Authenticate with Google Drive API"""
        try:
            creds_dict = json.loads(self.credentials_json)
            
            # For service account authentication
            if 'type' in creds_dict and creds_dict['type'] == 'service_account':
                from google.oauth2 import service_account
                credentials = service_account.Credentials.from_service_account_info(
                    creds_dict, scopes=['https://www.googleapis.com/auth/drive.readonly']
                )
            else:
                # For OAuth2 authentication - this is more complex and would need a proper flow
                # For now, we'll assume service account is used
                raise ValueError("OAuth2 authentication not implemented yet. Please use service account credentials.")
            
            self.service = build('drive', 'v3', credentials=credentials)
            return True
            
        except Exception as e:
            raise Exception(f"Failed to authenticate with Google Drive: {str(e)}")
    
    async def list_files(self, folder_id: Optional[str] = None, file_types: Optional[List[str]] = None, max_files: int = 10) -> List[Dict[str, Any]]:
        """List files from Google Drive"""
        if not self.service:
            raise Exception("Not authenticated. Call authenticate() first.")
        
        try:
            # Build query
            query_parts = []
            
            if folder_id:
                query_parts.append(f"'{folder_id}' in parents")
            
            if file_types:
                mime_type_queries = [f"mimeType='{mime_type}'" for mime_type in file_types]
                query_parts.append(f"({' or '.join(mime_type_queries)})")
            
            # Exclude trashed files
            query_parts.append("trashed=false")
            
            query = " and ".join(query_parts) if query_parts else "trashed=false"
            
            # Execute the query
            results = self.service.files().list(
                q=query,
                pageSize=max_files,
                fields="nextPageToken, files(id, name, mimeType, size, createdTime, modifiedTime, webViewLink, parents)"
            ).execute()
            
            files = results.get('files', [])
            return files
            
        except HttpError as e:
            raise Exception(f"Failed to list files: {str(e)}")
    
    async def get_file_content(self, file_id: str, mime_type: str) -> Optional[str]:
        """Get file content based on MIME type"""
        if not self.service:
            raise Exception("Not authenticated. Call authenticate() first.")
        
        try:
            # For Google Docs, Sheets, etc., export as text
            if mime_type.startswith('application/vnd.google-apps.'):
                if 'document' in mime_type:
                    export_mime_type = 'text/plain'
                elif 'spreadsheet' in mime_type:
                    export_mime_type = 'text/csv'
                elif 'presentation' in mime_type:
                    export_mime_type = 'text/plain'
                else:
                    export_mime_type = 'text/plain'
                
                result = self.service.files().export(
                    fileId=file_id, 
                    mimeType=export_mime_type
                ).execute()
                
                return result.decode('utf-8')
            
            # For other file types, get the media content
            else:
                result = self.service.files().get_media(fileId=file_id).execute()
                try:
                    return result.decode('utf-8')
                except UnicodeDecodeError:
                    return f"[Binary content - {len(result)} bytes]"
                    
        except HttpError as e:
            return f"[Error reading content: {str(e)}]"
        except Exception as e:
            return f"[Error: {str(e)}]"


@element.startup
async def startup(ctx: Context[Inputs, Outputs, Settings]):
    # Called when the element starts up.
    # We'll initialize the Google Drive service here
    ctx.drive_service = GoogleDriveService(ctx.settings.credentials_json.value)
    try:
        await ctx.drive_service.authenticate()
        await ctx.logger.log("Successfully authenticated with Google Drive")
    except Exception as e:
        await ctx.logger.log(f"Failed to authenticate with Google Drive: {str(e)}")
        raise


@element.shutdown
async def shutdown(ctx: Context[Inputs, Outputs, Settings]):
    # Called when the element shuts down.
    # Clean up any resources
    if hasattr(ctx, 'drive_service'):
        del ctx.drive_service


@element.executor
async def run(ctx: Context[Inputs, Outputs, Settings]):
    # Main execution function that fetches documents from Google Drive
    try:
        # Parse file types
        file_types = [ft.strip() for ft in ctx.settings.file_types.split(',') if ft.strip()] if ctx.settings.file_types else None
        
        # Get list of files
        files = await ctx.drive_service.list_files(
            folder_id=ctx.settings.folder_id if ctx.settings.folder_id else None,
            file_types=file_types,
            max_files=int(ctx.settings.max_files)
        )
        
        await ctx.logger.log(f"Found {len(files)} files in Google Drive")
        
        # Process each file
        for file_info in files:
            document_data = {
                'id': file_info['id'],
                'name': file_info['name'],
                'mime_type': file_info['mimeType'],
                'size': file_info.get('size'),
                'created_time': file_info.get('createdTime'),
                'modified_time': file_info.get('modifiedTime'),
                'web_view_link': file_info.get('webViewLink'),
                'parents': file_info.get('parents', [])
            }
            
            # Get file content if requested
            content = await ctx.drive_service.get_file_content(
                file_info['id'], 
                file_info['mimeType']
            )
            document_data['content'] = content
            
            # Create output frame with document data
            output_frame = Frame(data=document_data)
            yield ctx.outputs.documents(output_frame)
            
            await ctx.logger.log(f"Processed document: {file_info['name']}")
    
    except Exception as e:
        error_message = f"Error loading documents from Google Drive: {str(e)}"
        await ctx.logger.log(error_message)
        
        # Output error as a frame
        error_frame = Frame(data={'error': error_message})
        yield ctx.outputs.documents(error_frame)
    