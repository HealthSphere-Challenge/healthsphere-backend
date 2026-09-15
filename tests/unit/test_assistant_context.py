from app.assistant_context import AssistantContextMode, AssistantContextRouter

router = AssistantContextRouter()


def test_routes_general_medical_information() -> None:
    assert (
        router.route("What is high blood pressure?").mode
        == AssistantContextMode.general_medical_information
    )


def test_routes_profile_and_minimum_field() -> None:
    broad = router.route("What health data is in my profile?")
    assert broad.mode == AssistantContextMode.own_profile_data and broad.requested_fields == ()
    height = router.route("What is my height?")
    assert height.mode == AssistantContextMode.own_profile_data
    assert height.requested_fields == ("height_cm",)


def test_routes_latest_measurement() -> None:
    decision = router.route("What is my latest blood pressure?")
    assert decision.mode == AssistantContextMode.own_latest_measurements
    assert decision.requested_fields == ("blood_pressure",)


def test_selected_assessment_takes_precedence() -> None:
    assert (
        router.route("Explain my selected assessment", True).mode
        == AssistantContextMode.selected_assessment_explanation
    )


def test_routes_broad_health_analysis_to_safe_narrowing() -> None:
    assert (
        router.route("Tell me everything about my health").mode
        == AssistantContextMode.unsupported_or_ambiguous
    )


def test_routes_observed_french_profile_regression() -> None:
    for text in ("donner les données da ma santé dans mon profil", "Montre mes données de santé"):
        assert router.route(text).mode == AssistantContextMode.own_profile_data


def test_personal_diagnosis_stays_on_safe_agent_path() -> None:
    assert (
        router.route("My blood pressure is 128/82. Do I have hypertension?").mode
        == AssistantContextMode.general_medical_information
    )
