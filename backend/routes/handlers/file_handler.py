import logging
import os
import json
from pathlib import Path
from fastapi import WebSocket
from typing import Dict, Any
from core.conversation_manager import conversation_manager
from config.file_types import SUPPORTED_FILE_TYPES
from .base_handler import BaseHandler

logger = logging.getLogger(__name__)

class FileHandler(BaseHandler):
    """Handler for file and folder operations"""
    
    async def handle(self, data: Dict[str, Any]) -> bool:
        """Handle file-related messages"""
        
        if data.get('type') == 'scan_folder':
            await self._process_folder_scan(
                data.get('folder_path', ''),
                data.get('force_refresh', False)
            )
            return True
            
        return False
            
    async def _process_folder_scan(self, folder_path: str, force_refresh: bool = False):
        """Process a folder scan request"""
        try:
            result = await self._scan_folder(folder_path, force_refresh)
            logger.info(f"Scan result: {result['success']}, files found: {len(result.get('files', []))}")
            
            if result["success"]:
                await conversation_manager.add_folder_context(self.chat_id, result["folder_path"], result["files"])
                
            await self.send_json({
                "type": "folder_scan_result",
                **result
            })
        except Exception as e:
            self.log_error(f"Error scanning folder: {e}", e)
            await self.send_json({
                "type": "folder_scan_result",
                "success": False,
                "error": f"Error scanning folder: {str(e)}"
            })
    
    async def _scan_folder(self, folder_path: str, force_refresh: bool = False) -> dict:
        """Scan a folder for supported files"""
        try:
            logger.debug(f"Original folder path received: {folder_path}, force_refresh: {force_refresh}")
            
            # Handle relative vs absolute paths
            path = Path(folder_path)
            if not path.is_absolute():
                # Try Desktop path first
                desktop_path = Path(os.path.expanduser('~')) / 'Desktop' / folder_path
                if desktop_path.exists() and desktop_path.is_dir():
                    path = desktop_path
                    logger.debug(f"Found path on Desktop: {path}")
                else:
                    # Try Documents folder
                    documents_path = Path(os.path.expanduser('~')) / 'Documents' / folder_path
                    if documents_path.exists() and documents_path.is_dir():
                        path = documents_path
                        logger.debug(f"Found path in Documents: {path}")
                    else:
                        # If not found in common locations, use current directory
                        cwd_path = Path.cwd() / folder_path
                        logger.debug(f"Using current directory path: {cwd_path}")
                        path = cwd_path
            
            path = path.resolve()
            logger.debug(f"Resolved path: {path}")
                
            if not path.exists():
                logger.error(f"Path does not exist: {path}")
                return {
                    "success": False,
                    "error": f"Folder not found: {path}"
                }
                
            if not path.is_dir():
                logger.error(f"Path is not a directory: {path}")
                return {
                    "success": False,
                    "error": f"Not a folder: {path}"
                }

            files = []
            supported_extensions = SUPPORTED_FILE_TYPES['extensions']
            
            # Clear cache by reading directory contents
            if force_refresh:
                logger.info(f"Forcing refresh of folder: {path}")
            
            for file_path in path.rglob("*"):
                if file_path.is_file():
                    extension = file_path.suffix.lower()
                    if extension in supported_extensions:
                        try:
                            # Re-read file content every time to get the latest version
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                relative_path = str(file_path.relative_to(path))
                                files.append({
                                    "name": file_path.name,
                                    "path": relative_path,
                                    "full_path": str(file_path),
                                    "type": extension,
                                    "content": content,
                                    "language": SUPPORTED_FILE_TYPES['language_map'].get(extension, 'plaintext')
                                })
                        except Exception as e:
                            logger.error(f"Error reading file {file_path}: {e}")
                            continue
                            
            if not files:
                logger.error(f"No supported files found in folder: {path}")
                return {
                    "success": False,
                    "error": f"No supported files found in folder: {path}"
                }
                            
            return {
                "success": True,
                "folder_path": str(path),
                "files": files
            }
        except Exception as e:
            logger.error(f"Error scanning folder: {e}")
            return {
                "success": False,
                "error": f"Error scanning folder: {str(e)}"
            }