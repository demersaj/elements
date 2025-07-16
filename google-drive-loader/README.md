# Google Drive Loader Element

This WebAI element allows you to import documents from Google Drive and pass them as output to other elements in your workflow.

## Features

- **Flexible Authentication**: Supports Google Service Account credentials
- **Configurable Filtering**: Filter by folder, file types, and maximum number of files
- **Full Content Extraction**: Always includes the actual content of documents
- **Multiple File Types**: Supports Google Docs, PDFs, text files, and more
- **Rich Metadata**: Provides file metadata including size, timestamps, and links

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Create Google Drive API Credentials

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Drive API
4. Create a Service Account:
   - Go to "IAM & Admin" > "Service Accounts"
   - Click "Create Service Account"
   - Fill in the details and click "Create"
   - Skip the optional steps and click "Done"
5. Generate credentials:
   - Click on your service account
   - Go to the "Keys" tab
   - Click "Add Key" > "Create new key"
   - Choose "JSON" format and download the file

### 3. Share Google Drive Content

Since you're using a service account, you need to share the Google Drive folders/files with the service account email address (found in your credentials JSON file).

## Configuration

The element provides the following settings:

### Required Settings

- **Credentials JSON File**: Upload your Google Service Account JSON file

### Optional Settings

- **Folder ID**: Specific Google Drive folder ID to search in (leave empty to search all accessible files)
- **File Types**: Comma-separated list of MIME types to include (default: Google Docs, PDFs, text files)
- **Max Files**: Maximum number of files to retrieve (1-100, default: 10)

## Common File Types

Here are some common MIME types you can use in the "File Types" setting:

- `application/vnd.google-apps.document` - Google Docs
- `application/vnd.google-apps.spreadsheet` - Google Sheets
- `application/vnd.google-apps.presentation` - Google Slides
- `application/pdf` - PDF files
- `text/plain` - Text files
- `application/msword` - Microsoft Word documents
- `application/vnd.openxmlformats-officedocument.wordprocessingml.document` - Word (.docx)

## Output Format

Each document is output as a Frame with the following data structure:

```json
{
  "id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
  "name": "My Document.docx",
  "mime_type": "application/vnd.google-apps.document",
  "size": "12345",
  "created_time": "2023-01-01T12:00:00.000Z",
  "modified_time": "2023-01-02T12:00:00.000Z",
  "web_view_link": "https://docs.google.com/document/d/...",
  "parents": ["0BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"],
  "content": "The actual content of the document..."
}
```

## Troubleshooting

### Authentication Issues

- Ensure your Service Account JSON is valid and properly formatted
- Make sure you've shared the Google Drive content with your service account email
- Verify that the Google Drive API is enabled in your Google Cloud project

### No Files Found

- Check that the folder ID is correct (you can find it in the Google Drive URL)
- Verify that your service account has access to the files/folders
- Ensure your file type filters match the actual MIME types of your files

### Content Reading Issues

- Some file types may not be readable as text
- Large files may take time to process - content is always included
- Binary files will show a size indicator instead of content

## Example Usage

1. Upload your Google Service Account JSON credentials file
2. Optionally specify a folder ID to limit the search scope  
3. Set appropriate file type filters
4. Connect the `documents` output to other elements in your workflow
5. Each document will be output as a separate frame with metadata and content 