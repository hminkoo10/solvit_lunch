import schedule
import time
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, BadPassword, ChallengeRequired
import requests
import os
import tempfile
import json
import traceback
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SECRET_FILE = os.path.join(BASE_DIR, "secret.json")
SESSION_FILE = os.path.join(BASE_DIR, "insta_settings.json")

DIET_TEMPLATE_PATH = os.path.join(BASE_DIR, "diet_template.png")
FONT_PATH = os.path.join(BASE_DIR, "MalangmalangR.ttf")

SCHOOL_NAME = "솔빛중학교"
GRADE = 2
CLASS_NUM = 2

cl = Client()
_secret_cache = None


def jload(fn):
    with open(fn, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def load_secret():
    global _secret_cache
    if _secret_cache is None:
        _secret_cache = jload(SECRET_FILE)
    return _secret_cache


def get_neis_key(api_key=None):
    if api_key:
        return api_key
    return load_secret()["neis_key"]


def get_instagram_credentials():
    secret = load_secret()
    return secret["insta_id"], secret["insta_pw"]


def login_instagram():
    """
    Instagram 로그인.
    기존 세션 파일이 있으면 먼저 불러오고, 없으면 새 로그인 후 저장.
    """
    insta_id, insta_pw = get_instagram_credentials()

    try:
        if os.path.exists(SESSION_FILE):
            print("기존 인스타그램 세션을 불러옵니다.")
            cl.load_settings(SESSION_FILE)

            cl.login(insta_id, insta_pw)
            cl.get_timeline_feed()

            print("인스타그램 세션 로그인 성공")
        else:
            print("인스타그램 신규 로그인을 시도합니다.")
            cl.login(insta_id, insta_pw)
            cl.dump_settings(SESSION_FILE)

            print("인스타그램 신규 로그인 성공 및 세션 저장 완료")

    except BadPassword as e:
        print("인스타그램 로그인 실패: 비밀번호 오류 또는 IP 차단 가능성이 있습니다.")
        print(e)
        raise

    except ChallengeRequired as e:
        print("인스타그램 로그인 실패: 이메일/전화번호/앱 인증 챌린지가 필요합니다.")
        print(e)
        raise

    except Exception as e:
        print("인스타그램 로그인 중 알 수 없는 오류 발생:")
        print(repr(e))
        raise


def ensure_login():
    """
    업로드 전에 로그인 상태 확인.
    세션이 만료되었으면 재로그인 후 세션 저장.
    """
    insta_id, insta_pw = get_instagram_credentials()

    try:
        cl.get_timeline_feed()

    except LoginRequired:
        print("인스타그램 세션이 만료되었습니다. 재로그인합니다.")
        cl.login(insta_id, insta_pw)
        cl.dump_settings(SESSION_FILE)

    except Exception as e:
        print("인스타그램 로그인 상태 확인 중 오류:")
        print(repr(e))
        raise


def get_korean_day_name(date):
    days = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
    return days[date.weekday()]


def get_school_info(sc, n=0, api_key=None):
    url = "https://open.neis.go.kr/hub/schoolInfo"

    params = {
        "KEY": get_neis_key(api_key),
        "Type": "json",
        "pIndex": 1,
        "pSize": 100,
        "SCHUL_NM": sc,
    }

    try:
        res = requests.get(url=url, params=params, verify=False, timeout=10)
        res.encoding = "UTF-8"
        rj = res.json()

        row = rj["schoolInfo"][1]["row"][n]

        return {
            "교육청": row["ATPT_OFCDC_SC_NM"],
            "지역": row["LCTN_SC_NM"],
            "주소": row["ORG_RDNMA"],
            "교육지원청": row["JU_ORG_NM"],
            "한글이름": row["SCHUL_NM"],
            "영어이름": row["ENG_SCHUL_NM"],
            "전화": row["ORG_TELNO"],
            "팩스": row["ORG_FAXNO"],
            "사이트": row["HMPG_ADRES"],
            "남녀공학": row["COEDU_SC_NM"],
            "우편번호": row["ORG_RDNZC"],
            "학교코드": row["SD_SCHUL_CODE"],
            "설립일": row["FOND_YMD"],
            "교육청코드": row["ATPT_OFCDC_SC_CODE"],
        }

    except Exception:
        return "없는 학교에요"


def get_school_codes(sc, n=0, api_key=None):
    url = "https://open.neis.go.kr/hub/schoolInfo"

    params = {
        "KEY": get_neis_key(api_key),
        "Type": "json",
        "pIndex": 1,
        "pSize": 100,
        "SCHUL_NM": sc,
    }

    try:
        res = requests.get(url=url, params=params, verify=False, timeout=10)
        res.encoding = "UTF-8"
        rj = res.json()

        row = rj["schoolInfo"][1]["row"][n]

        return {
            "school_code": row["SD_SCHUL_CODE"],
            "office_code": row["ATPT_OFCDC_SC_CODE"],
            "school_name": row["SCHUL_NM"],
        }

    except Exception as e:
        print("학교 코드 조회 실패:", repr(e))
        return None


def format_diet_row(row):
    meal = row.get("DDISH_NM", "").replace("<br/>", "\n").strip()
    calorie = row.get("CAL_INFO", "").strip()

    if not meal:
        return "급식 정보가 없어요"
    if calorie:
        return f"{meal}\n\n칼로리: {calorie}"
    return meal


def get_diet(sc, date, n=0, api_key=None):
    school = get_school_codes(sc, n, api_key=api_key)

    if school is None:
        return "급식 정보가 없어요"

    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"

    params = {
        "KEY": get_neis_key(api_key),
        "Type": "json",
        "pIndex": 1,
        "pSize": 100,
        "ATPT_OFCDC_SC_CODE": school["office_code"],
        "SD_SCHUL_CODE": school["school_code"],
        "MLSV_YMD": date,
    }

    try:
        res = requests.get(url=url, params=params, verify=False, timeout=10)
        res.encoding = "UTF-8"
        rj = res.json()

        row = rj["mealServiceDietInfo"][1]["row"][0]
        return format_diet_row(row)

    except Exception as e:
        print("급식 정보 조회 실패:", repr(e))
        return "급식 정보가 없어요"


def get_time(sc, date, grade, class_, n=0, api_key=None):
    school = get_school_codes(sc, n, api_key=api_key)

    if school is None:
        return "시간표 정보가 없어요"

    school_name = school["school_name"]

    if school_name.endswith("초등학교"):
        url = "https://open.neis.go.kr/hub/elsTimetable"
        table_name = "elsTimetable"
    elif school_name.endswith("중학교"):
        url = "https://open.neis.go.kr/hub/misTimetable"
        table_name = "misTimetable"
    elif school_name.endswith("고등학교"):
        url = "https://open.neis.go.kr/hub/hisTimetable"
        table_name = "hisTimetable"
    else:
        return "시간표 정보가 없어요"

    params = {
        "KEY": get_neis_key(api_key),
        "Type": "json",
        "pIndex": 1,
        "pSize": 100,
        "ATPT_OFCDC_SC_CODE": school["office_code"],
        "SD_SCHUL_CODE": school["school_code"],
        "TI_FROM_YMD": date,
        "TI_TO_YMD": date,
        "GRADE": grade,
        "CLASS_NM": class_,
    }

    try:
        res = requests.get(url=url, params=params, verify=False, timeout=10)
        res.encoding = "UTF-8"
        rj = res.json()

        total_count = rj[table_name][0]["head"][0]["list_total_count"]

        time_info = ""
        for q in range(total_count):
            subject = rj[table_name][1]["row"][q]["ITRT_CNTNT"].replace("-", "")
            time_info += f"{q + 1}교시 : {subject}\n"

        return time_info.strip()

    except Exception as e:
        print("시간표 정보 조회 실패:", repr(e))
        return "시간표 정보가 없어요"


def calculate_font_size(draw, text, font_path, max_width, max_height, max_font_size):
    font_size = max_font_size
    font = ImageFont.truetype(font_path, font_size)

    while font_size > 0:
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

        if text_width <= max_width and text_height <= max_height:
            break

        font_size -= 1
        font = ImageFont.truetype(font_path, font_size)

    return font


def calculate_multiline_font(draw, lines, font_path, max_width, max_height, max_font_size, min_font_size=24):
    font_size = max_font_size

    while font_size >= min_font_size:
        font = ImageFont.truetype(font_path, font_size)
        line_spacing = max(8, int(font_size * 0.2))
        max_line_width = 0
        line_heights = []

        for line in lines:
            line_bbox = draw.textbbox((0, 0), line or " ", font=font)
            line_width = line_bbox[2] - line_bbox[0]
            line_height = line_bbox[3] - line_bbox[1]
            max_line_width = max(max_line_width, line_width)
            line_heights.append(line_height)

        total_text_height = sum(line_heights) + line_spacing * max(0, len(lines) - 1)

        if max_line_width <= max_width and total_text_height <= max_height:
            return font, line_spacing, line_heights, total_text_height

        font_size -= 1

    font = ImageFont.truetype(font_path, min_font_size)
    line_spacing = max(8, int(min_font_size * 0.2))
    line_heights = []

    for line in lines:
        line_bbox = draw.textbbox((0, 0), line or " ", font=font)
        line_heights.append(line_bbox[3] - line_bbox[1])

    total_text_height = sum(line_heights) + line_spacing * max(0, len(lines) - 1)
    return font, line_spacing, line_heights, total_text_height


def create_image_with_template(text, title, date, template_path, file_name):
    korean_day_name = get_korean_day_name(date)
    date_str = date.strftime("%Y년 %m월 %d일 ") + korean_day_name

    full_title = f"{title} - {date_str}"

    text_color = (0, 0, 0)
    title_color = (0, 0, 0)

    font_size = 55
    title_font_size = 30

    template = Image.open(template_path).convert("RGB")
    width, height = template.size

    image = template.copy()
    draw = ImageDraw.Draw(image)

    title_font = ImageFont.truetype(FONT_PATH, title_font_size)

    title_bbox = draw.textbbox((0, 0), full_title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_height = title_bbox[3] - title_bbox[1]

    draw.text(
        ((width - title_width) / 2, 10),
        full_title,
        fill=title_color,
        font=title_font,
    )

    content_lines = text.split("\n")
    font, line_spacing, line_heights, total_text_height = calculate_multiline_font(
        draw,
        content_lines,
        FONT_PATH,
        width - 80,
        height - title_height - 80,
        font_size,
    )

    y_text = (height - total_text_height) / 2 + title_height / 2

    for index, line in enumerate(content_lines):
        line_bbox = draw.textbbox((0, 0), line, font=font)
        line_width = line_bbox[2] - line_bbox[0]

        draw.text(
            ((width - line_width) / 2, y_text),
            line,
            fill=text_color,
            font=font,
        )

        y_text += line_heights[index] + line_spacing

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
    output_path = temp_file.name
    temp_file.close()

    image.save(output_path, format="JPEG")
    return output_path


def upload_to_instagram(image_paths, caption):
    ensure_login()

    valid_paths = []

    for path in image_paths:
        print(f"업로드 파일 확인 중: {path}")

        if not os.path.exists(path):
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")

        try:
            with Image.open(path) as img:
                img.verify()

            valid_paths.append(path)

        except Exception as e:
            print(f"잘못된 이미지 파일입니다: {path} - {e}")

    if not valid_paths:
        raise Exception("업로드할 수 있는 정상 이미지가 없습니다.")

    try:
        cl.photo_upload(valid_paths[0], caption=caption)
        print("피드 사진이 업로드되었습니다.")

        story_text = "오늘의 급식을 확인하세요!"
        cl.photo_upload_to_story(valid_paths[0], caption=story_text)
        print("스토리에 게시물이 공유되었습니다.")

    except Exception as e:
        print("인스타그램 업로드 실패:")
        print(repr(e))
        raise


def create_and_upload_daily_info():
    print("작업을 시작합니다.")

    today = datetime.today() + timedelta(days=1)
    date_str = today.strftime("%Y%m%d")

    diet_info = get_diet(SCHOOL_NAME, date_str)

    if diet_info == "급식 정보가 없어요":
        print("급식 정보가 없어서 업로드하지 않습니다.")
        return

    diet_image_path = create_image_with_template(
        diet_info,
        "급식 정보",
        today,
        DIET_TEMPLATE_PATH,
        "diet_info.jpg",
    )

    caption = f"#{date_str} #{SCHOOL_NAME}\n{SCHOOL_NAME} 급식"

    upload_to_instagram([diet_image_path], caption)

    try:
        os.remove(diet_image_path)
        print("임시 이미지 파일 삭제 완료")
    except Exception as e:
        print("임시 이미지 파일 삭제 실패:", repr(e))


def main():
    login_instagram()

    print("ready")
    schedule.every().day.at("18:00").do(create_and_upload_daily_info)

    while True:
        try:
            schedule.run_pending()

        except Exception:
            print("스케줄 실행 중 오류 발생:")
            traceback.print_exc()

        time.sleep(1)


if __name__ == "__main__":
    main()
