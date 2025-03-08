from typing import Dict, List, Any, Optional
from .base_agent import BaseAgent

class BudgetAgent(BaseAgent):
    def __init__(self, llm_service):
        super().__init__(
            name="Budget and Planning Expert",
            expertise=[
                # English keywords
                "budget", "cost", "expense", "saving", "price", "compare",
                "affordable", "essential", "investment", "planning", "financial",
                "shopping", "deals", "discount", "value", "second-hand", "used",
                # Hebrew keywords
                "תקציב", "עלות", "הוצאה", "חיסכון", "מחיר", "השוואה",
                "במחיר סביר", "חיוני", "השקעה", "תכנון", "פיננסי",
                "קניות", "מבצעים", "הנחה", "ערך", "יד שנייה", "משומש"
            ],
            llm_service=llm_service
        )
        self.required_context = [
            "child_age",
            "budget_range",
            "priority_items",
            "timeframe",
            "existing_items"
        ]
        
        # Budget category specific questions
        self.context_questions_map = {
            "gear": [
                "specific_items",
                "new_vs_used",
                "quality_requirements",
                "urgency_level",
                "storage_space"
            ],
            "ongoing": [
                "monthly_budget",
                "recurring_costs",
                "insurance_coverage",
                "childcare_needs",
                "emergency_fund"
            ],
            "healthcare": [
                "insurance_type",
                "expected_costs",
                "specialist_needs",
                "medication_costs",
                "wellness_visits"
            ],
            "education": [
                "education_type",
                "duration_needed",
                "additional_fees",
                "transportation_costs",
                "materials_needed"
            ],
            "planning": [
                "saving_goals",
                "investment_options",
                "tax_benefits",
                "family_support",
                "future_expenses"
            ]
        }

    def _identify_budget_category(self, query: str) -> Optional[str]:
        category_keywords = {
            "gear": ["stroller", "crib", "equipment", "עגלה", "מיטה", "ציוד"],
            "ongoing": ["diapers", "food", "monthly", "חיתולים", "אוכל", "חודשי"],
            "healthcare": ["medical", "doctor", "health", "רפואי", "רופא", "בריאות"],
            "education": ["daycare", "school", "classes", "מעון", "גן", "חוגים"],
            "planning": ["save", "invest", "plan", "לחסוך", "להשקיע", "לתכנן"]
        }
        
        query_lower = query.lower()
        for category, keywords in category_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                return category
        return None

    def _prepare_prompt(self, query: str) -> str:
        # Identify budget category and set appropriate context questions
        budget_category = self._identify_budget_category(query)
        if budget_category in self.context_questions_map:
            self.required_context = self.context_questions_map[budget_category]
            
        return f"""As a baby budget and planning expert, analyze and advise on: {query}

                  Analysis Framework:
                  1. Cost Analysis
                     - Essential vs optional items
                     - Initial setup costs
                     - Recurring expenses
                     - Hidden costs
                     - Insurance considerations
                  
                  2. Product Evaluation
                     - Quality vs price balance
                     - Long-term value assessment
                     - Safety vs cost considerations
                     - Brand comparison
                     - Durability factors
                  
                  3. Shopping Strategy
                     - Best purchase timing
                     - Sales and discounts
                     - Second-hand options
                     - Rental possibilities
                     - Bulk buying benefits
                  
                  4. Financial Planning
                     - Budget allocation
                     - Payment planning
                     - Saving strategies
                     - Emergency fund
                     - Future expenses
                  
                  5. Resource Optimization
                     - Multi-purpose items
                     - Growth accommodation
                     - Sharing possibilities
                     - Resale value
                     - Warranty importance
                  
                  Key Considerations:
                  - Prioritize safety and quality
                  - Consider long-term costs
                  - Factor in growth rates
                  - Plan for unexpected expenses
                  - Balance needs vs wants
                  
                  Respond in the same language as the question."""

    async def can_handle_query(self, query: str, keywords: List[str]) -> bool:
        confidence = self._calculate_confidence(query, keywords)
        print(f"Budget confidence for '{query}': {confidence}")
        return confidence > 0.2 

    def _set_role_boundaries(self):
        self.role_boundaries = {
            "can_do": [
                "basic budgeting advice",
                "cost comparison tips",
                "expense planning",
                "saving strategies",
                "product recommendations",
                "general financial guidance"
            ],
            "cannot_do": [
                "specific investment advice",
                "tax planning",
                "insurance recommendations",
                "legal financial guidance",
                "loan/mortgage advice",
                "specific product guarantees"
            ],
            "refer_to": {
                "investments": "financial advisor",
                "taxes": "tax professional",
                "insurance": "insurance agent",
                "legal": "financial lawyer",
                "loans": "banking professional",
                "debt": "financial counselor"
            }
        } 