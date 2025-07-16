import asyncio
import time
from pathlib import Path
from typing import Any, AsyncIterator, List
from uuid import UUID

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from webai_element_sdk.comms.messages import TextFrame
from webai_element_sdk.element import Context, Element
from webai_element_sdk.element.settings import (
    BoolSetting,
    ElementSettings,
    NumberSetting,
    TextSetting,
)
from webai_element_sdk.element.variables import ElementOutputs, Output


class Settings(ElementSettings):
    bucket_name = TextSetting(
        name="bucket_name",
        display_name="S3 Bucket Name",
        description="The name of the S3 bucket containing the documents.",
        default="",
        required=True,
    )
    prefix = TextSetting(
        name="prefix",
        display_name="Object Prefix",
        description="Optional prefix to filter objects in the bucket (e.g., 'documents/').",
        default="",
        required=False,
    )
    aws_access_key_id = TextSetting(
        name="aws_access_key_id",
        display_name="AWS Access Key ID",
        description="AWS Access Key ID. Leave empty to use default credential chain.",
        default="",
        required=False,
        hints=["secret"],
    )
    aws_secret_access_key = TextSetting(
        name="aws_secret_access_key",
        display_name="AWS Secret Access Key",
        description="AWS Secret Access Key. Leave empty to use default credential chain.",
        default="",
        required=False,
        hints=["secret"],
    )
    aws_region = TextSetting(
        name="aws_region",
        display_name="AWS Region",
        description="AWS region where the bucket is located.",
        default="us-east-1",
        required=False,
    )
    file_extensions = TextSetting(
        name="file_extensions",
        display_name="File Extensions",
        description="Comma-separated list of file extensions to process (e.g., '.txt,.pdf,.md'). Leave empty for all files.",
        default=".txt,.md,.pdf,.doc,.docx",
        required=False,
    )
    delay_between_files = NumberSetting[float](
        name="delay_between_files",
        display_name="Delay Between Files (seconds)",
        description="Time delay between processing each file.",
        default=1.0,
        hints=["advanced"],
    )


class Outputs(ElementOutputs):
    default = Output[TextFrame]()


element = Element(
    id=UUID("2b8c3f7e-9d1a-4e6b-8c5d-1a2b3c4d5e6f"),
    name="s3_document_loader",
    display_name="S3 Document Loader",
    version="0.2.2",
    description="Imports documents from an S3 bucket so that AI models can process them",
    outputs=Outputs(),
    settings=Settings(),
)


def _get_s3_client(settings: Settings) -> boto3.client:
    """Create and return an S3 client with the provided credentials."""
    session_kwargs = {}
    
    if settings.aws_access_key_id.value and settings.aws_secret_access_key.value:
        session_kwargs.update({
            'aws_access_key_id': settings.aws_access_key_id.value,
            'aws_secret_access_key': settings.aws_secret_access_key.value,
        })
    
    session = boto3.Session(**session_kwargs)
    return session.client('s3', region_name=settings.aws_region.value)


def _is_supported_file(key: str, extensions: List[str]) -> bool:
    """Check if the file extension is in the supported list."""
    if not extensions:  # If no extensions specified, process all files
        return True
    
    file_ext = Path(key).suffix.lower()
    return file_ext in extensions


def _read_text_file(content: bytes, key: str) -> str:
    """Attempt to read file content as text with various encodings."""
    encodings = ['utf-8', 'utf-16', 'latin-1', 'cp1252']
    
    for encoding in encodings:
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    
    # If all encodings fail, return a representation with error info
    return f"Error: Could not decode file {key}. File may be binary or use an unsupported encoding."


def _list_s3_objects(s3_client, bucket_name: str, prefix: str, extensions: List[str]):
    """List all objects in the S3 bucket that match the criteria."""
    objects = []
    
    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        page_iterator = paginator.paginate(Bucket=bucket_name, Prefix=prefix)
        
        for page in page_iterator:
            if 'Contents' in page:
                for obj in page['Contents']:
                    key = obj['Key']
                    # Skip directories (keys ending with /)
                    if not key.endswith('/') and _is_supported_file(key, extensions):
                        objects.append(key)
        
        return objects
    except ClientError as e:
        raise ValueError(f"Error listing objects in bucket {bucket_name}: {e}")


def _load_documents_from_s3(s3_client, bucket_name: str, prefix: str, extensions: List[str]):
    """Generator function to load documents from S3 bucket."""
    objects = _list_s3_objects(s3_client, bucket_name, prefix, extensions)
    
    for key in objects:
        try:
            # Download object content
            response = s3_client.get_object(Bucket=bucket_name, Key=key)
            content = response['Body'].read()
            
            # Convert content to text
            text_content = _read_text_file(content, key)
            
            # Create metadata
            metadata = {
                'source': f's3://{bucket_name}/{key}',
                'bucket': bucket_name,
                'key': key,
                'size': len(content),
                'last_modified': response.get('LastModified', '').isoformat() if response.get('LastModified') else '',
                'content_type': response.get('ContentType', ''),
                'filename': Path(key).name
            }
            
            yield text_content, metadata
            
        except ClientError as e:
            print(f"Error downloading {key}: {e}")
            continue
        except Exception as e:
            print(f"Error processing {key}: {e}")
            continue


@element.executor  # type: ignore
async def run(ctx: Context[None, Outputs, Settings]) -> AsyncIterator[Any]:
    try:
        delay: float = ctx.settings.delay_between_files.value
        await ctx.logger.log(f"Starting S3 document loader execution")

        # ── validate required settings ─────────────────────────────────────────────
        bucket_name = ctx.settings.bucket_name.value.strip()
        if not bucket_name:
            await ctx.logger.log("No bucket name provided in settings")
            raise ValueError("Bucket name is required")

        # Parse file extensions
        extensions_str = ctx.settings.file_extensions.value.strip()
        extensions = []
        if extensions_str:
            extensions = [ext.strip().lower() for ext in extensions_str.split(',') if ext.strip()]
        
        prefix = ctx.settings.prefix.value.strip()
        
        await ctx.logger.log(f"Configuration: bucket={bucket_name}, prefix='{prefix}', extensions={extensions}")

        # Create S3 client
        try:
            s3_client = _get_s3_client(ctx.settings)
            await ctx.logger.log("S3 client created successfully")
        except NoCredentialsError:
            raise ValueError("AWS credentials not found. Please provide credentials or configure AWS CLI.")
        except Exception as e:
            raise ValueError(f"Failed to create S3 client: {e}")

        # ── process all documents once ────────────────────────────────────────────────
        document_count = 0
        generator = _load_documents_from_s3(s3_client, bucket_name, prefix, extensions)
        next_document_time = time.perf_counter()

        for text_content, metadata in generator:
            if delay:
                wait = next_document_time - time.perf_counter()
                if wait > 0:
                    time.sleep(wait)
                next_document_time += delay

            if text_content is None:
                await ctx.logger.log("Received None text content, skipping document")
                continue

            try:
                document_count += 1

                if document_count % 10 == 0:  # Log every 10 documents
                    await ctx.logger.log(f"Yielding document {document_count}")

                yield ctx.outputs.default(
                    TextFrame(
                        text=text_content,
                        other_data=metadata
                    )
                )
            except Exception as e:
                await ctx.logger.log(
                    f"Error processing document {document_count}: {e}"
                )
                continue

        await ctx.logger.log(f"S3 document loader completed. Total documents processed: {document_count}")

    except Exception as e:
        await ctx.logger.log(f"Unhandled error in S3 document loader: {e}")
        print(f"Critical error: {e}")
        raise
    