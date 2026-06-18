# FastAPI + Azure Entra ID RBAC demo

A FastAPI app where users authenticate against **Entra ID** and each endpoint is
authorized by comparing the user's app roles (from the JWT `roles` claim) against the
roles required for that endpoint — and those required roles live in a **SQLModel table**,
not in code, so an admin can re-point them at runtime.

## How it works

- A user signs in via Entra (auth-code flow); Entra mints an access token whose `roles`
  claim is filled from the App Roles assigned to that user.
- The client calls the API with `Authorization: Bearer <token>`. `azure_scheme`
  (`auth.py`) validates the token and yields a `User`.
- `require("<endpoint_key>")` loads the allowed roles for that key from the
  `endpointpermission` table and returns **403** unless the user's roles overlap.
- `PUT /admin/permissions` (Admin-only) rewrites a row, changing who can hit an endpoint
  without a code change.

| Method & path | Endpoint key | Seeded roles |
|---|---|---|
| `GET /expenses` | `expenses:read` | Viewer, Approver, Admin |
| `POST /expenses/{id}/approve` | `expenses:approve` | Approver, Admin |
| `PUT /admin/permissions` | `admin:permissions` | Admin |

The table is seeded on startup (`db.py`); SQLite by default (`rbac.db`), swap `DB_URL`
for Postgres etc.

## Azure setup

You need two app registrations in the same tenant:

1. **Backend API** (`APP_CLIENT_ID`)
   - Expose an API: Application ID URI `api://<api-client-id>`, add scope
     `user_impersonation`.
   - Define App Roles `Viewer`, `Approver`, `Admin` (member type Users/Groups).
   - Set the manifest to **issue v2 access tokens**
     (`requestedAccessTokenVersion: 2`) — otherwise every call 401s.
   - Assign test users to roles under **Enterprise applications → Users and groups**
     (direct assignment only; nested groups don't flow into `roles`).

2. **Swagger client** (`OPENAPI_CLIENT_ID`) — lets `/docs` log you in
   - SPA platform with redirect URI `http://localhost:8000/oauth2-redirect`
     (enable access + ID tokens).
   - API permission → delegated `user_impersonation` on the backend API, grant admin
     consent.

## Run

```bash
cp .env.example .env   # fill TENANT_ID, APP_CLIENT_ID, OPENAPI_CLIENT_ID
uv run uvicorn main:app --reload
# open http://localhost:8000/docs → Authorize → call the endpoints
uv run pytest -q       # tests stub Entra, so no Azure needed
```
