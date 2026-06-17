from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


class EndpointPermission(SQLModel, table=True):
    endpoint_key: str = Field(primary_key=True)
    roles: list[str] = Field(default_factory=list, sa_column=Column(JSON))
