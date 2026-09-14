from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from sqlalchemy.orm import Session

from app.agent_client import HealthSphereAgentClient
from app.api.auth import AuthServiceDep, CurrentSession
from app.conversation_service import ConversationService
from app.core.errors import DomainError
from app.core.settings import Settings
from app.db.session import get_db
from app.schemas import ConversationListResponse, ConversationMessageCreate, ConversationResponse

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])
Db = Annotated[Session, Depends(get_db)]
CsrfHeader = Annotated[str | None, Header()]


def get_agent_client(request: Request) -> HealthSphereAgentClient:
    settings: Settings = request.app.state.settings
    if not settings.agent_service_url or not settings.agent_internal_token:
        raise DomainError(503, "agent_unavailable", "The assistant service is unavailable.")
    return HealthSphereAgentClient(
        settings.agent_service_url,
        settings.agent_internal_token,
        settings.agent_timeout_seconds,
        settings.agent_connect_timeout_seconds,
    )


AgentClient = Annotated[HealthSphereAgentClient, Depends(get_agent_client)]


@router.post("", status_code=201, response_model=ConversationResponse)
def create_conversation(
    authenticated: CurrentSession, auth: AuthServiceDep, db: Db, x_csrf_token: CsrfHeader = None
) -> ConversationResponse:
    auth.require_csrf(authenticated, x_csrf_token)
    return ConversationService(db).create(authenticated.user)


@router.get("", response_model=ConversationListResponse)
def list_conversations(
    authenticated: CurrentSession, db: Db, cursor: Annotated[str | None, Query()] = None
) -> ConversationListResponse:
    return ConversationService(db).list(authenticated.user, cursor)


@router.get("/{conversation_id}", response_model=ConversationResponse)
def get_conversation(
    conversation_id: UUID, authenticated: CurrentSession, db: Db
) -> ConversationResponse:
    return ConversationService(db).get(authenticated.user, conversation_id)


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: UUID,
    authenticated: CurrentSession,
    auth: AuthServiceDep,
    db: Db,
    x_csrf_token: CsrfHeader = None,
) -> Response:
    auth.require_csrf(authenticated, x_csrf_token)
    ConversationService(db).delete(authenticated.user, conversation_id)
    return Response(status_code=204)


@router.post("/{conversation_id}/messages", response_model=ConversationResponse)
def send_message(
    conversation_id: UUID,
    body: ConversationMessageCreate,
    authenticated: CurrentSession,
    auth: AuthServiceDep,
    db: Db,
    agent: AgentClient,
    x_csrf_token: CsrfHeader = None,
) -> ConversationResponse:
    auth.require_csrf(authenticated, x_csrf_token)
    return ConversationService(db, agent).send(
        authenticated.user, conversation_id, body.content.strip(), body.assessment_id
    )
