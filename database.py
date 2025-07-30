import os
import requests
import json
import sqlite3
import struct
import base64
import ctypes
import src.config as config
import src.cryption as cryption

output_dir = "./"
libc = ctypes.cdll.LoadLibrary("./src/bisque/BisquseDLL.dll")
libc.CreateFromKey.argtypes = [ctypes.c_char_p]
libc.CreateFromKey.restype = ctypes.c_void_p
libc.Decrypt.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.POINTER(ctypes.POINTER(ctypes.c_char))]
libc.Decrypt.restype = ctypes.c_int
libc.Encrypt.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
libc.Encrypt.restype = ctypes.c_char_p
libc.ReleaseBuffer.argtypes = [ctypes.c_char_p]
libc.ReleaseInst.argtypes = [ctypes.c_void_p]

def check_resources():
    try:
        url = f"{config.get_api_url()}/resources/resource_list_path.json"
        r = config.SESSION.get(url, headers=config.SESSION.headers)
        decoded = cryption.decrypt(config.USER_INFO['session_key'], r.json()['data'])
        decoded = json.loads(decoded.value.decode('utf-8'))

        database_url = decoded['resource_list_uri']
        filename = database_url.split('/')[-1]
        version = filename.split("_")[0]
        return database_url, version
    except Exception as e:
        print(f"Error in check_resources: {e}")
        return None, None

def check_database(lang='ko'):
    database_url, version = check_resources()
    if not database_url:
        return

    decrypted_filename = download_resource_file(database_url)
    if not decrypted_filename:
        return

    urls = extract_resource_urls(decrypted_filename)
    if not urls:
        return

    for url in urls:
        download_and_decrypt_database(url)
    process_files(lang, version)

def download_resource_file(database_url):
    try:
        filename = database_url.split("/")[-1]
        response = requests.get(database_url)
        if response.status_code == 200:
            with open(filename, "wb") as resource:
                resource.write(response.content)
            k = cryption.create_from_key("J6oxF6iN")
            return cryption.nty_decryptor(k, filename, ".json")
        else:
            print(f"Failed to download resource file: {filename}")
    except Exception as e:
        print(f"Error in download_resource_file: {e}")

def extract_resource_urls(json_filename):
    try:
        with open(json_filename, 'r', encoding='utf-8') as input_file:
            data = json.load(input_file)
            urls = [
                f"{resource.get('url')}/{resource.get('name')}"
                for resource in data['resources']
                if resource.get('type') == "sqlite_database"
            ]
        os.remove(json_filename)
        return urls
    except Exception as e:
        print(f"Error in extract_resource_urls: {e}")
        return []

def download_and_decrypt_database(url):
    try:
        filename = url.split('/')[-1]
        name = filename.split("-")[0] + ".nty"
        filepath = os.path.join(output_dir, name)
        response = requests.get(url)
        if response.status_code == 200:
            with open(filepath, 'wb') as file:
                file.write(response.content)
            k = cryption.create_from_key("J6oxF6iN")
            cryption.nty_decryptor(k, name, None)
        else:
            print(f"Failed to download the file {name}.")
    except Exception as e:
        print(f"Error in download_and_decrypt_database: {e}")

def process_files(lang='ko', version=''):
    try:
        key = "JGcu2DjohFm84viZHe1Et5Qt"
        keydata = libc.CreateFromKey(key.encode('utf-8'))

        def read_header(fh):
            magic, _ = struct.unpack('<4s12s', fh.read(16))
            assert magic == b'IKMN'

        def read_map_tables(fh):
            tables_crypted, = struct.unpack('<512s', fh.read(512))
            tables_crypted_b64 = base64.b64encode(tables_crypted)
            tables = ctypes.pointer(ctypes.c_char())
            decrypted_len = libc.Decrypt(keydata, tables_crypted_b64, ctypes.byref(tables))
            assert decrypted_len == 512
            enc_map = bytearray(tables[0:256])
            dec_map = bytearray(tables[256:512])
            libc.ReleaseBuffer(tables)
            return enc_map, dec_map

        def remap_block(the_map, original):
            return bytearray(the_map[b] for b in original)

        def dec_db(db_encrypted, db_decrypted):
            with open(db_encrypted, "rb") as fh_encrypted, open(db_decrypted, "wb") as fh_decrypted:
                read_header(fh_encrypted)
                enc_map, dec_map = read_map_tables(fh_encrypted)
                while True:
                    coded = fh_encrypted.read(8192)
                    if not coded:
                        break
                    decoded = remap_block(dec_map, coded)
                    fh_decrypted.write(decoded)
            new_file_name = generate_new_filename(db_encrypted, lang)
            os.rename(db_decrypted, new_file_name)

        def generate_new_filename(db_encrypted, lang):
            index = 1
            while True:
                new_file_name = f"sakura_master_db_{index:03}_{lang}.db"
                if not os.path.exists(new_file_name):
                    return new_file_name
                index += 1

        files = [f for f in os.listdir('.') if f.startswith('Sakura') and f.endswith('.nty')]
        for file in files:
            db_encrypted = file
            db_decrypted = db_encrypted.replace('.nty', '.db')
            dec_db(db_encrypted, db_decrypted)
            os.remove(db_encrypted)

        migrate_databases(lang, version)
    except Exception as e:
        print(f"Error in process_files: {e}")

def migrate_databases(lang='ko', version=''):
    try:
        destination_db_path = f'./data/sakura_{lang}.db'
        source_db_paths = [f for f in os.listdir('.') if f.startswith('sakura_master_db_') and f.endswith(f'_{lang}.db')]
        destination_conn = sqlite3.connect(destination_db_path)
        destination_cursor = destination_conn.cursor()

        for source_db_path in source_db_paths:
            migrate_database(source_db_path, destination_cursor)

        destination_conn.commit()
        destination_conn.close()

        for delete in source_db_paths:
            os.remove(delete)

        insert_version_into_db(destination_db_path, version)
    except Exception as e:
        print(f"Error in migrate_databases: {e}")

def migrate_database(source_db_path, destination_cursor):
    try:
        source_conn = sqlite3.connect(source_db_path)
        source_cursor = source_conn.cursor()
        source_cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = source_cursor.fetchall()

        for table in tables:
            table_name = table[0]
            destination_cursor.execute(f"DROP TABLE IF EXISTS {table_name};")
            source_cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}';")
            create_table_query = source_cursor.fetchone()[0]
            destination_cursor.execute(create_table_query)

            source_cursor.execute(f"SELECT * FROM {table_name};")
            rows = source_cursor.fetchall()
            for row in rows:
                placeholders = ', '.join(['?'] * len(row))
                insert_query = f"INSERT INTO {table_name} VALUES ({placeholders})"
                destination_cursor.execute(insert_query, row)

            source_cursor.execute(f"SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='{table_name}';")
            indexes = source_cursor.fetchall()
            for index in indexes:
                destination_cursor.execute(index[1])
        source_conn.close()
    except Exception as e:
        print(f"Error in migrate_database: {e}")

def insert_version_into_db(db_path, version):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS Version (Version TEXT)''')
        cursor.execute("INSERT INTO Version VALUES (?)", (version,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error in insert_version_into_db: {e}")

if __name__ == "__main__":
    check_database(lang='ko')
