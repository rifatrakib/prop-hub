from pydantic import BaseSettings


class Settings(BaseSettings):
    app_name: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    mongo_connection_uri: str
    database_name: str

    class Config:
        env_file = ".env"


settings = Settings().dict()


def read_config(name):
    return settings.get(name, None)
