import json
import os
import sys
import time
from pathlib import Path
from typing import cast

import filetype
import typer
from notion_client import Client as NotionClient
from prompt_toolkit import prompt
from prompt_toolkit.completion import PathCompleter

from gonagi_saa.settings import CONFIG_DIR, CONFIG_FILE, settings
from gonagi_saa.services import answer_question, save_to_notion
from gonagi_saa.utils import is_vision_model, generate_session_id
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
    """설정 파일을 생성하거나 에디터로 엽니다."""
    # 설정 파일이 없으면 템플릿 생성
    if not CONFIG_FILE.exists():
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        # 기본 템플릿 생성
        template = {
            "default_model": "gpt-4o",
            "notion_database_id": "",
            "notion_api_key": "",
            "anthropic_api_key": "",
            "openai_api_key": "",
            "google_api_key": "",
            "imgbb_api_key": "",
        }

        with open(CONFIG_FILE, "w") as f:
            f.write(json.dumps(template, indent=2))

        os.chmod(CONFIG_FILE, 0o600)
        typer.echo("✅ 설정 파일 템플릿이 생성되었습니다.")

    # 에디터로 파일 열기
    try:
        editor = os.environ.get("EDITOR", os.environ.get("VISUAL", "vi"))

        typer.echo(f"📝 설정 파일을 {editor}로 엽니다: {CONFIG_FILE}")
        typer.echo("💡 팁: API Key는 따옴표로 감싸주세요.")

        # 에디터 실행
        exit_code = os.system(f'{editor} "{CONFIG_FILE}"')

        if exit_code == 0:
            typer.secho("✅ 설정 파일이 저장되었습니다.", fg=typer.colors.GREEN)
        else:
            typer.secho("⚠️  에디터가 비정상 종료되었습니다.", fg=typer.colors.YELLOW)

    except Exception as e:
        typer.secho(
            f"❌ 에디터 실행 중 오류가 발생했습니다: {e}",
            fg=typer.colors.RED,
            err=True,
        )
        typer.echo(f"수동으로 파일을 수정하세요: {CONFIG_FILE}")
        raise typer.Exit(code=1)


@config_app.command("clean")
def config_clean():
    """설정 파일을 삭제합니다."""
    confirm = typer.confirm("정말로 설정을 초기화 하시겠습니까? [Y/N]", show_default=False)
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

    # Session ID 생성 및 표시
    session_id = generate_session_id()
    typer.secho(f"🔗 Session: {session_id}", fg=typer.colors.CYAN)

    # 1. 텍스트 질문 입력
    print("💡 질문을 입력하고 저장하세요!")
    time.sleep(0.5)
    question = cast(str | None, typer.edit())

    if question is None or question.strip() == "":
        typer.echo("❌ 질문이 입력되지 않았습니다.")
        raise typer.Exit()

    # 2. 이미지 추가 여부 확인
    image_paths: list[str] = []
    add_images = typer.confirm("📸 이미지를 추가하시겠습니까? [Y/N]", default=False, show_default=False)

    if add_images:
        if not is_vision_model(model):
            typer.secho(
                f"⚠️  현재 설정된 모델({model})은 이미지를 지원하지 않습니다.",
                fg=typer.colors.YELLOW,
            )
            typer.echo("텍스트만으로 진행합니다.")
        else:
            # PathCompleter로 파일 경로 자동완성 지원
            path_completer = PathCompleter(expanduser=True)

            typer.echo("💡 이미지를 추가하세요 (최대 3개, Enter=종료, q=취소)\n")

            for i in range(MAX_IMAGES):
                try:
                    # prompt_toolkit의 prompt 사용 (Tab 자동완성 지원)
                    image_path = prompt(
                        f"이미지 경로 ({i + 1}/{MAX_IMAGES}): ",
                        completer=path_completer,
                    ).strip()
                except (KeyboardInterrupt, EOFError):
                    # Ctrl+C 또는 Ctrl+D 입력 시 전체 프로세스 중단
                    typer.echo("\n👋 질문이 취소되었습니다.")
                    raise typer.Exit()

                if image_path == "":
                    break

                # 취소 명령어 처리
                if image_path.lower() in ["q", "quit", "cancel", "exit"]:
                    typer.echo("👋 질문이 취소되었습니다.")
                    raise typer.Exit()

                path = Path(image_path)
                if not path.exists():
                    typer.secho(
                        f"❌ 이미지 파일을 찾을 수 없습니다: {image_path}",
                        fg=typer.colors.RED,
                    )
                    continue

                if not path.is_file():
                    typer.secho(
                        f"❌ 디렉토리가 아닌 파일을 입력해주세요: {image_path}",
                        fg=typer.colors.RED,
                    )
                    continue

                # 이미지 파일 타입 확인
                kind = filetype.guess(str(path))
                if kind is None or not kind.mime.startswith("image/"):
                    typer.secho(
                        f"❌ 이미지 파일이 아닙니다: {image_path}",
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
    print(f"\n📝 시험 팁:")
    for tip in result.exam_tips:
        print(f"  {tip}")
    print(f"\n⚠️  주의사항:")
    for trap in result.common_traps:
        print(f"  {trap}")
    print(f"\n🏷️  태그: {', '.join(result.tags)}\n")
    print(f"{'='*60}\n")

    # 5. Notion 저장 여부 확인
    save_to_notion_confirm = typer.confirm(
        "💾 Notion에 저장하시겠습니까? [Y/N]",
        default=True,
        show_default=False,
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
