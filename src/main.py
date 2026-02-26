import logging
import os
import sys

from dotenv import load_dotenv

from src.adapters.gemini_adapter import GeminiAdapter
from src.core.config import get_categories, load_config
from src.core.database import Ticket, init_db
from src.core.utils import calculate_content_hash  # Dependencia para FinOps

# --- Configuration & Setup ---

# Configure logging structure
# In a real container, these logs would be captured by Datadog/Splunk/CloudWatch
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("TriageEngine")

# Load environment variables
load_dotenv()


def main() -> None:
    logger.info("--- Starting Intelligent Triage Engine (FinOps Enabled) ---")

    # 1. Load Configuration (Fail fast if config is bad)
    try:
        app_config = load_config("config.yaml")
        categories = get_categories(app_config)
        logger.info(f"Loaded {len(categories)} classification categories from config.")
    except Exception as e:
        logger.critical(f"Failed to load configuration: {e}")
        sys.exit(1)

    # 2. Initialize Database Connection
    db_url = os.getenv("DB_URL", "sqlite:///tickets.db")
    SessionLocal = init_db(db_url)

    # 3. Initialize AI Adapter
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.critical("GEMINI_API_KEY is missing from environment variables.")
        sys.exit(1)

    try:
        classifier = GeminiAdapter(api_key)
        logger.info(f"AI Adapter initialized successfully using model: {classifier.model_name}")
    except Exception as e:
        logger.critical(f"Failed to initialize AI Adapter: {e}")
        sys.exit(1)

    # 4. Database Interaction Context
    # We use a context manager ('with') to ensure the session is always closed
    with SessionLocal() as session:
        # Fetch 'New' tickets
        tickets_to_process = session.query(Ticket).filter(Ticket.status == "New").all()

        if not tickets_to_process:
            logger.info("No new tickets found. System is idle.")
            return

        logger.info(f"Found {len(tickets_to_process)} tickets pending classification.")

        # 5. Process Loop
        processed_count = 0
        cache_hits = 0  # Metric for FinOps report

        for ticket in tickets_to_process:
            logger.debug(f"Processing Ticket ID {ticket.id}...")

            try:
                # --- FINOPS LAYER: IDEMPOTENCY CHECK ---

                # A. Calculate Hash of the description
                ticket_hash = calculate_content_hash(ticket.description)
                ticket.content_hash = ticket_hash # Save hash for future reference

                # B. Check Cache (Is there a Classified ticket with same hash?)
                # We exclude 'Unclassified' results because we want to retry those
                cached_ticket = session.query(Ticket).filter(
                    Ticket.content_hash == ticket_hash,
                    Ticket.status == "Classified",
                    Ticket.category != "Unclassified"
                ).first()

                final_category = None

                if cached_ticket:
                    # --- CACHE HIT (Free) ---
                    final_category = cached_ticket.category
                    cache_hits += 1
                    logger.info(
                        f"💰 Cache Hit! Ticket {ticket.id} matches Ticket {cached_ticket.id}. "
                        f"Reusing category: '{final_category}'"
                    )
                else:
                    # --- CACHE MISS (Cost) ---
                    # Only call AI if we haven't seen this issue before
                    final_category = classifier.classify_ticket(ticket.description, categories)

                    # Business Logic: Validating the output
                    if final_category == "Unclassified":
                        logger.warning(
                            f"Ticket {ticket.id} could not be classified automatically."
                        )

                # Update Record
                ticket.category = final_category
                ticket.status = "Classified"
                processed_count += 1

                # Structured log for future analysis
                logger.info(
                    f"Ticket {ticket.id} -> {final_category}",
                    extra={
                        "ticket_id": ticket.id,
                        "category": final_category,
                        "source": "cache" if cached_ticket else "ai"
                    }
                )

            except Exception as e:
                logger.error(f"Error processing ticket {ticket.id}: {e}")
                # We continue with the next ticket instead of crashing
                continue

        # 6. Commit Transaction & Report
        if processed_count > 0:
            session.commit()

            # ROI Report (Return on Investment)
            total_cost_saved = cache_hits  # Assuming 1 unit cost per call
            logger.info("--- Batch Processing Complete ---")
            logger.info(f"Total Processed: {processed_count}")
            logger.info(f"AI Calls Made: {processed_count - cache_hits}")
            logger.info(f"Cache Hits (Savings): {cache_hits}")
        else:
            logger.info("No changes were made to the database.")

if __name__ == "__main__":
    main()