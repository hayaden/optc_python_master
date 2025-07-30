import ctypes
import src.config as config
import src.cryption as cryption

dll = ctypes.cdll.LoadLibrary("BisquseDLL.dll")
dll.CreateFromKey.argtypes = [ctypes.c_char_p]
dll.CreateFromKey.restype = ctypes.c_void_p
dll.DecryptNTY.argtypes = [
    ctypes.c_void_p,       # inst
    ctypes.c_char_p,       # encrypted input
    ctypes.c_int,          # input length
    ctypes.POINTER(ctypes.c_char_p),  # output buffer
    ctypes.c_bool          # flag
]
dll.DecryptNTY.restype = ctypes.c_int

with open("character_1020.nty", "rb") as f:
    encrypted = f.read()
encrypted_length = len(encrypted)

key_candidates = [
    "J6oxF6iN",
    "fD9dDpuO",
    "fD9dDpuA",
    "fD9dDpu1",
    "D81uUL9r",
    "xWI96tRI",
    "xXI96tSI",
    "teJL3mlu",
    "I7WuCU7Q",
    "yqXqLqR1",
    "D6GHJmzs",
    "v68C0IXMI",
    "2MYDYdYtY2",
    "xsj0ZQgS",
    "rZ1VwGf5",
    "8SIffK5W",
    "j2WrUvuj",
    "JuuOD53l",
    "UOjDYu1e",
    "g1TLyFQH",
    "Dd1aZ2eA",
    "It2ohpO2",
    "RaTHyO3R",
    "v8EMgQ7CT",
    "gSg3Gq6w",
    "M3Vxa8Fd",
    "5q3y3ucF",
    "2krWJWjWZWzWF",
    "lL5S3QH5",
    "13nKWtbK",
    "Dx6LqBgeyw",
    "E64NM7qIQo",
    "tQPR32MPQH",
    "7fzd9cNd9",
    "pZvlZpl7",
    "3RL53SLGnN1",
    "rxl1bz5A",
    "2cYrYjYZYzYn",
    "sPzBDV7a",
    "bTmp5Eo4Iq",
    "CxL6arcGe",
    "kOno4E65",
    "64sChfIh",
    "PHS4YSBv",
    "uLgAWb3z",
    "8en7OAyOSJ",
    "mV4EKz6x",
    "eM5vnGCe",
    "YRioC41s",
    "s6qrDxVc",
    "3ShoXT3R",
    "COpY9H9nC",
    "lWfzwVs3",
    "E20DXtti",
    "mLA68jvi",
    "K5aJvCkZJ",
    "mMSIDPN6",
    "cb6ZJ5YT",
    "LQXMOp6d7",
    "po7FvLkS",
    "TcL7sxqL",
    "YYiXTIf3",
    "wCSBy9TrD",
    "fZRttcg0C",
    "KcfJ0RaM",
    "kLtV0IxA",
    "4Nd4hiNd",
    "YPU4cZuZ",
    "uWhn85WX",
    "UfuUVoE5",
    "3Tmya2On",
    "8s098jdT",
    "znG3C3ij",
    "S33oHk20",
    "d91dYASo",
    "98VrmfBG",
    "oC6bZn46",
]

for key in key_candidates:
    inst = dll.CreateFromKey(key.encode('utf-8'))
    if not inst:
        print(f"❌ 키 생성 실패: {key}")
        continue

    decrypted = ctypes.c_char_p()
    try:
        length = dll.DecryptNTY(inst, encrypted, encrypted_length, ctypes.byref(decrypted), True)
        print(f"🔑 [{key}] Decrypted Length: {length}")
    except Exception as e:
        print(f"❌ [{key}] Decryption failed: {e}")