from typing import Optional, Tuple
from difflib import SequenceMatcher

def search_knowledge_base(db, query: str, category: str) -> Tuple[Optional[str], float]:
    """
    Search for similar responses in knowledge base
    Returns (response, confidence_score)
    """
    response = db.search_knowledge_base(query, category)
    if response:
        return response, 0.8  # High confidence for exact matches
    return None, 0.0 