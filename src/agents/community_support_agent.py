from typing import Dict, List, Any, Optional
from .base_agent import BaseAgent

class CommunityAgent(BaseAgent):
    def __init__(self, llm_service):
        super().__init__(
            name="Community Support Expert",
            expertise=[
                # English keywords
                "support", "community", "group", "relationship", "family",
                "partner", "social", "network", "resources", "help",
                "counseling", "self-care", "mental health", "connection",
                # Hebrew keywords
                "תמיכה", "קהילה", "קבוצה", "יחסים", "משפחה",
                "בן זוג", "חברתי", "רשת", "משאבים", "עזרה",
                "ייעוץ", "טיפול עצמי", "בריאות נפשית", "קשר"
            ],
            llm_service=llm_service
        )
        self.required_context = [
            "location",
            "child_age",
            "support_needs",
            "language_preferences",
            "schedule_availability"
        ]
        
        # Support type specific questions
        self.context_questions_map = {
            "playgroups": [
                "child_age",
                "location",
                "schedule_preferences",
                "group_size_comfort",
                "activity_interests"
            ],
            "education": [
                "child_age",
                "education_type",
                "location",
                "budget_range",
                "special_requirements"
            ],
            "healthcare": [
                "service_type",
                "location",
                "insurance_coverage",
                "urgency_level",
                "specialist_needs"
            ],
            "parent_support": [
                "support_type",
                "schedule_availability",
                "online_vs_inperson",
                "language_needs",
                "specific_concerns"
            ]
        }

    def _prepare_prompt(self, query: str) -> str:
        return f"""As a community and support expert, provide guidance about: {query}

              Analysis Framework:
              1. Support Network Development
                 - Local resources
                 - Online communities
                 - Professional services
                 - Parent groups
                 - Educational programs
              
              2. Relationship Management
                 - Partner communication
                 - Family dynamics
                 - Friend connections
                 - Professional relationships
                 - Community engagement
              
              3. Resource Access
                 - Available services
                 - Financial assistance
                 - Educational resources
                 - Healthcare support
                 - Emergency services
              
              4. Mental Health Support
                 - Stress management
                 - Emotional well-being
                 - Professional help
                 - Self-care practices
                 - Peer support
              
              5. Community Integration
                 - Local activities
                 - Cultural connections
                 - Support groups
                 - Playgroups
                 - Family events
              
              Key Principles:
              - Build sustainable connections
              - Maintain boundaries
              - Respect diversity
              - Foster mutual support
              - Prioritize well-being
              
              Note: For serious mental health concerns, seek professional help.
              Respond in the same language as the question."""

    async def can_handle_query(self, query: str, keywords: List[str]) -> bool:
        confidence = self._calculate_confidence(query, keywords)
        print(f"Community support confidence for '{query}': {confidence}")
        return confidence > 0.2

    def _identify_support_type(self, query: str) -> Optional[str]:
        support_keywords = {
            "playgroups": ["playgroup", "meetup", "social", "מפגש", "חברתי", "קבוצת משחק"],
            "education": ["daycare", "preschool", "school", "מעון", "גן", "חינוך"],
            "healthcare": ["doctor", "clinic", "medical", "רופא", "מרפאה", "רפואי"],
            "parent_support": ["support group", "counseling", "help", "קבוצת תמיכה", "ייעוץ", "עזרה"]
        }
        
        query_lower = query.lower()
        for stype, keywords in support_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                return stype
        return None

    def _set_role_boundaries(self):
        self.role_boundaries = {
            "can_do": [
                "community resource information",
                "support group referrals",
                "activity recommendations",
                "social connection tips",
                "local service navigation",
                "parent group suggestions"
            ],
            "cannot_do": [
                "professional counseling",
                "crisis intervention",
                "medical referrals",
                "legal advice",
                "financial assistance",
                "emergency response"
            ],
            "refer_to": {
                "mental_health": "mental health professional",
                "crisis": "crisis hotline/emergency services",
                "medical_needs": "healthcare provider",
                "legal_support": "legal aid services",
                "financial_aid": "social services",
                "domestic_issues": "family support services"
            }
        } 