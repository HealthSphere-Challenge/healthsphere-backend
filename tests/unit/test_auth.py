from datetime import date

from app.schemas import ProfilePatch
from app.services import age_years, digest, normalize_email


def test_auth_helpers_are_deterministic_and_normalize_email() -> None:
    assert normalize_email("  Person@EXAMPLE.TEST ") == "person@example.test"
    assert digest("secret") == digest("secret")
    assert digest("secret") != digest("other")


def test_age_policy_handles_birthdays() -> None:
    assert age_years(date(2008, 9, 13), date(2026, 9, 13)) == 18
    assert age_years(date(2008, 9, 14), date(2026, 9, 13)) == 17


def test_profile_patch_preserves_omitted_null_and_empty() -> None:
    patch = ProfilePatch(allergies=[], medications=None)
    assert patch.model_dump(exclude_unset=True) == {"allergies": [], "medications": None}
    assert ProfilePatch(chronic_conditions=[]).medical_conditions == []
