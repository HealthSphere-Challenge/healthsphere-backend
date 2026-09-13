from fastapi.testclient import TestClient

from app.main import create_app


def test_application_health_and_request_id(settings) -> None:
    with TestClient(create_app(settings)) as client:
        response = client.get(
            "/health", headers={"X-Request-ID": "c4a760a8-7d0b-4f98-9652-244be1ebcc2e"}
        )
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"] == "c4a760a8-7d0b-4f98-9652-244be1ebcc2e"


def test_invalid_request_id_is_replaced(settings) -> None:
    with TestClient(create_app(settings)) as client:
        response = client.get("/health", headers={"X-Request-ID": "medical-message"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] != "medical-message"
