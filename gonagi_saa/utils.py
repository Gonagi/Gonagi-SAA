import re
import base64
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
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


def upload_image_to_imgbb(image_path: str, api_key: str) -> str:
    """
    이미지를 imgbb에 업로드하고 URL 반환

    imgbb 무료 tier:
    - 파일 크기: 최대 32MB
    - 만료: 없음 (영구 저장)
    - 비공개 업로드 (URL을 아는 사람만 접근)

    Args:
        image_path: 업로드할 이미지 파일 경로
        api_key: imgbb API Key

    Returns:
        업로드된 이미지의 URL

    Raises:
        FileNotFoundError: 이미지 파일을 찾을 수 없는 경우
        requests.HTTPError: imgbb API 요청 실패
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"이미지 파일을 찾을 수 없습니다: {image_path}")

    # 이미지를 base64로 인코딩
    with open(path, "rb") as image_file:
        image_data = base64.b64encode(image_file.read()).decode("utf-8")

    # imgbb API 요청
    url = "https://api.imgbb.com/1/upload"
    data = {
        "key": api_key,
        "image": image_data,
    }

    response = requests.post(url, data=data)
    response.raise_for_status()

    # 업로드된 이미지 URL 반환
    result = response.json()
    return result["data"]["url"]


def generate_session_id() -> str:
    """
    현재 시간 기반 Session ID 생성

    형식: YYYY-MM-DD-HH:MM
    예: 2026-02-11-15:30

    Returns:
        Session ID 문자열
    """
    return datetime.now().strftime("%Y-%m-%d-%H:%M")
