"""
Main application entry point for VoiceHire AI FastAPI backend.

This module sets up the FastAPI application, configures CORS middleware
to allow communication from the frontend, and registers the API routes.
"""

import sys
from pathlib import Path

# Ensure the backend directory is in the Python module search path.
# This allows running the server from either the project root or backend folder.
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as general_router
from app.api.speech import router as speech_router
from app.core.config import settings

# Initialize FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for VoiceHire AI - AI-powered voice interview screening platform",
    version=settings.VERSION,
)

# Configure CORS (Cross-Origin Resource Sharing)
# Allows the React frontend running on localhost:5173 to communicate with this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(general_router)
app.include_router(speech_router)
