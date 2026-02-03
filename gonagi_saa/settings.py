from pathlib import Path
from pydantic import SecretStr
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    JsonConfigSettingsSource,
)

CONFIG_DIR = Path.home() / ".config" / "gonagi-saa"
CONFIG_FILE = CONFIG_DIR / "config.json"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="GONAGI_SAA_", json_file=CONFIG_FILE, extra="ignore"
    )

    default_model: str = "gpt-4o"
    notion_database_id: str = ""
    notion_api_key: SecretStr = SecretStr("")
    anthropic_api_key: SecretStr = SecretStr("")
    openai_api_key: SecretStr = SecretStr("")
    google_api_key: SecretStr = SecretStr("")
    imgur_client_id: SecretStr = SecretStr("")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        sources = [
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
        ]

        # 설정 파일이 존재하고 비어있지 않은 경우에만 JSON 설정 로드
        if CONFIG_FILE.exists() and CONFIG_FILE.stat().st_size > 0:
            try:
                sources.append(JsonConfigSettingsSource(settings_cls))
            except Exception:
                # 유효하지 않은 JSON 파일이면 무시하고 기본값 사용
                pass

        return tuple(sources)


settings = Settings()

__all__ = ["settings", "CONFIG_DIR", "CONFIG_FILE"]
