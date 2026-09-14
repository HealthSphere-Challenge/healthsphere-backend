from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.core.settings import Settings
from app.db.session import get_db
from app.schemas import (
    AccountResponse,
    LoginRequest,
    ProfilePatch,
    ProfileResponse,
    RegisterRequest,
    UserResponse,
)
from app.services import AuthenticatedSession, AuthService, ProfileService, age_years

router = APIRouter(prefix="/api/v1", tags=["authentication"])


Db = Annotated[Session, Depends(get_db)]


def request_settings(request: Request) -> Settings:
    return request.app.state.settings


AppSettings = Annotated[Settings, Depends(request_settings)]


def auth_service(db: Db, settings: AppSettings) -> AuthService:
    return AuthService(db, settings)


AuthServiceDep = Annotated[AuthService, Depends(auth_service)]


def current_session(request: Request, service: AuthServiceDep) -> AuthenticatedSession:
    authenticated = service.authenticate(request.cookies.get(service.settings.session_cookie_name))
    csrf = request.cookies.get("healthsphere_csrf")
    if csrf:
        try:
            service.require_csrf(authenticated, csrf)
            authenticated.csrf_token = csrf
        except DomainError:
            pass
    return authenticated


def account_response(
    authenticated: AuthenticatedSession, db: Session, csrf: str
) -> AccountResponse:
    profile = ProfileService(db).get(authenticated.user)
    profile_data = ProfileResponse.model_validate(profile).model_copy(
        update={"age_years": age_years(profile.date_of_birth)}
    )
    return AccountResponse(
        user=UserResponse.model_validate(authenticated.user), profile=profile_data, csrf_token=csrf
    )


def set_session_cookie(
    response: Response, authenticated: AuthenticatedSession, settings: Settings
) -> str:
    secure = (
        settings.session_cookie_secure
        if settings.session_cookie_secure is not None
        else settings.app_environment == "production"
    )
    response.set_cookie(
        settings.session_cookie_name,
        authenticated.session_token or "",
        max_age=settings.session_absolute_seconds,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        "healthsphere_csrf",
        authenticated.csrf_token or "",
        max_age=settings.session_absolute_seconds,
        httponly=False,
        secure=secure,
        samesite="lax",
        path="/",
    )
    return authenticated.csrf_token or ""


CurrentSession = Annotated[AuthenticatedSession, Depends(current_session)]
CsrfHeader = Annotated[str | None, Header()]


@router.post("/auth/register", status_code=201, response_model=AccountResponse)
def register(
    body: RegisterRequest, response: Response, db: Db, settings: AppSettings
) -> AccountResponse:
    authenticated = AuthService(db, settings).register(body)
    return account_response(
        authenticated, db, set_session_cookie(response, authenticated, settings)
    )


@router.post("/auth/login", response_model=AccountResponse)
def login(body: LoginRequest, response: Response, db: Db, settings: AppSettings) -> AccountResponse:
    authenticated = AuthService(db, settings).login(str(body.email), body.password)
    return account_response(
        authenticated, db, set_session_cookie(response, authenticated, settings)
    )


@router.get("/auth/me", response_model=AccountResponse)
def me(authenticated: CurrentSession, db: Db) -> AccountResponse:
    return account_response(authenticated, db, authenticated.csrf_token or "")


@router.post("/auth/logout", status_code=204)
def logout(
    response: Response,
    authenticated: CurrentSession,
    service: AuthServiceDep,
    x_csrf_token: CsrfHeader = None,
) -> None:
    service.require_csrf(authenticated, x_csrf_token)
    service.revoke(authenticated)
    response.delete_cookie(service.settings.session_cookie_name, path="/")
    response.delete_cookie("healthsphere_csrf", path="/")


@router.get("/profile", response_model=ProfileResponse)
def get_profile(authenticated: CurrentSession, db: Db) -> ProfileResponse:
    profile = ProfileService(db).get(authenticated.user)
    return ProfileResponse.model_validate(profile).model_copy(
        update={"age_years": age_years(profile.date_of_birth)}
    )


@router.patch("/profile", response_model=ProfileResponse)
def patch_profile(
    body: ProfilePatch,
    authenticated: CurrentSession,
    service: AuthServiceDep,
    db: Db,
    x_csrf_token: CsrfHeader = None,
) -> ProfileResponse:
    service.require_csrf(authenticated, x_csrf_token)
    profile = ProfileService(db).patch(authenticated.user, body)
    return ProfileResponse.model_validate(profile).model_copy(
        update={"age_years": age_years(profile.date_of_birth)}
    )
