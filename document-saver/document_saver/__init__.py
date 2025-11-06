import asyncio
import os
import time
from pathlib import Path
from typing import Any, AsyncIterator
from uuid import UUID

from webai_element_sdk.comms.messages import TextFrame
from webai_element_sdk.element import Context, Element
from webai_element_sdk.element.settings import (
    BoolSetting,
    ElementSettings,
    TextSetting,
)
from webai_element_sdk.element.variables import ElementInputs, Input


class Settings(ElementSettings):
    output_directory = TextSetting(
        name="output_directory",
        display_name="Output Directory",
        description="Directory path where documents will be saved.",
        default="./downloaded_documents",
        hints=["folder_path"],
        required=True,
    )
    filename_pattern = TextSetting(
        name="filename_pattern",
        display_name="Filename Pattern",
        description="Pattern for naming files. Use {filename}, {key}, {bucket} placeholders. Default uses original filename.",
        default="{filename}",
        required=False,
    )
    overwrite_existing = BoolSetting(
        name="overwrite_existing",
        display_name="Overwrite Existing Files",
        description="Whether to overwrite existing files with the same name.",
        default=False,
        hints=["advanced"],
    )
    create_subdirectories = BoolSetting(
        name="create_subdirectories",
        display_name="Create Subdirectories",
        description="Create subdirectories based on S3 key structure.",
        default=True,
        hints=["advanced"],
    )
    add_metadata_file = BoolSetting(
        name="add_metadata_file",
        display_name="Save Metadata Files",
        description="Save a .meta.json file alongside each document with metadata.",
        default=False,
        hints=["advanced"],
    )


class Inputs(ElementInputs):
    default = Input[TextFrame]()


element = Element(
    id=UUID("3c9d4e8f-0e2b-5f7c-9d6e-2f3a4b5c6d7e"),
    name="document_saver",
    display_name="Document Saver",
    version="0.1.3",
    description="Saves documents from TextFrame inputs to disk with configurable naming and organization",
    inputs=Inputs(),
    settings=Settings(),
)


def _sanitize_filename(filename: str) -> str:
    """Sanitize filename to be safe for filesystem."""
    # Replace invalid characters with underscores
    invalid_chars = '<>:"|?*\\/\0'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Remove leading/trailing whitespace and dots
    filename = filename.strip('. ')
    
    # Ensure filename is not empty
    if not filename:
        filename = "unnamed_file"
    
    return filename


def _format_filename(pattern: str, metadata: dict) -> str:
    """Format filename using pattern and metadata."""
    try:
        # Extract values from metadata
        filename = metadata.get('filename', 'unnamed_file')
        key = metadata.get('key', '')
        bucket = metadata.get('bucket', '')
        
        # Remove extension from filename for pattern replacement
        name_without_ext = Path(filename).stem
        extension = Path(filename).suffix
        
        # Format the pattern
        formatted = pattern.format(
            filename=name_without_ext,
            key=key.replace('/', '_'),  # Replace slashes for filesystem safety
            bucket=bucket
        )
        
        # Add back the extension
        formatted_filename = f"{formatted}{extension}"
        
        return _sanitize_filename(formatted_filename)
    except (KeyError, ValueError) as e:
        # If formatting fails, fall back to original filename
        return _sanitize_filename(metadata.get('filename', 'unnamed_file'))


def _create_directory_structure(base_path: Path, key: str, create_subdirs: bool) -> Path:
    """Create directory structure based on S3 key."""
    if create_subdirs and '/' in key:
        # Create subdirectories based on S3 key structure
        key_path = Path(key).parent
        target_dir = base_path / key_path
    else:
        target_dir = base_path
    
    # Create directories if they don't exist
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir


def _save_document(text_content: str, metadata: dict, settings: Settings) -> tuple[bool, str, Path]:
    """Save document to disk. Returns (success, message, file_path)."""
    try:
        output_dir = Path(settings.output_directory.value).resolve()
        
        # Format filename
        filename = _format_filename(settings.filename_pattern.value, metadata)
        
        # Create directory structure
        target_dir = _create_directory_structure(
            output_dir, 
            metadata.get('key', ''), 
            settings.create_subdirectories.value
        )
        
        file_path = target_dir / filename
        
        # Check if file exists and handle overwrite setting
        if file_path.exists() and not settings.overwrite_existing.value:
            # Add number suffix to avoid overwrite
            counter = 1
            name_part = file_path.stem
            extension = file_path.suffix
            
            while file_path.exists():
                new_filename = f"{name_part}_{counter}{extension}"
                file_path = target_dir / new_filename
                counter += 1
        
        # Write the document
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(text_content)
        
        # Save metadata file if requested
        if settings.add_metadata_file.value:
            import json
            metadata_path = file_path.with_suffix(file_path.suffix + '.meta.json')
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, default=str)
        
        return True, f"Successfully saved: {file_path}", file_path
        
    except Exception as e:
        return False, f"Error saving document: {e}", None


@element.executor  # type: ignore
async def run(ctx: Context[Inputs, None, Settings]) -> AsyncIterator[Any]:
    try:
        await ctx.logger.log("Starting document saver execution")
        
        # Validate output directory setting
        output_dir = ctx.settings.output_directory.value.strip()
        if not output_dir:
            raise ValueError("Output directory is required")
        
        # Create base output directory
        output_path = Path(output_dir).resolve()
        output_path.mkdir(parents=True, exist_ok=True)
        await ctx.logger.log(f"Output directory: {output_path}")
        
        document_count = 0
        
        async for input_frame in ctx.inputs.default:
            try:
                if input_frame is None:
                    await ctx.logger.log("Received None input, skipping")
                    continue
                
                document_count += 1
                
                # Extract text content and metadata
                text_content = input_frame.text
                metadata = input_frame.other_data or {}
                
                if not text_content:
                    await ctx.logger.log(f"Document {document_count}: Empty text content, skipping")
                    continue
                
                # Save document to disk
                success, message, file_path = _save_document(text_content, metadata, ctx.settings)
                
                if success:
                    await ctx.logger.log(f"Document {document_count}: {message}")
                else:
                    await ctx.logger.log(f"Document {document_count}: {message}")
                
            except Exception as e:
                await ctx.logger.log(f"Error processing document {document_count}: {e}")
                continue
        
        await ctx.logger.log(f"Document saver completed. Processed {document_count} documents.")
        
    except Exception as e:
        await ctx.logger.log(f"Unhandled error in document saver: {e}")
        print(f"Critical error: {e}")
        raise 