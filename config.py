from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    TENANT_ID: str
    APP_CLIENT_ID: str
    OPENAPI_CLIENT_ID: str
    DB_URL: str = "sqlite:///rbac.db"
    DEBUG: bool = False

    @property
    def scope_name(self) -> str:
        return f"api://{self.APP_CLIENT_ID}/user_impersonation"

    @property
    def scopes(self) -> dict[str, str]:
        return {self.scope_name: "user_impersonation"}


settings = Settings()  # ty: ignore[missing-argument]
