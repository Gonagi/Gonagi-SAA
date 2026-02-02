import re
import base64
from pathlib import Path
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chat_models.base import BaseChatModel

from gonagi_saa.settings import settings
from gonagi_saa.constants import VISION_SUPPORTED_MODELS


def llm_model_factory(
    name: str,
) -> BaseChatModel:
    """모델명으로 LLM 인스턴스 생성"""
    if name.startswith("claude"):
        return ChatAnthropic(
            model_name=name,
            api_key=settings.anthropic_api_key,
            temperature=0.0,
            max_retries=3,
            timeout=None,
            stop=None,
        )
    elif name.startswith("gpt"):
        return ChatOpenAI(
            name=name,
            model=name,
            api_key=settings.openai_api_key,
            temperature=0.0,
            max_retries=3,
        )
    elif re.match(r"^o\d", name):
        return ChatOpenAI(
            name=name,
            model=name,
            api_key=settings.openai_api_key,
            max_retries=3,
        )
    elif name.startswith("gemini"):
        return ChatGoogleGenerativeAI(
            name=name,
            model=name,
            api_key=settings.google_api_key,
            temperature=0.0,
            max_retries=3,
        )
    else:
        raise ValueError(f"Unknown model: {name}")


def is_vision_model(model_name: str) -> bool:
    """모델이 이미지 입력을 지원하는지 확인"""
    return model_name in VISION_SUPPORTED_MODELS


def encode_image(image_path: str) -> str:
    """이미지 파일을 base64로 인코딩"""
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"이미지 파일을 찾을 수 없습니다: {image_path}")

    with open(path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def get_image_mime_type(image_path: str) -> str:
    """이미지 파일의 MIME 타입 반환"""
    path = Path(image_path)
    suffix = path.suffix.lower()

    mime_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }

    return mime_types.get(suffix, "image/jpeg")


def prepare_image_content(image_path: str) -> dict[str, Any]:
    """이미지를 LangChain 메시지 형식으로 변환"""
    base64_image = encode_image(image_path)
    mime_type = get_image_mime_type(image_path)

    return {
        "type": "image_url",
        "image_url": {
            "url": f"data:{mime_type};base64,{base64_image}"
        },
    }
