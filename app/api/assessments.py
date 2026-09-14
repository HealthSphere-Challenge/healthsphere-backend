"""Authenticated application assessment endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy.orm import Session

from app.ai_client import HealthSphereAiClient
from app.api.auth import AuthServiceDep, CurrentSession
from app.assessment_service import AssessmentService
from app.core.errors import DomainError
from app.core.settings import Settings
from app.db.session import get_db
from app.schemas import AssessmentListResponse, AssessmentResponse

router = APIRouter(prefix="/api/v1", tags=["assessments"])
Db = Annotated[Session, Depends(get_db)]
CsrfHeader = Annotated[str | None, Header()]


def get_ai_client(request: Request) -> HealthSphereAiClient:
    settings: Settings = request.app.state.settings
    if not settings.ai_service_url or not settings.ai_internal_token:
        raise DomainError(503, "ai_unavailable", "The assessment service is unavailable.")
    return HealthSphereAiClient(
        settings.ai_service_url,
        settings.ai_internal_token,
        settings.ai_timeout_seconds,
        settings.ai_connect_timeout_seconds,
    )


AiClient = Annotated[HealthSphereAiClient, Depends(get_ai_client)]


@router.post("/assessments", response_model=AssessmentResponse)
def create_assessment(
    request: Request,
    authenticated: CurrentSession,
    auth_service: AuthServiceDep,
    db: Db,
    ai_client: AiClient,
    x_csrf_token: CsrfHeader = None,
) -> AssessmentResponse:
    auth_service.require_csrf(authenticated, x_csrf_token)
    return AssessmentService(db, ai_client).create(
        authenticated.user, UUID(request.state.request_id)
    )


@router.get("/assessments", response_model=AssessmentListResponse)
def list_assessments(
    authenticated: CurrentSession,
    db: Db,
    cursor: Annotated[str | None, Query()] = None,
) -> AssessmentListResponse:
    return AssessmentService(db).list(authenticated.user, cursor)


@router.get("/assessments/{assessment_id}", response_model=AssessmentResponse)
def get_assessment(
    assessment_id: UUID,
    authenticated: CurrentSession,
    db: Db,
) -> AssessmentResponse:
    return AssessmentService(db).get(authenticated.user, assessment_id)
