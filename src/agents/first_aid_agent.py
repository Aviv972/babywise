def _set_role_boundaries(self):
    self.role_boundaries = {
        "can_do": [
            "basic first aid information",
            "preventive measures",
            "emergency preparation",
            "first response steps",
            "safety guidelines",
            "wound care basics"
        ],
        "cannot_do": [
            "emergency medical advice",
            "diagnosis of conditions",
            "treatment prescriptions",
            "complex medical procedures",
            "medication recommendations",
            "serious injury handling"
        ],
        "refer_to": {
            "emergencies": "emergency services (call emergency number)",
            "serious_injuries": "emergency room",
            "medical_treatment": "healthcare provider",
            "poisoning": "poison control center",
            "burns": "burn unit/emergency services",
            "head_injuries": "emergency medical services"
        }
    } 