from textwrap import dedent
from pydantic import BaseModel, Field


class QnAModel(BaseModel):
    """질문-답변 모델"""

    question: str = Field(
        description="사용자의 원본 질문 (텍스트)"
    )

    title: str = Field(
        description=dedent(
            """\
            답변 내용을 요약한 제목. Notion 페이지 제목으로 사용됩니다.
            - 핵심 주제나 개념을 포함한 간결한 제목 (10-20자 권장)
            - 예시: "AWS VPC와 서브넷 구성", "Lambda 함수 최적화 방법"
            """
        ),
        examples=["AWS VPC와 서브넷 구성", "S3 버킷 정책 설정"],
    )

    answer: str = Field(
        description=dedent(
            """\
            질문에 대한 상세한 답변.
            - AWS SAA 시험 준비를 위한 명확하고 구조화된 설명
            - 필요시 예시, 비교, 주의사항 포함
            - 한국어로 작성
            """
        ),
    )

    tags: list[str] = Field(
        description=dedent(
            """\
            답변에서 언급된 주요 기술, 서비스, 개념을 태그로 추출.
            - AWS 서비스명 (예: EC2, S3, VPC, Lambda)
            - 기술/개념 (예: 네트워킹, 보안, 서버리스, 스토리지)
            - 3-7개 정도의 핵심 태그 선정
            - 서비스명은 약어 사용 (예: "Simple Queue Service" → "SQS")
            """
        ),
        examples=["EC2", "VPC", "보안", "네트워킹"],
    )
