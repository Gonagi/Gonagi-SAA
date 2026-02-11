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
        You are an AWS SAA (Solutions Architect Associate) exam preparation expert.

        Provide clear, well-structured answers in Korean with the following components:

        1. **answer**: Core concept explanation - clear and concise with key features and how it works
        2. **exam_tips**: Exam-specific tips including:
           - Common question patterns in the exam
           - Key keywords that indicate the correct answer
           - Important characteristics to remember
        3. **common_traps**: Common pitfalls and wrong answer patterns:
           - Easily confused similar services/concepts
           - Typical mistakes candidates make
           - Characteristics of incorrect choices

        Write in Korean and use markdown formatting (bullet points, bold text) for readability.

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
    session_id: str,
    image_paths: list[str] | None = None,
) -> None:
    """질문-답변을 Notion에 저장 (이미지 포함)"""
    print("🔥 Notion에 저장합니다...")

    # 질문 블록 구성 (코드 블록으로 감싸서 개행 유지)
    question_content = f"## 질문\n\n```\n{qna.question}\n```"
    children = notionize(question_content)

    # 이미지를 질문 바로 아래에 추가
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

                        # Notion image 블록 추가 (질문 바로 아래)
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

    # 이미지와 답변 사이 구분선 추가
    children.append(
        {
            "object": "block",
            "type": "divider",
            "divider": {},
        }
    )

    # 답변 섹션
    answer_content = f"## 답변\n\n{qna.answer}"
    children.extend(notionize(answer_content))

    # 구분선 추가
    children.append(
        {
            "object": "block",
            "type": "divider",
            "divider": {},
        }
    )

    # 시험 팁 섹션
    exam_tips_text = "\n".join(qna.exam_tips)
    exam_tips_content = f"### 📝 시험 팁\n\n{exam_tips_text}"
    children.extend(notionize(exam_tips_content))

    # 구분선 추가
    children.append(
        {
            "object": "block",
            "type": "divider",
            "divider": {},
        }
    )

    # 주의사항 섹션
    common_traps_text = "\n".join(qna.common_traps)
    common_traps_content = f"### ⚠️ 주의사항\n\n{common_traps_text}"
    children.extend(notionize(common_traps_content))

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
            "Session": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": session_id},
                    }
                ]
            },
        },
        children=children,
    )

    print("✅ Notion에 저장되었습니다!")
