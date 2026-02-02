import json
import os
import sys
import time
from pathlib import Path
from typing import cast

import typer
from notion_client import Client as NotionClient

from gonagi_saa.settings import CONFIG_DIR, CONFIG_FILE, settings
from gonagi_saa.services import answer_question, save_to_notion
from gonagi_saa.utils import is_vision_model
from gonagi_saa.constants import MAX_IMAGES

app = typer.Typer()
config_app = typer.Typer(
    help="CLI 설정을 관리합니다.",
    no_args_is_help=True,
)
app.add_typer(config_app, name="config")


@config_app.command("path")
def config_path():
    """설정 파일 경로를 출력합니다."""
    typer.echo(f"Configuration file location: {CONFIG_FILE}")


@config_app.command("init")
def config_init():
    """설정 파일을 초기화합니다."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if CONFIG_FILE.exists():
        overwrite = typer.confirm("설정 파일이 이미 존재합니다. 덮어쓰시겠습니까?")
        if not overwrite:
            typer.echo("초기화를 취소합니다.")
            raise typer.Exit()

    CONFIG_FILE.touch(exist_ok=True)
    os.chmod(CONFIG_FILE, 0o600)

    default_model = typer.prompt(
        "기본 모델을 입력하세요 (예: gpt-4o, claude-3-5-sonnet-20241022, gemini-2.5-flash)",
        default="gpt-4o",
    )
    notion_db_id = typer.prompt(
        "Notion DB ID를 입력하세요",
        default="",
    )
    notion_api_key = typer.prompt(
        "Notion API Key를 입력하세요",
        default="",
        show_default=False,
    )
    anthropic_api_key = typer.prompt(
        "Anthropic API Key를 입력하세요",
        default="",
        show_default=False,
    )
    openai_api_key = typer.prompt(
        "OpenAI API Key를 입력하세요",
        default="",
        show_default=False,
    )
    google_api_key = typer.prompt(
        "Google API Key를 입력하세요",
        default="",
        show_default=False,
    )

    config_data = {
        "default_model": default_model,
        "notion_database_id": notion_db_id,
        "notion_api_key": notion_api_key,
        "anthropic_api_key": anthropic_api_key,
        "openai_api_key": openai_api_key,
        "google_api_key": google_api_key,
    }

    with open(CONFIG_FILE, "w") as f:
        f.write(json.dumps(config_data, indent=2))

    typer.secho(
        "✅ 성공적으로 설정이 저장되었습니다.",
        fg=typer.colors.GREEN,
    )


@config_app.command("clean")
def config_clean():
    """설정 파일을 삭제합니다."""
    confirm = typer.confirm("정말로 설정을 초기화 하시겠습니까?")
    if not confirm:
        typer.echo("삭제가 취소되었습니다.")
        raise typer.Exit()

    try:
        os.remove(CONFIG_FILE)
        typer.secho(
            f"✅ 성공적으로 설정 파일을 삭제했습니다: {CONFIG_FILE}",
            fg=typer.colors.GREEN,
        )
    except OSError as e:
        typer.secho(
            f"❌ 설정 파일을 삭제하는 중 오류가 발생했습니다: {e}",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)


@app.command()
def ask():
    """질문을 입력받아 답변을 생성하고, Notion에 저장할 수 있습니다."""
    model = settings.default_model

    # 1. 텍스트 질문 입력
    print("💡 질문을 입력하고 저장하세요!")
    time.sleep(0.5)
    question = cast(str | None, typer.edit())

    if question is None or question.strip() == "":
        typer.echo("❌ 질문이 입력되지 않았습니다.")
        raise typer.Exit()

    # 2. 이미지 추가 여부 확인
    image_paths: list[str] = []
    add_images = typer.confirm("📸 이미지를 추가하시겠습니까?", default=False)

    if add_images:
        if not is_vision_model(model):
            typer.secho(
                f"⚠️  현재 설정된 모델({model})은 이미지를 지원하지 않습니다.",
                fg=typer.colors.YELLOW,
            )
            typer.echo("텍스트만으로 진행합니다.")
        else:
            for i in range(MAX_IMAGES):
                image_path = typer.prompt(
                    f"이미지 경로를 입력하세요 ({i + 1}/{MAX_IMAGES}, 종료하려면 Enter)",
                    default="",
                    show_default=False,
                )
                if image_path.strip() == "":
                    break

                path = Path(image_path.strip())
                if not path.exists():
                    typer.secho(
                        f"❌ 이미지 파일을 찾을 수 없습니다: {image_path}",
                        fg=typer.colors.RED,
                    )
                    continue

                image_paths.append(str(path.absolute()))
                typer.secho(f"✅ 이미지 추가됨: {path.name}", fg=typer.colors.GREEN)

    # 3. AI 답변 생성
    try:
        result = answer_question(
            model,
            question,
            image_paths if image_paths else None,
        )
    except Exception as e:
        typer.secho(
            f"❌ 답변 생성 중 오류가 발생했습니다: {e}",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    # 4. 답변 출력
    print(f"\n{'='*60}")
    print(f"📌 제목: {result.title}")
    print(f"{'='*60}\n")
    print(f"💡 답변:\n\n{result.answer}\n")
    print(f"🏷️  태그: {', '.join(result.tags)}\n")
    print(f"{'='*60}\n")

    # 5. Notion 저장 여부 확인
    save_to_notion_confirm = typer.confirm(
        "💾 Notion에 저장하시겠습니까?",
        default=True,
    )

    if save_to_notion_confirm:
        try:
            notion_client = NotionClient(
                auth=settings.notion_api_key.get_secret_value()
            )
            save_to_notion(notion_client, result, image_paths if image_paths else None)
        except Exception as e:
            typer.secho(
                f"❌ Notion 저장 중 오류가 발생했습니다: {e}",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=1)
    else:
        print("👋 저장하지 않고 종료합니다.")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """gonagi-saa: AWS SAA 시험 대비를 위한 멀티모달 Q&A CLI 도구"""
    if ctx.invoked_subcommand is None:
        # 서브커맨드가 없으면 ask 실행
        ask()


if __name__ == "__main__":
    app()
