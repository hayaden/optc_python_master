import sqlite3
import json

# ================================
# ① DB 연결
# ================================
conn = sqlite3.connect("data/sakura_ko.db")
cursor = conn.cursor()

# ================================
# ② 부모/자식 정보 읽기
# ================================
cursor.execute("""
    SELECT serverId_, logbookId_, childCharacterIds_, versusChildCharacterIds_
    FROM MstCharacter_
""")

server_to_logbook = {}         # 캐릭터ID → logbookId
child_to_parent_info = {}      # 자식ID → (부모logbookId, 몇번째 자식인지)
parent_has_children = set()    # 자식 목록을 가진 부모들

for sid, logbookId, childJson, vschildJson in cursor.fetchall():
    server_to_logbook[sid] = logbookId

    has_children = False

    # childCharacterIds_ 처리
    if logbookId != -1 and childJson:
        try:
            children = json.loads(childJson)
            if children:
                has_children = True
                for idx, child_id in enumerate(children):
                    child_to_parent_info[child_id] = (logbookId, idx)
        except json.JSONDecodeError:
            pass

    # versusChildCharacterIds_ 처리
    if logbookId != -1 and vschildJson:
        try:
            children = json.loads(vschildJson)
            if children:
                has_children = True
                for idx, child_id in enumerate(children):
                    child_to_parent_info[child_id] = (logbookId, idx)
        except json.JSONDecodeError:
            pass

    # 자식이 하나라도 있으면 부모ID를 등록
    if has_children:
        parent_has_children.add(sid)

# ================================
# ③ 태그 메타정보 읽기
# ================================
cursor.execute("SELECT serverId_, name_, category_ FROM MstCharacterTag_")
tag_info_map = {}

for sid, name, category in cursor.fetchall():
    tag_info_map[sid] = {
        "name": name,
        "category": category
    }

# ================================
# ④ 태그 관계 → logbookId로 변환
# ================================
cursor.execute("SELECT characterTagId_, characterId_ FROM MstCharacterTagRelation_")
merged_tags = {}

for tag_id, char_id in cursor.fetchall():
    if tag_id not in tag_info_map:
        continue

    name = tag_info_map[tag_id]["name"]
    category = tag_info_map[tag_id]["category"]

    entries_to_add = []

    logbook_id = server_to_logbook.get(char_id)
    if logbook_id is None:
        continue

    if logbook_id != -1:
        # ✅ 부모 캐릭터인데 자식을 가진 부모라면 제외
        if char_id in parent_has_children:
            continue
        # ✅ 자식 없는 부모만 추가
        entries_to_add.append({"logbookId": logbook_id})

    else:
        # ✅ 자식 → 부모 logbookId + 몇번째인지 index 포함
        parent_info = child_to_parent_info.get(char_id)
        if parent_info is not None:
            parent_logbookId, child_index = parent_info
            entries_to_add.append({
                "logbookId": parent_logbookId,
                "childIndex": child_index
            })

    if not entries_to_add:
        continue

    if name not in merged_tags:
        merged_tags[name] = {
            "category": category,
            "characterIds": []
        }

    merged_tags[name]["characterIds"].extend(entries_to_add)

# ================================
# ⑤ 중복 제거 + 정렬
# ================================
for tag in merged_tags.values():
    seen = set()
    unique = []
    for entry in tag["characterIds"]:
        # 딕셔너리 비교 → 튜플로 변환
        key = (entry.get("logbookId"), entry.get("childIndex"))
        if key not in seen:
            seen.add(key)
            unique.append(entry)
    # logbookId, childIndex 기준으로 정렬
    tag["characterIds"] = sorted(unique, key=lambda x: (x["logbookId"], x.get("childIndex", -1)))

# ================================
# ⑥ JS 파일로 저장
# ================================
with open("./data/characterTags.js", "w", encoding="utf-8") as f:
    f.write("window.characterTags = {\n")
    lines = []
    for name, data in merged_tags.items():
        line = f'  {json.dumps(name, ensure_ascii=False)}: {json.dumps(data, ensure_ascii=False)}'
        lines.append(line)
    f.write(",\n".join(lines))
    f.write("\n};\n")

print("✅ characterTags.js 생성 완료 (자식 정보 포함, 부모자식 구분 반영)")
