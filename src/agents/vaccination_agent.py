def _set_role_boundaries(self):
    self.role_boundaries = {
        "can_do": [
            "general vaccination information",
            "schedule guidance",
            "common side effects",
            "preparation tips",
            "aftercare advice",
            "record keeping guidance"
        ],
        "cannot_do": [
            "specific medical advice",
            "vaccination prescriptions",
            "medical exemptions",
            "alternative schedules",
            "side effect treatment",
            "medical emergencies"
        ],
        "refer_to": {
            "medical_advice": "pediatrician",
            "adverse_reactions": "emergency services",
            "schedule_changes": "healthcare provider",
            "exemptions": "medical specialist",
            "complications": "immediate medical care",
            "specific_concerns": "vaccination specialist"
        }
    } 