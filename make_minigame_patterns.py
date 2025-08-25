# make_minigame_patterns_sequence.py
# -*- coding: utf-8 -*-
import os
import json
import pandas as pd
from PIL import Image, ImageDraw

# ===== 경로(고정) =====
PLACEMENT_CSV = "./table/MstRunGamePlacement_.csv"  # id_, serverId_, category_, runGamePartGroupIdsJson_
PART_CSV      = "./table/MstRunGamePart_.csv"       # id_, serverId_, groupId_, positionX_, positionY_, objectType_
IMG_DIR       = "./img/minigame"
OUT_DIR       = "./patterns"
os.makedirs(OUT_DIR, exist_ok=True)

# ===== 필수 컬럼 =====
REQ_PLACEMENT_COLS = ["id_", "serverId_", "category_", "runGamePartGroupIdsJson_"]
REQ_PART_COLS      = ["id_", "serverId_", "groupId_", "positionX_", "positionY_", "objectType_"]

# ===== 옵션 =====
MIN_COLS        = 19                   # 최소 가로칸
BLANK_GROUP_IDS = {1}                  # 빈칸으로 취급
PRIORITY_ITEMS  = [5, 4, 3]            # 상자>고기>베리

# ===== 렌더 설정 =====
TILE_SIZE = 48
TILE_GAP  = 4
PADDING_X = 16
PADDING_Y = 16
ROW_GAP_Y = 6
HEADER_H  = 28
LABEL_W   = 0

GREEN_L   = (46,160,105,255)   # 1층
GREEN_M   = (36,130, 85,255)   # 2층
GREEN_D   = (24,100, 70,255)   # 3층
TRAP_GRAY = (60, 65, 72,255)   # 함정
BORDER    = (25, 30, 35,255)
BG        = (15, 20, 26,  0)
TEXT      = (235,240,245,255)

ICON_MAP = {3:"berry.png", 4:"meat.png", 5:"chest.png"}
_icon_cache = {}

# ===== 유틸 =====
def load_icon_path(path: str):
    if not path or not os.path.exists(path): return None
    if path in _icon_cache: return _icon_cache[path]
    try:
        img = Image.open(path).convert("RGBA")
        _icon_cache[path] = img
        return img
    except Exception:
        return None

def paste_icon(img, draw, path, col, row_idx, tile_pos_fn, scale=0.85):
    icon = load_icon_path(path)
    if icon is None: return
    x0, y0 = tile_pos_fn(col, row_idx)
    w = h = int(TILE_SIZE * scale)
    icon_r = icon.resize((w, h), Image.LANCZOS)
    img.paste(icon_r, (x0 + (TILE_SIZE - w)//2, y0 + (TILE_SIZE - h)//2), icon_r)

def parse_group_ids_json(txt):
    if pd.isna(txt): return []
    s = str(txt).strip()
    try:
        arr = json.loads(s)
        if isinstance(arr, list):
            out = []
            for v in arr:
                try: out.append(int(v))
                except:
                    num = "".join(ch for ch in str(v) if ch.isdigit())
                    if num: out.append(int(num))
            return out
    except Exception:
        pass
    s2 = s.strip("[] ").replace("'", "").replace('"', "")
    if not s2: return []
    out = []
    for t in s2.split(","):
        t = t.strip()
        if not t: continue
        try: out.append(int(t))
        except:
            num = "".join(ch for ch in t if ch.isdigit())
            if num: out.append(int(num))
    return out

def floor_to_row_index(posy: int) -> int:
    if posy == 3: return 0
    if posy == 2: return 1
    return 2   # 1층(혹은 기타)

def get_group_icon_path(gid):
    gid_str = str(gid)
    cands = []
    for ext in (".PNG",".png",".WebP",".webp"):
        cands.append(os.path.join(IMG_DIR, f"{gid_str}{ext}"))
    enemy_dir = os.path.join(IMG_DIR, "enemy")
    for ext in (".PNG",".png",".WebP",".webp"):
        cands.append(os.path.join(enemy_dir, f"{gid_str}{ext}"))
    for p in cands:
        if os.path.exists(p): return p
    return None

# ===== 시퀀스 → 열 계획 =====
# over 항목 형태: (gid, floor_override, item_type_override or None, offset_override or None)
# - trap2 그룹인 경우: 같은 그룹의 아이템 행을 읽어 positionX_==1/2/3 → offset 0/1/2 칸에 해당 층에 그 아이템 타입으로 배치
# - 일반 그룹은 (gid, None, None, None) 1개
def build_columns_plan(seq, group_to_rows):
    columns = []
    idx = 0
    n = len(seq)

    while idx < n:
        gid = seq[idx]
        rows = group_to_rows.get(gid, [])
        has_trap2 = any(int(r["t"]) == 2 for r in rows)

        if has_trap2:
            # 3칸 예약
            c_start = len(columns)
            for _ in range(3):
                columns.append({"trap2": True, "trap1": False, "over": []})

            # 같은 그룹의 아이템 행만 사용: positionX_(1/2/3) → 좌/중/우
            items = [r for r in rows if int(r["t"]) in (3,4,5)]
            # 지정이 없거나 범위 밖이면 '중간(2)'로 보정
            for r in items:
                try:
                    loc = int(pd.to_numeric(r["x"], errors="coerce"))
                except Exception:
                    loc = 2
                if loc not in (1,2,3): loc = 2
                offset = loc - 1  # 0/1/2
                floor_idx = floor_to_row_index(int(r["y"]))
                t = int(r["t"])
                columns[c_start + offset]["over"].append((gid, floor_idx, t, offset))

            # 함정2 자신만 소비 (뒤 요소는 그대로)
            idx += 1
            continue

        # 일반 그룹
        if gid in BLANK_GROUP_IDS:
            columns.append({"trap2": False, "trap1": False, "over": []})
        else:
            has_trap1 = any(int(r["t"]) == 1 for r in rows)
            columns.append({"trap2": False, "trap1": has_trap1, "over": [(gid, None, None, None)]})
        idx += 1

    return columns

# ===== 렌더 =====
def render_pattern_sequence(pattern_info, columns, group_to_rows, out_path):
    width_cols = max(MIN_COLS, len(columns))

    rows = 4
    inner_w = LABEL_W + PADDING_X + width_cols*TILE_SIZE + max(width_cols-1,0)*TILE_GAP
    inner_h = rows*TILE_SIZE + (rows-1)*ROW_GAP_Y
    W = PADDING_X + inner_w + PADDING_X
    H = PADDING_Y + HEADER_H + inner_h + PADDING_Y

    img = Image.new("RGBA", (W, H), BG)
    d = ImageDraw.Draw(img)

    title = f"server:{pattern_info.get('serverId_', '?')} / category:{pattern_info.get('category_', '?')} / patternId:{pattern_info.get('id_', '?')}"
    d.text((PADDING_X, PADDING_Y), title, fill=TEXT)

    def row_bg_color(i): return [GREEN_D, GREEN_M, GREEN_L, None][i]
    grid_x0 = PADDING_X
    grid_y0 = PADDING_Y + HEADER_H

    for row_i in range(4):
        y = grid_y0 + row_i*(TILE_SIZE+ROW_GAP_Y)
        x = grid_x0 + PADDING_X
        fcol = row_bg_color(row_i)
        for _ in range(width_cols):
            if fcol is not None:
                d.rounded_rectangle([(x,y),(x+TILE_SIZE,y+TILE_SIZE)],
                                    radius=8, fill=fcol, outline=BORDER, width=1)
            x += TILE_SIZE + TILE_GAP

    def tile_pos(col, row_idx):
        y = grid_y0 + row_idx*(TILE_SIZE+ROW_GAP_Y)
        x = grid_x0 + PADDING_X + col*(TILE_SIZE+TILE_GAP)
        return x, y

    def draw_trap(col_start, length=1):
        x0, y0 = tile_pos(col_start, 3)
        for i in range(length):
            xx = x0 + i*(TILE_SIZE+TILE_GAP)
            d.rounded_rectangle([(xx,y0),(xx+TILE_SIZE,y0+TILE_SIZE)],
                                radius=8, fill=TRAP_GRAY, outline=BORDER, width=1)

    # 1) 함정 타일 칠하기
    col = 0
    while col < len(columns):
        c = columns[col]
        if c["trap2"]:
            start = col
            while col < len(columns) and columns[col]["trap2"]:
                col += 1
            end = col - 1
            draw_trap(start, end-start+1)
            continue
        else:
            if c.get("trap1", False):
                draw_trap(col, 1)
        col += 1

    # 2) 아이콘/적 배치
    for col, c in enumerate(columns):
        if not c["over"]:
            continue

        # 아이템(층별 1개)
        chosen_items = {}  # floor -> icon_path

        # (A) trap2에서 온 "정확한 위치/층/타입" 오버레이 먼저
        forced_entries = [(gid, fi, t) for (gid, fi, t, off) in c["over"] if fi is not None and t in (3,4,5)]
        for gid, fi, t in forced_entries:
            if fi in chosen_items:
                # 충돌 시 우선순위(상자>고기>베리)
                curr = [k for k,v in ICON_MAP.items() if v.endswith(os.path.basename(chosen_items[fi]))]
                curr_t = curr[0] if curr else -1
                if PRIORITY_ITEMS.index(t) < PRIORITY_ITEMS.index(curr_t):
                    chosen_items[fi] = os.path.join(IMG_DIR, ICON_MAP[t])
            else:
                chosen_items[fi] = os.path.join(IMG_DIR, ICON_MAP[t])

        # (B) 일반 오버레이(gid만) → 아이템 자동 선택
        normals = [(gid, fi, t) for (gid, fi, t, off) in c["over"] if fi is None]
        for gid, _, _ in normals:
            rows = group_to_rows.get(gid, [])
            for prio_t in PRIORITY_ITEMS:
                for r in rows:
                    if int(r["t"]) != prio_t: continue
                    fi = floor_to_row_index(int(r["y"]))
                    if fi not in chosen_items:
                        chosen_items[fi] = os.path.join(IMG_DIR, ICON_MAP[prio_t])

        # 아이템 붙이기
        for fi, icon_path in chosen_items.items():
            paste_icon(img, d, icon_path, col, fi, tile_pos)

        # 적(같은 칸 같은 gid 1회, 높은 층 우선)
        used_floors = set(chosen_items.keys())
        placed_gids = set()
        for (gid, fi_override, t_override, off_override) in c["over"]:
            if gid in placed_gids: continue
            group_icon = get_group_icon_path(gid)
            if not group_icon:
                placed_gids.add(gid); continue
            rows = group_to_rows.get(gid, [])
            enemy_floors = sorted(
                [floor_to_row_index(int(r["y"])) for r in rows if int(r["t"]) not in (1,2,3,4,5)],
                reverse=True
            )
            target_floor = None
            for fi in enemy_floors:
                if fi not in used_floors:
                    target_floor = fi; break
            if target_floor is not None:
                paste_icon(img, d, group_icon, col, target_floor, tile_pos, scale=0.95)
                used_floors.add(target_floor)
            placed_gids.add(gid)

    img.save(out_path)

# ===== 메인 =====
def main():
    dfP = pd.read_csv(PLACEMENT_CSV, encoding="utf-8")
    dfG = pd.read_csv(PART_CSV,      encoding="utf-8")

    for c in REQ_PLACEMENT_COLS:
        if c not in dfP.columns:
            raise KeyError(f"[Placement] 컬럼 누락: {c} / 실제: {list(dfP.columns)}")
    for c in REQ_PART_COLS:
        if c not in dfG.columns:
            raise KeyError(f"[Part] 컬럼 누락: {c} / 실제: {list(dfG.columns)}")

    # groupId → 행 목록(우리가 쓰는 키만 리매핑)
    group_to_rows = {}
    for _, r in dfG.iterrows():
        gid = int(pd.to_numeric(r["groupId_"],   errors="coerce"))
        x   = int(pd.to_numeric(r["positionX_"], errors="coerce"))
        y   = int(pd.to_numeric(r["positionY_"], errors="coerce"))
        t   = int(pd.to_numeric(r["objectType_"],errors="coerce"))
        group_to_rows.setdefault(gid, []).append({"x": x, "y": y, "t": t})

    made = 0
    for _, pr in dfP.iterrows():
        seq = parse_group_ids_json(pr["runGamePartGroupIdsJson_"])
        if not seq: continue

        columns = build_columns_plan(seq, group_to_rows)

        pid = pr.get("id_", None); sid = pr.get("serverId_", None); cat = pr.get("category_", None)
        out_path = os.path.join(OUT_DIR, f"pattern_id_{pid}__server_{sid}__cat_{cat}.png")
        pattern_info = {"id_": pid, "serverId_": sid, "category_": cat}
        render_pattern_sequence(pattern_info, columns, group_to_rows, out_path)
        made += 1

    print(f"✅ 생성 완료: {made}개 → {OUT_DIR}  (시퀀스 모드 / 함정2=3칸+positionX_ 정렬)")

if __name__ == "__main__":
    main()
