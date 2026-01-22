"""
═══════════════════════════════════════════════════════════════
 📊 COSMIC AI - Real-time Progress Tracking Service
═══════════════════════════════════════════════════════════════
"""

import asyncio
from typing import Dict, List, Optional, Set
from datetime import datetime
from enum import Enum

class ProcessingStage(str, Enum):
    """Document processing stages"""
    UPLOADING = "uploading"
    PARSING = "parsing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    VECTOR_STORING = "vector_storing"
    BM25_INDEXING = "bm25_indexing"
    ENTITY_EXTRACTION = "entity_extraction"
    GRAPH_BUILDING = "graph_building"
    COMPLETED = "completed"
    FAILED = "failed"

class ProgressTracker:
    """
    ┌─────────────────────────────────────────────┐
    │  📊 Real-time Progress Tracker              │
    │                                             │
    │  • Track document processing stages         │
    │  • Broadcast updates to connected clients   │
    │  • Provide detailed progress information    │
    └─────────────────────────────────────────────┘
    """
    
    def __init__(self):
        # Storage for all file progress
        self.progress_data: Dict[str, Dict] = {}
        
        # WebSocket connections (file_id -> set of websocket connections)
        self.connections: Dict[str, Set] = {}
        
        # Stage metadata with emoji and descriptions
        self.stage_info = {
            ProcessingStage.UPLOADING: {
                "emoji": "📤",
                "display": "Uploading Document",
                "description": "Receiving and validating file"
            },
            ProcessingStage.PARSING: {
                "emoji": "📋",
                "display": "Parsing Document",
                "description": "Extracting text from document"
            },
            ProcessingStage.CHUNKING: {
                "emoji": "✂️",
                "display": "Chunking Text",
                "description": "Splitting into semantic segments"
            },
            ProcessingStage.EMBEDDING: {
                "emoji": "🧠",
                "display": "Generating Embeddings",
                "description": "Creating vector representations"
            },
            ProcessingStage.VECTOR_STORING: {
                "emoji": "💾",
                "display": "Storing Vectors",
                "description": "Saving to vector database"
            },
            ProcessingStage.BM25_INDEXING: {
                "emoji": "🔨",
                "display": "Building BM25 Index",
                "description": "Creating keyword search index"
            },
            ProcessingStage.ENTITY_EXTRACTION: {
                "emoji": "🧩",
                "display": "Extracting Entities",
                "description": "Identifying key concepts and relationships"
            },
            ProcessingStage.GRAPH_BUILDING: {
                "emoji": "🕸️",
                "display": "Building Knowledge Graph",
                "description": "Constructing relationship network"
            },
            ProcessingStage.COMPLETED: {
                "emoji": "🎉",
                "display": "Processing Complete",
                "description": "Document ready for queries"
            },
            ProcessingStage.FAILED: {
                "emoji": "❌",
                "display": "Processing Failed",
                "description": "An error occurred"
            }
        }
    
    def start_processing(self, file_id: str, filename: str, total_stages: int = 8):
        """Initialize progress tracking for a file"""
        self.progress_data[file_id] = {
            "file_id": file_id,
            "filename": filename,
            "stage": ProcessingStage.UPLOADING,
            "progress": 0,
            "total_stages": total_stages,
            "current_stage_num": 0,
            "details": {},
            "started_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "error": None
        }
        
    def update_stage(
        self, 
        file_id: str, 
        stage: ProcessingStage, 
        details: Optional[Dict] = None,
        stage_num: Optional[int] = None
    ):
        """Update the current processing stage"""
        if file_id not in self.progress_data:
            return
            
        progress_info = self.progress_data[file_id]
        progress_info["stage"] = stage
        progress_info["updated_at"] = datetime.now().isoformat()
        
        if stage_num is not None:
            progress_info["current_stage_num"] = stage_num
            progress_info["progress"] = int((stage_num / progress_info["total_stages"]) * 100)
        
        if details:
            progress_info["details"].update(details)
        
        # Broadcast update
        asyncio.create_task(self._broadcast_update(file_id))
    
    def update_substage(self, file_id: str, message: str, current: int = None, total: int = None):
        """Update substage progress (e.g., "Batch 5/10")"""
        if file_id not in self.progress_data:
            return
            
        self.progress_data[file_id]["details"]["substage"] = message
        if current is not None and total is not None:
            self.progress_data[file_id]["details"]["substage_progress"] = {
                "current": current,
                "total": total,
                "percent": int((current / total) * 100) if total > 0 else 0
            }
        
        self.progress_data[file_id]["updated_at"] = datetime.now().isoformat()
        asyncio.create_task(self._broadcast_update(file_id))
    
    def mark_completed(self, file_id: str, summary: Optional[Dict] = None):
        """Mark processing as completed"""
        if file_id not in self.progress_data:
            return
            
        self.progress_data[file_id]["stage"] = ProcessingStage.COMPLETED
        self.progress_data[file_id]["progress"] = 100
        self.progress_data[file_id]["current_stage_num"] = self.progress_data[file_id]["total_stages"]
        self.progress_data[file_id]["completed_at"] = datetime.now().isoformat()
        
        if summary:
            self.progress_data[file_id]["summary"] = summary
        
        asyncio.create_task(self._broadcast_update(file_id))
    
    def mark_failed(self, file_id: str, error: str):
        """Mark processing as failed"""
        if file_id not in self.progress_data:
            return
            
        self.progress_data[file_id]["stage"] = ProcessingStage.FAILED
        self.progress_data[file_id]["error"] = error
        self.progress_data[file_id]["failed_at"] = datetime.now().isoformat()
        
        asyncio.create_task(self._broadcast_update(file_id))
    
    def get_progress(self, file_id: str) -> Optional[Dict]:
        """Get current progress for a file"""
        progress = self.progress_data.get(file_id)
        if not progress:
            return None
            
        # Enrich with stage info
        stage = progress["stage"]
        stage_meta = self.stage_info.get(stage, {})
        
        return {
            **progress,
            "stage_emoji": stage_meta.get("emoji", "📄"),
            "stage_display": stage_meta.get("display", stage),
            "stage_description": stage_meta.get("description", "")
        }
    
    async def register_connection(self, file_id: str, websocket):
        """Register a WebSocket connection for progress updates"""
        if file_id not in self.connections:
            self.connections[file_id] = set()
        self.connections[file_id].add(websocket)
    
    async def unregister_connection(self, file_id: str, websocket):
        """Unregister a WebSocket connection"""
        if file_id in self.connections:
            self.connections[file_id].discard(websocket)
            if not self.connections[file_id]:
                del self.connections[file_id]
    
    async def _broadcast_update(self, file_id: str):
        """Broadcast progress update to all connected clients"""
        if file_id not in self.connections:
            return
            
        progress = self.get_progress(file_id)
        if not progress:
            return
        
        # Send to all connected websockets
        dead_connections = set()
        for websocket in self.connections[file_id]:
            try:
                await websocket.send_json(progress)
            except Exception:
                dead_connections.add(websocket)
        
        # Remove dead connections
        for websocket in dead_connections:
            self.connections[file_id].discard(websocket)


# Global singleton instance
_progress_tracker = None

def get_progress_tracker() -> ProgressTracker:
    """Get or create progress tracker singleton"""
    global _progress_tracker
    if _progress_tracker is None:
        _progress_tracker = ProgressTracker()
    return _progress_tracker
