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

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router

# Load environment variables from .env file if available
load_dotenv()

# Initialize FastAPI application
app = FastAPI(
    title="VoiceHire AI",
    description="Backend API for VoiceHire AI - AI-powered voice interview screening platform",
    version="0.1.0",
)

# Configure CORS (Cross-Origin Resource Sharing)
# Allows the React frontend running on localhost:5173 to communicate with this backend
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(router)

