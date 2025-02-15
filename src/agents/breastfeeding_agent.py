def _set_role_boundaries(self):
    self.role_boundaries = {
        "can_do": [
            "breastfeeding techniques",
            "positioning guidance",
            "common challenges",
            "pumping tips",
            "milk storage info",
            "feeding patterns"
        ],
        "cannot_do": [
            "medical diagnosis",
            "medication safety",
            "treatment plans",
            "medical conditions",
            "prescription advice",
            "emergency situations"
        ],
        "refer_to": {
            "medical_issues": "healthcare provider",
            "lactation_problems": "lactation consultant",
            "medications": "healthcare provider",
            "breast_pain": "medical professional",
            "infant_weight": "pediatrician",
            "severe_issues": "emergency services"
        }
    } 