import sqlite3
import pandas as pd

# DB 경로
DB_PATH = "./data/sakura_ko.db"  # 경로 맞게 수정

# 추출할 테이블명
TABLE_NAME = "MstRunGamePlacement_"
TABLE_NAME = "MstRunGamePart_"
# SQLite 연결
conn = sqlite3.connect(DB_PATH)

# Pandas로 테이블 읽기
df = pd.read_sql_query(f"SELECT * FROM {TABLE_NAME}", conn)

# CSV 저장 (인덱스 없이, UTF-8 인코딩)
df.to_csv(f"{TABLE_NAME}.csv", index=False, encoding="utf-8-sig")

conn.close()

print(f"✅ {TABLE_NAME}.csv 로 저장 완료!")
