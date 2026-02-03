from typing import cast
from pathlib import Path
from textwrap import dedent

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import PydanticOutputParser
from notion_client import Client as NotionClient
from notionize import notionize

from gonagi_saa.models import QnAModel
from gonagi_saa.utils import llm_model_factory, prepare_image_content, upload_image_to_imgbb
from gonagi_saa.settings import settings


def answer_question(
    model_name: str,
    question: str,
    image_paths: list[str] | None = None,
) -> QnAModel:
    """질문에 대한 답변 생성 (텍스트 + 이미지 지원)"""
    parser = PydanticOutputParser(pydantic_object=QnAModel)

    # 프롬프트 구성
    system_prompt = dedent(
        """\
        You are a helpful assistant that answers questions about AWS SAA (Solutions Architect Associate) exam preparation.

        Provide clear, structured, and detailed explanations in Korean.
        Include practical examples and important considerations when relevant.

        {format_instructions}
        """
    )

    # 멀티모달 메시지 구성
    if image_paths:
        # 이미지가 있는 경우: HumanMessage content를 리스트로 구성
        content_parts: list[dict | str] = [{"type": "text", "text": question}]
        for image_path in image_paths:
            content_parts.append(prepare_image_content(image_path))

        messages = [
            ("system", system_prompt),
            HumanMessage(content=content_parts),
        ]
        prompt = ChatPromptTemplate.from_messages(messages)
    else:
        # 텍스트만 있는 경우
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("human", "{question}"),
            ]
        )

    model = llm_model_factory(model_name)
    chain = prompt | model | parser

    print("🔥 질문에 대한 답변을 생성합니다...")

    if image_paths:
        result = cast(
            QnAModel,
            chain.invoke({"format_instructions": parser.get_format_instructions()}),
        )
    else:
        result = cast(
            QnAModel,
            chain.invoke(
                {
                    "question": question,
                    "format_instructions": parser.get_format_instructions(),
                }
            ),
        )

    # question 필드에 원본 질문 저장
    result.question = question

    return result


def save_to_notion(
    notion_client: NotionClient,
    qna: QnAModel,
    image_paths: list[str] | None = None,
) -> None:
    """질문-답변을 Notion에 저장 (이미지 포함)"""
    print("🔥 Notion에 저장합니다...")

    # 본문 구성: 질문 + 답변
    content = f"## 질문\n\n{qna.question}\n\n## 답변\n\n{qna.answer}"

    # 마크다운 -> Notion 블록 변환
    children = notionize(content)

    # 이미지 업로드 및 추가
    if image_paths:
        imgbb_api_key = settings.imgbb_api_key.get_secret_value()

        if not imgbb_api_key:
            print("⚠️  imgbb API Key가 설정되지 않았습니다. 이미지를 건너뜁니다.")
        else:
            for image_path in image_paths:
                path = Path(image_path)
                if path.exists():
                    try:
                        print(f"📤 이미지를 imgbb에 업로드 중: {path.name}")
                        # imgbb에 이미지 업로드
                        image_url = upload_image_to_imgbb(str(path), imgbb_api_key)
                        print(f"✅ 업로드 완료: {image_url}")

                        # Notion image 블록 추가
                        children.append(
                            {
                                "object": "block",
                                "type": "image",
                                "image": {
                                    "type": "external",
                                    "external": {"url": image_url},
                                },
                            }
                        )
                    except Exception as e:
                        print(f"⚠️  이미지 업로드 실패 ({path.name}): {e}")
                        # 실패 시 파일명만 텍스트로 기록
                        children.append(
                            {
                                "object": "block",
                                "type": "paragraph",
                                "paragraph": {
                                    "rich_text": [
                                        {
                                            "type": "text",
                                            "text": {
                                                "content": f"📎 첨부 이미지 (업로드 실패): {path.name}"
                                            },
                                        }
                                    ]
                                },
                            }
                        )

    # Notion 페이지 생성
    notion_client.pages.create(
        parent={"database_id": settings.notion_database_id},
        icon={"type": "emoji", "emoji": "💡"},
        properties={
            "title": {
                "title": [
                    {
                        "type": "text",
                        "text": {"content": qna.title},
                    }
                ]
            },
            "Tags": {
                "multi_select": [{"name": tag} for tag in qna.tags]
            },
        },
        children=children,
    )

    print("✅ Notion에 저장되었습니다!")
