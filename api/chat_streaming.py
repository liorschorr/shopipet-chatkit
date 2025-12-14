"""
Streaming Chat Router - FastAPI Implementation with OpenAI Streaming
This replaces the polling mechanism with real-time streaming responses
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import os
import json
import re
import logging
from typing import AsyncGenerator

from .models import ChatRequest
from .chat_router import get_openai_client, get_woocommerce_api, fetch_products

logger = logging.getLogger(__name__)

router = APIRouter()


async def stream_chat_response(
    client,
    thread_id: str,
    assistant_id: str,
    user_message: str
) -> AsyncGenerator[str, None]:
    """
    Stream chat responses from OpenAI Assistant API

    Yields Server-Sent Events (SSE) formatted chunks:
    - data: {"type": "text", "content": "..."} for text deltas
    - data: {"type": "products", "data": [...]} for product displays
    - data: {"type": "done", "thread_id": "..."} when complete
    """
    try:
        # Add user message to thread
        await client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_message
        )

        # Create streaming run
        async with client.beta.threads.runs.stream(
            thread_id=thread_id,
            assistant_id=assistant_id,
            event_handler=None  # We'll handle events manually
        ) as stream:

            accumulated_text = ""

            async for event in stream:
                event_type = event.event

                # Handle text deltas (streaming text response)
                if event_type == "thread.message.delta":
                    delta = event.data.delta
                    if delta.content:
                        for content_block in delta.content:
                            if hasattr(content_block, 'text') and content_block.text:
                                text_delta = content_block.text.value

                                # Clean citation markers
                                text_delta = re.sub(r'【.*?】', '', text_delta)

                                accumulated_text += text_delta

                                # Yield text delta to frontend
                                yield f"data: {json.dumps({'type': 'text', 'content': text_delta})}\n\n"

                # Handle tool calls (e.g., show_products)
                elif event_type == "thread.run.requires_action":
                    run = event.data
                    tool_calls = run.required_action.submit_tool_outputs.tool_calls

                    for tool in tool_calls:
                        if tool.function.name == "show_products":
                            # Extract product IDs
                            args = json.loads(tool.function.arguments)
                            product_ids = args.get("product_ids", [])

                            # Fetch products from WooCommerce
                            products_data = await fetch_products(product_ids)

                            # Yield products event
                            yield f"data: {json.dumps({'type': 'products', 'data': products_data})}\n\n"

                            # Cancel the run since we're handling products client-side
                            await client.beta.threads.runs.cancel(
                                thread_id=thread_id,
                                run_id=run.id
                            )
                            break

                # Handle completion
                elif event_type == "thread.run.completed":
                    yield f"data: {json.dumps({'type': 'done', 'thread_id': thread_id})}\n\n"
                    break

                # Handle errors
                elif event_type == "thread.run.failed":
                    run = event.data
                    error_msg = run.last_error.message if run.last_error else "Unknown error"
                    yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
                    break

                elif event_type in ["thread.run.expired", "thread.run.cancelled"]:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'Run was cancelled or expired'})}\n\n"
                    break

    except Exception as e:
        logger.error(f"Streaming error: {e}")
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Streaming chat endpoint using Server-Sent Events (SSE)

    Returns a stream of events:
    - Text deltas as they're generated
    - Product data when show_products is called
    - Completion signal when done

    Frontend should use EventSource or fetch with stream processing
    """
    try:
        client = get_openai_client()
        assistant_id = os.getenv("OPENAI_ASSISTANT_ID")

        if not assistant_id:
            raise HTTPException(status_code=500, detail="Missing OPENAI_ASSISTANT_ID")

        # Create or use existing thread
        thread_id = request.thread_id
        if not thread_id:
            thread = await client.beta.threads.create()
            thread_id = thread.id

            # Send thread_id immediately so frontend can store it
            async def init_stream():
                yield f"data: {json.dumps({'type': 'thread_id', 'thread_id': thread_id})}\n\n"
                async for chunk in stream_chat_response(
                    client, thread_id, assistant_id, request.message
                ):
                    yield chunk

            return StreamingResponse(
                init_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"  # Disable nginx buffering
                }
            )
        else:
            return StreamingResponse(
                stream_chat_response(client, thread_id, assistant_id, request.message),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat stream error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
