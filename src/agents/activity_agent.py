def _set_role_boundaries(self):
    self.role_boundaries = {
        "can_do": [
            "age-appropriate activities",
            "play suggestions",
            "developmental games",
            "exercise guidelines",
            "indoor/outdoor activities",
            "safety precautions"
        ],
        "cannot_do": [
            "physical therapy",
            "medical exercise plans",
            "rehabilitation activities",
            "injury treatment",
            "developmental therapy",
            "special needs programming"
        ],
        "refer_to": {
            "physical_therapy": "pediatric physical therapist",
            "injuries": "healthcare provider",
            "development_concerns": "developmental specialist",
            "special_needs": "occupational therapist",
            "motor_skills": "physical development specialist",
            "sports_injuries": "sports medicine professional"
        }
    } 