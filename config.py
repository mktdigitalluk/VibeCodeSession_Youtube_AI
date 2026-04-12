import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv("keys.env")

@dataclass(frozen=True)
class Config:
    # Gemini (idea generation)
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_text_model: str = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.5-flash")

    # Replicate (thumbnail 16:9 + short image 9:16)
    replicate_api_token: str = os.getenv("REPLICATE_API_TOKEN", "")

    # Kie.ai (music generation)
    kie_api_key: str = os.getenv("KIE_API_KEY", "")
    kie_model: str = os.getenv("KIE_MODEL", "V4_5")
    kie_callback_url: str = os.getenv("KIE_CALLBACK_URL", "https://example.com/kie-callback")
    kie_poll_seconds: int = int(os.getenv("KIE_POLL_SECONDS", "20"))
    kie_timeout_seconds: int = int(os.getenv("KIE_TIMEOUT_SECONDS", "900"))

    # Video
    video_duration_minutes: int = int(os.getenv("VIDEO_DURATION_MINUTES", "60"))
    video_privacy_status: str = os.getenv("VIDEO_PRIVACY_STATUS", "private")
    loop_audio: bool = os.getenv("LOOP_AUDIO", "true").lower() == "true"

    # YouTube OAuth
    youtube_client_id: str = os.getenv("YOUTUBE_CLIENT_ID", "")
    youtube_client_secret: str = os.getenv("YOUTUBE_CLIENT_SECRET", "")
    youtube_refresh_token: str = os.getenv("YOUTUBE_REFRESH_TOKEN", "")

    # Short video
    short_duration_seconds: int = int(os.getenv("SHORT_DURATION_SECONDS", "20"))
    short_start_offset_seconds: int = int(os.getenv("SHORT_START_OFFSET_SECONDS", "30"))

    # Data / state
    history_file: str = os.getenv("HISTORY_FILE", "data/history.json")
    history_size: int = int(os.getenv("HISTORY_SIZE", "20"))

    # Runtime
    cleanup_on_success: bool = os.getenv("CLEANUP_ON_SUCCESS", "false").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    business_timezone: str = os.getenv("BUSINESS_TIMEZONE", "America/Sao_Paulo")
