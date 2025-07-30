import os
import json
import re
import requests
import base64
import sys
import src.cryption as cryption
from src.auth import register_user, login_user
from database import check_resources
from charDownloadKR import download_and_save_resource_file

### ✅ 경로 설정
DATA_DIR = "./data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

resource_list_file = os.path.join(DATA_DIR, "original_resource_list.json")


################################################
# 1️⃣ 리소스 리스트에서 character_face 범위 필터
################################################
def filter_character_face_by_range(json_path, num_range):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    resources = data["resources"]
    result = []

    for res in resources:
        if res.get('type') != "character_face":
            continue

        name = res.get('name')
        if not name:
            continue

        # ✅ 이름에서 범위 추출 ex) character_face_9000_9099-0.nty
        match = re.search(r'character_face_(\d+)_(\d+)-', name)
        if not match:
            continue

        start = int(match.group(1))
        end = int(match.group(2))

        # ✅ 사용자가 지정한 범위와 교집합이 있으면 추가
        if end < num_range[0]:
            continue
        if start > num_range[1]:
            continue

        result.append(res)

    return result


################################################
# 2️⃣ 개별 .nty 다운로드 + 복호화
################################################
def download_and_decrypt_nty(url):
    try:
        filename = url.split('/')[-1]
        local_nty = os.path.join(DATA_DIR, filename)

        response = requests.get(url)
        if response.status_code == 200:
            with open(local_nty, 'wb') as file:
                file.write(response.content)
                file.flush()
                os.fsync(file.fileno())

            print(f"✅ 다운로드 완료: {filename}")

            # ✅ 복호화
            k = cryption.create_from_key("J6oxF6iN")
            SIGNATURE_HEX = "93E35661A79183D17B2A3F3B99B78A22"
            decrypted_file = cryption.nty_decryptor_multi(k, local_nty, SIGNATURE_HEX, False)

            if decrypted_file:
                print(f"✅ 복호화 완료: {decrypted_file}")
                return os.path.join(".", decrypted_file)
            else:
                print(f"❌ 복호화 실패: {filename}")
                return None
        else:
            print(f"❌ 다운로드 실패: {filename} (HTTP {response.status_code})")
            return None
    except Exception as e:
        print(f"❌ Error in download_and_decrypt_nty: {e}")
        return None


################################################
# 3️⃣ JSON → 이미지 여러장 추출
################################################
def extract_images_from_json(json_file, output_folder):
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if "images" not in data:
            print(f"⚠️ images 키가 없음 → 단일 이미지일 수도 있음: {json_file}")
            return False

        for img in data["images"]:
            name = img.get("name")
            b64data = img.get("data")
            if not name or not b64data:
                continue

            out_path = os.path.join(output_folder, name)
            with open(out_path, 'wb') as out_file:
                out_file.write(base64.b64decode(b64data))

            print(f"✅ 이미지 저장 완료: {out_path}")

        return True

    except Exception as e:
        print(f"❌ Error in extract_images_from_json: {e}")
        return False


################################################
# 4️⃣ 단일 이미지 저장
################################################
def save_single_image_file(decrypted_file, target_name):
    new_path = os.path.join(DATA_DIR, target_name)
    if os.path.exists(new_path):
        os.remove(new_path)
    os.rename(decrypted_file, new_path)
    print(f"✅ 단일 이미지 저장 완료: {new_path}")


################################################
# 5️⃣ 전체 파이프라인
################################################
def process_character_face_all(resource_list_path, num_range):
    targets = filter_character_face_by_range(resource_list_path, num_range)
    print(f"\n⭐ 총 {len(targets)}개의 character_face 리소스가 선택되었습니다.\n")

    for res in targets:
        url = f"{res['url']}/{res['name']}"
        print(f"\n⬇️ Download & Decrypt: {res['name']}")

        decrypted_file = download_and_decrypt_nty(url)
        if not decrypted_file:
            continue

        print("-" * 40)


################################################
# ✅ 메인 진입점
################################################
def main(num_range=(14501, 14505)):
    # ✅ 리소스 리스트 없으면 먼저 다운로드 & 복호화
    if not os.path.exists(resource_list_file):
        print(f"⚠️ 리소스 리스트가 없어 서버에서 다운로드를 시작합니다!")
        lang = 'ko'
        register_user(language=lang)
        login_user(language=lang)
        database_url, version = check_resources()
        if not database_url:
            print("❌ 리소스 URL을 못 가져옴.")
            return
        download_and_save_resource_file(database_url)

    # ✅ 이제 리스트가 존재하니 처리 시작
    if not os.path.exists(resource_list_file):
        print(f"❌ 리소스 리스트가 여전히 없습니다: {resource_list_file}")
        return

    process_character_face_all(resource_list_file, num_range)

    if os.path.exists(resource_list_file):
        os.remove(resource_list_file)
        print(f"🗑️ 리소스 리스트 파일 삭제 완료: {resource_list_file}")

    nty_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.nty')]
    for f in nty_files:
        file_path = os.path.join(DATA_DIR, f)
        os.remove(file_path)
        print(f"🗑️ nty 파일 삭제 완료: {file_path}")
if __name__ == "__main__":
    if len(sys.argv) == 3:
        num_start = int(sys.argv[1])
        num_end = int(sys.argv[2])
        num_range = (num_start, num_end)
    else:
        num_range = (14501, 14505)  # 기본값

    main(num_range=num_range)