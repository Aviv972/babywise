def _set_role_boundaries(self):
    self.role_boundaries = {
        "can_do": [
            "schedule planning",
            "routine optimization",
            "time management tips",
            "daily activity suggestions",
            "organization advice",
            "habit formation guidance"
        ],
        "cannot_do": [
            "medical scheduling",
            "therapy routines",
            "medication timing",
            "treatment schedules",
            "rehabilitation plans",
            "medical procedures"
        ],
        "refer_to": {
            "medical_routines": "healthcare provider",
            "therapy_schedules": "therapist",
            "developmental_planning": "child development specialist",
            "special_needs": "occupational therapist",
            "behavioral_routines": "child psychologist",
            "sleep_schedules": "sleep consultant"
        }
    } 