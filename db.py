from collections.abc import Generator

from sqlalchemy import Engine
from sqlmodel import Session, SQLModel, create_engine

from config import settings
from models import EndpointPermission

SEED: dict[str, list[str]] = {
    "expenses:read": ["Viewer", "Approver", "Admin"],
    "expenses:approve": ["Approver", "Admin"],
    "admin:permissions": ["Admin"],
}


def get_session() -> Generator[Session]:
    engine = create_engine(settings.DB_URL, echo=settings.DEBUG)
    with Session(engine) as session:
        yield session


def create_db_and_seed(engine: Engine) -> None:
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        for permission, roles in SEED.items():
            existing_permission = session.get(EndpointPermission, permission)
            if existing_permission is None:
                new_permission = EndpointPermission(
                    endpoint_key=permission, roles=roles
                )
                session.add(new_permission)
        session.commit()
