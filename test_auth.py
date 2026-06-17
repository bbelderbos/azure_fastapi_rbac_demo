from collections.abc import Generator
from types import SimpleNamespace

import httpx2 as httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlmodel import Session, create_engine
from sqlmodel.pool import StaticPool

import db
from auth import azure_scheme
from main import app


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def engine() -> Generator[Engine]:
    eng = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    db.create_db_and_seed(eng)
    yield eng
    eng.dispose()


def client_as(engine: Engine, *roles: str) -> TestClient:
    def fake_user():
        return SimpleNamespace(roles=list(roles), name="tester")

    def session_override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[azure_scheme] = fake_user
    app.dependency_overrides[db.get_session] = session_override
    return TestClient(app)


def read(client: TestClient) -> httpx.Response:
    return client.get("/expenses")


def approve(client: TestClient) -> httpx.Response:
    return client.post("/expenses/1/approve")


def admin(client: TestClient) -> httpx.Response:
    return client.put(
        "/admin/permissions",
        params={"endpoint_key": "expenses:approve"},
        json=["Admin"],
    )


@pytest.mark.parametrize(
    "roles, call, expected",
    [
        # expenses:read — Viewer, Approver, Admin
        (("Viewer",), read, 200),
        (("Approver",), read, 200),
        (("Admin",), read, 200),
        ((), read, 403),
        (("Unknown",), read, 403),
        # expenses:approve — Approver, Admin
        (("Viewer",), approve, 403),
        (("Approver",), approve, 200),
        (("Admin",), approve, 200),
        ((), approve, 403),
        (("Unknown",), approve, 403),
        # admin:permissions — Admin only
        (("Viewer",), admin, 403),
        (("Approver",), admin, 403),
        (("Admin",), admin, 200),
        ((), admin, 403),
        (("Unknown",), admin, 403),
        # multiple roles take the union of what each grants
        (("Viewer", "Approver"), approve, 200),
        (("Viewer", "Approver"), admin, 403),
        (("Viewer", "Admin"), admin, 200),
    ],
)
def test_rbac_matrix(engine, roles, call, expected):
    assert call(client_as(engine, *roles)).status_code == expected


def test_repoint_revokes_access(engine):
    assert approve(client_as(engine, "Approver")).status_code == 200
    assert admin(client_as(engine, "Admin")).status_code == 200  # drops Approver
    assert approve(client_as(engine, "Approver")).status_code == 403


def test_repoint_grants_access(engine):
    assert approve(client_as(engine, "Viewer")).status_code == 403
    r = client_as(engine, "Admin").put(
        "/admin/permissions",
        params={"endpoint_key": "expenses:approve"},
        json=["Viewer", "Approver", "Admin"],
    )
    assert r.status_code == 200
    assert approve(client_as(engine, "Viewer")).status_code == 200


def test_empty_roles_rejected(engine):
    r = client_as(engine, "Admin").put(
        "/admin/permissions",
        params={"endpoint_key": "expenses:approve"},
        json=[],
    )
    assert r.status_code == 422


def test_admin_cannot_lock_itself_out(engine):
    r = client_as(engine, "Admin").put(
        "/admin/permissions",
        params={"endpoint_key": "admin:permissions"},
        json=["Viewer"],
    )
    assert r.status_code == 422


def test_admin_creates_new_permission_key(engine):
    r = client_as(engine, "Admin").put(
        "/admin/permissions",
        params={"endpoint_key": "reports:export"},
        json=["Admin"],
    )
    assert r.status_code == 200
    assert r.json() == {"endpoint_key": "reports:export", "roles": ["Admin"]}
