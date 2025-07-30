import sqlite3
import json
import os
import re
from collections import defaultdict

BASE_IMG_URL = "https://hayaden.github.io/optc-gimmicks/img"

ICON_MAP = {
    1: "common_attack_up_01_icon", 60: "common_icon_chain_upper_limit", 15: "common_icon_blind",
    183: "common_icon_252_skill", 25: "common_icon_damagecut_dummy", 22: "state_icon_invincible",
    47: "common_damagecut_icon", 115: "common_icon_hungry", 134: "common_icon_chain_damagedown",
    177: "common_icon_247_skill", 138: "common_icon_210", 125: "common_icon_damage_limit",
    99: "common_icon_damage_onlyone", 8: "common_icon_mighty_guard_00", 166: "common_icon_230_skill",
    74: "common_icon_mighty_guard", 51: "common_icon_mighty_guard_01", 52: "common_icon_mighty_guard_02",
    53: "common_icon_mighty_guard_03", 54: "common_icon_mighty_guard_04", 55: "common_state_icon_attack_down",
    57: "common_status_ico_damage_increase", 59: "common_icon_chain_down", 127: "common_icon_death_invalid",
    128: "common_icon_ratio_damagedown", 88: "common_icon_skill_limit", 180: "common_icon_251_skill",
    13: "common_icon_deffence_up", 44: "common_guts_icon", 171: "common_icon_235_skill",
    84: "common_icon_restore_zero", 97: "common_icon_burn", 66: "common_icon_taunt",
    77: "common_icon_captain_change", 0: None
}

def to_int(val, default=0):
    try:
        return int(val)
    except:
        return default

def highlight_element_tags(text):
    tag_colors = {
        "[힘]": "#ff4d4d", "[기]": "#4dff4d", "[속]": "#4d9aff",
        "[심]": "#ffff4d", "[지]": "#d24dff", "[고기]": "#a0522d"
    }
    for tag, color in tag_colors.items():
        text = text.replace(tag, f'<span style="color:{color}; font-weight:bold;">{tag}</span>')
    return text

def clean_text(text):
    text = text.replace("\u003c", "<").replace("\u003e", ">")
    return re.sub(r"<.*?>", "", text).strip()

def difficulty_label(min_lv, max_lv):
    return "Level: 100+" if max_lv >= 100 else f"Level: {min_lv}-{max_lv}" if (min_lv or max_lv) else "레벨 없음"

def format_text_with_icon(texts, icons):
    lines = []
    for i, text in enumerate(texts):
        icon_id = icons[i] if i < len(icons) else 0
        icon_name = ICON_MAP.get(icon_id)
        prefix = f'<img src="{BASE_IMG_URL}/{icon_name}.png">' if icon_name else ""
        full_text = clean_text(text)
        highlighted = highlight_element_tags(full_text)
        lines.append(f'<div class="icon-line">{prefix}{highlighted}</div>')
    return lines

def export_gimmick_html(server_id=1001971, db_path="data/sakura_ko.db", output_path="index.html"):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT gimmickJson_ FROM MstQuestGimmickInformation_ WHERE questId_=?", (server_id,))
        row = cursor.fetchone()
        if not row:
            print(f"❌ serverId={server_id}에 해당하는 기믹 데이터 없음")
            return

        parsed_json = json.loads(row[0])
        gimmick_list = []

        for stage_id, items in parsed_json.items():
            for phase in items:
                min_level = to_int(phase.get("min_trail_level"))
                max_level = to_int(phase.get("max_trail_level"))
                stage_num = to_int(stage_id)

                entry = {
                    "stage": stage_num,
                    "minLevel": min_level,
                    "maxLevel": max_level,
                    "patterns": []
                }

                if "level_condition_text" in phase:
                    entry["level_condition_text"] = phase["level_condition_text"]

                for key, value in phase.items():
                    if key in ("min_trail_level", "max_trail_level", "level_condition_text", "level_condition_text_fr"):
                        continue
                    if not isinstance(value, dict):
                        continue
                    entry["patterns"].append({
                        "slot": key,
                        "texts": value.get("texts", []),
                        "icons": value.get("icon", []),
                        "conditions": value.get("condition_texts", [])
                    })
                gimmick_list.append(entry)

        grouped = defaultdict(list)
        for entry in gimmick_list:
            grouped[(entry["minLevel"], entry["maxLevel"])].append(entry)

        # 디버그용 출력
        print("🧩 grouped key 목록 (minLevel, maxLevel):")
        for k in grouped.keys():
            print(f"  🔹 {k} → 타입: ({type(k[0]).__name__}, {type(k[1]).__name__})")

        LABEL_INFO = {
            "6_": ("초기 상태", "label-initial"),
            "1_": ("선제 행동", "label-preemptive"),
            "5_": ("특수 끼어들기", "label-special"),
            "4_": ("격파 시 행동", "label-death"),
            "3_": ("끼어들기", "label-interrupt"),
            "2_": ("1턴 경과 후 일반 행동", "label-after1turn"),
        }

        SORT_PRIORITY = {k: i for i, k in enumerate(LABEL_INFO.keys())}

        html = ["""<html>
<head>
<meta charset="UTF-8">
<style>
  body { background-color: #13514d; color: #f2f2f7; font-family: sans-serif; padding: 2em; font-size: 26px; }
  img { height: 40px; vertical-align: middle; margin-right: 2px; }
  h2 { border-bottom: 1px solid #f2f2f7; padding-bottom: 0.3em; font-size: 30px; }
  h3 { font-size: 28px; margin-top: 1em; }
  .icon-line { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; font-size: 24px; }
  .label-initial { background-color: #267d4a; color: #f2f2f7; padding: 6px 12px; border-radius: 999px; font-weight: bold; display: inline-block; margin-bottom: 6px; }
  .label-preemptive { background-color: #24567a; color: #f2f2f7; padding: 6px 12px; border-radius: 999px; font-weight: bold; display: inline-block; margin-bottom: 6px; }
  .label-special { background-color: #aa8500; color: #fff; padding: 6px 12px; border-radius: 999px; font-weight: bold; display: inline-block; margin-bottom: 6px; }
  .label-death { background-color: #b71c1c; color: #fff; padding: 6px 12px; border-radius: 999px; font-weight: bold; display: inline-block; margin-bottom: 6px; }
  .label-interrupt { background-color: #6a1b9a; color: #fff; padding: 6px 12px; border-radius: 999px; font-weight: bold; display: inline-block; margin-bottom: 6px; }
  .label-after1turn { background-color: #6a1b9a; color: #fff; padding: 6px 12px; border-radius: 999px; font-weight: bold; display: inline-block; margin-bottom: 6px; }

</style>
</head>
<body>"""]

        rendered_levels = set()
        for (min_lv, max_lv), entries in sorted(grouped.items()):
            label = difficulty_label(min_lv, max_lv)

            if label == "레벨 없음":
                label = None
            
            if label and label not in rendered_levels:
                html.append(f"<h2>{label}</h2>")
                rendered_levels.add(label)

            for entry in sorted(entries, key=lambda x: x["stage"]):
                html.append(f"<h3>Stage {entry['stage']}:</h3>")
                if "level_condition_text" in entry:
                    html.append(f'<div style="color: gold; font-weight: bold;">{clean_text(entry["level_condition_text"])}</div>')

                sorted_patterns = sorted(
                    entry["patterns"],
                    key=lambda p: SORT_PRIORITY.get(
                        next((k for k in SORT_PRIORITY if p["slot"].startswith(k)), "zzz")
                    )
                )

                for pattern in sorted_patterns:
                    slot = pattern["slot"]
                    for prefix, (label_text, label_class) in LABEL_INFO.items():
                        if slot.startswith(prefix):
                            if pattern["conditions"]:
                                for cond in pattern["conditions"]:
                                    html.append(f'<span class="{label_class}" style="color:#87cefa">{label_text}: {clean_text(cond)}</span><br>')
                            else:
                                html.append(f'<span class="{label_class}">{label_text}:</span><br>')
                            html += format_text_with_icon(pattern["texts"], pattern["icons"])
                            break
                html.append("<br>")

        html.append("</body></html>")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(html))
        print(f"✅ HTML 저장 완료: {output_path}")

        json_output_path = f"gimmicks_raw_{server_id}.json"
        with open(json_output_path, "w", encoding="utf-8") as jf:
            json.dump(parsed_json, jf, ensure_ascii=False, indent=2)
        print(f"✅ JSON 저장 완료: {json_output_path}")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")

def get_gimmick_html_as_string(server_id=5000029, db_path="data/sakura_ko.db"):
    from io import StringIO
    import contextlib

    buf = StringIO()
    with contextlib.redirect_stdout(buf):
        export_gimmick_html(server_id=server_id, db_path=db_path, output_path="__temp__.html")
    if os.path.exists("__temp__.html"):
        with open("__temp__.html", "r", encoding="utf-8") as f:
            html_body = f.read()
        os.remove("__temp__.html")
    else:
        html_body = ""

    return html_body.strip()

if __name__ == "__main__":
    export_gimmick_html()
