import os
import sqlite3
import json
import subprocess
from collections import defaultdict
from readTMGimmickInformation import export_gimmick_html, get_gimmick_html_as_string

DB_PATH = "./data/sakura_ko.db"
OUTPUT_DIR = "./docs"
os.makedirs("./data", exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

if not os.path.exists(DB_PATH):
    print("📥 sakura_ko.db가 없어 다운로드를 시작합니다...")
    subprocess.run(["python", "download_SakuraDB.py"], check=True)
    print("✅ DB 다운로드 완료!")

attribute_color_map = {
    1: ("힘", "#ff4d4d"),
    2: ("기", "#228B22"),
    3: ("속", "#4d9aff"),
    4: ("심", "#ffaa00"),
    5: ("지", "#d24dff"),
}

difficulty_map = {
    7: ("통통배 난이도", "TM_EB_full.html"),
    4: ("위대한 항로 난이도", "TM_GL_full.html"),
    1: ("신세계 난이도", "TM_NW_full.html")
}

STYLE_BLOCK = """
<style>
  body { background-color: #13514d; color: #f2f2f7; font-family: sans-serif; padding: 2em; font-size: 26px; }
  img { height: 40px; vertical-align: middle; margin-right: 2px; }
  h1 {
    font-size: 36px;
    color: gold;
    margin-bottom: 10px;
    border-bottom: 2px solid #f2f2f7;
    padding-bottom: 6px;
  }
  ...
</style>
"""

def make_boss_header(name, attr_id, tag=None):
    attr, color = attribute_color_map.get(attr_id, ("?", "#ccc"))
    label = f"<span style='color:{color}'>[{attr}] {name}</span>"
    if tag == "보스":
        label += f"<span style='color:{color}'> (보스) </span>"
    elif tag == "난입":
        label += f"<span style='color:{color}'> (난입) </span>"
    return f"<h2>{label}</h2>"

# DB 연결
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("SELECT questId_, questName_ FROM MstQuest_")
quest_name_map = dict(cursor.fetchall())

cursor.execute("SELECT questId_, gimmickJson_ FROM MstQuestGimmickInformation_")
gimmick_map = {sid: json.loads(js) for sid, js in cursor.fetchall() if js}

# ✅ intrusion 보스 questId
cursor.execute("SELECT questId_ FROM MstMapGameIntrusionEnemy_")
intrusion_set = set(row[0] for row in cursor.fetchall())

# ✅ lastBoss = 1 questId
cursor.execute("SELECT questId_ FROM MstMapGameBoss_ WHERE lastBoss_ = 1")
lastboss_set = set(row[0] for row in cursor.fetchall())

# 난이도별 HTML 누적
all_html = {
    7: [f"""<html><head><meta charset='UTF-8'><title>통통배 난이도</title></head>
<body>
<h1 solid #ccc; padding-bottom:10px;">
<img src="img/icon_league_1.png" style="height:58px; vertical-align:middle; margin-right:6px;">
통통배 난이도 패턴</h1>"""],

    4: [f"""<html><head><meta charset='UTF-8'><title>위대한 항로 난이도</title></head>
<body>
<h1 style="solid #ccc; padding-bottom:10px;">
<img src="img/icon_league_2.png" style="height:58px; vertical-align:middle; margin-right:6px;">
위대한 항로 난이도 패턴</h1>"""],

    1: [f"""<html><head><meta charset='UTF-8'><title>신세계 난이도</title></head>
<body>
<h1 style="solid #ccc; padding-bottom:10px;">
<img src="img/icon_league_3.png" style="height:58px; vertical-align:middle; margin-right:6px;">
신세계 난이도 패턴</h1>"""]
}


for server_id in gimmick_map:
    name = quest_name_map.get(server_id, f"퀘스트 {server_id}")

    cursor.execute("""
        SELECT overwriteTrademarkId_, mapGameId_ FROM MstMapGameBoss_ WHERE questId_=?
        UNION
        SELECT overwriteTrademarkId_, mapGameId_ FROM MstMapGameIntrusionEnemy_ WHERE questId_=?
    """, (server_id, server_id))
    row = cursor.fetchone()
    if not row:
        continue

    attr_id, map_id = row
    if map_id not in (1, 4, 7):
        continue

    # ✅ 태그 판단
    if server_id in intrusion_set:
        tag = "난입"
    elif server_id in lastboss_set:
        tag = "보스"
    else:
        tag = None

    body = get_gimmick_html_as_string(server_id)
    header = make_boss_header(name, attr_id, tag)
    all_html[map_id].append(f"<hr>{header}\n{body}")

conn.close()

# HTML 저장
for map_id, contents in all_html.items():
    contents.append("</body></html>")
    filename = difficulty_map[map_id][1]
    with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
        f.write("\n".join(contents))

# index.html 생성
index_html = ["<html><head><meta charset='UTF-8'><title>보스 패턴 인덱스</title></head><body>"]
index_html.append("<h1>🚩7월 트맵 패턴</h1><ul>")
for _, (label, file) in sorted(difficulty_map.items()):
    index_html.append(f"<li><a href='{file}' style='font-size: 32px;'>{label}</a></li>")
index_html.append("</ul></body></html>")
with open(os.path.join(OUTPUT_DIR, "index.html"), "w", encoding="utf-8") as f:
    f.write("\n".join(index_html))

# ✅ 루트 경로 gimmicks_raw_*.json 삭제
for file in os.listdir("."):
    if file.startswith("gimmicks_raw_") and file.endswith(".json"):
        try:
            os.remove(file)
            #print(f"🗑️ 삭제 완료: {file}")
        except Exception as e:
            print(f"⚠️ 삭제 실패: {file} → {e}")


docs_path = os.path.join(".", "docs")
# ✅ docs 내 기존 gimmicks_*.html 전부 삭제
for file in os.listdir(docs_path):
    if file.startswith("gimmicks_") and file.endswith(".html"):
        try:
            os.remove(os.path.join(docs_path, file))
            #print(f"🗑️ 삭제 완료: docs/{file}")
        except Exception as e:
            print(f"⚠️ 삭제 실패: docs/{file} → {e}")
