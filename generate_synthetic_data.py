import json
import logging
import os
import random
import time
from typing import Any, Dict, List

from dotenv import load_dotenv
from google import genai
from google.genai import types

from src.core.database import Ticket, init_db

# --- Configuration ---
# Set up logging to replace standard print statements for better observability
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] Generator: %(message)s",
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Constants
BATCH_SIZE = 5
TOTAL_BATCHES = 1
MODEL_NAME = "gemini-1.5-flash"  # Using 1.5 Flash for stability and speed


def generate_batch(client: genai.Client, model_name: str, batch_size: int = 20) -> List[Dict[str, Any]]:
    """
    Asks Gemini to generate a batch of unique, realistic IT tickets in JSON format.
    Includes retry logic to handle Rate Limits (429) during bulk generation.
    """

    prompt = f"""
    You are a QA Engineer creating test data for an IT Service Desk.
    Generate {batch_size} UNIQUE and REALISTIC IT support tickets.

    Requirements:
    1. Variety: Include hardware, software, network, access, and security issues.
    2. Tone: Mix polite requests, frustrated users, and urgent panics.
    3. Urgency: Distribute between 'Low', 'Medium', 'High', 'Critical'.
    4. Language: English.

    Output Format: JSON Array of objects with keys: "description", "urgency", "user_id".
    Example: [{{"description": "Mouse broken", "urgency": "Low", "user_id": "u99"}}]
    """

    # Retry Configuration
    max_retries = 5
    base_delay = 4.0

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    # High temperature for creativity and variety in test data
                    temperature=0.7,
                ),
            )

            # Parse the JSON response
            data = json.loads(response.text)

            # Basic validation: ensure it's a list
            if isinstance(data, list):
                return data
            else:
                logger.warning("AI returned valid JSON but not a list. Retrying...")
                continue

        except json.JSONDecodeError:
            logger.error("Failed to decode JSON from AI response. Retrying...")

        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                if attempt == max_retries - 1:
                    logger.error("Max retries exceeded for this batch.")
                    return []

                sleep_time = (base_delay * (2**attempt)) + random.uniform(0, 1)
                logger.warning(
                    f"Rate limit hit (429). Retrying in {sleep_time:.2f}s... (Attempt {attempt + 1})"
                )
                time.sleep(sleep_time)
            else:
                logger.error(f"Non-retriable error: {e}")
                return []

    return []


def main() -> None:
    logger.info("--- Starting Synthetic Data Generation (Powered by Gemini) ---")

    # 1. Setup Gemini
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.critical("GEMINI_API_KEY missing from environment.")
        return

    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        logger.critical(f"Failed to initialize Gemini client: {e}")
        return

    # 2. Setup Database
    db_url = os.getenv("DB_URL", "sqlite:///tickets.db")
    SessionLocal = init_db(db_url)

    # 3. Generation Loop
    total_inserted = 0

    with SessionLocal() as session:
        for i in range(TOTAL_BATCHES):
            logger.info(f"Requesting Batch {i+1}/{TOTAL_BATCHES} from AI...")

            tickets_data = generate_batch(client, MODEL_NAME, BATCH_SIZE)

            if not tickets_data:
                logger.warning(f"Batch {i+1} failed to generate data. Skipping.")
                continue

            count = 0
            for item in tickets_data:
                # Defensive coding: Validate fields strictly
                if "description" in item and "urgency" in item:
                    # Fallback for user_id if the AI forgets it
                    uid = item.get("user_id", f"u{random.randint(1000, 9999)}")

                    ticket = Ticket(
                        user_id=str(uid),
                        description=item["description"],
                        urgency=item["urgency"],
                        status="New",  # Important: So our main script picks them up later
                    )
                    session.add(ticket)
                    count += 1

            session.commit()
            total_inserted += count
            logger.info(f" -> Batch {i+1} saved: {count} tickets inserted.")

            # Proactive Throttling: Sleep between batches to be a good API citizen
            # This reduces the chance of hitting 429s in the first place
            time.sleep(2)

    logger.info(f"--- Data Generation Complete. Total inserted: {total_inserted} ---")
    logger.info("Run 'python -m src.main' to classify these new tickets.")


if __name__ == "__main__":
    main()