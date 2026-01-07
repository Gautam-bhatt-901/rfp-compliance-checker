"""
FastAPI Main Application - OPTIMIZED VERSION
Includes database initialization + performance optimizations
"""

import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import sys
import logging

# Import database components
from app.database import engine, Base
from app.config import CORS_ORIGINS

# Import routers
from app.routers import analysis, auth, rfp, files

# Configure logging
if sys.platform == 'win32':
    import codecs
    # Force UTF-8 encoding on stdout/stderr
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Configure logging with UTF-8 encoding
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


# ============ LIFESPAN EVENTS (Startup/Shutdown) ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events
    Handles startup and shutdown tasks
    """
    # ========== STARTUP ==========
    logger.info("=" * 70)
    logger.info("RFP COMPLIANCE APPLICATION - STARTING")
    logger.info("=" * 70)
    
    # 1. Initialize Database (YOUR ORIGINAL CODE)
    try:
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("[OK] Database tables created/verified")
    except Exception as e:
        logger.error(f"[FAIL] Database initialization failed: {e}")
        raise
    
    # 2. Display Optimization Status
    from app.config import (
        ENABLE_BACKGROUND_PROCESSING,
        ENABLE_PARALLEL_PROCESSING,
        ENABLE_CHUNKED_PROCESSING,
        ENABLE_CACHE,
        CACHE_BACKEND,
        MAX_WORKER_PROCESSES,
        MAX_PDF_SIZE_MB,
        DATABASE_URL
    )
    
    logger.info("Configuration:")
    logger.info(f"  Database: {DATABASE_URL[:50]}...")
    logger.info(f"  Background Processing: {'ENABLED' if ENABLE_BACKGROUND_PROCESSING else 'DISABLED'}")
    logger.info(f"  Parallel Processing: {'ENABLED' if ENABLE_PARALLEL_PROCESSING else 'DISABLED'}")
    logger.info(f"    - Max Workers: {MAX_WORKER_PROCESSES if MAX_WORKER_PROCESSES > 0 else 'Auto-detect'}")
    logger.info(f"  Chunked Processing: {'ENABLED' if ENABLE_CHUNKED_PROCESSING else 'DISABLED'}")
    logger.info(f"  Caching: {'ENABLED' if ENABLE_CACHE else 'DISABLED'} (Backend: {CACHE_BACKEND})")
    logger.info(f"  Max PDF Size: {MAX_PDF_SIZE_MB}MB")
    
    # 3. Initialize Global Components
    try:
        from app.parallel_processor import get_parallel_processor
        from app.cache import get_cache
        
        # Initialize parallel processor
        if ENABLE_PARALLEL_PROCESSING:
            processor = get_parallel_processor()
            logger.info(f"[OK] Parallel processor initialized ({processor.max_workers} workers)")
        
        # Initialize cache
        if ENABLE_CACHE:
            cache = get_cache()
            cache_backend = cache.backend.__class__.__name__ if cache.backend else 'None'
            logger.info(f"[OK] Cache initialized (Backend: {cache_backend})")
            
    except Exception as e:
        logger.warning(f"[WARNING] Optional component initialization failed: {e}")
    
    # 4. Create required directories
    from app.config import DATA_DIR, UPLOAD_RFP_DIR, UPLOAD_DOCS_DIR
    import os
    
    for directory in [DATA_DIR, UPLOAD_RFP_DIR, UPLOAD_DOCS_DIR]:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"[OK] Directory ready: {directory}")
    
    logger.info("=" * 70)
    logger.info("APPLICATION STARTED SUCCESSFULLY")
    logger.info("=" * 70)
    
    yield  # Application runs here
    
    # ========== SHUTDOWN ==========
    logger.info("=" * 70)
    logger.info("APPLICATION SHUTTING DOWN...")
    logger.info("=" * 70)
    
    # 1. Shutdown parallel processor
    try:
        from app.parallel_processor import get_parallel_processor
        if ENABLE_PARALLEL_PROCESSING:
            processor = get_parallel_processor()
            processor.shutdown(wait=True)
            logger.info("[OK] Parallel processor shutdown complete")
    except Exception as e:
        logger.warning(f"[WARNING] Parallel processor shutdown error: {e}")
    
    # 2. Close database connections (if needed)
    try:
        engine.dispose()
        logger.info("[OK] Database connections closed")
    except Exception as e:
        logger.warning(f"[WARNING] Database cleanup error: {e}")
    
    # 3. Clear cache (optional - you may want to persist cache)
    # Uncomment if you want to clear cache on shutdown:
    # try:
    #     from app.cache import get_cache
    #     if ENABLE_CACHE:
    #         cache = get_cache()
    #         cache.clear_all()
    #         logger.info("[OK] Cache cleared")
    # except Exception as e:
    #     logger.warning(f"[WARNING] Cache cleanup error: {e}")
    
    logger.info("=" * 70)
    logger.info("SHUTDOWN COMPLETE")
    logger.info("=" * 70)


# ============ CREATE FASTAPI APP ============

app = FastAPI(
    title="RFP Compliance Checker API",
    description="AI-powered RFP document compliance checker with optimized performance",
    version="2.0.0",
    lifespan=lifespan  # Add lifespan context manager
)


# ============ MIDDLEWARE ============

# 1. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Trusted Host Middleware (Security)
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["*"]  # Configure for production: ["yourdomain.com"]
)

# 3. Request Logging Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Log all requests with timing and status
    """
    start_time = time.time()
    
    # Log request
    logger.info(f"→ {request.method} {request.url.path} from {request.client.host}")
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Log response
    status_emoji = "[OK]" if response.status_code < 400 else "[FAIL]"
    logger.info(
        f"{status_emoji} {request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Duration: {duration:.2f}s"
    )
    
    return response


# 4. Error Handling Middleware
@app.middleware("http")
async def error_handling_middleware(request: Request, call_next):
    """
    Global error handler
    """
    try:
        return await call_next(request)
    except Exception as e:
        logger.error(f"Unhandled error: {e}", exc_info=True)
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": "An unexpected error occurred. Please contact support.",
                "detail": str(e) if app.debug else None
            }
        )


# ============ INCLUDE ROUTERS ============

app.include_router(auth.router)
app.include_router(analysis.router)
app.include_router(rfp.router)
app.include_router(files.router)


# ============ ROOT ENDPOINTS ============

@app.get("/")
async def root():
    """
    API root endpoint with status information
    """
    from app.config import (
        ENABLE_BACKGROUND_PROCESSING,
        ENABLE_PARALLEL_PROCESSING,
        ENABLE_CACHE,
        CACHE_BACKEND
    )
    
    return {
        "application": "RFP Compliance Checker API",
        "version": "2.0.0",
        "status": "running",
        "features": {
            "background_processing": ENABLE_BACKGROUND_PROCESSING,
            "parallel_processing": ENABLE_PARALLEL_PROCESSING,
            "caching": ENABLE_CACHE,
            "cache_backend": CACHE_BACKEND if ENABLE_CACHE else None
        },
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "auth": "/api/auth",
            "analysis": "/api/analysis"
        }
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring
    """
    from app.config import ENABLE_CACHE
    
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "checks": {}
    }
    
    # Check database
    try:
        from app.database import SessionLocal
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        health_status["checks"]["database"] = "ok"
    except Exception as e:
        health_status["checks"]["database"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"
    
    # Check cache (if enabled)
    if ENABLE_CACHE:
        try:
            from app.cache import get_cache
            cache = get_cache()
            cache.backend.set("health_check", "ok", ttl=10)
            result = cache.backend.get("health_check")
            health_status["checks"]["cache"] = "ok" if result == "ok" else "error"
        except Exception as e:
            health_status["checks"]["cache"] = f"error: {str(e)}"
    
    # Check parallel processor
    try:
        from app.parallel_processor import get_parallel_processor
        processor = get_parallel_processor()
        health_status["checks"]["parallel_processor"] = {
            "status": "ok",
            "workers": processor.max_workers
        }
    except Exception as e:
        health_status["checks"]["parallel_processor"] = f"error: {str(e)}"
    
    return health_status


@app.get("/metrics")
async def metrics():
    """
    Application metrics endpoint (for monitoring/observability)
    """
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    
    metrics_data = {
        "system": {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_mb": process.memory_info().rss / (1024 * 1024),
            "memory_percent": process.memory_percent()
        },
        "application": {
            "uptime_seconds": time.time() - process.create_time()
        }
    }
    
    # Add cache stats if enabled
    from app.config import ENABLE_CACHE
    if ENABLE_CACHE:
        try:
            from app.cache import get_cache
            cache = get_cache()
            
            if hasattr(cache.backend, 'cache'):  # MemoryCache
                metrics_data["cache"] = {
                    "backend": "memory",
                    "size": len(cache.backend.cache),
                    "max_size": cache.backend.max_size
                }
            elif hasattr(cache.backend, 'client'):  # RedisCache
                info = cache.backend.client.info()
                metrics_data["cache"] = {
                    "backend": "redis",
                    "keys": info.get('db0', {}).get('keys', 0),
                    "memory_mb": info.get('used_memory', 0) / (1024 * 1024)
                }
        except Exception as e:
            metrics_data["cache"] = {"error": str(e)}
    
    return metrics_data


# ============ DEVELOPMENT MODE ============

if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting in development mode...")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes
        log_level="info"
    )
