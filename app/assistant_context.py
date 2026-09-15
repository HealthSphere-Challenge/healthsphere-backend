"""Deterministic routing for minimum-context Assistant requests."""

import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum


class AssistantContextMode(StrEnum):
    general_medical_information = "general_medical_information"
    own_profile_data = "own_profile_data"
    own_latest_measurements = "own_latest_measurements"
    selected_assessment_explanation = "selected_assessment_explanation"
    unsupported_or_ambiguous = "unsupported_or_ambiguous"


@dataclass(frozen=True)
class AssistantRoutingDecision:
    mode: AssistantContextMode
    requested_fields: tuple[str, ...] = ()


PROFILE_FIELDS = {
    "height_cm": ("my height", "height saved", "ma taille"),
    "date_of_birth": ("my date of birth", "my age", "ma date de naissance", "mon age"),
    "sex_at_birth": ("my sex", "sexe a la naissance"),
    "smoking_status": ("my smoking status", "do i smoke", "mon statut tabagique"),
    "allergies": ("my allergies", "mes allergies"),
    "medications": ("my medications", "my medicines", "mes medicaments"),
    "medical_conditions": ("my medical conditions", "mes maladies", "mes antecedents"),
    "activity_level": ("my activity level", "mon niveau d activite"),
    "typical_sleep_minutes": ("my sleep", "mon sommeil"),
}

MEASUREMENT_FIELDS = {
    "blood_pressure": (
        "my blood pressure",
        "my latest blood pressure",
        "ma tension",
        "ma pression arterielle",
    ),
    "heart_rate": (
        "my heart rate",
        "my latest heart rate",
        "ma frequence cardiaque",
        "mon rythme cardiaque",
    ),
    "weight": ("my weight", "my latest weight", "mon poids"),
    "blood_glucose": ("my blood glucose", "my latest blood glucose", "ma glycemie"),
    "sleep_duration": ("my sleep duration", "my latest sleep duration", "ma duree de sommeil"),
    "physical_activity_duration": (
        "my activity duration",
        "my latest activity duration",
        "ma duree d activite",
    ),
}


def normalize_text(value: str) -> str:
    folded = unicodedata.normalize("NFKD", value.casefold())
    return re.sub(r"\s+", " ", "".join(c for c in folded if not unicodedata.combining(c))).strip()


class AssistantContextRouter:
    def route(self, message: str, assessment_selected: bool = False) -> AssistantRoutingDecision:
        if assessment_selected:
            return AssistantRoutingDecision(AssistantContextMode.selected_assessment_explanation)
        text = normalize_text(message)
        if any(
            phrase in text
            for phrase in (
                "do i have",
                "am i hypertensive",
                "is my blood pressure normal",
                "diagnose",
                "est ce que j ai",
                "suis je hypertendu",
                "ma tension est elle normale",
            )
        ):
            return AssistantRoutingDecision(AssistantContextMode.general_medical_information)
        if any(
            phrase in text
            for phrase in (
                "tell me everything about my health",
                "analyze all my records",
                "analyse toutes mes donnees",
                "tout sur ma sante",
            )
        ):
            return AssistantRoutingDecision(AssistantContextMode.unsupported_or_ambiguous)
        measurements = tuple(
            field
            for field, phrases in MEASUREMENT_FIELDS.items()
            if any(phrase in text for phrase in phrases)
        )
        if measurements:
            return AssistantRoutingDecision(
                AssistantContextMode.own_latest_measurements, measurements
            )
        if any(phrase in text for phrase in ("my latest measurement", "mes dernieres mesures")):
            return AssistantRoutingDecision(AssistantContextMode.own_latest_measurements)
        fields = tuple(
            field
            for field, phrases in PROFILE_FIELDS.items()
            if any(phrase in text for phrase in phrases)
        )
        broad_profile = any(
            phrase in text
            for phrase in (
                "my profile",
                "my health data",
                "my information",
                "what do you have saved about me",
                "mon profil",
                "mes donnees",
                "mes donnees de sante",
                "donnees da ma sante",
            )
        )
        if fields or broad_profile:
            return AssistantRoutingDecision(AssistantContextMode.own_profile_data, fields)
        return AssistantRoutingDecision(AssistantContextMode.general_medical_information)
