from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings

ENV_PREFIX = "a_book_store_"


class Config(BaseSettings):
    bind_address: str = Field(default="0.0.0.0", env=f"{ENV_PREFIX}bind_address")
    port: int = 8080
    database_uri: Optional[str] = Field(default=None, env=f"{ENV_PREFIX}database_uri")

    class Config:
        env_prefix = ENV_PREFIX
