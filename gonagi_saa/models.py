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
            질문에 대한 핵심 개념 설명.
            - 명확하고 간결한 설명
            - 주요 특징과 작동 원리
            - 필요시 예시 포함
            - 한국어로 작성
            """
        ),
    )

    exam_tips: list[str] = Field(
        description=dedent(
            """\
            AWS SAA 시험 관련 팁과 중요 포인트 리스트.
            - 시험에 자주 나오는 유형
            - 정답을 고르는 핵심 키워드
            - 주의해야 할 특징들
            - 각 항목은 마크다운 형식으로 작성 (예: "- **키워드**: 설명")
            """
        ),
        examples=[
            [
                "- 비용 최적화 문제에서는 S3 Intelligent-Tiering 고려",
                "- '실시간'이라는 키워드가 나오면 Kinesis 선택"
            ]
        ],
    )

    common_traps: list[str] = Field(
        description=dedent(
            """\
            시험에서 자주 나오는 함정과 오답 리스트.
            - 헷갈리기 쉬운 유사 서비스/개념
            - 흔히 실수하는 부분
            - 틀린 선택지의 특징
            - 각 항목은 마크다운 형식으로 작성 (예: "- **주의**: 설명")
            """
        ),
        examples=[
            [
                "- CloudWatch와 CloudTrail 혼동 주의",
                "- S3 Standard-IA는 30일 이상 보관 시 적합"
            ]
        ],
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
