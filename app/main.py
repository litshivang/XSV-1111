
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
from app.api import email_routes, health_routes
from app.config import settings
from app.utils.logger import get_logger
from app.agent import TravelAgent

logger = get_logger(__name__)

# Initialize the travel agent
travel_agent = TravelAgent()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("Starting AI Travel Agent application...")
    
    # Start background email processing
    asyncio.create_task(travel_agent.start_processing())
    
    yield
    
    logger.info("Shutting down AI Travel Agent application...")

# Create FastAPI app
app = FastAPI(
    title="AI Travel Agent",
    description="Automated travel inquiry processing and quote generation",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_routes.router, prefix="/health", tags=["health"])
app.include_router(email_routes.router, prefix="/api/emails", tags=["emails"])

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AI Travel Agent API",
        "version": "1.0.0",
        "status": "running"
    }

@app.post("/api/process-emails")
async def trigger_email_processing():
    """Manually trigger email processing"""
    try:
        result = await travel_agent.process_emails()
        return {
            "message": "Email processing completed",
            "processed": result.get("processed", 0),
            "failed": result.get("failed", 0)
        }
    except Exception as e:
        logger.error(f"Manual email processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=3000,
        reload=True
    )
