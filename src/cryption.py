import ctypes
import re
# Load the DLL
libc = ctypes.cdll.LoadLibrary("./src/bisque/BisquseDLL.dll")

# Function type declarations
libc.CreateFromKey.argtypes = [ctypes.c_char_p]
libc.CreateFromKey.restype = ctypes.c_void_p
libc.Decrypt.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.POINTER(ctypes.c_char_p)]
libc.Decrypt.restype = ctypes.c_int
libc.Encrypt.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
libc.Encrypt.restype = ctypes.c_char_p
libc.ReleaseBuffer.argtypes = [ctypes.c_char_p]
libc.ReleaseInst.argtypes = [ctypes.c_void_p]
libc.DecryptNTY.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, ctypes.POINTER(ctypes.c_char_p), ctypes.c_bool]
libc.DecryptNTY.restype = ctypes.c_int

def create_from_key(key):
    """
    Return a pointer to a MD159 ("inst" used in all functions below)
    """
    try:
        return libc.CreateFromKey(key.encode('utf-8'))
    except Exception as e:
        print(f"Error in create_from_key: {e}")
        return None
    
def extract_start_number(filename):
    """
    filename에서 character_face_9000_9099-2.nty 처럼
    9000을 추출
    """
    match = re.search(r'character_face_(\d+)_\d+-', filename)
    if match:
        return int(match.group(1))
    return None

def decrypt(key, data_to_decrypt):
    """
    Decrypt the given data using the provided key.
    """
    try:
        decrypted = ctypes.c_char_p()
        libc.Decrypt(key, data_to_decrypt.encode('utf-8'),  ctypes.byref(decrypted))
        
        return decrypted
    except Exception as e:
        print(f"Error in decrypt: {e}")
        return None
    finally:
        if decrypted:
            release_buffer(decrypted)


def encrypt(key, data_to_encrypt):
    """
    Encrypt the given data using the provided key.
    """
    try:
        data_to_encrypt_utf8 = data_to_encrypt.encode('utf-8')
        encrypted = libc.Encrypt(key, data_to_encrypt.encode('utf-8'), len(data_to_encrypt_utf8))
        return encrypted
    except Exception as e:
        print(f"Error in encrypt: {e}")
        return None

def release_buffer(buffer):
    """
    Release the buffer given by the Decrypt or Encrypt function.
    """
    try:
        libc.ReleaseBuffer(buffer)
    except Exception as e:
        print(f"Error in release_buffer: {e}")
def remove_slice(data, start, end):
    return data[:start] + data[end:]
def release_key(key):
    """
    Release an MD159 instance when it is no longer needed.
    """
    try:
        libc.ReleaseInst(key)
    except Exception as e:
        print(f"Error in release_key: {e}")

def find_signature_offsets(data, signature_bytes):
    """
    바이너리 안에서 signature_bytes 패턴이 나오는 오프셋 모두 리턴
    """
    positions = []
    i = 0
    while i <= len(data) - len(signature_bytes):
        if data[i:i+len(signature_bytes)] == signature_bytes:
            positions.append(i)
        i += 1
    return positions

def patch_block_size(full_block, size_diff):
    """
    full_block 헤더의 6~7 바이트를 size_diff로 세팅
    """
    b = bytearray(full_block)
    size_bytes = size_diff.to_bytes(2, 'big')
    b[6] = size_bytes[0]
    b[7] = size_bytes[1]
    return bytes(b)

def nty_decryptor_multi(key, filename, signature_hex, is_text=False):
    """
    NTY 파일에서 signature_hex 패턴을 기준으로
    16 ~ Base_nth_image 구간을 제거하며 반복 추출
    """
    decrypted = None
    decryptedLength = -1

    try:
        # 1️⃣ 파일 열기
        with open(f"./{filename}", "rb") as file:
            encrypted = file.read()
        encryptedLength = len(encrypted)
        print(f"[DEBUG] 전체 encrypted size: {encryptedLength}")

        # 2️⃣ 시그니처 패턴 바이트
        signature_bytes = bytes.fromhex(signature_hex)

        # 3️⃣ 시그니처 위치 찾기
        offsets = find_signature_offsets(encrypted, signature_bytes)
        if not offsets:
            print("❌ 시그니처가 발견되지 않았습니다.")
            return None

        print(f"✅ 발견된 시그니처 오프셋들: {offsets}")

        size_diffs = []
        for i in range(len(offsets) - 1):
            size_diffs.append(offsets[i+1] - offsets[i])
        # 마지막 블록 크기 추정
        size_diffs.append(len(encrypted) - offsets[-1])
        print(f"✅ 블록 크기 추정값들: {size_diffs}")

        # 5️⃣ 반복 처리
        start_num = extract_start_number(filename)
        if start_num is None:
            print(f"⚠️ 이름에서 시작 번호 추출 실패. 기본값 0 사용")
            start_num = 0

        for idx, Base_nth_image in enumerate(offsets):
            #print(f"\n⭐️ [{idx+1}] Base_nth_image 오프셋 = {Base_nth_image}")

            # 6️⃣ 16 ~ Base_nth_image 제거
            full_block = remove_slice(encrypted, 16, Base_nth_image)
            #print(f"  ➜ full_block 길이(패치 전): {len(full_block)}")

            # 7️⃣ 헤더 크기 필드 패치
            size_diff = size_diffs[idx]
            full_block = patch_block_size(full_block, size_diff)
            #print(f"  ➜ 패치된 size_diff: {size_diff}")

            # 8️⃣ Decrypt
            decrypted = ctypes.c_char_p(None)
            decryptedLength = libc.DecryptNTY(
                key,
                full_block,
                len(full_block),
                ctypes.byref(decrypted),
                is_text
            )
            #print(f"  ➜ Decrypted size: {decryptedLength}")

            if decryptedLength <= 0:
                print("❌ 복호화 실패")
                continue

            # 9️⃣ 결과 파일 저장
            final_number = start_num + (idx + 1)
            out_name = f"{final_number}_face.png"
            output_file_path = f"./data/{out_name}"
            with open(output_file_path, "wb") as output_file:
                output_file.write(ctypes.string_at(decrypted, decryptedLength))

            #print(f"✅ 저장 완료: {output_file_path}")

            # 10️⃣ 해제
            release_buffer(decrypted)

        print("\n✅ 모든 이미지 추출 완료!")

    except Exception as e:
        print(f"❌ Error in nty_decryptor_multi: {e}")

def nty_decryptor(key, filename, extension=None, is_text=True):
    """
    Decrypt an NTY file and save the decrypted data.
    """
    decrypted = None
    decryptedLength = -1  # 초기화 해줌
    try:
        with open(f"./{filename}", "rb") as file:
            encrypted = file.read()
        encryptedLength = len(encrypted)

      
        decrypted = ctypes.c_char_p(None)
        decryptedLength = libc.DecryptNTY(key, encrypted, encryptedLength, ctypes.byref(decrypted), is_text)

        print(f"[DEBUG] decrypted size: {decryptedLength}")

        if decryptedLength <= 0:
            print(f"❌ 복호화 실패: {filename}")
            return None

        name = f"{filename}{extension}" if extension else filename
        output_file_path = f"./{name}"
        with open(output_file_path, "wb") as output_file:
            output_file.write(ctypes.string_at(decrypted, decryptedLength))

        return name

    except Exception as e:
        print(f"Error in nty_decryptor: {e}")
        return None

    finally:
        if decrypted:  # decryptedLength는 이제 안전하게 무시 가능
            release_buffer(decrypted)