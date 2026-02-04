import logging
import os
import sys

from dotenv import load_dotenv

from src.adapters.gemini_adapter import GeminiAdapter
from src.core.database import Ticket, init_db

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

# Business Logic Configuration
# Ideally, this should live in a YAML config file or a database table
CATEGORIES = [
    "Password Reset",
    "Software Issue",
    "Hardware Failure",
    "Network Connectivity",
    "Access Request",
]


def main() -> None:
    logger.info("--- Starting Intelligent Triage Engine ---")

    # 1. Initialize Database Connection
    db_url = os.getenv("DB_URL", "sqlite:///tickets.db")
    SessionLocal = init_db(db_url)

    # 2. Initialize AI Adapter
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

    # 3. Database Interaction Context
    # We use a context manager ('with') to ensure the session is always closed
    with SessionLocal() as session:
        # Fetch 'New' tickets
        tickets_to_process = session.query(Ticket).filter(Ticket.status == "New").all()

        if not tickets_to_process:
            logger.info("No new tickets found. System is idle.")
            return

        logger.info(f"Found {len(tickets_to_process)} tickets pending classification.")

        # 4. Process Loop
        processed_count = 0
        for ticket in tickets_to_process:
            logger.debug(f"Processing Ticket ID {ticket.id}...")

            try:
                # Call AI Strategy
                category = classifier.classify_ticket(ticket.description, CATEGORIES)

                # Business Logic: Validating the output
                if category == "Unclassified":
                    logger.warning(
                        f"Ticket {ticket.id} could not be classified automatically."
                    )
                    # We leave status as 'New' or move to 'Manual Review' depending on policy
                    # For this POC, we mark it as Classified but with 'Unclassified' category
                
                # Update Record
                ticket.category = category
                ticket.status = "Classified"
                processed_count += 1

                logger.info(
                    f"Ticket {ticket.id} -> {category}",
                    extra={"ticket_id": ticket.id, "category": category}
                )

            except Exception as e:
                logger.error(f"Error processing ticket {ticket.id}: {e}")
                # We continue with the next ticket instead of crashing
                continue

        # 5. Commit Transaction
        # Committing in batch is more performant than committing per ticket
        if processed_count > 0:
            session.commit()
            logger.info(f"Batch complete. {processed_count} tickets updated in database.")
        else:
            logger.info("No changes were made to the database.")

if __name__ == "__main__":
    main()