from instagrapi import Client
import json

with open("./secret.json", "r", encoding="utf-8-sig") as f:
    secret = json.load(f)

insta_id = secret["insta_id"]
insta_pw = secret["insta_pw"]

cl = Client()

# 너무 빠른 요청 방지
cl.delay_range = [3, 7]

cl.login(insta_id, insta_pw)
cl.dump_settings("insta_settings.json")

print("세션 저장 완료: insta_settings.json")