from __future__ import annotations

from pydantic import BaseModel, field_validator


class Profile(BaseModel):
    name: str
    jdbc_url: str
    username: str
    changelog_file: str
    default_schema: str | None = None
    protected: bool = False
    contexts: str | None = None

    @field_validator("jdbc_url")
    @classmethod
    def validate_jdbc(cls, v: str) -> str:
        if not v.startswith("jdbc:"):
            raise ValueError("jdbc_url must start with 'jdbc:'")
        return v

    @property
    def driver_class(self) -> str:
        mapping = {
            "jdbc:postgresql": "org.postgresql.Driver",
            "jdbc:mysql": "com.mysql.cj.jdbc.Driver",
            "jdbc:mariadb": "org.mariadb.jdbc.Driver",
            "jdbc:oracle": "oracle.jdbc.OracleDriver",
            "jdbc:sqlserver": "com.microsoft.sqlserver.jdbc.SQLServerDriver",
        }
        for prefix, driver in mapping.items():
            if self.jdbc_url.startswith(prefix):
                return driver
        return ""


class Config(BaseModel):
    active: str | None = None
    profiles: list[Profile] = []

    def get(self, name: str) -> Profile | None:
        for p in self.profiles:
            if p.name == name:
                return p
        return None

    def active_profile(self) -> Profile | None:
        if self.active:
            return self.get(self.active)
        return None
