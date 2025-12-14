"""
Chat Router - FastAPI Implementation
Handles chat requests with OpenAI Assistant API integration
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import os
import json
import re
import time
import logging

from .models import ChatRequest, ChatResponse, Product, ProductVariation

logger = logging.getLogger(__name__)

router = APIRouter()


def get_openai_client():
    """Get OpenAI client instance"""
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Missing OPENAI_API_KEY")

    return OpenAI(api_key=api_key)


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
        timeout=20
    )


async def fetch_products(product_ids: list[int]) -> list[dict]:
    """
    Fetch product details from WooCommerce

    Args:
        product_ids: List of WooCommerce product IDs

    Returns:
        List of product dictionaries with details
    """
    if not product_ids:
        return []

    wcapi = get_woocommerce_api()
    products_data = []

    try:
        ids_str = ",".join(map(str, product_ids))
        res = wcapi.get("products", params={"include": ids_str})

        if res.status_code != 200:
            logger.error(f"WooCommerce API error: {res.status_code} - {res.text}")
            return []

        for p in res.json():
            # Extract image
            img_src = ""
            if p.get('images') and len(p['images']) > 0:
                img_src = p['images'][0]['src']

            # Clean HTML from short_description
            short_desc = p.get('short_description', '')
            if short_desc:
                short_desc = re.sub(r'<[^>]+>', '', short_desc)
                short_desc = ' '.join(short_desc.split())

            # Get SKU
            sku = p.get('sku', '')

            # Check product type and fetch variations
            product_type = p.get('type', 'simple')
            variations = []
            in_stock_variations = []

            if product_type == 'variable':
                try:
                    var_res = wcapi.get(
                        f"products/{p.get('id')}/variations",
                        params={"per_page": 100}
                    )

                    if var_res.status_code == 200:
                        all_variations = var_res.json()

                        # Filter only in-stock variations
                        in_stock_variations = [
                            v for v in all_variations
                            if v.get('stock_status') == 'instock' and v.get('purchasable', True)
                        ]

                        # Limit to first 3 variations
                        for v in in_stock_variations[:3]:
                            var_name = v.get('name', '')
                            attributes = v.get('attributes', [])
                            attr_text = ', '.join([
                                f"{a.get('name')}: {a.get('option')}"
                                for a in attributes if a.get('option')
                            ])

                            variations.append({
                                "id": v.get('id'),
                                "name": attr_text or var_name,
                                "price": f"{v.get('price')} ₪",
                                "regular_price": f"{v.get('regular_price')} ₪",
                                "sale_price": f"{v.get('sale_price')} ₪" if v.get('sale_price') else "",
                                "on_sale": v.get('on_sale', False),
                                "sku": v.get('sku', '')
                            })
                except Exception as var_e:
                    logger.error(f"Variation fetch error: {var_e}")

            products_data.append({
                "id": p.get('id'),
                "name": p.get('name'),
                "sku": sku,
                "price": f"{p.get('price')} ₪",
                "regular_price": f"{p.get('regular_price')} ₪",
                "sale_price": f"{p.get('sale_price')} ₪",
                "on_sale": p.get('on_sale', False),
                "image": img_src,
                "short_description": short_desc,
                "permalink": p.get('permalink'),
                "add_to_cart_url": f"{os.getenv('WOO_BASE_URL')}/?add-to-cart={p.get('id')}",
                "type": product_type,
                "variations": variations,
                "has_more_variations": product_type == 'variable' and len(in_stock_variations) > 3
            })

    except Exception as e:
        logger.error(f"Error fetching products: {e}")

    return products_data


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Handle chat messages with OpenAI Assistant API

    This endpoint uses polling (will be upgraded to streaming in Phase 2)
    """
    try:
        client = get_openai_client()
        assistant_id = os.getenv("OPENAI_ASSISTANT_ID")

        if not assistant_id:
            raise HTTPException(status_code=500, detail="Missing OPENAI_ASSISTANT_ID")

        # Create or use existing thread
        thread_id = request.thread_id
        if not thread_id:
            thread = client.beta.threads.create()
            thread_id = thread.id

        # Add user message to thread
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=request.message
        )

        # Create run
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id
        )

        # Polling loop with timeout (will be replaced with streaming in Phase 2)
        start_time = time.time()
        timeout = 120  # 2 minutes

        while True:
            # Timeout protection
            if time.time() - start_time > timeout:
                return JSONResponse(
                    status_code=408,
                    content={
                        "reply": "הפעולה לקחה יותר מדי זמן (Timeout). נסה שוב.",
                        "thread_id": thread_id
                    }
                )

            # Check run status
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )

            if run_status.status == 'completed':
                # Get the assistant's response
                msgs = client.beta.threads.messages.list(thread_id=thread_id)
                reply = msgs.data[0].content[0].text.value

                # Clean citation markers
                reply = re.sub(r'【.*?】', '', reply)

                return ChatResponse(
                    reply=reply,
                    thread_id=thread_id
                )

            elif run_status.status == 'requires_action':
                # Handle tool calls (e.g., show_products)
                tool_calls = run_status.required_action.submit_tool_outputs.tool_calls

                for tool in tool_calls:
                    if tool.function.name == "show_products":
                        # Extract product IDs
                        args = json.loads(tool.function.arguments)
                        product_ids = args.get("product_ids", [])

                        # Fetch products from WooCommerce
                        products_data = await fetch_products(product_ids)

                        # Cancel the run (we're returning products directly)
                        client.beta.threads.runs.cancel(
                            thread_id=thread_id,
                            run_id=run.id
                        )

                        return ChatResponse(
                            action="show_products",
                            products=products_data,
                            reply="מצאתי את המוצרים הבאים:",
                            thread_id=thread_id
                        )

            elif run_status.status in ['failed', 'expired', 'cancelled']:
                error_msg = run_status.last_error.message if run_status.last_error else "Unknown AI Error"
                raise HTTPException(status_code=500, detail=f"AI Error: {error_msg}")

            # Wait before next poll
            time.sleep(0.5)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
