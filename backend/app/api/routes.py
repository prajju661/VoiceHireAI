"""
API Routes for VoiceHire AI backend.

Defines the core application endpoints including root welcome and health check.
"""

from fastapi import APIRouter

# Initialize the API router
router = APIRouter()


@router.get("/", tags=["General"])
def get_root():
    """
    Root endpoint that provides an application welcome message.
    """
    return {
        "message": "Welcome to the VoiceHire AI Backend API",
        "application": "VoiceHire AI",
        "docs_url": "/docs"
    }


@router.get("/health", tags=["Health"])
def get_health():
    """
    Health check endpoint to verify backend operational status.
    Returns the required application health payload.
    """
    return {
        "status": "healthy",
        "application": "VoiceHire AI"
    }

