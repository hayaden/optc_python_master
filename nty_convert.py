from src.auth import register_user, login_user
from database import check_resources, download_resource_file, extract_resource_urls, download_and_decrypt_database
import os
import requests
import json
import sqlite3
import struct
import base64
import ctypes
import src.config as config
import src.cryption as cryption

# 리소스 목록 JSON 복호화: 기존 고정 키 사용
def download_and_save_resource_file(database_url):
    try:
        filename = database_url.split("/")[-1]
        response = requests.get(database_url)
        if response.status_code == 200:
            with open(filename, "wb") as resource:
                resource.write(response.content)

            # ✅ 고정된 복호화 키 사용
            fixed_key = cryption.create_from_key("J6oxF6iN")
            decrypted_filename = cryption.nty_decryptor(fixed_key, filename, ".json",True)

            # ✅ 복호화 성공 시 저장
            if decrypted_filename and os.path.exists(decrypted_filename):
                target_name = "original_resource_list.json"
                if os.path.exists(target_name):
                    os.remove(target_name)  # 기존 파일 삭제
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

# 개별 nty 파일은 로그인 후 동적 키 사용
def download_and_decrypt_nty(url):
    try:
        output_dir = "./"
        filename = url.split('/')[-1]
        name = filename.split("-")[0] + ".nty"
        filepath = os.path.join(output_dir, name)
        response = requests.get(url)
        if response.status_code == 200:
            with open(filepath, 'wb') as file:
                file.write(response.content)
                file.flush()
                os.fsync(file.fileno())  # ✅ 저장 확정
            k = cryption.create_from_key("J6oxF6iN")
            cryption.nty_decryptor(k, name, ".png",False)
        else:
            print(f"Failed to download the file {name}.")
    except Exception as e:
        print(f"Error in download_and_decrypt_database: {e}")

def extract_resource_urls_jhs(json_filename):
    try:
        with open(json_filename, 'r', encoding='utf-8') as input_file:
            data = json.load(input_file)
            urls = [
                f"{resource.get('url')}/{resource.get('name')}"
                for resource in data['resources']
                 if (
                resource.get('content_id') is not None and
                14422 <= resource['content_id'] <= 14425 and
                resource.get('type') == "character"
                )
                #if resource.get('name') == "character_1536-0.nty"
                #if resource.get('type') == "sqlite_database"
            ]
        #os.remove(json_filename)    
        return urls
    except Exception as e:
        print(f"Error in extract_resource_urls: {e}")
        return []

def main():
    lang = 'ko'
    register_user(language=lang)
    login_user(language=lang)
    database_url, version = check_resources()
    if not database_url:
        return

    decrypted_filename = download_and_save_resource_file(database_url)
    if not decrypted_filename:
        return

    urls = extract_resource_urls_jhs(decrypted_filename)
    if not urls:
        return

    for url in urls:
        download_and_decrypt_nty(url)


if __name__ == "__main__":
    main()
