from venv import create
import schedule
import time
from datetime import datetime,timedelta
from PIL import Image, ImageDraw, ImageFont
from instagrapi import Client
import requests
import os
import tempfile
import json

def jload(fn):
    jstring = open(fn, "r", encoding='utf-8-sig').read()
    a = json.loads(jstring)
    return a

secret = jload("./secret.json")
neis_key = secret["neis_key"]
insta_id = secret["insta_id"]
insta_pw = secret["insta_pw"]
cl = Client()
cl.login(insta_id, insta_pw)

def get_korean_day_name(date):
    days = ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일']
    return days[date.weekday()]

def get_school_info(sc, n=0):
    scu = "https://open.neis.go.kr/hub/schoolInfo"
    para = {
        "KEY": None,
        "Type": "json",
        "pIndex": None,
        "pSize": None,
        "ATPT_OFCDDC_SC_CODE": None,
        "SD_SCHUL_CODE": None,
        "SCHUL_NM": sc,
        "SCHUL_KND_SC_NM": None,
        "LCTN_SC_NM": None,
        "FOND_SC_NM": None,
    }
    res = requests.get(url=scu, params=para, verify=False, json=True)
    res.encoding = "UTF-8"
    rj = res.json()
    try:
        a = rj["schoolInfo"][1]["row"][n]["LCTN_SC_NM"]
    except:
        a = "없는 학교에요"
        return a
    return {
        "교육청": rj["schoolInfo"][1]["row"][n]["ATPT_OFCDC_SC_NM"],
        "지역": rj["schoolInfo"][1]["row"][n]["LCTN_SC_NM"],
        "주소": rj["schoolInfo"][1]["row"][n]["ORG_RDNMA"],
        "교육지원청": rj["schoolInfo"][1]["row"][n]["JU_ORG_NM"],
        "한글이름": rj["schoolInfo"][1]["row"][n]["SCHUL_NM"],
        "영어이름": rj["schoolInfo"][1]["row"][n]["ENG_SCHUL_NM"],
        "전화": rj["schoolInfo"][1]["row"][n]["ORG_TELNO"],
        "팩스": rj["schoolInfo"][1]["row"][n]["ORG_FAXNO"],
        "사이트": rj["schoolInfo"][1]["row"][n]["HMPG_ADRES"],
        "남녀공학": rj["schoolInfo"][1]["row"][n]["COEDU_SC_NM"],
        "우편번호": rj["schoolInfo"][1]["row"][n]["ORG_RDNZC"],
        "학교코드": rj["schoolInfo"][1]["row"][n]["SD_SCHUL_CODE"],
        "설립일": rj["schoolInfo"][1]["row"][n]["FOND_YMD"]
    }

def get_diet(sc, date, n=0):
    scu = "https://open.neis.go.kr/hub/schoolInfo"
    para = {
        "KEY": None,
        "Type": "json",
        "pIndex": None,
        "pSize": None,
        "ATPT_OFCDDC_SC_CODE": None,
        "SD_SCHUL_CODE": None,
        "SCHUL_NM": sc,
        "SCHUL_KND_SC_NM": None,
        "LCTN_SC_NM": None,
        "FOND_SC_NM": None,
    }
    res = requests.get(url=scu, params=para, verify=False, json=True)
    res.encoding = "UTF-8"
    rj = res.json()
    try:
        sccode = rj["schoolInfo"][1]["row"][n]["SD_SCHUL_CODE"]
        gccode = rj["schoolInfo"][1]["row"][n]["ATPT_OFCDC_SC_CODE"]
    except:
        return "급식 정보가 없어요"
    
    mscu = f"https://open.neis.go.kr/hub/mealServiceDietInfo?KEY={neis_key}&Type=json&pIndex=1&pSize=100&ATPT_OFCDC_SC_CODE={gccode}&SD_SCHUL_CODE={sccode}"
    mpara = {
        "KEY": neis_key,
        "Type": "json",
        "pIndex": 1,
        "pSize": 100,
        "ATPT_OFCDDC_SC_CODE": gccode,
        "SD_SCHUL_CODE": sccode,
        "MLSV_YMD": date
    }
    mres = requests.get(url=mscu, params=mpara, verify=False, json=True)
    mres.encoding = "UTF-8"
    mrj = mres.json()
    try:
        return mrj["mealServiceDietInfo"][1]["row"][0]["DDISH_NM"].replace("<br/>", "\n")
    except:
        return "급식 정보가 없어요"

def get_time(sc, date, grade, class_, n=0):
    scu = "https://open.neis.go.kr/hub/schoolInfo"
    para = {
        "KEY": None,
        "Type": "json",
        "pIndex": None,
        "pSize": None,
        "ATPT_OFCDDC_SC_CODE": None,
        "SD_SCHUL_CODE": None,
        "SCHUL_NM": sc,
        "SCHUL_KND_SC_NM": None,
        "LCTN_SC_NM": None,
        "FOND_SC_NM": None,
    }
    res = requests.get(url=scu, params=para, verify=False, json=True)
    res.encoding = "UTF-8"
    rj = res.json()
    try:
        sccode = rj["schoolInfo"][1]["row"][n]["SD_SCHUL_CODE"]
        gccode = rj["schoolInfo"][1]["row"][n]["ATPT_OFCDC_SC_CODE"]
    except:
        return "시간표 정보가 없어요"
    
    if rj["schoolInfo"][1]["row"][n]["SCHUL_NM"].endswith("초등학교"):
        mscu = f"https://open.neis.go.kr/hub/elsTimetable?KEY={neis_key}&Type=json&pIndex=1&pSize=100&ATPT_OFCDC_SC_CODE={gccode}&SD_SCHUL_CODE={sccode}"
        tb = "elsTimetable"
    elif rj["schoolInfo"][1]["row"][n]["SCHUL_NM"].endswith("중학교"):
        mscu = f"https://open.neis.go.kr/hub/misTimetable?KEY={neis_key}&Type=json&pIndex=1&pSize=100&ATPT_OFCDC_SC_CODE={gccode}&SD_SCHUL_CODE={sccode}"
        tb = "misTimetable"
    elif rj["schoolInfo"][1]["row"][n]["SCHUL_NM"].endswith("고등학교"):
        mscu = f"https://open.neis.go.kr/hub/hisTimetable?KEY={neis_key}&Type=json&pIndex=1&pSize=100&ATPT_OFCDC_SC_CODE={gccode}&SD_SCHUL_CODE={sccode}"
        tb = "hisTimetable"
    mpara = {
        "KEY": neis_key,
        "Type": "json",
        "pIndex": 1,
        "pSize": 100,
        "ATPT_OFCDDC_SC_CODE": gccode,
        "SD_SCHUL_CODE": sccode,
        "TI_FROM_YMD": date,
        "TI_TO_YMD": date,
        "GRADE": grade,
        "CLASS_NM": class_
    }
    mres = requests.get(url=mscu, params=mpara, verify=False, json=True)
    mres.encoding = "UTF-8"
    mrj = mres.json()
    try:
        t = mrj[tb][0]["head"][0]["list_total_count"]
        time_info = ""
        for q in range(t):
            tn = mrj[tb][1]["row"][q]["ITRT_CNTNT"].replace("-", "")
            time_info += f"{q+1}교시 : {tn}\n"
        return time_info.strip()
    except Exception as e:
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

def create_image_with_template(text, title, date, template_path, file_name):
    korean_day_name = get_korean_day_name(date)
    date_str = date.strftime("%Y년 %m월 %d일 ") + korean_day_name

    full_title = f"{title} - {date_str}"

    text_color = (0, 0, 0)
    title_color = (0, 0, 0) 
    font_path = "./MalangmalangR.ttf"
    font_size = 55 
    title_font_size = 30 

    template = Image.open(template_path).convert("RGB")
    width, height = template.size
    image = template.copy()
    draw = ImageDraw.Draw(image)

    font = ImageFont.truetype(font_path, font_size)
    title_font = ImageFont.truetype(font_path, title_font_size)

    title_bbox = draw.textbbox((0, 0), full_title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_height = title_bbox[3] - title_bbox[1]
    draw.text(((width - title_width) / 2, 10), full_title, fill=title_color, font=title_font)

    max_content_height = height - title_height - 60
    content_lines = text.split('\n')
    total_text_height = len(content_lines) * (font_size + 10)

    y_text = (height - total_text_height) / 2 + title_height / 2

    for line in content_lines:
        line_bbox = draw.textbbox((0, 0), line, font=font)
        line_width = line_bbox[2] - line_bbox[0]
        draw.text(((width - line_width) / 2, y_text), line, fill=text_color, font=font)
        y_text += font_size + 10

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
    file_name = temp_file.name

    image.save(file_name, format='JPEG')
    return file_name


def upload_to_instagram(image_paths, caption):
    valid_paths = []
    for path in image_paths:
        print(f"Uploading file: {path}")
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")

        try:
            with Image.open(path) as img:
                img.verify() 
                valid_paths.append(path)
        except (IOError, SyntaxError) as e:
            print(f"Invalid image file: {path} - {e}")
    
    if not valid_paths:
        raise Exception("No valid images to upload")

    try:
        #album = cl.album_upload(paths=valid_paths, caption=caption)
        album = cl.photo_upload(valid_paths[0], caption=caption)
        print("사진이 업로드되었습니다.")

        story_text = "오늘의 급식을 확인하세요!"
        #cl.photo_upload_to_story(image_paths[0], caption=story_text)
        cl.photo_upload_to_story(image_paths[0], caption=story_text) #1
        print("스토리에 게시물이 공유되었습니다.")
        
    except Exception as e:
        print(f"Failed to upload album: {e}")


def create_and_upload_daily_info():
    print("작업을 시작합니다")
    sc = "솔빛중학교"
    grade = 2
    class_ = 2
    today = datetime.today() + timedelta(days=1)
    date_str = today.strftime("%Y%m%d")

    diet_info = get_diet(sc, date_str)
    #time_info = get_time(sc, date_str, grade, class_)

    diet_template_path = "./diet_template.png"
    #timetable_template_path = "./timetable_template.png"
    diet_image_path = create_image_with_template(diet_info, "급식 정보", today, diet_template_path, "diet_info.jpg")
    #time_image_path = create_image_with_template(time_info, "시간표 정보", today, timetable_template_path, "time_info.jpg")
    if diet_info == "급식 정보가 없어요":
        return
    upload_to_instagram([diet_image_path], f"#{date_str} #{sc}\n솔빛중학교  급식")

print("ready")
schedule.every().day.at("18:00").do(create_and_upload_daily_info)
#create_and_upload_daily_info()

while True:
    try:
        schedule.run_pending()
    except:
        pass
    time.sleep(1)
