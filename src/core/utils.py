import hashlib

def calculate_content_hash(text: str) -> str:
    """
    Computes the SHA256 hash of a string for idempotency checks.

    Args:
        text (str): The input text (e.g., ticket description).

    Returns:
        str: The hexadecimal hash string.
    """
    # Normalize text (lowercase, strip) to ensure 'Mouse Broken' matches 'mouse broken '
    normalized_text = text.lower().strip()
    return hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()