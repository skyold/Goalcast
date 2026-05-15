from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    oddalerts_api_key: str
    goalcast_db_path: str = "goalcast.db"

    model_config = {"env_file": "../.env", "extra": "ignore"}

settings = Settings()
