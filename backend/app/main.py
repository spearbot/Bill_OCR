import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.auth import router as auth_router
from app.bills import router as bills_router
from app.admin import router as admin_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.DATA_DIR, exist_ok=True)

    # Ensure admin user exists
    from app.store import get_user_by_email, create_user, load_users
    from app.security import get_password_hash
    from datetime import datetime
    import uuid
    admin = get_user_by_email("admin@billocr.com")
    if not admin:
        create_user({
            "id": str(uuid.uuid4()),
            "name": "Admin",
            "email": "admin@billocr.com",
            "password_hash": get_password_hash("admin123456"),
            "role": "admin",
            "is_active": "true",
            "created_at": datetime.now().isoformat(),
        })
        logger.info("Admin user created (admin@billocr.com / admin123456)")

    logger.info("Startup complete")
    yield
    logger.info("Shutdown complete")


app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

app.include_router(auth_router)
app.include_router(bills_router)
app.include_router(admin_router)


@app.exception_handler(Exception)
async def global_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/api/health")
async def health():
    return {"status": "healthy", "version": settings.APP_VERSION}


@app.get("/")
async def root():
    return {"message": "Medical Bill OCR API", "docs": "/docs", "version": settings.APP_VERSION}
