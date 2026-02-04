import os
from src.adapters.gemini_adapter import GeminiAdapter
# form src.adapters.ollama_adapter import OllamaAdapter (Future implementation)

# Mocking database data for the POC (Portfolio safe - No Client Data)
mock_tickets = [
    {"id": 1, "desc": "I cannot login, my password expired.", "urgency": "High"},
    {"id": 2, "desc": "The wifi in the meeting room is down.", "urgency": "Medium"},
    {"id": 3, "desc": "My mouse is clicking twice.", "urgency": "Low"}
]

# Configurable categories (loaded dynamically in real app)
CATEGORIES = [
    "Password Reset",
    "Account Lockout",
    "Network Issues",
    "Hardware Failure",
    "Software Glitch"
]

def main():
    # Factory logic to select provider based on ENV variable
    # This demonstrates architectural flexibility
    provider_type = os.getenv("LLM_PROVIDER", "GEMINI")

    llm_service = None

    if provider_type == "GEMINI":
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set.")
        llm_service = GeminiAdapter(api_key)
    elif provider_type == "LOCAL":
        # llm_service = OllamaAdapter(model="mistral")
        print("Local adapter not yet fully implemented.")
        return

    print(f"--- Starting Classification using {provider_type} ---")

    for ticket in mock_tickets:
        category = llm_service.classify_ticket(ticket["desc"], CATEGORIES)
        print(f"Ticket ID {ticket['id']}: '{ticket['desc']}' -> [ {category} ]")

if __name__ == "__main__":
    main()