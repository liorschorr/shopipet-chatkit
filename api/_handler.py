"""
Vercel Serverless Handler Wrapper
This file ensures proper ASGI handling for Vercel
"""
from mangum import Mangum
from .index import app

# Mangum handler for Vercel
handler = Mangum(app, lifespan="off")
