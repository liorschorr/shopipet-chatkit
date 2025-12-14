"""
ShopiPet ChatKit - FastAPI Entry Point
Main application with CORS, global exception handling, and router registration.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import traceback
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="ShopiPet ChatKit API",
    description="AI-powered chat widget for WooCommerce stores",
    version="2.0.0"
)

# Custom CORS middleware to ensure headers are always added
class CustomCORSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Handle preflight requests
        if request.method == "OPTIONS":
            return JSONResponse(
                content={},
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Max-Age": "3600",
                }
            )

        # Process the request
        response = await call_next(request)

        # Add CORS headers to response
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = "*"

        return response

# Add custom CORS middleware
app.add_middleware(CustomCORSMiddleware)

# Also add FastAPI CORS middleware as backup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catch all unhandled exceptions and return sanitized error response.
    Logs full traceback but only returns user-friendly message to client.
    """
    error_trace = traceback.format_exc()
    logger.error(f"Unhandled exception on {request.url.path}:\n{error_trace}")

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error occurred",
            "message": str(exc),
            # Only include trace in development/debugging
            # "trace": error_trace  # Uncomment for debugging
        }
    )


# Health check endpoint
@app.get("/")
async def root():
    """Root endpoint for health checks"""
    return {
        "status": "ok",
        "service": "ShopiPet ChatKit",
        "version": "2.0.0"
    }


@app.get("/api")
async def api_root():
    """API root endpoint"""
    return {
        "status": "ok",
        "endpoints": {
            "chat": "/api/chat",
            "sync": "/api/sync",
            "health": "/api/health"
        }
    }


@app.get("/api/health")
async def health_check():
    """Detailed health check endpoint"""
    import os

    # Check required environment variables
    required_vars = [
        "OPENAI_API_KEY",
        "OPENAI_ASSISTANT_ID",
        "WOO_BASE_URL",
        "WOO_CONSUMER_KEY",
        "WOO_CONSUMER_SECRET"
    ]

    missing_vars = [var for var in required_vars if not os.getenv(var)]

    return {
        "status": "healthy" if not missing_vars else "degraded",
        "environment": "configured" if not missing_vars else "incomplete",
        "missing_vars": missing_vars if missing_vars else None
    }


# Import and register routers
try:
    from .chat_router import router as chat_router
    app.include_router(chat_router, prefix="/api", tags=["chat"])
except ImportError as e:
    logger.warning(f"Chat router not available: {e}")

try:
    from .chat_streaming import router as chat_streaming_router
    app.include_router(chat_streaming_router, prefix="/api", tags=["chat-streaming"])
except ImportError as e:
    logger.warning(f"Streaming chat router not available: {e}")

try:
    from .sync_router import router as sync_router
    app.include_router(sync_router, prefix="/api", tags=["sync"])
except ImportError as e:
    logger.warning(f"Sync router not available: {e}")


# For Vercel serverless deployment
handler = app
