import logging
from typing import Dict, List, Optional

import chromadb

logger = logging.getLogger("SemanticCache")


class SemanticCache:
    """
    Manages the local vector database for semantic caching and RAG context.
    Uses ChromaDB's default local embedding model (all-MiniLM-L6-v2) 
    to ensure zero API cost for text vectorization.
    """
    
    def __init__(self, persist_directory: str = "./chroma_data") -> None:
        # Initialize persistent local storage for vectors
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Get or create the collection using Cosine Similarity
        self.collection = self.client.get_or_create_collection(
            name="ticket_cache",
            metadata={"hnsw:space": "cosine"} 
        )
        logger.info(f"🧠 Semantic Cache initialized at {persist_directory}")

    def check_cache(self, description: str, threshold: float = 0.5) -> Optional[str]:
        """
        Searches the vector space for a semantically similar ticket to bypass the LLM.
        """
        if self.collection.count() == 0:
            return None

        # Query the vector database (runs locally, 0 API cost)
        results = self.collection.query(
            query_texts=[description],
            n_results=1
        )
        
        if not results["distances"] or not results["distances"][0]:
            return None

        distance = results["distances"][0][0]
        
        if distance < threshold:
            category = results["metadatas"][0][0]["category"]
            logger.info(f"🎯 Semantic Match! Distance: {distance:.4f} (Threshold: {threshold}) -> Category: '{category}'")
            return category
        
        logger.warning(f"🛡️ Cache Miss. Nearest neighbor distance was {distance:.4f} > {threshold}.")
        return None

    def add_to_cache(self, ticket_id: str, description: str, category: str) -> None:
        """
        Adds a newly classified ticket to the vector space.
        """
        self.collection.add(
            documents=[description],
            metadatas=[{"category": category}],
            ids=[str(ticket_id)]
        )
        logger.debug(f"Added Ticket {ticket_id} to Semantic Cache.")

    def get_similar_examples(self, description: str, limit: int = 3) -> List[Dict[str, str]]:
        """
        RAG Component: Retrieves the nearest neighbors for dynamic Few-Shot prompting.
        It bypasses the strict threshold to provide the LLM with the closest conceptual context.
        """
        if self.collection.count() == 0:
            return []

        # Prevent requesting more results than elements in the database
        safe_limit = min(limit, self.collection.count())
        
        results = self.collection.query(
            query_texts=[description],
            n_results=safe_limit
        )

        examples = []
        if results["documents"] and results["metadatas"]:
            for i in range(len(results["documents"][0])):
                examples.append({
                    "description": results["documents"][0][i],
                    "category": results["metadatas"][0][i]["category"]
                })
        
        logger.debug(f"🧠 Retrieved {len(examples)} historical examples for context.")
        return examples

    def update_ticket_category(self, ticket_id: str, new_category: str) -> None:
        """
        Human-in-the-Loop: Updates the ground truth in the vector space after human correction.
        """
        try:
            # We fetch the existing document first because Chroma requires the text to update metadata easily
            result = self.collection.get(ids=[str(ticket_id)])
            
            if result and result["documents"] and len(result["documents"]) > 0:
                self.collection.update(
                    ids=[str(ticket_id)],
                    documents=result["documents"], # Keep the original text intact
                    metadatas=[{"category": new_category}] # Update the corrected category
                )
                logger.info(f"🔄 Ground Truth Updated for Ticket {ticket_id} -> '{new_category}'")
            else:
                logger.warning(f"Could not find Ticket {ticket_id} in vector cache to update.")
        except Exception as e:
            logger.error(f"Failed to update vector cache: {e}")