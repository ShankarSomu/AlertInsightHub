"""
API routes for webhook processing
"""

from fastapi import APIRouter, HTTPException
import logging
import sys
import os
from pathlib import Path

# Add the parent directory to sys.path
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import the process_webhook module
from app.process_webhook import process_pending_webhooks

router = APIRouter(prefix="/api/process", tags=["process"])
logger = logging.getLogger(__name__)

@router.post("/webhooks")
async def process_webhooks(limit: int = 10):
    """Process pending webhooks"""
    try:
        result = process_pending_webhooks(limit)
        return {
            "status": "success",
            "message": f"Processed {result['processed']} webhooks, {result['errors']} errors",
            "details": result
        }
    except Exception as e:
        logger.error(f"Error processing webhooks: {e}")
        raise HTTPException(status_code=500, detail=str(e))