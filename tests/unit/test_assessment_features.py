from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace

from app.assessment_service import HypertensionFeatureBuilder, calculate_age
from app.models import MetricType, SexAtBirth


def profile(**overrides):
    values = {
        "date_of_birth": date(2000, 9, 15),
        "sex_at_birth": SexAtBirth.female,
        "height_cm": 180.0,
        "smoking_status": "never",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def measurement(**values):
    return SimpleNamespace(**values)


def test_age_before_after_birthday_and_exactly_18():
    assert calculate_age(date(2000, 9, 15), date(2026, 9, 14)) == 25
    assert calculate_age(date(2000, 9, 15), date(2026, 9, 15)) == 26
    assert calculate_age(date(2008, 9, 14), date(2026, 9, 14)) == 18
    assert calculate_age(date(2009, 9, 14), date(2026, 9, 14)) == 17


def test_builder_uses_same_latest_bp_record_latest_hr_and_derived_bmi():
    latest = {
        MetricType.blood_pressure: measurement(systolic=128, diastolic=82),
        MetricType.heart_rate: measurement(numeric_value=Decimal("76")),
        MetricType.weight: measurement(numeric_value=Decimal("81")),
    }
    built = HypertensionFeatureBuilder().build(profile(), latest, datetime(2026, 9, 14, tzinfo=UTC))
    assert built.features.model_dump() == {
        "age_years": 25.0,
        "systolic_blood_pressure": 128.0,
        "diastolic_blood_pressure": 82.0,
        "heart_rate": 76.0,
        "bmi": 25.0,
        "sex_at_birth": "female",
        "smoking_status": "never",
    }
    assert built.missing_required == []


def test_builder_preserves_missing_data_and_normalizes_categories():
    built = HypertensionFeatureBuilder().build(
        profile(
            date_of_birth=None,
            sex_at_birth=SexAtBirth.intersex,
            height_cm=None,
            smoking_status="prefer_not_to_say",
        ),
        {},
        datetime(2026, 9, 14, tzinfo=UTC),
    )
    assert built.missing_required == [
        "age_years",
        "systolic_blood_pressure",
        "diastolic_blood_pressure",
    ]
    assert built.features.heart_rate is None and built.features.bmi is None
    assert built.features.sex_at_birth == "unknown"
    assert built.features.smoking_status == "unknown"
