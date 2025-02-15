def _set_role_boundaries(self):
    self.role_boundaries = {
        "can_do": [
            "recovery information",
            "self-care tips",
            "emotional support guidance",
            "lifestyle adjustments",
            "physical recovery tips",
            "bonding suggestions"
        ],
        "cannot_do": [
            "medical diagnosis",
            "mental health treatment",
            "medication advice",
            "physical therapy plans",
            "emergency care",
            "psychological counseling"
        ],
        "refer_to": {
            "medical_issues": "healthcare provider",
            "mental_health": "mental health professional",
            "physical_therapy": "physical therapist",
            "lactation": "lactation consultant",
            "depression": "mental health crisis services",
            "complications": "emergency medical services"
        }
    } 