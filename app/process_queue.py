#!/usr/bin/env python3
"""
Script to process the webhook queue items.
This can be run as a scheduled task or triggered manually.
"""

import os
import time
from datetime import datetime
import logging
from app import db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def process_queue_item(item):
    """Process a single webhook queue item"""
    try:
        webhook_id = item['id']
        raw_data = item['raw_data']
        logger.info(f"Processing webhook queue item: {webhook_id}")
        
        # Here you can implement more sophisticated processing logic
        # For example, you might:
        # - Extract different types of data based on webhook content
        # - Create different types of alerts
        # - Trigger notifications
        # - Perform additional validation
        
        # For now, we'll just mark it as processed if it wasn't already
        if item['status'] == 'pending':
            db.update_webhook_status(webhook_id, 'processed')
            logger.info(f"Marked webhook {webhook_id} as processed")
        
        return True
    except Exception as e:
        logger.error(f"Error processing webhook {item.get('id', 'unknown')}: {e}")
        # Mark as error
        if 'id' in item:
            db.update_webhook_status(item['id'], 'error', str(e))
        return False

def process_queue(batch_size=10, sleep_seconds=1):
    """Process pending items in the webhook queue"""
    logger.info("Starting webhook queue processing")
    
    # Set AWS environment variables for DynamoDB Local if not set
    if "AWS_ENDPOINT_URL" not in os.environ:
        os.environ["AWS_ENDPOINT_URL"] = "http://localhost:8001"
        os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
        os.environ["AWS_ACCESS_KEY_ID"] = "fakeAccessKeyId"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "fakeSecretAccessKey"
    
    # Get pending items
    pending_items = db.get_webhook_queue_items(status='pending', limit=batch_size)
    logger.info(f"Found {len(pending_items)} pending webhook items")
    
    processed_count = 0
    error_count = 0
    
    # Process each item
    for item in pending_items:
        success = process_queue_item(item)
        if success:
            processed_count += 1
        else:
            error_count += 1
        
        # Sleep briefly between items to avoid overwhelming resources
        time.sleep(sleep_seconds)
    
    logger.info(f"Queue processing complete. Processed: {processed_count}, Errors: {error_count}")
    return {
        "processed": processed_count,
        "errors": error_count,
        "total": len(pending_items)
    }

if __name__ == "__main__":
    process_queue()
    print("Done! Queue processing complete.")