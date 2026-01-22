"""
═══════════════════════════════════════════════════════════════
 🌌 COSMIC AI - Document Upload Routes
═══════════════════════════════════════════════════════════════
"""

import os
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from config.settings import settings
from utils.file_handler import validate_file, save_upload_file
from services.document_processor import process_document
from services.vector_store import get_vector_store
from services.progress_service import get_progress_tracker
from utils.logger import setup_logger

logger = setup_logger()
progress_tracker = get_progress_tracker()

router = APIRouter(prefix="/api", tags=["documents"])


from services.graph_service import get_graph_service

@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    ┌─────────────────────────────────────────────┐
    │  📤 Upload and process a document           │
    └─────────────────────────────────────────────┘
    """
    
    logger.info("═" * 60)
    logger.info("📤 NEW DOCUMENT UPLOAD")
    logger.info("═" * 60)
    logger.info(f"   └─ Filename: {file.filename}")
    logger.info(f"   └─ Content-Type: {file.content_type}")
    
    # ─────────────────────────────────────
    # Step 0: Clear Previous Data (Fresh Start)
    # ─────────────────────────────────────
    logger.info("🧹 Clearing previous data (Clean Slate Mode)...")
    try:
        get_graph_service().clear_all()
        get_vector_store().clear_all()
        logger.info("✨ Previous data cleared successfully.")
    except Exception as e:
        logger.error(f"⚠️ Error clearing previous data: {e}")
        # We continue anyway, as it might just be empty

    # Validate file
    validate_file(file)
    
    # Save file to disk
    file_path, file_id = await save_upload_file(file)
    
    # Process document in background
    logger.info("🔄 Starting background processing...")
    
    # Mark as processing immediately so status endpoint finds it
    vector_store = get_vector_store()
    vector_store.mark_as_processing(file_id)
    
    background_tasks.add_task(process_document, file_path, file_id)
    
    return {
        "status": "processing",
        "file_id": file_id,
        "filename": file.filename,
        "message": "🚀 Document uploaded! Processing in background..."
    }


@router.get("/analyze/status/{file_id}")
async def get_analysis_status(file_id: str):
    """
    ┌─────────────────────────────────────────────┐
    │  📊 Get document analysis status            │
    │  (Enhanced with real-time progress)         │
    └─────────────────────────────────────────────┘
    """
    
    # Try to get from progress tracker first (more detailed)
    progress = progress_tracker.get_progress(file_id)
    
    if progress:
        logger.info(f"📊 Status check for: {file_id} - {progress['stage']}")
        return progress
    
    # Fallback to vector store status
    vector_store = get_vector_store()
    status = vector_store.get_document_status(file_id)
    
    logger.info(f"📊 Status check for: {file_id} - {status.get('status', 'unknown')}")
    
    return {
        "file_id": file_id,
        "status": status.get("status", "processing"),
        "chunks_count": status.get("chunks_count", 0),
        "stage": status.get("status", "unknown"),
        "progress": 0
    }


@router.websocket("/ws/progress/{file_id}")
async def websocket_progress(websocket: WebSocket, file_id: str):
    """
    ┌─────────────────────────────────────────────┐
    │  🔌 WebSocket for Real-time Progress        │
    │  Connect to receive live processing updates │
    └─────────────────────────────────────────────┘
    """
    await websocket.accept()
    
    try:
        # Register this connection for updates
        await progress_tracker.register_connection(file_id, websocket)
        
        # Send current progress immediately
        current_progress = progress_tracker.get_progress(file_id)
        if current_progress:
            await websocket.send_json(current_progress)
        
        logger.info(f"🔌 WebSocket connected for file: {file_id}")
        
        # Keep connection alive and wait for disconnect
        while True:
            # Just receive any messages (ping/pong)
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket disconnected for file: {file_id}")
    finally:
        # Unregister connection
        await progress_tracker.unregister_connection(file_id, websocket)


@router.get("/documents/{file_id}/view")
async def view_document(file_id: str):
    """
    ┌─────────────────────────────────────────────┐
    │  👁️ Serve document for PDF/Text preview     │
    └─────────────────────────────────────────────┘
    """
    
    logger.info(f"👁️ Document view request: {file_id}")
    
    # Search for file in upload directory
    for filename in os.listdir(settings.UPLOAD_DIR):
        if filename.startswith(file_id):
            file_path = os.path.join(settings.UPLOAD_DIR, filename)
            logger.info(f"   └─ Serving: {file_path}")
            return FileResponse(file_path)
    
    logger.warning(f"   └─ File not found: {file_id}")
    raise HTTPException(status_code=404, detail="File not found")


@router.get("/documents/{file_id}/text-preview")
async def get_document_text(file_id: str):
    """
    ┌─────────────────────────────────────────────┐
    │  📄 Get extracted text from vector store    │
    └─────────────────────────────────────────────┘
    """
    
    logger.info(f"📄 Text preview request: {file_id}")
    
    vector_store = get_vector_store()
    chunks = vector_store.get_all_chunks_for_file(file_id)
    
    if not chunks:
        logger.warning(f"   └─ No chunks found for: {file_id}")
        raise HTTPException(status_code=404, detail="Document content not found")
    
    logger.info(f"   └─ Returning {len(chunks)} chunks")
    
    return {
        "content": "\n\n".join(chunks),
        "chunks_count": len(chunks)
    }


@router.post("/clear-all")
async def clear_all_data():
    """
    ┌─────────────────────────────────────────────┐
    │  🗑️ CLEAR ALL DATA - Fresh Start             │
    └─────────────────────────────────────────────┘
    
    Clears all databases and uploaded files.
    Use this when starting a new session or project.
    """
    
    logger.info("═" * 60)
    logger.info("🗑️ CLEAR ALL DATA REQUEST")
    logger.info("═" * 60)
    
    try:
        # Clear Vector Store (includes FAISS index, chunks, uploaded files, BM25)
        vector_store = get_vector_store()
        vector_store.clear_all()
        
        # Clear Graph Database
        from services.graph_service import get_graph_service
        graph_service = get_graph_service()
        graph_service.clear_all()
        
        logger.info("✅ All data cleared successfully!")
        logger.info("═" * 60)
        
        return {
            "status": "success",
            "message": "✅ All data cleared! Ready for fresh start.",
            "details": {
                "vector_store": "cleared",
                "graph_database": "cleared",
                "bm25_index": "cleared",
                "uploaded_files": "cleared"
            }
        }
    
    except Exception as e:
        logger.error(f"❌ Error clearing data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear data: {str(e)}")

