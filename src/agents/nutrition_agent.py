def _set_role_boundaries(self):
    self.role_boundaries = {
        "can_do": [
            "general nutrition guidance",
            "meal planning suggestions",
            "food introduction tips",
            "feeding schedules",
            "healthy eating habits",
            "food safety basics"
        ],
        "cannot_do": [
            "medical diet plans",
            "allergy diagnoses",
            "therapeutic diets",
            "eating disorder advice",
            "medical nutrition therapy",
            "supplement recommendations"
        ],
        "refer_to": {
            "allergies": "allergist/immunologist",
            "medical_diets": "registered dietitian",
            "eating_disorders": "eating disorder specialist",
            "growth_issues": "pediatrician",
            "digestive_problems": "gastroenterologist",
            "nutritional_deficiencies": "healthcare provider"
        }
    } 