import os
import re
import requests
import json
import sqlite3
import sys
from src.auth import register_user, login_user
from database import check_resources
import src.cryption as cryption

DATA_DIR = "./data"
ROOT_DIR = "./data"
os.makedirs(DATA_DIR, exist_ok=True)

def filter_resource_list(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [res for res in data["resources"] if res.get("type") == "ship"]

def download_and_save_resource_file(database_url):
    try:
        filename = database_url.split("/")[-1]
        local_path = os.path.join(DATA_DIR, filename)
        resp = requests.get(database_url)
        if resp.status_code != 200:
            print(f"❌ 다운로드 실패: {filename}")
            return None
        with open(local_path, "wb") as resource:
            resource.write(resp.content)

        fixed_key = cryption.create_from_key("J6oxF6iN")
        decrypted_filename = cryption.nty_decryptor(
            fixed_key, local_path, ".json", True
        )
        if decrypted_filename and os.path.exists(decrypted_filename):
            target_name = os.path.join(DATA_DIR, "original_resource_list.json")
            if os.path.exists(target_name):
                os.remove(target_name)
            os.rename(decrypted_filename, target_name)
            print(f"✅ 저장: {target_name}")
            return target_name
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def get_ship_id_from_db(server_id, db_path=os.path.join(ROOT_DIR, "sakura_ko.db")):
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT shipId_ FROM MstShip_ WHERE serverId_=?", (server_id,))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else None
    except:
        return None

def extract_ship_num_from_name(name):
    m = re.search(r"ship_(\d+)", name)
    return m.group(1) if m else None

def rename_image(img_path, ship_id=None, content_id=None, name=None):
    if not os.path.exists(img_path):
        print(f"❌ 파일 없음: {img_path}")
        return
    base_id = None
    if ship_id is not None:
        base_id = ship_id
    elif content_id is not None:
        base_id = content_id
    elif name:
        base_id = extract_ship_num_from_name(name)
    if base_id is None:
        base_id = "unknown"

    new_name = os.path.join(DATA_DIR, f"ship_{base_id}.png")
    if os.path.exists(new_name):
        os.remove(new_name)
    os.rename(img_path, new_name)
    print(f"✅ 저장: {new_name}")

def download_and_decrypt_nty(url):
    try:
        filename = url.split("/")[-1]
        name = filename.split("-")[0] + ".nty"
        local_nty = os.path.join(DATA_DIR, name)
        resp = requests.get(url)
        if resp.status_code != 200:
            print(f"❌ 다운로드 실패: {name}")
            return None
        with open(local_nty, "wb") as file:
            file.write(resp.content)
            file.flush()
            os.fsync(file.fileno())

        k = cryption.create_from_key("J6oxF6iN")
        decrypted_file = cryption.nty_decryptor(k, local_nty, None, False)
        return os.path.join(DATA_DIR, os.path.basename(decrypted_file)) if decrypted_file else None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def process_all_ships(resource_list_path, db_path=os.path.join(ROOT_DIR, "sakura_ko.db")):
    targets = filter_resource_list(resource_list_path)
    print(f"\n⭐ 총 {len(targets)}개의 ship 리소스\n")
    for res in targets:
        url = f"{res['url']}/{res['name']}"
        server_id = res.get("content_id")
        print(f"⬇️ ship: {res['name']} (content_id={server_id})")
        img_file = download_and_decrypt_nty(url)
        if img_file:
            ship_id = None
            if server_id is not None:
                ship_id = get_ship_id_from_db(server_id, db_path)
            rename_image(img_file, ship_id=ship_id, content_id=server_id, name=res['name'])
        print("-" * 40)

def main():
    register_user(language="ko")
    login_user(language="ko")
    database_url, _ = check_resources()
    if not database_url:
        return
    decrypted_filename = download_and_save_resource_file(database_url)
    if not decrypted_filename:
        return
    process_all_ships(decrypted_filename)

if __name__ == "__main__":
    main()
