import sqlite3
import json
import os
import re
from collections import defaultdict

BASE_IMG_URL = "https://hayaden.github.io/optc-gimmicks/img"
BASE_IMG_URL = "img"

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
    77: "common_icon_captain_change",
    72: "popuptext_slot_poison",
    132: "",
    9: "common_icon_heal_down",
    5: "common_icon_poison",
    10: "common_icon_slot",
    11: "common_icon_restore_boost",
    16: "common_berserk_icon",
    137: "common_icon_209_skill",
    126: "common_icon_cureslot_to_damage",
    124: "common_icon_heal_to_damage",
    106: "common_icon_disable_attribute_influence",
    1001: "common_despair",
    1002: "common_special_bind",
    1003: "common_palsy",
    1004: "common_special_reverse",
    1005: "common_bind",
    1006: "common_slot",
    1007: "common_territory",
    80: "common_icon_incidence_down_own",
    81: "common_duration_enemy_icon",
    1009: "common_slot_lock",
    1010: "common_stun",
    1011: "common_blow",
    1012: "common_icon_skill_lock",
    1013: "common_heal",
    1014: "common_silence",
    1015: "common_del",
    1016: "characterbox_icon_ex",
    1017: "common_run",
    1018: "characterbox_icon_vs",
    1019: "common_change_charge",
    1020: "common_special_charge",
    1021: "common_resi_up",
    1022: "common_member_disable",
    1023: "common_color_change",
    1024: "common_slot_chance",
    1025: "common_slot_random",
    1026: "common_change_lock",
    1027: "common_slot_bind",
    2001: "common_weak_01",
    2002: "common_weak_02",
    2003: "common_weak_03",
    2004: "common_weak_04",
    2005: "common_weak_05",
    2006: "common_weak_06",
    2007: "common_weak_07",
    2008: "common_weak_08",
    3001: "popuptext_slot_obstacle",
    3002: "popuptext_slot_negative",
    3003: "popuptext_slot_superobstacle",
    3004: "popuptext_slot_wa",
    
    3006: "popuptext_slot_semla",
    3007: "popuptext_slot_meat",
    3008: "popuptext_slot_gigant",
    3009: "popuptext_slot_cooperation",
    3010: "popuptext_slot_bomb",
    3011: "popuptext_slot_megabomb",
    3012: "popuptext_slot_blank",
    3013: "popuptext_slot_palsy",
    3014: "popuptext_slot_poison",
    3015: "popuptext_slot_red",
    3016: "popuptext_slot_green",
    3017: "popuptext_slot_blue",
    3018: "popuptext_slot_yellow",
    3019: "popuptext_slot_purple",
    3020: "popuptext_slot_rainbow",    
    
    4001: "quest_combo_barrier_power",  
    4002: "quest_combo_barrier_skill",  
    4003: "quest_combo_barrier_speed",
    4004: "quest_combo_barrier_heart",
    4005: "quest_combo_barrier_wisdom",
    4006: "quest_combo_barrier_meat",
    4007: "quest_combo_barrier_1",
    4008: "quest_combo_barrier_2",
    4009: "quest_combo_barrier_3",
    4010: "quest_combo_barrer_damage",
    4011: "quest_combo_barrer_hit",
    4012: "quest_combo_barrier_g",
    4013: "quest_combo_barrier_cooperation",
    4014: "quest_combo_barrier_bomb",
    4015: "quest_combo_barrier_wa",
    5001: "common_damage",
    10000: "filter_attribute_power",
    10001: "filter_attribute_technical",
    10002: "filter_attribute_speed",
    10003: "filter_attribute_heart",
    10004: "filter_attribute_intellect",
    0: None
}


FORCED_ICON_KEYWORDS = [
    ("슬롯 봉쇄", 1027),
    ("선장효과 무효", 1001),     # 도주 텍스트 있으면 → 선장교체 아이콘 (예시)
    ("필살기 봉쇄", 1002),
    ("을 마비", 1003,),
    ("동안 마비", 1003,),
    ("되돌리기", 1004,),
    ("봉쇄", 1005),
    
    ("구역:", 1007),
    #("[불리] 슬롯으로 취급", 1008),
    ("슬롯 고정", 1009),
    ("기절", 1010),
    ("날려버리기", 1011),
    ("필살기 턴 고정", 1012),
    ("까지 회복", 1013),
    ("전부 회복", 1013),
    ("침묵", 1014),
    ("축적치 해제", 1015),
    ("유리 효과 해제", 1015),
    ("속성을 속성 초월", 1016),
    ("도주", 1017),
    ("VS 효과의 게이지를", 1018),
    ("슈퍼 체인지 효과를", 1019),
    ("필살기 턴을", 1020),
    ("내성", 1021),
    ("선원효과 무효", 1022),
    ("속성<col=1> 변화", 1023),
    ("슬롯 출현율 상승", 1024),
    ("슬롯을 랜덤으로 변환", 1025),
    ("슬롯 변환 불가", 1026),
    
    ("약점 타입: 격투형", 2001),
    ("약점 타입: 참격형", 2002),
    ("약점 타입: 타격형", 2003),
    ("약점 타입: 사격형", 2004),
    ("약점 타입: 자유형", 2005),
    ("약점 타입: 야심형", 2006),
    ("약점 타입: 박식형", 2007),
    ("약점 타입: 강인형", 2008),
    ("[방해] 슬롯으로 변환", 3001),
    ("[불리] 슬롯으로 변환", 3002),
    ("[초 방해] 슬롯으로 변환", 3003),
    ("[和] 슬롯으로 변환", 3004),
    ("[셈라] 슬롯으로 변환", 3006),
    ("<col=13>[고기]<col=1> 슬롯으로 변환", 3007),
    ("[G] 슬롯으로 변환", 3008),
    ("[연] 슬롯으로 변환", 3009),
    ("[폭탄] 슬롯으로 변환", 3010),
    ("[강화 폭탄] 슬롯으로 변환", 3011),
    ("[공백] 슬롯으로 변환", 3012),
    ("[마비] 슬롯으로 변환", 3013),
    ("[독] 슬롯으로 변환", 3014),
    ("<col=12>[힘]<col=1> 슬롯으로 변환", 3015),
    ("<col=11>[기]<col=1> 슬롯으로 변환", 3016),
    ("<col=9>[속]<col=1> 슬롯으로 변환", 3017),
    ("<col=10>[심]<col=1> 슬롯으로 변환", 3018),
    ("<col=8>[지]<col=1> 슬롯으로 변환", 3019),
    ("[무지개] 슬롯으로 변환", 3020),

    ("데미지 배리어", 4010),
    ("hit 배리어", 4011),
    ("슬롯 배리어([G] 슬롯", 4012), 
    ("슬롯 배리어([연] 슬롯", 4013), 
    ("슬롯 배리어([폭탄] 슬롯", 4014), 
    ("슬롯 배리어([和] 슬롯", 4015), 
    ("슬롯 배리어(<col=12>[힘]<col=1> 슬롯", 4001), 
    ("슬롯 배리어(<col=11>[기]<col=1> 슬롯", 4002), 
    ("슬롯 배리어(<col=9>[속]<col=1> 슬롯", 4003), 
    ("슬롯 배리어(<col=10>[심]<col=1> 슬롯", 4004), 
    ("슬롯 배리어(<col=8>[지]<col=1> 슬롯", 4005), 
    ("슬롯 배리어(<col=13>[고기]<col=1> 슬롯", 4006),
    ("[和] 슬롯으로 변환", 3004),
    ("배리어(GOOD", 4007),
    ("배리어(GREAT", 4008),
    ("배리어(PERFECT", 4009),
    ("데미지", 5001), 

    
]

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
    if icons is None:
        icons = []
    lines = []
    for i, text in enumerate(texts):
        icon_id = icons[i] if i < len(icons) else 0

        if icon_id == 0:# ✅ 텍스트 기반 아이콘 강제 지정
            for keyword, forced_icon_id in FORCED_ICON_KEYWORDS:
                if keyword in text:
                    icon_id = forced_icon_id
                    break

        icon_name = ICON_MAP.get(icon_id)
        prefix = f'<img src="{BASE_IMG_URL}/{icon_name}.png">' if icon_name else ""
        full_text = clean_text(text)
        highlighted = (full_text)
        lines.append(f'<div class="icon-line">{prefix}{highlighted}</div>')
    return lines

def export_pka_gimmick_html(server_id=1001971, db_path="data/sakura_ko.db", output_path="docs/index.html"):
    try:
        LEVEL_CUTOFF = 150  # ✅ 컷오프 기준: 150 이상이면 무시

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT questName_ FROM MstQuest_ WHERE questId_=?", (server_id,))
        name_row = cursor.fetchone()
        quest_name = name_row[0] if name_row else f"Quest {server_id}"
        

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

                if min_level >= LEVEL_CUTOFF:
                    continue  # ✅ 컷오프 이상이면 무시

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

                # ✅ 중복 방지: 동일한 항목 있는지 확인
                is_duplicate = any(
                    e["stage"] == entry["stage"] and
                    e["minLevel"] == entry["minLevel"] and
                    e["maxLevel"] == entry["maxLevel"] and
                    e["patterns"] == entry["patterns"]
                    for e in gimmick_list
                )
                if not is_duplicate:
                    gimmick_list.append(entry)

        # ✅ 그룹핑: maxLevel >= 100 → "100+" 그룹
        grouped = defaultdict(list)
        for entry in gimmick_list:
            if entry["maxLevel"] >= 100:
                group_key = "100+"
            else:
                group_key = (entry["minLevel"], entry["maxLevel"])
            grouped[group_key].append(entry)

        LABEL_INFO = {
            "6_": ("초기 상태", "label-initial"),
            "1_": ("선제 행동", "label-preemptive"),
            "5_": ("특수 끼어들기", "label-special"),
            "4_": ("격파 시 행동", "label-death"),
            "3_": ("끼어들기", "label-interrupt"),
            "2_": ("1턴 경과 후 일반 행동", "label-after1turn"),
            "7_": ("적의 체력에 따라 속성이 변화", "label-after1turn"),
        }
        SORT_PRIORITY = {k: i for i, k in enumerate(LABEL_INFO.keys())}

        html = [f"""<html>
<head>
<meta charset="UTF-8">
<style>
  body {{ background-color: #13514d; color: #f2f2f7; font-family: sans-serif; padding: 2em; font-size: 26px; }}
  img {{ height: 40px; vertical-align: middle; margin-right: 2px; }}
  h1 {{ font-size: 36px; color: gold; margin-bottom: 0.3em; }}
  h2 {{ solid #f2f2f7; padding-bottom: 0.3em; font-size: 30px; }}
  h3 {{ font-size: 28px; margin-top: 1em; }}
  .icon-line {{ display: flex; align-items: center; gap: 6px; margin-bottom: 4px; font-size: 24px; }}
  .label-initial {{ background-color: #267d4a; color: #f2f2f7; padding: 2px 8px; border-radius: 12px; font-weight: bold; display: inline-block; margin-bottom: 6px; }}
  .label-preemptive {{ background-color: #24567a; color: #f2f2f7; padding: 2px 8px; border-radius: 12px; font-weight: bold; display: inline-block; margin-bottom: 6px; }}
  .label-special {{ background-color: #aa8500; color: #fff; padding: 2px 8px; border-radius: 12px; font-weight: bold; display: inline-block; margin-bottom: 6px; }}
  .label-death {{ background-color: #b71c1c; color: #fff; padding: 2px 8px; border-radius: 12px; font-weight: bold; display: inline-block; margin-bottom: 6px; }}
  .label-interrupt {{ background-color: #6a1b9a; color: #fff; padding: 2px 8px; border-radius: 12px; font-weight: bold; display: inline-block; margin-bottom: 6px; }}
  .label-after1turn {{ background-color: #6a1b9a; color: #fff; padding: 2px 8px; border-radius: 12px; font-weight: bold; display: inline-block; margin-bottom: 6px; }}
</style>
</head>
<body>
<h1>{quest_name}</h1>"""]
        
        rendered_level_flags = set()
        for level_key, entries in sorted(grouped.items(), key=lambda x: (x[0] != "100+", x[0])):
            if level_key == "100+":
                label = "Level: 100+"
                level_flag = "100+"
            else:
                min_lv, max_lv = level_key
                label = difficulty_label(min_lv, max_lv)
                level_flag = level_key

            if label and level_flag not in rendered_level_flags:
                html.append('<hr style="border: 1px solid white;">')
                html.append(f'<h2 style="color: gold;">{label}</h2>')
                rendered_level_flags.add(level_flag)

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



def get_pka_gimmick_html_as_string(server_id=5000029, db_path="data/sakura_ko.db"):
    from io import StringIO
    import contextlib

    buf = StringIO()
    with contextlib.redirect_stdout(buf):
        export_pka_gimmick_html(server_id=server_id, db_path=db_path, output_path="__temp__.html")
    if os.path.exists("__temp__.html"):
        with open("__temp__.html", "r", encoding="utf-8") as f:
            html_body = f.read()
        os.remove("__temp__.html")
    else:
        html_body = ""

    return html_body.strip()

if __name__ == "__main__":
    export_pka_gimmick_html()
