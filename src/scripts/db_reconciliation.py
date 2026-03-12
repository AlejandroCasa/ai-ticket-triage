import logging
import os
import time
from sqlalchemy.orm import Session
from src.adapters.ollama_adapter import OllamaAdapter # Ajusta a GeminiAdapter si volviste a la nube
from src.core.config import get_categories, load_config
from src.core.database import Ticket, init_db
from src.core.semantic_cache import SemanticCache

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] RECONCILIATION: %(message)s")
logger = logging.getLogger("DB_Reconciliation")

def run_db_reconciliation() -> None:
    logger.info("Initiating Database Reconciliation Sweep...")

    # 1. Bootstrapping Infrastructure
    config = load_config("config.yaml")
    categories = get_categories(config)
    
    # Path handling for both Docker and Bare-Metal
    db_path = os.getenv("DB_URL", "sqlite:///data/tickets.db")
    if "sqlite:////" not in db_path and "sqlite:///" in db_path:
        db_path = db_path.replace("sqlite:///", "sqlite:////app/") if os.path.exists("/app") else db_path
        
    SessionLocal = init_db(db_path)
    chroma_path = "/app/chroma_data" if os.path.exists("/app/chroma_data") else "./chroma_data"
    semantic_cache = SemanticCache(persist_directory=chroma_path)
    
    # Using local sovereign AI
    classifier = OllamaAdapter(host="http://localhost:11434", model_name="llama3")

    metrics = {"processed": 0, "cache_hits": 0, "ai_calls": 0}

    # 2. Sweep the DB
    db: Session = SessionLocal()
    try:
        # Target tickets that bypassed the API or failed previously
        pending_tickets = db.query(Ticket).filter(Ticket.status.in_(["Pending", "Unclassified"])).all()
        
        if not pending_tickets:
            logger.info("Database is clean. Zero pending tickets found.")
            return

        logger.info(f"Found {len(pending_tickets)} unclassified tickets. Commencing triage...")

        for ticket in pending_tickets:
            metrics["processed"] += 1
            
            # FINOPS SHIELD: Check Vector DB
            cached_category = semantic_cache.check_cache(ticket.description, threshold=0.4)
            
            if cached_category:
                ticket.category = cached_category
                ticket.status = "Classified_By_Cache"
                metrics["cache_hits"] += 1
                logger.info(f"[ID: {ticket.id}] 🛡️ Cache Hit -> {cached_category}")
            else:
                # AI INFERENCE
                past_examples = semantic_cache.get_similar_examples(ticket.description, limit=3)
                category = classifier.classify_ticket(ticket.description, categories, past_examples)
                
                ticket.category = category
                ticket.status = "Classified_By_AI"
                metrics["ai_calls"] += 1
                logger.info(f"[ID: {ticket.id}] 🧠 AI Inferred -> {category}")
                
                # Teach the cache
                if category != "Unclassified":
                    semantic_cache.add_to_cache(str(ticket.id), ticket.description, category)

            # Commit dynamically to avoid locking
            db.commit()

    except Exception as e:
        logger.error(f"Reconciliation halted due to fatal error: {e}")
        db.rollback()
    finally:
        db.close()

    logger.info(f"--- SWEEP COMPLETE | Processed: {metrics['processed']} | Cache Hits: {metrics['cache_hits']} | AI Calls: {metrics['ai_calls']} ---")

if __name__ == "__main__":
    run_db_reconciliation()