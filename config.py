from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    BOT_TOKEN: str = "YOUR_BOT_TOKEN_HERE"
    ADMIN_IDS: str = ""
    STUDIO_NAME: str = "LEO DANCE STUDIO"
    STUDIO_CITY: str = "Дрогобич"
    STUDIO_ADDRESS: str = "вул. Грушевського 148 Б"
    STUDIO_PHONE: str = "0983223561"
    STUDIO_INSTAGRAM: str = "leo_danceee_studio"
    STUDIO_DIRECTOR: str = "_ireeendtk"
    STUDIO_BOXING_CLUB: str = "hunterclub_dro"
    DATABASE_PATH: str = "leo_dance.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def admin_id_list(self) -> List[int]:
        if not self.ADMIN_IDS:
            return []
        res = []
        for item in self.ADMIN_IDS.split(","):
            item = item.strip()
            if item.isdigit():
                res.append(int(item))
        return res

settings = Settings()
