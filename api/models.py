"""
Pydantic models for request/response validation
"""
from pydantic import BaseModel, Field
from typing import Optional, List


class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    message: str = Field(..., min_length=1, max_length=10000, description="User message")
    thread_id: Optional[str] = Field(None, description="OpenAI thread ID for conversation continuity")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "אני מחפש מזון לכלב",
                "thread_id": "thread_abc123"
            }
        }


class ProductVariation(BaseModel):
    """Product variation model"""
    id: int
    name: str
    price: str
    regular_price: str
    sale_price: str = ""
    on_sale: bool = False
    sku: str = ""


class Product(BaseModel):
    """Product model for display"""
    id: int
    name: str
    sku: str
    price: str
    regular_price: str
    sale_price: str
    on_sale: bool
    image: str
    short_description: str
    permalink: str
    add_to_cart_url: str
    type: str = "simple"
    variations: List[ProductVariation] = []
    has_more_variations: bool = False


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""
    reply: Optional[str] = None
    thread_id: str
    action: Optional[str] = None
    products: Optional[List[Product]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "reply": "מצאתי כמה מוצרים שמתאימים לך",
                "thread_id": "thread_abc123",
                "action": None,
                "products": None
            }
        }


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    message: Optional[str] = None
    trace: Optional[str] = None


class SyncResponse(BaseModel):
    """Response model for sync endpoint"""
    status: str
    message: str
    products_count: Optional[int] = None
    vector_store_id: Optional[str] = None
    skipped: Optional[bool] = False
    hash: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "Catalog synced successfully",
                "products_count": 150,
                "vector_store_id": "vs_abc123",
                "skipped": False
            }
        }
