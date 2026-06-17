from collections.abc import Generator

from sqlalchemy import Engine
from sqlmodel import Session, SQLModel, create_engine

from config import settings
from models import EndpointPermission

engine = create_engine(settings.DB_URL, echo=settings.DEBUG)

SEED: dict[str, list[str]] = {
    "expenses:read": ["Viewer", "Approver", "Admin"],
    "expenses:approve": ["Approver", "Admin"],
    "admin:permissions": ["Admin"],
}
# azure users:
# bob->admin, pybob approver, testuser viewer


def get_session() -> Generator[Session]:
    with Session(engine) as session:
        yield session


def create_db_and_seed(engine: Engine = engine) -> Engine:
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

    return engine
