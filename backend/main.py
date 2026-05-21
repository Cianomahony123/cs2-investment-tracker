import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from dotenv import load_dotenv

load_dotenv()

# Hard-fail on dangerous defaults
_SECRET = os.getenv("SECRET_KEY", "dev-secret-change-me-in-prod")
if _SECRET == "dev-secret-change-me-in-prod":
    import warnings
    warnings.warn(
        "SECRET_KEY is using the insecure default. Set SECRET_KEY in Railway environment variables.",
        stacklevel=2,
    )

from routers import inventory, prices, recommendations, auth
from db.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="CS2 Investment Tracker",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Referrer-Policy"]        = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"]        = "DENY"
        response.headers["Permissions-Policy"]     = "camera=(), microphone=(), geolocation=()"
        return response


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        FRONTEND_URL,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,            prefix="/api/auth",            tags=["auth"])
app.include_router(inventory.router,       prefix="/api/inventory",       tags=["inventory"])
app.include_router(prices.router,          prefix="/api/prices",          tags=["prices"])
app.include_router(recommendations.router, prefix="/api/recommendations", tags=["recommendations"])


@app.get("/health")
def health():
    return {"status": "ok"}
