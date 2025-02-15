def _set_role_boundaries(self):
    self.role_boundaries = {
        "can_do": [
            "social skill guidance",
            "play suggestions",
            "interaction tips",
            "friendship advice",
            "sharing/cooperation skills",
            "emotional expression help"
        ],
        "cannot_do": [
            "behavioral diagnosis",
            "social disorder treatment",
            "therapy services",
            "psychological assessment",
            "medical evaluations",
            "developmental diagnosis"
        ],
        "refer_to": {
            "behavioral_issues": "child psychologist",
            "social_disorders": "developmental specialist",
            "emotional_concerns": "mental health professional",
            "learning_problems": "educational specialist",
            "developmental_delays": "developmental pediatrician",
            "communication_issues": "speech-language pathologist"
        }
    } 