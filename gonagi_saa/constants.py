"""상수 정의"""

# 이미지를 지원하는 모델 목록
VISION_SUPPORTED_MODELS = {
    # OpenAI
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-4-turbo-2024-04-09",
    "gpt-4-vision-preview",
    # Anthropic Claude
    "claude-3-5-sonnet-20241022",
    "claude-3-5-sonnet-20240620",
    "claude-3-opus-20240229",
    "claude-3-sonnet-20240229",
    "claude-3-haiku-20240307",
    "claude-3-5-haiku-20241022",
    # Google Gemini
    "gemini-1.5-pro",
    "gemini-1.5-flash",
    "gemini-2.0-flash-exp",
    "gemini-2.5-flash",
    "gemini-pro-vision",
}

# 최대 이미지 개수
MAX_IMAGES = 3
