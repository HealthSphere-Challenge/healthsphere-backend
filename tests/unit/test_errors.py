from fastapi import APIRouter, Query
from fastapi.testclient import TestClient

from app.main import create_app


def test_unexpected_error_uses_safe_canonical_shape(settings) -> None:
    app = create_app(settings)
    router = APIRouter()

    @router.get("/fail")
    def fail() -> None:
        raise RuntimeError("private downstream details")

    app.include_router(router)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/fail")
    body = response.json()
    assert response.status_code == 500
    assert body["error"]["code"] == "internal_error"
    assert body["error"]["request_id"] == response.headers["X-Request-ID"]
    assert "private downstream details" not in response.text


def test_validation_error_uses_canonical_shape(settings) -> None:
    app = create_app(settings)
    router = APIRouter()

    @router.get("/validate")
    def validate(limit: int = Query(ge=1)) -> dict[str, int]:
        return {"limit": limit}

    app.include_router(router)
    with TestClient(app) as client:
        response = client.get("/validate", params={"limit": 0})
    body = response.json()
    assert response.status_code == 422
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["details"][0]["path"] == "query.limit"
    assert body["error"]["request_id"] == response.headers["X-Request-ID"]
