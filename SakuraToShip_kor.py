import sqlite3
import re
import json

### --- Helper Functions ---

def clean_text(text):
    if not text:
        return ""
    text = text.replace("\n", " ")
    text = text.replace("<icon=common_icon_cureslot_to_damage.png>", "[EOT_HEAL_TO_DAMAGE]")
    text = text.replace("<icon=common_continuous_restore_icon.png>", "[EOT_HEAL]")
    text = text.replace("<icon=common_damagecut_icon.png>", "[THRESHOLD_DAMAGE_CUT]")
    text = text.replace("<icon=common_attack_up_01_icon.png>", "[ATK_UP]")
    text = text.replace("힘 속성", "[힘]속성")
    text = text.replace("기 속성", "[기]속성")
    text = text.replace("속 속성", "[속]속성")
    text = text.replace("심 속성", "[심]속성")
    text = text.replace("지 속성", "[지]속성")
    
    text = re.sub(r"<.*?>", "", text)
    return text.strip()

def ts_units_array_string(units, indent=2):
    space = " " * indent
    lines = []
    for item in units:
        fields = []
        for k, v in item.items():
            if isinstance(v, str):
                fields.append(f'{k}: "{v}"')
            else:
                fields.append(f'{k}: {v}')
        line = space + "{ " + ", ".join(fields) + " }"
        lines.append(line)
    return "[\n" + ",\n".join(lines) + "\n]"

def extract_cd_and_special_and_effect(effect):
    if not effect:
        return "", "-", "-"

    effect = effect.strip()

    if "필살기:" not in effect:
        return effect, "-", "-"

    effect_part, special_part = effect.split("필살기:", 1)
    effect_part = effect_part.strip()

    cd = "-"
    cd_match = re.search(r"\((\d+)턴\)", special_part)
    if cd_match:
        cd = int(cd_match.group(1))
        special_part = special_part.replace(cd_match.group(0), "").strip()

    special_part = special_part.strip()

    return effect_part, cd, special_part

def ts_string(value, indent=2, skip_empty_arrays=False):
    space = " " * indent
    if isinstance(value, str):
        return f'"{value}"'
    elif isinstance(value, list):
        items = [ts_string(v, indent) for v in value]
        return f"[{', '.join(items)}]"
    elif isinstance(value, dict):
        lines = []
        for k, v in value.items():
            # 루트 수준에서만 빈 배열 제거
            if skip_empty_arrays and isinstance(v, list) and len(v) == 0:
                continue
            # 내부에서는 무조건 출력
            lines.append(f"{space}{k}: {ts_string(v, indent + 2)}")
        return "{\n" + ",\n".join(lines) + f"\n{' ' * (indent - 2)}}}"
    else:
        return str(value)
def ts_object_string(obj, indent=2):
    space = " " * indent
    lines = []
    for item in obj:
        fields = []
        for k, v in item.items():
            if isinstance(v, str):
                fields.append(f'{k}: "{v}"')
            else:
                fields.append(f'{k}: {v}')
        line = space + "{ " + ", ".join(fields) + " }"
        lines.append(line)
    return "[\n" + ",\n".join(lines) + "\n]"

def sum_array(arr):
    return sum([x for x in arr if isinstance(x, int)])

def get_last_effect(effects):
    for e in reversed(effects):
        if e and e.strip() != "":
            return clean_text(e)
    return ""

def detect_has_special(ship):
    # ✅ ① cd 먼저 검사
    if "cd" in ship and any(c != "-" for c in ship.get("cd", [])):
        return "yes"
    # ✅ ② modification.cd 검사
    if "modification" in ship and any(c != "-" for c in ship["modification"].get("cd", [])):
        return "afterMRank5"
    # ✅ ③ 둘 다 없으면
    return "no"

### --- DB 연결 ---
conn = sqlite3.connect("common/data/sakura_ko.db")
cursor = conn.cursor()

### --- ① Ship 기본 정보 ---
ships = {}
cursor.execute("""
    SELECT serverId_, name_, subName_, description_, boostPhase1Description_, boostPhase2Description_
    FROM MstShip_
""")
for row in cursor.fetchall():
    sid, name, subname, desc, boost1, boost2 = row
    if sid == 0:
        continue

    full_name = clean_text(name)
    if subname and subname.strip():
        full_name = f"{full_name} - {clean_text(subname)}"

    ships[sid] = {
        "name": full_name,
        "obtain": "",
        "cola": [],
        "superCola": [],
        "effect": [],
        "cd": [],
        "special": [],
        "specialEffect1": clean_text(boost1),
        "specialEffect2": clean_text(boost2),
        "modification": {
            "phase": [],
            "effect": [],
            "cd": [],
            "special": []
        }
    }

### --- ② ShipLevelBoost_ → modification ---
cursor.execute("""
    SELECT shipId_, level_, phase_, effectDescription_
    FROM MstShipLevelBoost_
""")
for shipId, level, phase, effect in cursor.fetchall():
    if shipId == 0:
        continue
    if shipId not in ships:
        ships[shipId] = {
            "name": "",
            "obtain": "",
            "cola": [],
            "superCola": [],
            "effect": [],
            "cd": [],
            "special": [],
            "specialEffect1": "",
            "specialEffect2": "",
            "modification": {
                "phase": [],
                "effect": [],
                "cd": [],
                "special": []
            }
        }
    
    cleaned_effect = clean_text(effect)
    main_effect, cd, special = extract_cd_and_special_and_effect(cleaned_effect)

    mod = ships[shipId]["modification"]
    mod["phase"].append(phase)
    mod["effect"].append(main_effect)
    mod["cd"].append(cd)
    mod["special"].append(special)

### --- ③ ShipLevel_ → cola / superCola / effect / cd / special ---
cursor.execute("""
    SELECT shipId_, level_, requiredShipParts_, requiredShipParts2_, effectDescription_
    FROM MstShipLevel_
    WHERE shipId_ != 0
    ORDER BY shipId_, level_
""")
level_data = {}
for row in cursor.fetchall():
    shipId, level, requiredParts, requiredParts2, effect = row
    if shipId not in level_data:
        level_data[shipId] = {
            "cola": [],
            "superCola": [],
            "effect": [],
            "cd": [],
            "special": []
        }
    level_data[shipId]["cola"].append(requiredParts)
    level_data[shipId]["superCola"].append(requiredParts2)
    cleaned = clean_text(effect)
    eff, cd, special = extract_cd_and_special_and_effect(cleaned)
    level_data[shipId]["effect"].append(eff)
    level_data[shipId]["cd"].append(cd)
    level_data[shipId]["special"].append(special)

for shipId, data in level_data.items():
    if shipId not in ships:
        ships[shipId] = {
            "name": "",
            "obtain": "",
            "cola": [],
            "superCola": [],
            "effect": [],
            "cd": [],
            "special": [],
            "specialEffect1": "",
            "specialEffect2": "",
            "modification": {
                "phase": [],
                "effect": [],
                "cd": [],
                "special": []
            }
        }
    ships[shipId]["cola"] = [0] + data["cola"][:-1]
    ships[shipId]["superCola"] = [0] + data["superCola"][:-1]
    ships[shipId]["effect"] = data["effect"]

    if any(x != "-" for x in data["cd"]):
        ships[shipId]["cd"] = data["cd"]
    if any(x != "-" for x in data["special"]):
        ships[shipId]["special"] = data["special"]

### --- ④ obtain.json 읽어서 적용 ---
try:
    with open("obtain.json", encoding="utf-8") as f:
        obtain_data = json.load(f)
except FileNotFoundError:
    print("⚠️ obtain.json 파일이 없어서 obtain 필드 기본 ''로 유지합니다.")
    obtain_data = {}

for sid in ships:
    sid_str = str(sid)
    ships[sid]["obtain"] = obtain_data.get(sid_str, "")







### --- ⑤ TypeScript details_ko.ts 생성 ---
with open("details.ts", "w", encoding="utf-8") as f:
    f.write('import type { ShipInfo } from "@/types/Ship";\n\n')
    f.write('export const details: Record<number, ShipInfo> = {\n')
    ship_items = sorted(ships.items())
    for idx, (sid, data) in enumerate(ship_items):
        # ✅ ① 빈 문자열 필드 제거
        if data.get("specialEffect1", "").strip() == "":
            data.pop("specialEffect1", None)
        if data.get("specialEffect2", "").strip() == "":
            data.pop("specialEffect2", None)
        # ✅ ② 루트 cd, special이 빈 배열이면 제거
        if "cd" in data and isinstance(data["cd"], list) and len(data["cd"]) == 0:
            data.pop("cd", None)
        if "special" in data and isinstance(data["special"], list) and len(data["special"]) == 0:
            data.pop("special", None)        
        # ✅ ② modification 내부 전부 빈 배열이면 제거
        mod = data.get("modification")
        if mod:
            if all(isinstance(v, list) and len(v) == 0 for v in mod.values()):
                data.pop("modification", None)
        f.write(f"  {sid}: {ts_string(data, indent=4)}")
        if idx != len(ship_items) - 1:
            f.write(",\n")
        else:
            f.write("\n")
    f.write("};\n")

print("✅ details.ts 생성 완료!")

### --- ⑥ TypeScript units.ts 생성 ---
units = []
for sid, ship in ships.items():
    unit = {}
    unit["id"] = sid
    unit["name"] = ship.get("name", "")
    unit["colaCount"] = sum_array(ship.get("cola", []))
    unit["superColaCount"] = sum_array(ship.get("superCola", []))
    if "modification" in ship and ship["modification"].get("effect"):
        unit["effect"] = get_last_effect(ship["modification"]["effect"])
    else:
        unit["effect"] = get_last_effect(ship.get("effect", []))
    unit["hasSpecial"] = detect_has_special(ship)
    units.append(unit)

with open("units.ts", "w", encoding="utf-8") as f:
    f.write('import type { ShipOverview } from "@/types/Ship";\n')
    f.write('import { details } from "./details";\n\n')
    f.write('import { convertToPSTTimestamp, getPSTTimestamp } from "@/lib/utils";\n\n')
    f.write('export const units: ShipOverview[] = ')
    f.write(ts_units_array_string(units, indent=2))
    f.write(';')

print("✅ units.ts 생성 완료!")

