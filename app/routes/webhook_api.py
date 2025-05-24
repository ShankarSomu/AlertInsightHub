"""
API routes for webhook queue management
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime
from .. import db

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

@router.get("/queue")
async def get_queue_items(status: str = None, date: str = None, limit: int = 50):
    """Get webhook queue items, optionally filtered by status and date"""
    try:
        items = db.get_webhook_queue_items(status, date, limit)
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/queue/{webhook_id}")
async def get_queue_item(webhook_id: str):
    """Get a specific webhook queue item by ID"""
    try:
        # Get all items and filter by ID
        # This is inefficient but works for our simple example
        items = db.get_webhook_queue_items()
        for item in items:
            if item['id'] == webhook_id:
                return item
        
        raise HTTPException(status_code=404, detail="Webhook not found")
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/data/{webhook_id}")
async def get_webhook_data(webhook_id: str):
    """Get the raw data for a specific webhook"""
    try:
        # Get from postmark_data table
        dynamodb = db.get_dynamodb_client()
        table = dynamodb.Table('postmark_data')
        response = table.get_item(Key={'id': webhook_id})
        
        if 'Item' not in response:
            raise HTTPException(status_code=404, detail="Webhook data not found")
        
        return response['Item']
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/queue/{webhook_id}/reprocess")
async def reprocess_webhook(webhook_id: str):
    """Mark a webhook for reprocessing"""
    try:
        # Get the webhook item first
        items = db.get_webhook_queue_items()
        webhook_item = None
        for item in items:
            if item['id'] == webhook_id:
                webhook_item = item
                break
        
        if not webhook_item:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        # Update status to pending for reprocessing
        success = db.update_webhook_status(webhook_id, 'pending')
        if success:
            return {"status": "success", "message": f"Webhook {webhook_id} marked for reprocessing"}
        else:
            raise HTTPException(status_code=500, detail="Failed to update webhook status")
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_webhook_stats(date: str = None):
    """Get webhook queue statistics, optionally filtered by date"""
    try:
        stats = db.get_webhook_stats(date)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))