from typing import Awaitable, Callable

from fastapi import Depends, HTTPException, status
from fastapi_azure_auth import SingleTenantAzureAuthorizationCodeBearer
from fastapi_azure_auth.user import User
from sqlmodel import Session

from config import settings
from db import get_session
from models import EndpointPermission

azure_scheme = SingleTenantAzureAuthorizationCodeBearer(
    app_client_id=settings.APP_CLIENT_ID,
    tenant_id=settings.TENANT_ID,
    scopes=settings.scopes,
)


def require(endpoint_key: str) -> Callable[..., Awaitable[User]]:
    async def checker(
        user: User = Depends(azure_scheme),
        session: Session = Depends(get_session),
    ) -> User:
        perm = session.get(EndpointPermission, endpoint_key)
        allowed = set(perm.roles) if perm else set()
        if not allowed.intersection(set(user.roles)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this endpoint.",
            )
        return user

    return checker
