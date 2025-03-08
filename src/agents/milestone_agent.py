def _set_role_boundaries(self):
    self.role_boundaries = {
        "can_do": [
            "milestone information",
            "development patterns",
            "age-appropriate activities",
            "progress tracking",
            "general guidance",
            "typical ranges"
        ],
        "cannot_do": [
            "developmental diagnosis",
            "delay assessment",
            "medical evaluation",
            "therapy recommendations",
            "treatment plans",
            "disability determination"
        ],
        "refer_to": {
            "delays": "pediatrician",
            "assessment": "developmental specialist",
            "therapy": "early intervention services",
            "concerns": "child development expert",
            "learning_issues": "educational specialist",
            "behavioral_concerns": "child psychologist"
        }
    } 