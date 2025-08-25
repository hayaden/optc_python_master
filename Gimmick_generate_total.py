import os
import sqlite3
from datetime import datetime
from readTMGimmickInformation import export_tm_gimmick_html, get_tm_gimmick_html_as_string
from readKizunaGimmickInformation import export_kizuna_gimmick_html, get_kizuna_gimmick_html_as_string
from readPkaGimmickInformation import export_pka_gimmick_html, get_pka_gimmick_html_as_string
from TM_Gimmick_generate_index import attribute_color_map
from datetime import datetime, timezone, timedelta

DB_PATH = "./data/sakura_ko.db"
OUTPUT_DIR = "./docs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ✅ 시간 관련 설정
KST = timezone(timedelta(hours=9))
today_str = datetime.now(KST).strftime("최종 업데이트: %Y-%m-%d")
footer = f'<footer style="margin-top: 60px; font-size: 20px; color: #aaa;">{today_str}</footer>'

def to_kst_str(ts):
    return datetime.fromtimestamp(ts, KST).strftime("%Y-%m-%d %H:%M")

def get_event_status(start_ts, end_ts):
    now = datetime.now(KST).timestamp()
    if now < start_ts:
        return "⚪ 예정"
    elif start_ts <= now <= end_ts:
        return "🟢 개최 중"
    else:
        return "🔴 종료"

# ✅ DB 연결
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

KST = timezone(timedelta(hours=9))  

def to_kst_str(ts):
      return datetime.fromtimestamp(ts, KST).strftime("%Y-%m-%d %H:%M")  
  

# ✅ TM 정보
cursor.execute("""
SELECT startAt_, endAt_
FROM MstMapGameEvent_
ORDER BY serverId_ DESC LIMIT 1
""")
tm_start_ts, tm_end_ts = cursor.fetchone()
tm_status = get_event_status(tm_start_ts, tm_end_ts)
tm_period_kst = f"{to_kst_str(tm_start_ts)} ~ <br>{to_kst_str(tm_end_ts)}<br>{tm_status}"

# ✅ PKA 정보
cursor.execute("""
SELECT startAt_, endAt_
FROM MstTrailEvent_
ORDER BY startAt_ DESC LIMIT 1
""")
pka_start_ts, pka_end_ts = cursor.fetchone()
pka_status = get_event_status(pka_start_ts, pka_end_ts)
pka_period_kst = f"{to_kst_str(pka_start_ts)} ~ <br>{to_kst_str(pka_end_ts)}<br>{pka_status}"

# ✅ KIZUNA 정보
cursor.execute("""
SELECT startAt_, endAt_, name_
FROM MstKizunaBattleEvent_
ORDER BY startAt_ DESC LIMIT 1
""")
kizuna_start_ts, kizuna_end_ts, kizuna_name = cursor.fetchone()
kizuna_status = get_event_status(kizuna_start_ts, kizuna_end_ts)
kizuna_period_kst = f"{to_kst_str(kizuna_start_ts)} ~ <br>{to_kst_str(kizuna_end_ts)}<br>{kizuna_status}"

# ✅ index.html 생성
with open(os.path.join(OUTPUT_DIR, "index.html"), "w", encoding="utf-8") as f:
    f.write(f"""
<html>
<head><meta charset='UTF-8'><title>보스 패턴 인덱스</title></head>
<body style="background-color: #0d3b2e; color: #fff; font-family: sans-serif; text-align: center; padding: 2em;">
  <h1 style="color: gold; font-size: 36px;"> 원피스 트레저 크루즈 패턴 정리</h1>
  <div style="display: flex; justify-content: center; gap: 40px; margin-top: 40px;">
    
    <div>
      <a href="TM.html">
        <img src="img/common_TM_LOGO.png" style="height: 160px;">
      </a>
      <div style="font-size: 20px; color: white; margin-top: 6px;">{tm_period_kst}</div>
    </div>
    
    <div>
      <a href="PKA.html">
        <img src="img/common_PKA_LOGO.png" style="height: 160px;">
      </a>
      <div style="font-size: 20px; color: white; margin-top: 6px;">{pka_period_kst}</div>
    </div>
    
    <div>
      <a href="KIZUNA.html">
        <img src="img/common_KIZUNA_LOGO.png" style="height: 160px;">
      </a>
      <div style="font-size: 20px; color: white; margin-top: 6px;">{kizuna_period_kst}</div>
    </div>

  </div>
  {footer}
</body>
</html>
""")

print(f"✅ index.html 동적 상태 반영 완료 ({today_str})")

home_button = """
<!-- ✅ 홈으로 버튼 -->
<div style="text-align: right; margin-bottom: 1em;">
  <a href="index.html" color: #000; padding: 8px 16px; border-radius: 8px; text-decoration: none; font-weight: bold;">
    Home
  </a>
</div>
"""

# ✅ TM.html 생성
tm_html = f"""<html>
<head>
<meta charset='UTF-8'>
<style>
  body {{ background-color: #13514d; color: #f2f2f7; font-family: sans-serif; padding: 2em; font-size: 26px; }}
  h1 {{ font-size: 36px; color: gold; margin-bottom: 10px; border-bottom: 2px solid #f2f2f7; padding-bottom: 6px; }}
  ul {{ font-size: 24px; }}
  a {{ color: #ffd700; }}
  a:hover {{ color: #ffffff; }}
</style>
</head>
<body>
{home_button}
<iframe src="TM_NW_full.html" width="100%" height="90%" style="border:none;"></iframe>
<ul>
  <li><a href="TM_GL_full.html">위대한 항로</a></li>
  <li><a href="TM_EB_full.html">통통배</a></li>
</ul>
{footer}
</body>
</html>"""
with open(os.path.join(OUTPUT_DIR, "TM.html"), "w", encoding="utf-8") as f:
    f.write(tm_html)

# ✅ PKA.html 생성
cursor.execute("""
SELECT questId_, questName_
FROM MstQuest_
WHERE areaId_ = 11000
ORDER BY questId_ DESC LIMIT 3
""")
pka_rows = cursor.fetchall()
pka_files = ["PKA_BOSS.html", "PKA_MID_BOSS2.html", "PKA_MID_BOSS1.html"]

for (quest_id, quest_name), filename in zip(pka_rows, pka_files):
    html = get_pka_gimmick_html_as_string(quest_id)
    with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
        f.write(html)

# ✅ PKA.html 상단 최신보스 iframe + 하단 링크 출력
latest_filename = pka_files[0]
mid_boss_links = []

for (_, quest_name), filename in zip(pka_rows, pka_files):
    if filename != latest_filename:
        mid_boss_links.append(f"<li><a href='{filename}' style='font-size:24px'>{quest_name}</a></li>")

pka_html = f"""<html>
<head><meta charset='UTF-8'>
<style>
  body {{ background-color: #13514d; color: #f2f2f7; font-family: sans-serif; padding: 2em; font-size: 26px; }}
  h1 {{ font-size: 36px; color: gold; margin-bottom: 10px; border-bottom: 2px solid #f2f2f7; padding-bottom: 6px; }}
  ul {{ font-size: 24px; }}
  a {{ color: #ffd700; }}
  a:hover {{ color: #ffffff; }}
</style>
</head>
<body>
{home_button}
<iframe src="{latest_filename}" width="100%" height="90%" style="border:none;"></iframe>
<ul>
  {''.join(mid_boss_links)}
</ul>
{footer}
</body>
</html>"""

with open(os.path.join(OUTPUT_DIR, "PKA.html"), "w", encoding="utf-8") as f:
    f.write(pka_html)

# ✅ KIZUNA.html 생성
cursor.execute("""
SELECT k.kizunaBattleEventId_, k.questId_, k.requiredKizunaSuperBossTicket_,
       k.requiredKizunaBossTicket_, k.bossTrademark_, q.questName_
FROM MstKizunaBattleEventQuest_ k
LEFT JOIN MstQuest_ q ON k.questId_ = q.questId_
WHERE k.kizunaBattleEventId_ != 901
""")
rows = cursor.fetchall()
conn.close()

latest_event_id = max(row[0] for row in rows)
filtered = [r for r in rows if r[0] == latest_event_id and (r[2] == 30 or r[3] == 20)]

kizuna_html = ["""<html><head><meta charset='UTF-8'>
<style>
  body { background-color: #13514d; color: #f2f2f7; font-family: sans-serif; padding: 2em; font-size: 26px; }
  h1 { font-size: 36px; color: gold; margin-bottom: 10px; border-bottom: 2px solid #f2f2f7; padding-bottom: 6px; }
  ul { font-size: 24px; }
  a { color: #ffd700; }
  a:hover { color: #ffffff; }
</style>
</head>
<body>
""" + home_button + """
<h1>유대결전 패턴</h1>
<ul>"""]

boss_idx = 1
superboss_idx = 1

for eventId, questId, superTicket, bossTicket, attrId, questName in filtered:
    if superTicket == 30:
        tag = "초보스"
        filename = f"KIZUNA_SUPERBOSS{superboss_idx}.html"
        superboss_idx += 1
    elif bossTicket == 20:
        tag = "일반보스"
        filename = f"KIZUNA_BOSS{boss_idx}.html"
        boss_idx += 1
    else:
        continue

    attr_name = attribute_color_map.get(attrId, ("?",))[0]
    label = f"[{tag}] [{attr_name}] {questName}"
    kizuna_html.append(f"<li><a href='{filename}' style='font-size:28px !important'>{label}</a></li>")
    html_body = get_kizuna_gimmick_html_as_string(questId)
    with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
        f.write(html_body)

kizuna_html.append("</ul>")
kizuna_html.append(footer)
kizuna_html.append("</body></html>")
with open(os.path.join(OUTPUT_DIR, "KIZUNA.html"), "w", encoding="utf-8") as f:
    f.write("\n".join(kizuna_html))

# ✅ gimmicks_raw_*.json 삭제
for file in os.listdir("."):
    if file.startswith("gimmicks_raw_") and file.endswith(".json"):
        os.remove(file)

# ✅ docs 내 gimmicks_*.html 삭제
for file in os.listdir(OUTPUT_DIR):
    if file.startswith("gimmicks_") and file.endswith(".html"):
        os.remove(os.path.join(OUTPUT_DIR, file))

print(f"✅ 전체 패턴 HTML 생성 및 정리 완료 ({today_str})")
