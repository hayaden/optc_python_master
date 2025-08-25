import sqlite3
import json
import os
from datetime import datetime

# ✅ 기준 날짜 (이후 insert된 것만 대상)
DATE_AFTER = "2025-08-20"
DB_PATH = "./data/sakura_ko.db"
OUTPUT_DIR = f"./output/inserted_after_{DATE_AFTER.replace('-', '')}"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ✅ 날짜 → 유닉스 타임스탬프
def to_timestamp(date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return int(dt.timestamp())

cutoff_ts = to_timestamp(DATE_AFTER)

# ✅ DB 연결
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# ✅ 모든 테이블 목록 조회
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
all_tables = [row[0] for row in cursor.fetchall()]

# ✅ insertTimestamp_ 컬럼이 있는 테이블만 처리
for table in all_tables:
    try:
        # 컬럼 목록 확인
        cursor.execute(f"PRAGMA table_info({table})")
        columns_info = cursor.fetchall()
        columns = [col[1] for col in columns_info]

        # insertTimestamp_ 없는 테이블은 skip
        if "insertTimestamp_" not in columns:
            continue

        # 데이터 조회
        cursor.execute(f"""
            SELECT * FROM {table}
            WHERE insertTimestamp_ > ?
            ORDER BY insertTimestamp_ DESC
        """, (cutoff_ts,))
        rows = cursor.fetchall()

        if not rows:
            print(f"ℹ️ {table}: 해당 날짜 이후 데이터 없음")
            continue

        # JSON 저장
        data = [dict(zip(columns, row)) for row in rows]
        with open(os.path.join(OUTPUT_DIR, f"{table}.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"✅ {table}: {len(data)}건 저장 완료")

    except Exception as e:
        print(f"❌ {table} 처리 중 오류: {e}")

conn.close()
