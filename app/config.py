from pydantic import BaseModel
from functools import lru_cache

class Settings(BaseModel):
    app_name: str = "AI Assistant Backend"
    timezone: str = "Asia/Kolkata"

@lru_cache
def get_settings() -> Settings:
    return Settings()
