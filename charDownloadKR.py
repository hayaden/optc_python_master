from src.auth import register_user, login_user
from database import check_resources
import os
import requests
import json
import sqlite3
import src.config as config
import src.cryption as cryption
import sys

# ✅ 모든 작업파일을 저장할 폴더
DATA_DIR = "./data"
ROOT_DIR = "./data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)


### 1️⃣ 리소스 리스트 필터
def filter_resource_list(json_path, id_range=None, id_list=None):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    resources = data["resources"]
    result = []

    for res in resources:
        cid = res.get('content_id')
        rtype = res.get('type')

        if cid is None or rtype != "character":
            continue

        if id_range and (id_range[0] <= cid <= id_range[1]):
            result.append(res)
        elif id_list and cid in id_list:
            result.append(res)
    return result


### 2️⃣ 리소스 목록 JSON 복호화
def download_and_save_resource_file(database_url):
    try:
        filename = database_url.split("/")[-1]
        local_path = os.path.join(DATA_DIR, filename)
        
        response = requests.get(database_url)
        if response.status_code == 200:
            with open(local_path, "wb") as resource:
                resource.write(response.content)

            fixed_key = cryption.create_from_key("J6oxF6iN")
            decrypted_filename = cryption.nty_decryptor(
                fixed_key,
                local_path,
                ".json",
                True
            )

            if decrypted_filename and os.path.exists(decrypted_filename):
                target_name = os.path.join(DATA_DIR, "original_resource_list.json")
                if os.path.exists(target_name):
                    os.remove(target_name)
                os.rename(decrypted_filename, target_name)
                print(f"✅ 복호화 완료 및 저장: {target_name}")
                return target_name
            else:
                print("❌ 복호화 실패 또는 파일 없음")
                return None
        else:
            print(f"❌ 다운로드 실패: {filename} (status {response.status_code})")
            return None
    except Exception as e:
        print(f"❌ Error in download_and_save_resource_file: {e}")
        return None


### 3️⃣ DB에서 logbookId 조회
def get_logbook_id_from_db(server_id, db_path=os.path.join(ROOT_DIR, "sakura_ko.db")):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT logbookId_ FROM MstCharacter_ WHERE serverId_=?", (server_id,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception as e:
        print(f"❌ DB Error: {e}")
        return None


### 4️⃣ 이미지 리네임
def rename_image_to_logbookid(original_file, logbook_id):
    new_name = os.path.join(DATA_DIR, f"{logbook_id}.png")
    if os.path.exists(original_file):
        # ✅ 덮어쓰기 허용: 이미 대상 이름이 있으면 먼저 삭제
        if os.path.exists(new_name):
            os.remove(new_name)
            print(f"⚠️ 기존 파일 삭제(덮어쓰기): {new_name}")
        os.rename(original_file, new_name)
        print(f"✅ {original_file} → {new_name}")
    else:
        print(f"❌ File not found: {original_file}")  


### 5️⃣ 개별 nty 다운로드+복호화
def download_and_decrypt_nty(url):
    try:
        filename = url.split('/')[-1]
        name = filename.split("-")[0] + ".nty"
        local_nty = os.path.join(DATA_DIR, name)

        response = requests.get(url)
        if response.status_code == 200:
            with open(local_nty, 'wb') as file:
                file.write(response.content)
                file.flush()
                os.fsync(file.fileno())  

            k = cryption.create_from_key("J6oxF6iN")
            decrypted_file = cryption.nty_decryptor(k, local_nty,None, False)

            if decrypted_file:
                return os.path.join(DATA_DIR, os.path.basename(decrypted_file))
            else:
                return None
        else:
            print(f"❌ Failed to download the file {name}.")
            return None
    except Exception as e:
        print(f"❌ Error in download_and_decrypt_nty: {e}")
        return None


### 6️⃣ 전체 파이프라인
def process_all_images(resource_list_path, id_range=None, id_list=None, db_path=os.path.join(ROOT_DIR, "sakura_ko.db")):
    targets = filter_resource_list(resource_list_path, id_range, id_list)
    print(f"\n⭐ 총 {len(targets)}개의 리소스가 선택되었습니다.\n")

    for res in targets:
        url = f"{res['url']}/{res['name']}"
        server_id = res['content_id']
        print(f"⬇️ Download & Decrypt: serverId={server_id}")

        img_file = download_and_decrypt_nty(url)
        if img_file:
            logbook_id = get_logbook_id_from_db(server_id, db_path)
            if logbook_id:
                rename_image_to_logbookid(img_file, logbook_id)
            else:
                print(f"❌ logbookId not found in DB for serverId={server_id}")
        print("-" * 40)


### ✅ 메인 진입점
def main(id_range=(14500, 14501)):
    lang = 'ko'
    register_user(language=lang)
    login_user(language=lang)
    database_url, version = check_resources()
    if not database_url:
        return

    decrypted_filename = download_and_save_resource_file(database_url)
    if not decrypted_filename:
        return

    process_all_images(
        decrypted_filename,
        id_range=id_range
  #     id_list=[1020, 1050, 1100]       
    )
    if os.path.exists(decrypted_filename):
        os.remove(decrypted_filename)
        print(f"🗑️ 리소스 리스트 파일 삭제 완료: {decrypted_filename}")
    nty_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.nty')]
    for f in nty_files:
        file_path = os.path.join(DATA_DIR, f)
        os.remove(file_path)
        print(f"🗑️ nty 파일 삭제 완료: {file_path}")
if __name__ == "__main__":
    if len(sys.argv) == 3:
        id_start = int(sys.argv[1])
        id_end = int(sys.argv[2])
        id_range = (id_start, id_end)
    else:
        id_range = (14500, 14501)  # 기본값

    main(id_range=id_range)
