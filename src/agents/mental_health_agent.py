def _set_role_boundaries(self):
    self.role_boundaries = {
        "can_do": [
            "emotional support guidance",
            "stress management tips",
            "self-care suggestions",
            "parenting anxiety support",
            "work-life balance advice",
            "relationship adjustment tips"
        ],
        "cannot_do": [
            "mental health diagnosis",
            "therapy services",
            "medication advice",
            "crisis intervention",
            "trauma counseling",
            "psychiatric treatment"
        ],
        "refer_to": {
            "mental_health": "mental health professional",
            "crisis": "emergency mental health services",
            "therapy": "licensed therapist",
            "medication": "psychiatrist",
            "relationships": "family counselor",
            "postpartum_depression": "mental health specialist"
        }
    } 