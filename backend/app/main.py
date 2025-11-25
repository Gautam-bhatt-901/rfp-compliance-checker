"""
FastAPI Main Application
RFP Compliance Checker Backend
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn

from app.database import engine, Base
from app.routers import auth, rfp, files
from app import config

# Create database tables
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management"""
    # Startup
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created")
    print(f"✓ Server starting on http://localhost:8000")
    yield
    # Shutdown
    print("✓ Server shutting down")

# Initialize FastAPI app
app = FastAPI(
    title="RFP Compliance Checker API",
    description="Analyze RFP documents and match requirements with provided documents",
    version="2.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(rfp.router, prefix="/api/rfp", tags=["RFP Analysis"])
app.include_router(files.router, prefix="/api/files", tags=["File Management"])

# Health check endpoint
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "openai_available": bool(config.OPENAI_API_KEY),
        "anthropic_available": bool(config.ANTHROPIC_API_KEY)
    }

@app.get("/")
async def root():
    return {"message": "RFP Compliance Checker API v2.0", "docs": "/docs"}

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
