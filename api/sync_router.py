"""
Sync Router - Smart Catalog Synchronization with Redis Hash Checking
Prevents unnecessary uploads to OpenAI when catalog hasn't changed
"""
from fastapi import APIRouter, HTTPException
import os
import hashlib
import logging
from typing import Optional

from .models import SyncResponse

logger = logging.getLogger(__name__)

router = APIRouter()


def get_redis_client():
    """
    Get Redis client for caching
    Returns None if Redis is not configured (graceful degradation)
    """
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        logger.warning("REDIS_URL not configured, skipping hash checking")
        return None

    try:
        import redis
        return redis.from_url(redis_url, decode_responses=True)
    except ImportError:
        logger.warning("redis package not installed")
        return None
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        return None


def get_woocommerce_api():
    """Get WooCommerce API instance"""
    from woocommerce import API

    required_vars = ["WOO_BASE_URL", "WOO_CONSUMER_KEY", "WOO_CONSUMER_SECRET"]
    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        raise HTTPException(
            status_code=500,
            detail=f"Missing WooCommerce config: {', '.join(missing)}"
        )

    return API(
        url=os.getenv("WOO_BASE_URL"),
        consumer_key=os.getenv("WOO_CONSUMER_KEY"),
        consumer_secret=os.getenv("WOO_CONSUMER_SECRET"),
        version="wc/v3",
        timeout=60
    )


def get_openai_client():
    """Get OpenAI client instance"""
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Missing OPENAI_API_KEY")

    return OpenAI(api_key=api_key)


@router.get("/sync", response_model=SyncResponse)
async def sync_catalog():
    """
    Synchronize WooCommerce catalog with OpenAI Vector Store

    Smart synchronization:
    1. Fetch products from WooCommerce
    2. Format catalog text
    3. Calculate MD5 hash
    4. Compare with stored hash in Redis
    5. If unchanged, skip upload
    6. If changed, upload to Vector Store and update hash
    """
    try:
        # Get clients
        wcapi = get_woocommerce_api()
        redis_client = get_redis_client()

        # Fetch products from WooCommerce
        products_res = wcapi.get("products", params={"per_page": 100, "status": "publish"})

        if products_res.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail=f"WooCommerce Error {products_res.status_code}: {products_res.text}"
            )

        products = products_res.json()

        # Format catalog using centralized utility
        from utils.products import format_product_for_ai

        catalog_lines = []
        for product in products:
            catalog_lines.append(format_product_for_ai(product))

        catalog_text = "\n".join(catalog_lines)

        # Calculate hash
        catalog_hash = hashlib.md5(catalog_text.encode('utf-8')).hexdigest()

        # Check if catalog changed (using Redis if available)
        if redis_client:
            try:
                stored_hash = redis_client.get("catalog_hash")

                if stored_hash == catalog_hash:
                    logger.info("Catalog unchanged, skipping upload")
                    return SyncResponse(
                        status="skipped",
                        message="Catalog unchanged since last sync",
                        products_count=len(products),
                        skipped=True,
                        hash=catalog_hash
                    )
            except Exception as redis_error:
                logger.warning(f"Redis check failed: {redis_error}, proceeding with upload")

        # Catalog changed or Redis unavailable - proceed with upload
        logger.info(f"Catalog changed (hash: {catalog_hash}), uploading to OpenAI")

        # Save catalog to temporary file
        file_path = "/tmp/catalog.txt"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(catalog_text)

        # Upload to OpenAI Vector Store
        client = get_openai_client()
        assistant_id = os.getenv("OPENAI_ASSISTANT_ID")

        if not assistant_id:
            raise HTTPException(status_code=500, detail="Missing OPENAI_ASSISTANT_ID")

        my_assistant = client.beta.assistants.retrieve(assistant_id)
        tool_res = my_assistant.tool_resources

        # Get or create vector store
        vs_id = None
        if tool_res and tool_res.file_search and tool_res.file_search.vector_store_ids:
            vs_id = tool_res.file_search.vector_store_ids[0]

            # Delete old files from vector store
            for file in client.beta.vector_stores.files.list(vector_store_id=vs_id):
                try:
                    client.beta.vector_stores.files.delete(
                        vector_store_id=vs_id,
                        file_id=file.id
                    )
                except Exception as delete_error:
                    logger.warning(f"Failed to delete file {file.id}: {delete_error}")
        else:
            # Create new vector store
            vs = client.beta.vector_stores.create(name="ShopiPet Store")
            vs_id = vs.id

            # Update assistant with new vector store
            client.beta.assistants.update(
                assistant_id=assistant_id,
                tool_resources={"file_search": {"vector_store_ids": [vs_id]}}
            )

        # Upload new catalog file
        with open(file_path, "rb") as f:
            client.beta.vector_stores.files.upload_and_poll(
                vector_store_id=vs_id,
                file=f
            )

        # Update hash in Redis
        if redis_client:
            try:
                redis_client.set("catalog_hash", catalog_hash)
                redis_client.set("last_sync_timestamp", str(int(os.times().elapsed)))
                logger.info(f"Updated Redis hash: {catalog_hash}")
            except Exception as redis_error:
                logger.warning(f"Failed to update Redis hash: {redis_error}")

        return SyncResponse(
            status="success",
            message="Catalog synced successfully",
            products_count=len(products),
            vector_store_id=vs_id,
            skipped=False,
            hash=catalog_hash
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sync error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
