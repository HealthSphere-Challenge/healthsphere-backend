from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.api.auth import AuthServiceDep, CurrentSession
from app.db.session import get_db
from app.schemas import (
    DashboardResponse,
    MeasurementCreate,
    MeasurementListResponse,
    MeasurementResponse,
)
from app.services import MeasurementService

router = APIRouter(prefix="/api/v1", tags=["measurements"])
Db = Annotated[Session, Depends(get_db)]
CsrfHeader = Annotated[str | None, Header()]


@router.post("/measurements", status_code=201, response_model=MeasurementResponse)
def create_measurement(
    body: MeasurementCreate,
    authenticated: CurrentSession,
    auth_service: AuthServiceDep,
    db: Db,
    x_csrf_token: CsrfHeader = None,
) -> MeasurementResponse:
    auth_service.require_csrf(authenticated, x_csrf_token)
    return MeasurementService(db).create(authenticated.user, body)


@router.get("/measurements", response_model=MeasurementListResponse)
def list_measurements(
    authenticated: CurrentSession,
    db: Db,
    cursor: Annotated[str | None, Query()] = None,
) -> MeasurementListResponse:
    return MeasurementService(db).list(authenticated.user, cursor)


@router.get("/measurements/{measurement_id}", response_model=MeasurementResponse)
def get_measurement(
    measurement_id: UUID, authenticated: CurrentSession, db: Db
) -> MeasurementResponse:
    return MeasurementService(db).get(authenticated.user, measurement_id)


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(authenticated: CurrentSession, db: Db) -> DashboardResponse:
    values, generated_at = MeasurementService(db).dashboard(authenticated.user)
    return DashboardResponse(generated_at=generated_at, latest_measurements=values)
