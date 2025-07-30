import sqlite3
import json
import re
import os
# DB 연결
conn = sqlite3.connect("data/sakura_ko.db")
cursor = conn.cursor()

# 속성 태그 치환
def replace_element_tags(text):
    if not text:
        return text
    text = re.sub(r"힘 속성", "[STR]", text)
    text = re.sub(r"기 속성", "[DEX]", text)
    text = re.sub(r"속 속성", "[QCK]", text)
    text = re.sub(r"지 속성", "[INT]", text)
    text = re.sub(r"심 속성", "[PSY]", text)
    text = re.sub(r"\[고기\]>", "[RCV]", text)
    text = re.sub(r"<col=\d+>", "", text)
    icons = {
        "common_attack_up_01_icon.png": "공격력 상승",
        "common_berserk_icon.png": "격노",
        "common_continuous_restore_icon.png": "피 회복",
        "common_damagecut_icon.png": "데미지 격감",
        "common_duration_enemy_icon.png": "턴 종료 시 데미지",
        "common_icon_damagecut_dummy.png": "데미지 감소",
        "common_icon_base_attack_up.png": "기본 공격력 증가",
        "common_icon_bleeding.png": "출혈",
        "common_icon_chain_upper_limit.png": "체인 상한 고정",
        "common_icon_cureslot_to_damage.png": "[cureslot_to_damage]",
        "common_icon_215_skill.png": "[215_skill]",
        "common_icon_224_skill.png": "[224_skill]",
        "common_icon_225_skill.png": "[225_skill]",
        "common_icon_226_skill.png": "[226_skill]",
        "common_icon_damage_plus.png": "[damage_plus]",
        "common_icon_deffence_up.png": "방어력 상승",
        "common_icon_heal_to_damage.png": "[heal_to_damage]",
        "common_icon_mighty_guard_00.png": "[mighty_guard_00]",
        "common_icon_mighty_guard_04.png": "[mighty_guard_04]",
        "common_icon_over_heal.png": "[over_heal]",
        "common_icon_slot.png": "[slot]",
        "common_icon_slot_auto_change.png": "[auto_change]",
        "common_icon_slot_relations.png": "[slot_relations]",
        "common_state_icon_attack_down.png": "공격력 감소",
        "common_status_ico_damage_increase.png": "받는 데미지 증가",
        "gage_level_dummy.png": "[gage_level_dummy]",
        "common_icon_burn.png": "화상",
    }
    for icon, replacement in icons.items():
        text = re.sub(fr"<icon={icon}>", replacement, text)
    return text
def load_existing_details(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
# 매핑 로딩
def load_mapping():
    cursor.execute("SELECT fromLogbookNum_, toLogbookNum_ FROM MstLogbookNumMapping_")
    logbook_id_map = {f: t for f, t in cursor.fetchall()}
    cursor.execute("SELECT serverId_, name_ FROM MstCharacterTag_")
    character_tag_map = {sid: replace_element_tags(name) for sid, name in cursor.fetchall()}    
    cursor.execute("SELECT serverId_, description_ FROM MstLeaderSkill_")
    leader_skill_map = {sid: replace_element_tags(desc) for sid, desc in cursor.fetchall() if sid != -1}

    cursor.execute("SELECT serverId_, name_, description_ FROM MstAbility_")
    ability_map = {
        sid: {
            "name": replace_element_tags(name),
            "description": replace_element_tags(desc)
        }
        for sid, name, desc in cursor.fetchall() if sid != -1
    }

    cursor.execute("SELECT serverId_, targetDescription_, targetJson_ FROM MstSupportSkill_")
    support_char_map = {}
    for sid, desc, target_json in cursor.fetchall():
        if sid == -1:
            continue

        desc_clean = replace_element_tags(desc)

        # ✅ character_tags 추가 처리
        extra_tags = []
        if target_json:
            try:
                targets = json.loads(target_json)
                for item in targets:
                    if "character_tags" in item:
                        for tag_id in item["character_tags"]:
                            tag_name = character_tag_map.get(tag_id)
                            if tag_name:
                                extra_tags.append(tag_name)
            except Exception as e:
                print(f"⚠️ JSON 파싱 오류 in SupportSkill targetJson_: {e}")

        # ✅ 이름 붙이기
        if extra_tags:
            desc_clean += " [" + ", ".join(extra_tags) + "]"

        support_char_map[sid] = desc_clean
    cursor.execute("SELECT supportSkillId_, level_, description_ FROM MstSupportSkillEffect_")
    support_desc_map = {}
    for sid, lvl, desc in cursor.fetchall():
        support_desc_map.setdefault(sid, {})[lvl] = replace_element_tags(desc)
    cursor.execute("SELECT uniqueId_, groupId_ FROM MstPotentialSkill_")
    skill_to_group_map = {uid: gid for uid, gid in cursor.fetchall()}

    cursor.execute("SELECT uniqueId_, name_ FROM MstPotentialSkillGroup_")
    group_to_name_map = {gid: replace_element_tags(name) for gid, name in cursor.fetchall()}
    cursor.execute("""
    SELECT skillId_, level_, conditionDescription_, effectDescription_, effectDescriptionDetail_, description_
    FROM MstPotentialSkillEffect_
    """)
    potential_effect_map = {}
    for sid, lvl, cond, desc, detail, desc_simple in cursor.fetchall():
        group_id = skill_to_group_map.get(sid)

        cond = replace_element_tags(cond)
        desc = replace_element_tags(desc)
        detail = replace_element_tags(detail)
        desc_simple = replace_element_tags(desc_simple)

        if group_id in (25, 27, 28, 29, 100):
            # 특수 + 일반 같이 저장
            if sid not in potential_effect_map:
                potential_effect_map[sid] = [("", "", "", "")] * 5
            potential_effect_map[sid][lvl - 1] = (cond, desc, detail, desc_simple)
        else:
            # 일반 Potential → desc_simple 하나만
            if sid not in potential_effect_map:
                potential_effect_map[sid] = [""] * 5
            potential_effect_map[sid][lvl - 1] = desc_simple



    cursor.execute("SELECT serverId_, description_ FROM MstMemberSkill_")
    member_skill_map = {sid: replace_element_tags(desc) for sid, desc in cursor.fetchall() if sid != -1}

    cursor.execute("SELECT characterId_, sequence_, description_ FROM MstLimitBreak_")
    limit_break_map = {}
    for cid, seq, desc in cursor.fetchall():
        limit_break_map.setdefault(cid, []).append((seq, replace_element_tags(desc)))
    for cid in limit_break_map:
        limit_break_map[cid].sort(key=lambda x: x[0])

    cursor.execute("SELECT serverId_, leaderSkillId_ FROM MstCharacter_ WHERE leaderSkillId_ != -1")
    charid_to_leaderid = {sid: lid for sid, lid in cursor.fetchall()}
    
    return (
        leader_skill_map, ability_map, support_char_map,
        support_desc_map, potential_effect_map,
        skill_to_group_map, group_to_name_map, member_skill_map,
        limit_break_map, charid_to_leaderid,  logbook_id_map
    )

(
    leader_skill_map, ability_map, support_char_map, support_desc_map,
    potential_effect_map, skill_to_group_map, group_to_name_map, member_skill_map,
    limit_break_map, charid_to_leaderid, logbook_id_map
) = load_mapping()
cursor.execute("""
SELECT characterId_, step_, characterLevelLimitBreakType_, skillReplaceJson_
FROM MstCharacterLevelLimitBreak_
""")
level_break_rows = cursor.fetchall()

# 캐릭터ID별 -> 단계별 limit break 리스트 생성
charid_to_levelbreaks = {}
for cid, step, stype, replace_json in level_break_rows:
    try:
        parsed_json = json.loads(replace_json)
        charid_to_levelbreaks.setdefault(cid, []).append({
            "step": step,
            "type": stype,
            "json": parsed_json
        })
    except Exception as e:
        print(f"⚠️ JSON 파싱 오류: {replace_json} ({e})")

cursor.execute("""
SELECT characterId_, effectsJson_
FROM MstLimitBreak_
WHERE limitBreakType_ = 'LimitBreak::MemberSkill'
""")
limitbreak_member_skill_rows = cursor.fetchall()

# 캐릭터별 sailor 정보 저장
limitbreak_sailor_map = {}
for cid, effects_json in limitbreak_member_skill_rows:
    try:
        effects = json.loads(effects_json)
    except Exception as e:
        print(f"⚠️ JSON 파싱 오류: {effects_json} ({e})")
        continue

    sailor_obj = {}

    # ✅ JSON 안에서 꺼내오기
    skill1_id = effects.get("update_member_skill_1_id")
    skill2_id = effects.get("update_member_skill_2_id")

    if skill2_id in member_skill_map:
        sailor_obj["level1"] = member_skill_map[skill2_id]
    if skill1_id in member_skill_map:
        sailor_obj["level2"] = member_skill_map[skill1_id]

    if sailor_obj:
        existing = limitbreak_sailor_map.setdefault(cid, {})
        existing.update(sailor_obj)





# 캐릭터 정보 로딩
cursor.execute("""
SELECT 
    logbookId_, serverId_, name_, subName_, leaderSkillId_, memberSkillId1_, 
    memberSkillId2_, abilityId_, changeSkillId_, 
    firstPotentialSkillId_, secondPotentialSkillId_, thirdPotentialSkillId_,
    childCharacterIds_, versusChildCharacterIds_,
    exceedCharacterTypeSkillId_, extraExceedSkillId_, ExceedTrademarkSkillId_
FROM MstCharacter_
""")
characters = cursor.fetchall()

result = {}

for row in characters:
    (
        logbookId, serverId, name, subName, leaderSkillId, member1,
        member2, abilityId, changeSkillId,
        pot1, pot2, pot3, childIds, versusChildIds,
        exceedSkillId, extraSkillId, exceedtrademarkSkillId,
    ) = row
    if logbookId in logbook_id_map:
        logbookId = logbook_id_map[logbookId]
    if logbookId == -1:
        continue

    entry = {}
    row2 = cursor.execute("""
        SELECT piratesSpeed_, piratesDefense_, piratesStyle_
        FROM MstCharacter_
        WHERE serverId_=?
    """, (serverId,)).fetchone()
    if row2 and row2[0] is not None:
        spd, defense, style_id = row2
        style_map = {
            1: "ATK",
            2: "DEF",
            3: "HEAL",
            4: "SUPPORT",
            5: "DEBUFF",
            6: "BALANCE",
        }
        entry["festStats"] = {
            "spd": spd,
            "def": defense,
            "style": style_map.get(style_id, "UNKNOWN")
        }

    # 2️⃣ festAttackPattern, festAttackTarget
    row2 = cursor.execute("""
        SELECT piratesBehaviorPatternsJson_
        FROM MstCharacter_
        WHERE serverId_=?
    """, (serverId,)).fetchone()
    if row2 and row2[0]:
        try:
            patterns_data = json.loads(row2[0])
            if "data" in patterns_data and patterns_data["data"]:
                item = patterns_data["data"][0]
                target_type = item.get("target_type")
                target_type_map = {
                    1: "남은 체력이 적은 적을 노린다",
                    2: "남은 체력이 많은 적을 노린다",
                    3: "가까운 적을 노린다",
                    4: "공격력이 높은 적을 노린다",
                    5: "방어력이 높은 적을 노린다",
                    6: "속도가 높은 적을 노린다",
                }
                entry["festAttackTarget"] = target_type_map.get(target_type, "")

                behavior_ids = item.get("behavior_ids", [])
                attack_patterns = []
                for bid in behavior_ids:
                    row3 = cursor.execute("""
                        SELECT descriptionDetail_ FROM MstPiratesBehavior_ WHERE serverId_=?
                    """, (bid,)).fetchone()
                    if row3 and row3[0]:
                        attack_patterns.append(replace_element_tags(row3[0]))
                if attack_patterns:
                    entry["festAttackPattern"] = attack_patterns
        except Exception as e:
            print(f"⚠️ festAttackPattern JSON 파싱 오류: {e}")

    # 3️⃣ festResistance & festAbility
    row2 = cursor.execute("""
        SELECT piratesAbilityId_ FROM MstCharacter_
        WHERE serverId_=?
    """, (serverId,)).fetchone()
    if row2 and row2[0] != -1:
        aid = row2[0]
        row3 = cursor.execute("""
            SELECT description_ 
            FROM MstPiratesAbility_
            WHERE serverId_=?
        """, (aid,)).fetchone()
        if row3 and row3[0]:
            desc = row3[0]
            entry["festResistance"] = replace_element_tags(desc)

    # 4️⃣ festAbility (passive levels)
    row2 = cursor.execute("""
        SELECT piratesPassiveSkillId_ FROM MstCharacter_
        WHERE serverId_=?
    """, (serverId,)).fetchone()
    if row2 and row2[0] != -1:
        pid = row2[0]
        cursor.execute("""
            SELECT level_, description_
            FROM MstPiratesPassiveSkillEffect_
            WHERE piratesPassiveSkillId_=?
            ORDER BY level_
        """, (pid,))
        passive_rows = cursor.fetchall()
        if passive_rows:
            entry["festAbility"] = [replace_element_tags(desc) for _, desc in passive_rows]
    # 5️⃣ festSpecial
    row2 = cursor.execute("""
        SELECT piratesActiveSkillId_ FROM MstCharacter_
        WHERE serverId_=?
    """, (serverId,)).fetchone()
    if row2 and row2[0] != -1:
        aid = row2[0]
        cursor.execute("""
            SELECT level_, chargeIntervalTime_, description_
            FROM MstPiratesActiveSkillEffect_
            WHERE piratesActiveSkillId_=?
            ORDER BY level_
        """, (aid,))
        active_rows = cursor.fetchall()
        if active_rows:
            fest_special = []
            for _, cooldown, desc in active_rows:
                fest_special.append({
                    "cooldown": cooldown,
                    "description": replace_element_tags(desc)
                })
            if fest_special:
                entry["festSpecial"] = fest_special

    # 6️⃣ festAbilityGP
    row2 = cursor.execute("""
        SELECT piratesGpAbilityId_ FROM MstCharacter_
        WHERE serverId_=?
    """, (serverId,)).fetchone()
    if row2 and row2[0] != -1:
        gid = row2[0]
        cursor.execute("""
            SELECT level_, leaderSkillDescription_, burstDescription_, burstLimit_
            FROM MstPiratesGpAbilityEffect_
            WHERE piratesGpAbilityId_=?
            ORDER BY level_
        """, (gid,))
        gp_rows = cursor.fetchall()
        if gp_rows:
            fest_gp_ability = []
            for _, leader, burst, limit in gp_rows:
                fest_gp_ability.append({
                    "festGPAbility": replace_element_tags(leader),
                    "festGPSpecial": replace_element_tags(burst),
                    "uses": limit
                })
            entry["festAbilityGP"] = fest_gp_ability

        # 7️⃣ festAbilityGPCondition
        row3 = cursor.execute("""
            SELECT burstConditionDescription_
            FROM MstPiratesGpAbility_
            WHERE serverId_=?
        """, (gid,)).fetchone()
        if row3 and row3[0]:
            entry["festAbilityGPCondition"] = replace_element_tags(row3[0])
    if childIds and childIds != "-1":
        child_list = [int(c.strip()) for c in childIds.strip("[]").split(",")]
        entry["captain"] = {
            "character1": leader_skill_map.get(charid_to_leaderid.get(child_list[0], -1), f"ID {child_list[0]}"),
            "character2": leader_skill_map.get(charid_to_leaderid.get(child_list[1], -1), f"ID {child_list[1]}"),
            "combined": leader_skill_map.get(leaderSkillId, f"ID {leaderSkillId}")
        }
    elif leaderSkillId in leader_skill_map:
        entry["captain"] = leader_skill_map[leaderSkillId]

    if serverId in limit_break_map:
        entry["limit"] = [
            { "description": desc }
            for seq, desc in limit_break_map[serverId]
        ]

    potentials = []

    for pot_id in [pot1, pot2, pot3]:
        if pot_id not in potential_effect_map:
            continue

        group_id = skill_to_group_map.get(pot_id)
        levels = potential_effect_map[pot_id]

        # ✅ 먼저 특수 JSON 생성
        if group_id == 25:
            entry["superTandem"] = {
                "characterCondition": [lvl[0] for lvl in levels],
                "description": [lvl[1] for lvl in levels]
            }

        elif group_id == 27:
            if versusChildIds and versusChildIds != "-1":
                cid_list = [int(cid.strip()) for cid in versusChildIds.strip("[]").split(",")]
                for cid in cid_list:
                    row = cursor.execute("""
                        SELECT firstPotentialSkillId_, secondPotentialSkillId_, thirdPotentialSkillId_
                        FROM MstCharacter_
                        WHERE serverId_=?
                    """, (cid,)).fetchone()
                    if not row:
                        continue
                    for child_pot_id in row:
                        if child_pot_id == -1 or child_pot_id not in potential_effect_map:
                            continue
                        child_group_id = skill_to_group_map.get(child_pot_id)
                        child_levels = potential_effect_map[child_pot_id]
                        if child_group_id == 25:
                            entry["superTandem"] = {
                                "characterCondition": [lvl[0] for lvl in child_levels],
                                "description": [lvl[1] for lvl in child_levels]
                            }
                        elif child_group_id == 100:
                            entry["lastTap"] = {
                                "condition": child_levels[0][0],
                                "description": [lvl[1] for lvl in child_levels]
                            }

        elif group_id == 28:
            entry["rush"] = {
                "characterCondition": [lvl[0] for lvl in levels],
                "description": [lvl[1] for lvl in levels],
                "stats": [lvl[2] for lvl in levels]
            }

        elif group_id == 29:
            entry["superTandemBoost"] = {
                "characterCondition": [lvl[0] for lvl in levels],
                "description": [lvl[1] for lvl in levels]
            }

        elif group_id == 100:
            entry["lastTap"] = {
                "condition": levels[0][0],
                "description": [lvl[1] for lvl in levels]
            }

        # ✅ 무조건 potential은 추가
        if group_id in (25, 27, 28, 29, 100):
            # 특수 그룹 → 4번째에 description_ 들어있음
            descs = [lvl[3] for lvl in levels if len(lvl) > 3 and lvl[3] and lvl[3].strip()]
            if descs:
                potentials.append({
                    "Name": group_to_name_map.get(group_id, f"Skill {pot_id}"),
                    "description": descs
                })
        else:
            # 일반 그룹 → levels는 문자열 리스트
            descs = [lvl for lvl in levels if lvl and lvl.strip()]
            if descs:
                potentials.append({
                    "Name": group_to_name_map.get(group_id, f"Skill {pot_id}"),
                    "description": descs
                })

    if potentials:
        entry["potential"] = potentials

    if member1 != -1 and member2 != -1:
        entry["memberSkills"] = {
            "base1": member_skill_map.get(member1, f"ID {member1}"),
            "base2": member_skill_map.get(member2, f"ID {member2}")
        }
    elif member1 != -1:
        entry["memberSkills"] = {
            "base": member_skill_map.get(member1, f"ID {member1}")
        }
    if serverId in limitbreak_sailor_map:
        sailor_entry = entry.setdefault("sailor", {})
        sailor_entry.update(limitbreak_sailor_map[serverId])
    if member1 in member_skill_map:
        sailor_entry = entry.setdefault("sailor", {})
        sailor_entry.setdefault("base", member_skill_map[member1])
    if member2 in member_skill_map:
        sailor_entry = entry.setdefault("sailor", {})
        sailor_entry.setdefault("base2", member_skill_map[member2])
    if childIds and childIds != "-1":
        child_list = [int(c.strip()) for c in childIds.strip("[]").split(",")]
        specials = {}
        for i, cid in enumerate(child_list):
            aid = cursor.execute("SELECT abilityId_ FROM MstCharacter_ WHERE serverId_=?", (cid,)).fetchone()
            if aid and aid[0] in ability_map:
                specials[f"character{i+1}"] = ability_map[aid[0]]["description"]
        if abilityId in ability_map:
            specials["combined"] = ability_map[abilityId]["description"]
            entry["specialName"] = ability_map[abilityId]["name"]
        if specials:
            entry["special"] = specials
    elif abilityId in ability_map:
        entry["special"] = ability_map[abilityId]["description"]
        entry["specialName"] = ability_map[abilityId]["name"]

    if childIds and childIds != "-1":
        child_list = [int(c.strip()) for c in childIds.strip("[]").split(",")]
        sailors = {}
        for i, cid in enumerate(child_list):
            mids = cursor.execute("SELECT memberSkillId1_ FROM MstCharacter_ WHERE serverId_=?", (cid,)).fetchone()
            if mids and mids[0] in member_skill_map:
                sailors[f"character{i+1}"] = member_skill_map[mids[0]]
        if member1 in member_skill_map:
            sailors["combined"] = member_skill_map[member1]
        if member2 in member_skill_map:
            sailors["level1"] = member_skill_map[member2]
        if sailors:
            entry["sailor"] = sailors

    if changeSkillId != -1:
        swap = cursor.execute("""
            SELECT description_, superChangedescription_, superChangeInterval_
            FROM MstChangeSkill_ WHERE serverId_=?
        """, (changeSkillId,)).fetchone()
        if swap:
            base, superchg, turns = swap
            swap_obj = {}
            if base: swap_obj["base"] = replace_element_tags(base)
            if superchg:
                swap_obj["super"] = replace_element_tags(superchg)
                swap_obj["superTurns"] = turns
            entry["swap"] = swap_obj

    if serverId in support_char_map and serverId in support_desc_map:
        entry["support"] = [{
            "Characters": support_char_map[serverId],
            "description": [
                support_desc_map[serverId].get(i + 1, "")
                for i in range(5)
            ]
        }]

    if versusChildIds and versusChildIds != "-1":
        cid_list = [int(cid.strip()) for cid in versusChildIds.strip("[]").split(",")]
        vs_special = {}
        vs_conditions = []
        for i, cid in enumerate(cid_list):
            row = cursor.execute(
                "SELECT effectDescription_, versusSkillConditionId_ FROM MstVersusSkill_ WHERE serverId_=?",
                (cid,)
            ).fetchone()
            if row:
                effect_desc, cond_id = row
                vs_special[f"character{i+1}"] = replace_element_tags(effect_desc)
                if cond_id and cond_id != -1:
                    cond_row = cursor.execute(
                        "SELECT conditionDescription_ FROM MstVersusSkillCondition_ WHERE serverId_=?",
                        (cond_id,)
                    ).fetchone()
                    if cond_row and cond_row[0]:
                        vs_conditions.append(replace_element_tags(cond_row[0]))
        if vs_special:
            entry["VSSpecial"] = vs_special
        if vs_conditions:
            entry["VSCondition"] = "<br>".join(vs_conditions)

    # 🆕 superSpecial 처리
    if exceedSkillId != -1:
        row = cursor.execute("SELECT effectDescription_, conditionDescription_ FROM MstExceedCharacterTypeSkill_ WHERE serverId_=?", (exceedSkillId,)).fetchone()
        if row:
            entry["superSpecial"] = replace_element_tags(row[0])
            entry["superSpecialCriteria"] = replace_element_tags(row[1])
    elif extraSkillId != -1:
        row = cursor.execute("SELECT effectDescription_, conditionDescription_ FROM MstExtraExceedSkill_ WHERE serverId_=?", (extraSkillId,)).fetchone()
        if row:
            entry["superSpecial"] = replace_element_tags(row[0])
            entry["superSpecialCriteria"] = replace_element_tags(row[1])
    elif exceedtrademarkSkillId != -1:
        row = cursor.execute("SELECT effectDescription_, conditionDescription_ FROM MstExceedTrademarkSkill_ WHERE serverId_=?", (exceedtrademarkSkillId,)).fetchone()
        if row:
            entry["superSpecial"] = replace_element_tags(row[0])
            entry["superSpecialCriteria"] = replace_element_tags(row[1])
    if serverId in charid_to_levelbreaks:
        max_step = max(e['step'] for e in charid_to_levelbreaks[serverId])
        lLimit = [None] * max_step

        for lb in charid_to_levelbreaks[serverId]:
            step_idx = lb['step'] - 1

            # ✅ 기존 오브젝트가 있으면 꺼내오고 없으면 새로 생성
            if lLimit[step_idx] is None:
                lLimit[step_idx] = {}
            obj = lLimit[step_idx]

            # ✅ 각 타입별로 누적 추가
            if lb['type'] == "CharacterLevelLimitBreak::Skill":
                skill_id = lb['json'].get('id')
                if skill_id in ability_map:
                    obj.setdefault("special", {})
                    obj["special"]["base"] = ability_map[skill_id]["description"]

            elif lb['type'] == "CharacterLevelLimitBreak::MemberSkill":
                skill_id = lb['json'].get('id')
                number = lb['json'].get('number')
                if skill_id in member_skill_map and number:
                    sailor_level = "level2" if number == 1 else "level1"
                    obj.setdefault("sailor", {})
                    obj["sailor"][sailor_level] = member_skill_map[skill_id]

            elif lb['type'] == "CharacterLevelLimitBreak::LeaderSkill":
                skill_id = lb['json'].get('id')
                after_id = lb['json'].get('after_limit_break_id')
                if skill_id in leader_skill_map:
                    obj.setdefault("captain", {})
                    obj["captain"]["base"] = leader_skill_map[skill_id]
                    if after_id and after_id in leader_skill_map:
                        obj["captain"]["level1"] = leader_skill_map[after_id]
            elif lb['type'] == "CharacterLevelLimitBreak::PiratesPassiveSkill":
                obj["rAbility"] = True

                # ✅ base: serverId를 piratesPassiveSkillId로 바로 사용
                rows = cursor.execute("""
                    SELECT level_, description_
                    FROM MstPiratesPassiveSkillEffect_
                    WHERE piratesPassiveSkillId_ = ?
                    ORDER BY level_
                """, (serverId,)).fetchall()
                if rows:
                    if isinstance(entry.get("festAbility"), list):
                        entry["festAbility"] = {"base": entry["festAbility"]}
                    elif entry.get("festAbility") is None:
                        entry["festAbility"] = {}
                    entry["festAbility"]["base"] = [replace_element_tags(desc) for _, desc in rows]

                # ✅ llbbase: skillReplaceJson 안의 id로 사용
                skill_id = lb['json'].get('id')
                if skill_id:
                    rows = cursor.execute("""
                        SELECT level_, description_
                        FROM MstPiratesPassiveSkillEffect_
                        WHERE piratesPassiveSkillId_ = ?
                        ORDER BY level_
                    """, (skill_id,)).fetchall()
                    if rows:
                        if isinstance(entry.get("festAbility"), list):
                            entry["festAbility"] = {"base": entry["festAbility"]}
                        elif entry.get("festAbility") is None:
                            entry["festAbility"] = {}
                        
                        entry["festAbility"]["llbbase"] = [replace_element_tags(desc) for _, desc in rows]

                # =============================
                # ✅ PiratesAbility 처리
                # =============================
    # =============================
    # ✅ PiratesAbility 처리
    # =============================
            elif lb['type'] == "CharacterLevelLimitBreak::PiratesAbility":
                obj["rResilience"] = True

                # base: serverId 자체가 piratesAbilityId_
                row = cursor.execute("""
                    SELECT description_
                    FROM MstPiratesAbility_
                    WHERE serverId_ = ?
                """, (serverId,)).fetchone()
                if row and row[0]:
                    if isinstance(entry.get("festResistance"), str):
                        entry["festResistance"] = {"base": entry["festResistance"]}
                    elif entry.get("festResistance") is None:
                        entry["festResistance"] = {}
                    entry["festResistance"]["base"] = replace_element_tags(row[0])

                # llbbase: skillReplaceJson의 id
                skill_id = lb['json'].get('id')
                if skill_id:
                    row = cursor.execute("""
                        SELECT description_
                        FROM MstPiratesAbility_
                        WHERE serverId_ = ?
                    """, (skill_id,)).fetchone()
                    if row and row[0]:
                        if isinstance(entry.get("festResistance"), str):
                            entry["festResistance"] = {"base": entry["festResistance"]}
                        elif entry.get("festResistance") is None:
                            entry["festResistance"] = {}
                        entry["festResistance"]["llbbase"] = replace_element_tags(row[0])

            # =============================
            # ✅ PiratesActiveSkill 처리
            # =============================
            elif lb['type'] == "CharacterLevelLimitBreak::PiratesActiveSkill":
                obj["rSpecial"] = True

                # base: serverId
                rows = cursor.execute("""
                    SELECT level_, chargeIntervalTime_, description_
                    FROM MstPiratesActiveSkillEffect_
                    WHERE piratesActiveSkillId_ = ?
                    ORDER BY level_
                """, (serverId,)).fetchall()
                if rows:
                    if isinstance(entry.get("festSpecial"), list):
                        entry["festSpecial"] = {"base": entry["festSpecial"]}
                    elif entry.get("festSpecial") is None:
                        entry["festSpecial"] = {}
                    entry["festSpecial"]["base"] = [
                        {
                            "cooldown": cooldown,
                            "description": replace_element_tags(desc)
                        }
                        for _, cooldown, desc in rows
                    ]

                # llbbase: skillReplaceJson의 id
                skill_id = lb['json'].get('id')
                if skill_id:
                    rows = cursor.execute("""
                        SELECT level_, chargeIntervalTime_, description_
                        FROM MstPiratesActiveSkillEffect_
                        WHERE piratesActiveSkillId_ = ?
                        ORDER BY level_
                    """, (skill_id,)).fetchall()
                    if rows:
                        # ✅ 여기에 추가
                        if isinstance(entry.get("festSpecial"), list):
                            entry["festSpecial"] = {"base": entry["festSpecial"]}
                        elif entry.get("festSpecial") is None:
                            entry["festSpecial"] = {}
                        
                        entry["festSpecial"]["llbbase"] = [
                            {
                                "cooldown": cooldown,
                                "description": replace_element_tags(desc)
                            }
                            for _, cooldown, desc in rows
                        ]

            # =============================
            # ✅ PiratesSuperActiveSkill 처리
            # =============================
            elif lb['type'] == "CharacterLevelLimitBreak::PiratesSuperActiveSkill":
                obj["rSuperSpecial"] = True

                # base: serverId
                row = cursor.execute("""
                    SELECT conditionDescription_, effectDescription_
                    FROM MstPiratesSuperActiveSkill_
                    WHERE serverId_ = ?
                """, (serverId,)).fetchone()
                if row:
                    entry.setdefault("festSuperSpecial", {})
                    entry["festSuperSpecial"]["base"] = {
                        "condition": replace_element_tags(row[0]),
                        "description": replace_element_tags(row[1])
                    }

                # llbbase: skillReplaceJson의 id
                skill_id = lb['json'].get('id')
                if skill_id:
                    row = cursor.execute("""
                        SELECT conditionDescription_, effectDescription_
                        FROM MstPiratesSuperActiveSkill_
                        WHERE serverId_ = ?
                    """, (skill_id,)).fetchone()
                    if row:
                        entry.setdefault("festSuperSpecial", {})
                        entry["festSuperSpecial"]["llbbase"] = {
                            "condition": replace_element_tags(row[0]),
                            "description": replace_element_tags(row[1])
                        }  
        if any(lLimit):
            entry["lLimit"] = lLimit

            # ✅ lLimit -> 평면화해서 넣기
            for idx, stage in enumerate(lLimit):
                if not stage:
                    continue

                if "captain" in stage:
                    if not isinstance(entry.get("captain"), dict):
                        entry["captain"] = {"base": entry.get("captain")}
                    for k, v in stage["captain"].items():
                        entry["captain"][f"llb{k}"] = v

                if "sailor" in stage:
                    if not isinstance(entry.get("sailor"), dict):
                        entry["sailor"] = {"base": entry.get("sailor")}
                    for k, v in stage["sailor"].items():
                        entry["sailor"][f"llb{k}"] = v

                if "special" in stage:
                    if not isinstance(entry.get("special"), dict):
                        entry["special"] = {"base": entry.get("special")}
                    for k, v in stage["special"].items():
                        entry["special"][f"llb{k}"] = v

                                # ✅ 추가: Pirates 계열 플래그도 평면화

    result[logbookId] = entry

# JS 저장
sorted_result = dict(sorted(result.items()))
def js_object(obj, indent=0):
    IND = "  " * indent
    if obj is None:
        return "null"  # ✅ None → JS의 null
    if isinstance(obj, bool):
        return "true" if obj else "false"  # ✅ 추가!!   
    if isinstance(obj, dict):
        items = []
        for k, v in obj.items():
            k_str = str(k)
            # JS 변수명 규칙에 맞으면 따옴표 제거
            if re.match(r'^[A-Za-z_]\w*$', k_str):
                key = k_str
            elif k_str.isdigit():
                key = k_str  # 숫자 문자열이면 그냥 숫자 그대로
            else:
                key = json.dumps(k_str, ensure_ascii=False)
            items.append(f"{IND}  {key}: {js_object(v, indent + 1)}")
        return "{\n" + ",\n".join(items) + f"\n{IND}}}"
    
    elif isinstance(obj, list):
        items = [f"{IND}  {js_object(v, indent + 1)}" for v in obj]
        return "[\n" + ",\n".join(items) + f"\n{IND}]"
    
    elif isinstance(obj, str):
        return json.dumps(obj, ensure_ascii=False)
    
    else:
        return str(obj)

# 캐릭터 정보 result 생성 (여기에 실제 데이터 추출 코드 작성)
def build_new_details():
    result = {}
    # 예시: 실제로는 DB에서 읽어온 캐릭터 정보를 result[logbookId] = {...} 형태로 채워야 함
    return result
extra_js = """
    4986: {//Kung Fu Luffy
        captain: "Boosts ATK of all characters by 3.5x after the 2nd PERFECTs in a row, by 4x after the 5th PERFECTs in a row and boosts HP of all characters by 1.5x",
        special: "Deals 120x character's ATK in Typeless damage to all enemies, changes orbs of adjacent characters into Matching Orbs, boosts ATK of all characters by 1.75x for 2 turns, reduces any damage received above 5,656 HP by 97% for 2 turns and makes PERFECTs easier to hit for 2 turns",
        sailor: "Adds 3x character's ATK as Additional Damage",
        specialName: "Gum-Gum Giant Rifle: Kung Fu",
    },
    4987: {//Kung Fu Luffy
        captain: "Boosts ATK of all characters by 3.5x after the 2nd PERFECTs in a row, by 4x after the 5th PERFECTs in a row and boosts HP of all characters by 1.5x",
        special: "Deals 120x character's ATK in Typeless damage to all enemies, changes orbs of adjacent characters into Matching Orbs, boosts ATK of all characters by 1.75x for 2 turns, reduces any damage received above 5,656 HP by 97% for 2 turns and makes PERFECTs easier to hit for 2 turns",
        sailor: {
            base: "Adds 3x character's ATK as Additional Damage",
            level1: "Makes [DEX] orbs beneficial for all characters",
        },
        sailorNotes: "#{beneficial}",
        specialName: "Gum-Gum Giant Rifle: Kung Fu",
        limit: [
            { description: "Boosts base ATK by 10" },
            { description: "Boosts base ATK by 10" },
            { description: "Boosts base ATK by 10" },
            { description: "Acquire Potential 1: Critical Hit" },
            { description: "Boosts base ATK by 10" },
            { description: "Boosts base ATK by 15" },
            { description: "Boosts base RCV by 10" },
            { description: "Boosts base ATK by 15" },
            { description: "Boosts base HP by 30" },
            { description: "Boosts base HP by 30" },
            { description: "Boosts base ATK by 20" },
            { description: "Boosts base ATK by 20" },
            { description: "Boosts base HP by 35" },
            { description: "Boosts base HP by 35" },
            { description: "Acquire Potential 2: Reduce Slot Bind duration" },
            { description: "Boosts base HP by 45" },
            { description: "Boosts base HP by 45" },
            { description: "Boosts base ATK by 25" },
            { description: "Boosts base ATK by 25" },
            { description: "Boosts base HP by 55" },
            { description: "Boosts base HP by 55" },
            { description: "Boosts base RCV by 15" },
            { description: "Boosts base ATK by 30" },
            { description: "Boosts base HP by 70" },
            { description: "Boosts base RCV by 20" },
            { description: "Boosts base RCV by 25" },
            { description: "Acquire Sailor Ability 1: Makes [DEX] orbs beneficial for all characters" },
            { description: "Boosts base HP by 100" },
            { description: "Boosts base ATK by 40" },
            { description: "Acquire Potential 3: Pinch Healing" },
        ],
        potential: [
            {
                Name: "Critical Hit",
                description: [
                    "If you hit a PERFECT with this character, there is a 10% chance to deal 3% of this character's attack in extra damage",
                    "If you hit a PERFECT with this character, there is a 20% chance to deal 5% of this character's attack in extra damage",
                    "If you hit a PERFECT with this character, there is a 30% chance to deal 5% of this character's attack in extra damage",
                    "If you hit a PERFECT with this character, there is a 40% chance to deal 5% of this character's attack in extra damage",
                    "If you hit a PERFECT with this character, there is a 50% chance to deal 7% of this character's attack in extra damage"
                ]
            },
            {
                Name: "Reduce Slot Bind duration",
                description: [
                    "Reduces Slot Bind duration by 1 turn on this character",
                    "Reduces Slot Bind duration by 2 turns on this character",
                    "Reduces Slot Bind duration by 3 turns on this character",
                    "Reduces Slot Bind duration by 5 turns on this character",
                    "Reduces Slot Bind duration by 7 turns on this character"
                ]
            },
            {
                Name: "Pinch Healing",
                description: [
                    "If HP is below 40% at the start of the turn, recovers 0.75x this character's RCV at the end of the turn for each time you hit a PERFECT with this character",
                    "If HP is below 40% at the start of the turn, recovers 1x this character's RCV at the end of the turn for each time you hit a PERFECT with this character",
                    "If HP is below 40% at the start of the turn, recovers 1.25x this character's RCV at the end of the turn for each time you hit a PERFECT with this character",
                    "If HP is below 50% at the start of the turn, recovers 1.5x this character's RCV at the end of the turn for each time you hit a PERFECT with this character",
                    "If HP is below 50% at the start of the turn, recovers 2x this character's RCV at the end of the turn for each time you hit a PERFECT with this character"
                ]
            },
        ],
        support: [
            {
                Characters: "Roronoa Zoro, Nami, Usopp, Vinsmoke Sanji, Tony Tony Chopper, Nico Robin, Franky and Brook",
                description: [
                    "Once per adventure, when the supported character uses their special, makes PERFECTs slightly easier to hit for 1 turn.",
                    "Once per adventure, when the supported character uses their special, makes PERFECTs easier to hit for 1 turn.",
                    "Once per adventure, when the supported character uses their special, makes PERFECTs easier to hit for 1 turn.",
                    "Once per adventure, when the supported character uses their special, makes PERFECTs significantly easier to hit for 1 turn.",
                    "Once per adventure, when the supported character uses their special, changes orbs of adjacent characters into Matching orbs and makes PERFECTs significantly easier to hit for 1 turn."
                ]
            }
        ]
    },
    4988:{//Log Vivi
        captain: "Boosts ATK of Slasher and Striker characters by 1.5x. Boosts EXP gained by 1.25x",
        special: "Reduces crew's current HP by 90%, deals 10% of enemies' current HP in True damage to one enemy, changes [STR], [DEX], [QCK], [PSY] and [INT] orbs of top and bottom row characters into Matching orbs and boosts Orb Effects of all characters by 1.75x for 2 turns. If your Captain is a Slasher or Striker character, removes enemies' End of Turn Damage/Percent Cut Buffs duration completely",
        specialName: "Peacock String Slasher",
        sailor: "Boosts base ATK of top row characters by 60",
    },
    4989:{//Log Vivi
        captain: "Boosts ATK of Slasher and Striker characters by 1.75x and their RCV by 1.5x. Boosts EXP gained by 1.5x",
        special: "Reduces crew's current HP by 90%, deals 10% of enemies' current HP in True damage to one enemy, changes [STR], [DEX], [QCK], [PSY] and [INT] orbs of top and bottom row characters into Matching orbs and boosts Orb Effects of all characters by 1.75x for 2 turns. If your Captain is a Slasher or Striker character, removes enemies' End of Turn Damage/Percent Cut Buffs duration completely",
        specialName: "Peacock String Slasher",
        sailor: "Boosts base ATK of top row characters by 60",
    },
    4990:{//Log Ace
        captain: "Boosts ATK of Free Spirit and Powerhouse characters by 1.5x. Boosts Beli gained by 1.5x",
        special: "Reduces crew's current HP to 1, removes Poison duration completely, reduces Paralysis, Bind and Special Bind duration by 4 turns, recovers 7,000 HP at the end of the turn for 1 turn and changes [EMPTY], [BLOCK] and [BOMB] orbs into Matching orbs. If your Captain is a Free Spirit or Powerhouse character, reduces enemies' Threshold Damage Reduction duration by 5 turns.",
        specialName: "Flame Fence",
        sailor: "Reduces Special Bind duration by 3 turns on this character",
    },
    4991:{//Log Ace
        captain: "Boosts ATK of Free Spirit and Powerhouse characters by 1.75x and their HP by 1.5x. Boosts Beli gained by 2.5x",
        special: "Reduces crew's current HP to 1, removes Poison duration completely, reduces Paralysis, Bind and Special Bind duration by 4 turns, recovers 7,000 HP at the end of the turn for 1 turn and changes [EMPTY], [BLOCK] and [BOMB] orbs into Matching orbs. If your Captain is a Free Spirit or Powerhouse character, reduces enemies' Threshold Damage Reduction duration by 5 turns.",
        specialName: "Flame Fence",
        sailor: "Reduces Special Bind duration by 3 turns on this character",
    },
    4992: {//Pudding
        captain: "Boosts ATK of Cerebral characters by 1.75x",
        special: "Recovers 7,000 HP, reduces ATK DOWN duration by 5 turns and reduces enemies' Resilience Buffs duration by 5 turns and changes orbs of adjacent characters into Matching Orbs",
        specialName: "Eyes Hiding Shyness",
        sailor: "Reduces Paralysis duration by 1 turn",
    },
    4993: {//Pudding
        captain: "Boosts ATK of Cerebral characters by 2.25x and their RCV by 1.2x",
        special: "Recovers 7,000 HP, reduces ATK DOWN duration by 5 turns and reduces enemies' Resilience Buffs duration by 5 turns and changes orbs of adjacent characters into Matching Orbs",
        specialName: "Eyes Hiding Shyness",
        sailor: "Reduces Paralysis duration by 1 turn",
    },
    4994: {//EX Coby
        captain: "Boosts ATK of Fighter characters by 1.5x, reduces damage received by 0%-10% depending on the crew's current HP",
        specialName: "Pleading at the Risk of One's Life [EX]",
        special: "Locks all orbs for 1 turn and changes orbs of adjacent characters into [STR] orbs. If the special is activated with more than 50% health remaining, protects from defeat for 1 turn",
        specialNotes: "#{zombie}",
        sailor: "Boosts base ATK, HP and RCV of all characters by 50",
    },
    4995: {//EX Coby
        captain: "Boosts ATK of Fighter characters by 2x, reduces damage received by 0%-30% depending on the crew's current HP",
        specialName: "Pleading at the Risk of One's Life [EX]",
        special: "Locks all orbs for 1 turn and changes orbs of adjacent characters into [STR] orbs. If the special is activated with more than 50% health remaining, protects from defeat for 1 turn",
        specialNotes: "#{zombie}",
        sailor: {
            base: "Boosts base ATK, HP and RCV of all characters by 50",
            level1: "If this character has an [STR] orb and you hit a PERFECT with him, keep his [STR] orb for the next turn",
        },
        limit: [
            { description: "Boosts base HP by 10" },
            { description: "Boosts base HP by 20" },
            { description: "Boosts base ATK by 20" },
            { description: "Acquire Potential 1: [DEX] Damage Reduction" },
            { description: "Boosts base HP by 20" },
            { description: "Boosts base RCV by 10" },
            { description: "Boosts base HP by 30" },
            { description: "Boosts base ATK by 30" },
            { description: "Boosts base HP by 40" },
            { description: "Reduce base Special Cooldown by 1 turn" },
            { description: "Boosts base ATK by 35" },
            { description: "Boosts base RCV by 10" },
            { description: "Boosts base ATK by 40" },
            { description: "Acquire Sailor Ability 2: If this character has an [STR] orb and you hit a PERFECT with him, keep his [STR] orb for the next turn" },
            { description: "Acquire Potential 2: Reduce No Healing duration" },
        ],
        potential: [
            {
                Name: "[DEX] Damage Reduction",
                description: [
                    "Reduces damage taken from [DEX] characters by 1%",
                    "Reduces damage taken from [DEX] characters by 2%",
                    "Reduces damage taken from [DEX] characters by 3%",
                    "Reduces damage taken from [DEX] characters by 4%",
                    "Reduces damage taken from [DEX] characters by 6%"
                ]
            },
            {
                Name: "Reduce No Healing duration",
                description: [
                    "Reduces No Healing duration by 1 turn",
                    "Reduces No Healing duration by 3 turns",
                    "Reduces No Healing duration by 5 turns",
                    "Reduces No Healing duration by 7 turns",
                    "Reduces No Healing duration by 10 turns"
                ]
            },
        ],
        support: [
            {
                Characters: "[STR] characters",
                description: [
                    "Adds 1% of this character's base ATK, HP and RCV to the supported character's base ATK, HP and RCV.",
                    "Adds 2% of this character's base ATK, HP and RCV to the supported character's base ATK, HP and RCV.",
                    "Adds 3% of this character's base ATK, HP and RCV to the supported character's base ATK, HP and RCV.",
                    "Adds 4% of this character's base ATK, HP and RCV to the supported character's base ATK, HP and RCV.",
                    "Adds 6% of this character's base ATK, HP and RCV to the supported character's base ATK, HP and RCV."
                ]
            }
        ]
    },
    4996: {//EX Helmeppo
        special: "Reduces Bind duration by 3 turns",
        specialName: "Tempered Kukris [EX]",
        captain: "Boosts ATK and HP of Driven characters by 1.5x",
        support: [
            {
                Characters: "Coby",
                description: [
                    "Once per adventure, when the supported character uses an Orb Locking special, changes [BLOCK] orbs of the supported character into a Matching orb.",
                    "Once per adventure, when the supported character uses an Orb Locking special, changes [BLOCK] orbs of the supported character into a Matching orb.",
                    "Once per adventure, when the supported character uses an Orb Locking special, changes [BLOCK] orbs of all characters into Matching orbs.",
                    "Once per adventure, when the supported character uses an Orb Locking special, changes [BLOCK] orbs of all characters into Matching orbs.",
                    "Once per adventure, when the supported character uses an Orb Locking special, changes [BLOCK] orbs of all characters into Matching orbs. Removes enemies' End of Turn Damage/Percent Cut duration completely."
                ]
            }
        ]
    },
};
var calcGhostStartID = {start: 10000, increment: 0};

if (UnitUtils){
    UnitUtils.extendDouble(calcGhostStartID, 1983, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 1984, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 1985, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2000, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2180, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2181, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2399, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2417, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2418, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2445, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2446, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2468, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2469, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2516, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2517, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2531, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2532, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2533, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2534, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2535, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2536, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2537, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2538, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2539, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2540, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2541, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2542, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2543, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2544, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2549, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2550, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2551, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2552, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2556, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2557, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2560, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2561, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2576, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2577, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2600, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2601, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2602, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2603, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2618, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2795, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2801, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2802, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2818, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2819, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2831, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2834, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2835, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2850, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2859, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2860, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2861, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2862, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2863, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2864, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2865, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2866, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2867, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2894, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2895, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2919, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 2999, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3060, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3064, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3065, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3098, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3134, "vs");
    UnitUtils.extendDouble(calcGhostStartID, 3135, "vs");
    UnitUtils.extendDouble(calcGhostStartID, 3163, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3164, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3165, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3166, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3203, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3204, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3252, "vs");
    UnitUtils.extendDouble(calcGhostStartID, 3253, "vs");
    UnitUtils.extendDouble(calcGhostStartID, 3279, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3280, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3299, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3300, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3330, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3331, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3346, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3348, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3349, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3354, "vs");
    UnitUtils.extendDouble(calcGhostStartID, 3355, "vs");
    UnitUtils.extendDouble(calcGhostStartID, 3432, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3433, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3492, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3493, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3494, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3495, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3507, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3508, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3512, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3513, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3514, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3515, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3542, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3543, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3554, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3555, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3573, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3574, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3610, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3611, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3707, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3708, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3787, "vs");
    UnitUtils.extendDouble(calcGhostStartID, 3788, "vs");
    UnitUtils.extendDouble(calcGhostStartID, 3810, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3811, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3828, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3845, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3868, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3877, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3878, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3879, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3880, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3902, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3907, "vs");
    UnitUtils.extendDouble(calcGhostStartID, 3908, "vs");
    UnitUtils.extendDouble(calcGhostStartID, 3909, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3910, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3916, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3917, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3920, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3921, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3922, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3923, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3924, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3932, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3933, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3940, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3969, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3970, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3971, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3989, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3994, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 3995, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 4002, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 4003, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 4059, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 4060, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 4061, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 4062, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 4118, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 4121, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 4122, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 4123, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 4124, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 4140, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 4141, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 4142, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 4210, "vs");
    UnitUtils.extendDouble(calcGhostStartID, 4211, "vs");
    UnitUtils.extendDouble(calcGhostStartID, 4218, "vs");
    UnitUtils.extendDouble(calcGhostStartID, 4219, "vs");
    UnitUtils.extendDouble(calcGhostStartID, 4227, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 4230, "vs");
    UnitUtils.extendDouble(calcGhostStartID, 4231, "vs");
    UnitUtils.extendDouble(calcGhostStartID, 4257, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 4267, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 4268, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 4275, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 4276, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 4287, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 4289, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 4293, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 4307, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 4308, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 4319, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 4322, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 4323, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 4348, "dual");
    UnitUtils.extendDouble(calcGhostStartID, 4350, "dual");
}
"""



# 저장 (JS용)
main_js = js_object(sorted_result)
if main_js.endswith("}"):
    main_js = main_js[:-1]

with open("./data/details_kor.js", "w", encoding="utf-8") as f:
    f.write("window.details_kor = ")
    f.write(main_js)
    f.write(",")
    f.write(extra_js.strip() + ";")

print("✅ details.js 병합 완료 (기존 + 신규 포함, JS 포맷 저장)")
