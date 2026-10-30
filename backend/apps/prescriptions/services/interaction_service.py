import logging
from itertools import combinations
from typing import List, Dict, Any
from django.db.models import Q
from apps.prescriptions.models import DrugInteractionRule
from apps.medications.models import Medication
from apps.ai_services.openai_service import OpenAIService

logger = logging.getLogger('medivault.prescriptions')

# Standard validated high-risk interaction pairs seeded in clinical rule engine
DEFAULT_CLINICAL_RULES = [
    {
        "drug_a": "metformin",
        "drug_b": "ciprofloxacin",
        "severity": DrugInteractionRule.Severity.SEVERE,
        "effect": "Ciprofloxacin can alter blood glucose levels and significantly heighten the risk of severe hypoglycemia when taken with Metformin.",
        "advice": "Monitor blood glucose closely. Consider temporary dose reduction or alternative antibiotic."
    },
    {
        "drug_a": "aspirin",
        "drug_b": "warfarin",
        "severity": DrugInteractionRule.Severity.CONTRAINDICATED,
        "effect": "Concurrent use severely increases the risk of major hemorrhage and gastrointestinal bleeding due to combined anticoagulant and antiplatelet effects.",
        "advice": "Contraindicated unless specifically monitored under specialist anticoagulation protocol with INR checks."
    },
    {
        "drug_a": "ramipril",
        "drug_b": "spironolactone",
        "severity": DrugInteractionRule.Severity.SEVERE,
        "effect": "Concurrent ACE inhibitor and potassium-sparing diuretic can cause fatal hyperkalemia.",
        "advice": "Monitor serum potassium and renal function within 1-2 weeks of initiation."
    },
    {
        "drug_a": "methotrexate",
        "drug_b": "naproxen",
        "severity": DrugInteractionRule.Severity.CONTRAINDICATED,
        "effect": "NSAIDs decrease renal clearance of methotrexate, leading to severe methotrexate toxicity and bone marrow suppression.",
        "advice": "Avoid concurrent administration. Use paracetamol or approved non-NSAID analgesia."
    },
    {
        "drug_a": "atorvastatin",
        "drug_b": "clarithromycin",
        "severity": DrugInteractionRule.Severity.SEVERE,
        "effect": "Clarithromycin strongly inhibits CYP3A4, substantially increasing atorvastatin plasma concentrations and the risk of rhabdomyolysis.",
        "advice": "Temporarily suspend atorvastatin during the clarithromycin treatment course."
    },
    {
        "drug_a": "clopidogrel",
        "drug_b": "omeprazole",
        "severity": DrugInteractionRule.Severity.MODERATE,
        "effect": "Omeprazole inhibits CYP2C19, decreasing active clopidogrel metabolite and reducing antiplatelet efficacy.",
        "advice": "Consider substituting with pantoprazole or famotidine."
    }
]

class DrugInteractionService:
    """
    Evaluates newly prescribed drugs against concurrent medications and established interaction rules.
    Provides immediate clinical warnings and overrides for contraindicated combinations.
    """

    @classmethod
    def ensure_default_rules_seeded(cls):
        """Ensures fundamental clinical interaction rules are populated in the database."""
        for rule in DEFAULT_CLINICAL_RULES:
            DrugInteractionRule.objects.get_or_create(
                drug_a_generic=rule["drug_a"].lower(),
                drug_b_generic=rule["drug_b"].lower(),
                defaults={
                    "severity": rule["severity"],
                    "clinical_effect": rule["effect"],
                    "management_advice": rule["advice"]
                }
            )

    @classmethod
    def check_interactions(cls, new_generics: List[str], patient_id: str | None = None) -> List[Dict[str, Any]]:
        """
        Cross-checks a list of newly prescribed generic drugs with each other,
        and optionally with the patient's existing active medication roster.
        """
        cls.ensure_default_rules_seeded()

        all_generics_clean = [g.strip().lower() for g in new_generics if g and g.strip()]

        # If patient_id is provided, include patient's currently active medications
        existing_meds = []
        if patient_id:
            active_roster = Medication.objects.filter(patient_id=patient_id, is_active=True)
            for m in active_roster:
                gen = (m.generic_name or m.name).strip().lower()
                if gen and gen not in all_generics_clean:
                    all_generics_clean.append(gen)
                    existing_meds.append(gen)

        detected_interactions = []
        seen_pairs = set()

        # Pairwise cross-comparison
        for drug_x, drug_y in combinations(all_generics_clean, 2):
            pair_key = tuple(sorted([drug_x, drug_y]))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            # Query database rules bidirectionally
            rule = DrugInteractionRule.objects.filter(
                (Q(drug_a_generic=drug_x) & Q(drug_b_generic=drug_y)) |
                (Q(drug_a_generic=drug_y) & Q(drug_b_generic=drug_x))
            ).first()

            if rule:
                is_with_existing = (drug_x in existing_meds or drug_y in existing_meds)
                detected_interactions.append({
                    "drug_a": drug_x.title(),
                    "drug_b": drug_y.title(),
                    "severity": rule.severity,
                    "clinical_effect": rule.clinical_effect,
                    "management_advice": rule.management_advice,
                    "involves_existing_medication": is_with_existing,
                    "requires_doctor_override": rule.severity in [
                        DrugInteractionRule.Severity.CONTRAINDICATED,
                        DrugInteractionRule.Severity.SEVERE
                    ]
                })

        # Sort by severity (CONTRAINDICATED first)
        severity_order = {
            DrugInteractionRule.Severity.CONTRAINDICATED: 1,
            DrugInteractionRule.Severity.SEVERE: 2,
            DrugInteractionRule.Severity.MODERATE: 3,
            DrugInteractionRule.Severity.INFO: 4,
        }
        detected_interactions.sort(key=lambda item: severity_order.get(item["severity"], 99))

        logger.info(
            "DrugInteractionService evaluated %d generic drugs, detected %d interactions",
            len(all_generics_clean), len(detected_interactions)
        )
        return detected_interactions

