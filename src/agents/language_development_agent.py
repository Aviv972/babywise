def _set_role_boundaries(self):
    self.role_boundaries = {
        "can_do": [
            "language development guidance",
            "age-appropriate activities",
            "communication tips",
            "multilingual exposure advice",
            "reading suggestions",
            "speech milestones"
        ],
        "cannot_do": [
            "speech delay diagnosis",
            "language disorder treatment",
            "therapy plans",
            "medical assessments",
            "hearing evaluations",
            "developmental diagnoses"
        ],
        "refer_to": {
            "speech_delays": "speech-language pathologist",
            "hearing_concerns": "audiologist",
            "developmental_issues": "developmental pediatrician",
            "learning_difficulties": "educational specialist",
            "behavioral_concerns": "child psychologist",
            "medical_conditions": "healthcare provider"
        }
    } 