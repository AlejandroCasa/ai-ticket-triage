import logging
import os
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

# from src.adapters.gemini_adapter import GeminiAdapter
from src.adapters.ollama_adapter import OllamaAdapter
from src.api.schemas import ClassificationRequest, ClassificationResponse
from src.core.config import get_categories, load_config
from src.core.database import Ticket, init_db
from src.core.semantic_cache import SemanticCache

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("API")

app_state = {}

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # Initialize infrastructure on startup
#     logger.info("🚀 Starting API Gateway in Asynchronous Mode...")
    
#     app_state["categories"] = get_categories(load_config("config.yaml"))
    
#     # Ensure data directory exists if running via Docker Compose
#     os.makedirs("/app/data", exist_ok=True)
#     app_state["SessionLocal"] = init_db(os.getenv("DB_URL", "sqlite:////app/data/tickets.db"))
    
#     app_state["semantic_cache"] = SemanticCache(persist_directory="/app/chroma_data")

#     api_key = os.getenv("GEMINI_API_KEY")
#     if api_key:
#         app_state["classifier"] = GeminiAdapter(api_key)
#         logger.info("🤖 AI Adapter connected.")
#     else:
#         app_state["classifier"] = None

#     yield
#     logger.info("🛑 Shutting down API Gateway...")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting API Gateway in Asynchronous Mode...")

    app_state["categories"] = get_categories(load_config("config.yaml"))
    os.makedirs("/app/data", exist_ok=True)
    app_state["SessionLocal"] = init_db(os.getenv("DB_URL", "sqlite:////app/data/tickets.db"))
    app_state["semantic_cache"] = SemanticCache(persist_directory="/app/chroma_data")

    # --- SWAP THE LLM PROVIDER HERE ---
    # We bypass Gemini and inject the local Ollama adapter
    app_state["classifier"] = OllamaAdapter(host="http://ollama:11434", model_name="llama3")
    logger.info("🧠 Sovereign Local AI Adapter connected.")

    yield
    logger.info("🛑 Shutting down API Gateway...")

app = FastAPI(title="AI Triage Engine API", lifespan=lifespan)

def get_db():
    # Dependency injection for database sessions
    db = app_state["SessionLocal"]()
    try:
        yield db
    finally:
        db.close()

# --- THE BACKGROUND WORKER ---
def process_ticket_background(ticket_id: int, description: str) -> None:
    """
    Background worker that handles heavy I/O operations (ChromaDB & Gemini).
    Executes independently of the main HTTP response thread.
    """
    # Create a fresh database session for the background thread to prevent lockups
    db: Session = app_state["SessionLocal"]()
    try:
        semantic_cache: SemanticCache = app_state["semantic_cache"]
        classifier: GeminiAdapter = app_state["classifier"]
        
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            logger.error(f"Worker failed: Ticket {ticket_id} not found.")
            return

        # 1. Semantic Shield Check (Zero API Cost)
        cached_category = semantic_cache.check_cache(description)
        if cached_category:
            ticket.category = cached_category
            ticket.status = "Classified_By_Cache"
            db.commit()
            return

        if not classifier:
            ticket.status = "Failed_No_AI"
            db.commit()
            return

        # 2. RAG: Fetch Context & Call LLM
        past_examples = semantic_cache.get_similar_examples(description, limit=3)
        category = classifier.classify_ticket(
            description=description, 
            categories=app_state["categories"], 
            context_examples=past_examples
        )
        
        # 3. Persistence & Cache Teaching
        ticket.category = category
        ticket.status = "Classified_By_AI"
        db.commit()
        
        semantic_cache.add_to_cache(str(ticket_id), description, category)
        logger.info(f"✅ Background job complete for Ticket {ticket_id}: {category}")

    except Exception as e:
        logger.error(f"Background processing error for Ticket {ticket_id}: {e}")
        if 'ticket' in locals():
            ticket.status = "Failed_Processing"
            db.commit()
    finally:
        db.close()

# --- ASYNCHRONOUS INGESTION ENDPOINT ---
@app.post("/classify", status_code=202)
def ingest_ticket(request: ClassificationRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Ingests the ticket, saves as Pending, and returns HTTP 202 instantly.
    The actual AI classification runs in the background.
    """
    # 1. Immediate Persistence (State: Pending)
    new_ticket = Ticket(
        user_id="api_user",
        description=request.description,
        urgency="Medium",
        status="Pending" # Important: We do not know the category yet
    )
    db.add(new_ticket)
    db.commit()
    db.refresh(new_ticket)
    
    # 2. Delegate to Background Worker
    background_tasks.add_task(process_ticket_background, new_ticket.id, request.description)
    
    # 3. Surgical Execution: Return instantly
    return {
        "message": "Ticket received and queued for processing.",
        "ticket_id": new_ticket.id,
        "status": "Pending"
    }

# --- STATUS POLLING ENDPOINT ---
@app.get("/tickets/{ticket_id}")
def get_ticket_status(ticket_id: int, db: Session = Depends(get_db)):
    """
    Allows the client to poll the status of their ticket.
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found.")
    
    return {
        "ticket_id": ticket.id,
        "description": ticket.description,
        "category": ticket.category,
        "status": ticket.status
    }

# --- HUMAN-IN-THE-LOOP ENDPOINT ---
class FeedbackRequest(BaseModel):
    correct_category: str

@app.post("/tickets/{ticket_id}/feedback")
def submit_human_feedback(ticket_id: int, request: FeedbackRequest, db: Session = Depends(get_db)):
    """
    Overrides an AI classification and updates the Semantic Cache (RAG).
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found in DB.")
    
    if request.correct_category not in app_state["categories"]:
        raise HTTPException(status_code=400, detail="Invalid category.")
    
    old_category = ticket.category
    ticket.category = request.correct_category
    ticket.status = "Human_Corrected"
    db.commit()
    
    semantic_cache: SemanticCache = app_state["semantic_cache"]
    semantic_cache.update_ticket_category(str(ticket_id), request.correct_category)
    
    return {"status": "success", "message": f"Ticket {ticket_id} updated to '{request.correct_category}'."}