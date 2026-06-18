from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi_azure_auth.user import User
from sqlmodel import Session, create_engine

from auth import azure_scheme, require
from config import settings
from db import create_db_and_seed, get_session
from models import EndpointPermission


@asynccontextmanager
async def lifespan(app: FastAPI):
    await azure_scheme.openid_config.load_config()
    engine = create_engine(settings.DB_URL, echo=settings.DEBUG)
    create_db_and_seed(engine)
    yield
    engine.dispose()


app = FastAPI(
    lifespan=lifespan,
    swagger_ui_oauth2_redirect_url="/oauth2-redirect",
    swagger_ui_init_oauth={
        "usePkceWithAuthorizationCodeGrant": True,
        "clientId": settings.OPENAPI_CLIENT_ID,
        "scopes": settings.scope_name,
    },
)


@app.get("/expenses")
async def list_expenses(user: Annotated[User, Depends(require("expenses:read"))]):
    """List all expenses."""
    return {"expenses": ["expense1", "expense2"], "user": user.name}


@app.post("/expenses/{expense_id}/approve")
async def approve_expense(
    expense_id: int,
    user: Annotated[User, Depends(require("expenses:approve"))],
):
    """Approve an expense by id."""
    return {"approved": expense_id, "by": user.name}


def locks_out_admins(endpoint_key: str, roles: list[str]) -> bool:
    return endpoint_key == "admin:permissions" and "Admin" not in roles


@app.put("/admin/permissions")
async def set_permission(
    endpoint_key: str,
    roles: list[str],
    user: Annotated[User, Depends(require("admin:permissions"))],
    session: Annotated[Session, Depends(get_session)],
):
    """Set the roles allowed to access an endpoint."""
    if not roles:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "roles must be non-empty"
        )
    if locks_out_admins(endpoint_key, roles):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "cannot remove Admin from admin:permissions",
        )
    permission = session.get(EndpointPermission, endpoint_key)
    # upsert
    if permission is None:
        permission = EndpointPermission(endpoint_key=endpoint_key, roles=roles)
    else:
        permission.roles = roles
    session.add(permission)
    session.commit()
    session.refresh(permission)
    return permission
