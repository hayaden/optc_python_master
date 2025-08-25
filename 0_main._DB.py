import subprocess
import os

# 공통 범위 설정
id_range = (30030, 30030)

# ✅ data 폴더 없으면 생성
if not os.path.exists("data"):
    os.makedirs("data")
    print("📁 'data' 폴더 생성 완료")

# 0. 사쿠라 DB 다운로드
subprocess.run(["python", "download_SakuraDB.py"], check=True)

# 1. 상세정보 JS 추출
subprocess.run(["python", "SakuraToDetails_kor.py"], check=True)

# 2. 유닛 목록 JS 추출
subprocess.run(["python", "SakuraToUnits.py"], check=True)

# 3. 태그 정보 JS 추출
subprocess.run(["python", "SakuraToTags_child.py"], check=True)

# 4. 캐릭터 이미지 다운로드 (id_range 인자 전달)
subprocess.run(["python", "charDownloadKR.py", str(id_range[0]), str(id_range[1])], check=True)

# 5. 캐릭터 얼굴 이미지 다운로드 (num_range 인자 전달)
subprocess.run(["python", "charfaceDownloadKR.py", str(id_range[0]), str(id_range[1])], check=True)
