import argparse
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import lunch


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SCHOOL = "솔빛중학교"
DEFAULT_TEMPLATE = BASE_DIR / "diet_template.png"
DEFAULT_OUTPUT = BASE_DIR / "test_diet_info.jpg"
MISSING_DIET_MESSAGE = "급식 정보가 없어요"


def parse_target_date(date_text):
    if date_text:
        try:
            return datetime.strptime(date_text, "%Y%m%d")
        except ValueError as exc:
            raise argparse.ArgumentTypeError("날짜는 YYYYMMDD 형식으로 입력해주세요.") from exc
    return datetime.today() + timedelta(days=1)


def build_parser():
    parser = argparse.ArgumentParser(
        description="실제 NEIS API에서 급식 정보를 받아 테스트 이미지를 생성합니다."
    )
    parser.add_argument("--school", default=DEFAULT_SCHOOL, help="학교 이름")
    parser.add_argument("--date", type=parse_target_date, help="급식 날짜, 예: 20260507")
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE), help="이미지 템플릿 경로")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="생성할 이미지 경로")
    parser.add_argument(
        "--api-key",
        default=os.environ.get("NEIS_KEY"),
        help="NEIS API 키. 생략하면 secret.json의 neis_key를 사용합니다.",
    )
    return parser


def create_test_image(school, target_date, template_path, output_path, api_key=None):
    date_str = target_date.strftime("%Y%m%d")
    diet_info = lunch.get_diet(school, date_str, api_key=api_key)
    if diet_info == MISSING_DIET_MESSAGE:
        raise RuntimeError(f"{school} {date_str} 급식 정보가 없습니다.")

    created_path = Path(
        lunch.create_image_with_template(
            diet_info,
            "급식 정보",
            target_date,
            str(template_path),
            str(output_path),
        )
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if created_path.resolve() != output_path.resolve():
        shutil.copyfile(created_path, output_path)
        created_path.unlink(missing_ok=True)

    return diet_info, output_path


def main():
    os.chdir(BASE_DIR)

    parser = build_parser()
    args = parser.parse_args()

    target_date = args.date or parse_target_date(None)
    template_path = Path(args.template)
    output_path = Path(args.output)

    if not template_path.exists():
        parser.error(f"템플릿 파일을 찾을 수 없습니다: {template_path}")
    if args.api_key is None and not (BASE_DIR / "secret.json").exists():
        parser.error("secret.json을 찾을 수 없습니다. --api-key 또는 NEIS_KEY를 사용해주세요.")

    try:
        diet_info, image_path = create_test_image(
            args.school,
            target_date,
            template_path,
            output_path,
            api_key=args.api_key,
        )
    except FileNotFoundError as exc:
        parser.error(f"secret.json을 찾을 수 없습니다. --api-key 또는 NEIS_KEY를 사용해주세요. ({exc})")
    except KeyError as exc:
        parser.error(f"secret.json에 필요한 키가 없습니다: {exc}")
    except RuntimeError as exc:
        parser.error(str(exc))

    print(f"이미지 생성 완료: {image_path.resolve()}")
    print()
    print(diet_info)


if __name__ == "__main__":
    main()
