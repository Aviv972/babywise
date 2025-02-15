from typing import List
import re

def extract_keywords(text: str) -> List[str]:
    # Remove punctuation and convert to lowercase
    text = re.sub(r'[^\w\s]', '', text.lower())
    
    # Split into words
    words = text.split()
    
    # Remove common stop words (this is a simplified version)
    stop_words = {'the', 'is', 'at', 'which', 'on', 'a', 'an', 'and', 'or'}
    keywords = [word for word in words if word not in stop_words]
    
    return keywords

def contains_keywords(text: str, keywords: List[str]) -> bool:
    text_lower = text.lower()
    return any(keyword.lower() in text_lower for keyword in keywords) 