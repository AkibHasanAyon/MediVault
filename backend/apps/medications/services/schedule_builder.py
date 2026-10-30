import re
from datetime import time
from typing import List, Tuple
from django.db import transaction

from apps.medications.models import Medication, MedicationReminder

class ScheduleBuilder:
    """
    Parses clinical frequency patterns commonly used in Bangladesh and South Asia
    (e.g. '1+0+1', '1+1+1', '0+0+1') and constructs appropriate reminder alarm slots.
    """

    # Standard default times for dose patterns in Asia/Dhaka
    TIME_MORNING = time(8, 0)      # 08:00 AM
    TIME_NOON = time(14, 0)        # 02:00 PM
    TIME_EVENING = time(18, 0)     # 06:00 PM
    TIME_NIGHT = time(21, 0)       # 09:00 PM

    @classmethod
    def parse_dosage_pattern(cls, pattern: str) -> List[Tuple[time, str]]:
        """
        Interprets pattern e.g. '1+0+1' -> [(08:00, 'Morning Dose'), (21:00, 'Night Dose')]
        """
        pattern = pattern.strip().replace(' ', '')
        slots = []

        # Check for 3-part pattern: M + N + E (e.g. 1+0+1, 1+1+1)
        three_part_match = re.match(r'^([0-9\./]+)\+([0-9\./]+)\+([0-9\./]+)$', pattern)
        if three_part_match:
            morning, noon, night = three_part_match.groups()
            if morning not in ['0', '0.0']:
                slots.append((cls.TIME_MORNING, "Morning Dose"))
            if noon not in ['0', '0.0']:
                slots.append((cls.TIME_NOON, "Noon Dose"))
            if night not in ['0', '0.0']:
                slots.append((cls.TIME_NIGHT, "Night Dose"))
            return slots

        # Check for 4-part pattern: e.g. 1+1+1+1 (QDS)
        four_part_match = re.match(r'^([0-9\./]+)\+([0-9\./]+)\+([0-9\./]+)\+([0-9\./]+)$', pattern)
        if four_part_match:
            slots.append((time(8, 0), "Morning Dose"))
            slots.append((time(12, 0), "Noon Dose"))
            slots.append((time(18, 0), "Evening Dose"))
            slots.append((time(22, 0), "Night Dose"))
            return slots

        # Check for 2-part pattern: e.g. 1+1 (BD)
        two_part_match = re.match(r'^([0-9\./]+)\+([0-9\./]+)$', pattern)
        if two_part_match:
            slots.append((cls.TIME_MORNING, "Morning Dose"))
            slots.append((cls.TIME_NIGHT, "Night Dose"))
            return slots

        # Check for 'once daily' or simple single number e.g. '1'
        if pattern in ['1', '1+0', '0+1']:
            slots.append((cls.TIME_MORNING, "Daily Dose"))
            return slots

        # Fallback default: 1 morning reminder slot
        slots.append((cls.TIME_MORNING, "Daily Dose"))
        return slots

    @classmethod
    @transaction.atomic
    def generate_reminders_for_medication(cls, medication: Medication) -> List[MedicationReminder]:
        """
        Generates and persists MedicationReminder schedule for the given Medication.
        Existing reminders are preserved if already configured.
        """
        if medication.reminders.exists():
            return list(medication.reminders.all())

        parsed_slots = cls.parse_dosage_pattern(medication.dosage_pattern)
        reminders = []
        for reminder_time, label in parsed_slots:
            reminder = MedicationReminder.objects.create(
                medication=medication,
                reminder_time=reminder_time,
                label=label,
                is_enabled=True
            )
            reminders.append(reminder)

        return reminders

