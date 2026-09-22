"""
Main FastAPI Application Entrypoint.
Automated PII Anonymization & Redaction Engine
DPDP Act 2023 Compliance
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.config import settings
from backend.app.api.routes import router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "Production-grade PII detection, irreversible redaction, and forensic sanitization engine "
        "engineered for Indian public administrative records, compliant with the Digital Personal Data Protection (DPDP) Act 2023."
    ),
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for frontend review dashboards
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/")
async def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "compliance": settings.COMPLIANCE_STANDARD,
        "documentation": "/docs",
        "health": "/api/v1/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
