"""
Dict内容加解密
"""
import re
from mirage.crypto import Crypto

crypto = Crypto()

# 需加密的敏感词
sensitive_keys = (
    'key', 'token', 'secret', 'password', 'signature',  # 通用
    'vin', 'owner', 'address', 'name', 'number', 'authority',  # OCR识别
    'caller', 'called', 'dsc', 'src',  # 云讯双呼
)
# 需加密的敏感词正则编译
sensitive_pattern = re.compile('|'.join(sensitive_keys), re.I)


def encrypt_dic(dic: dict) -> dict:
    """
    Dict敏感字段加密，仅支持字符串
    """
    for key, val in dic.items():
        if not sensitive_pattern.search(key):
            if isinstance(val, dict):
                dic[key] = encrypt_dic(val)
            else:
                dic[key] = val
            continue
        if isinstance(val, str):
            dic[key] = crypto.encrypt(val)
        elif isinstance(val, dict):
            dic[key] = encrypt_dic(val)
        else:
            dic[key] = val
    return dic


def decrypt_dic(dic: dict) -> dict:
    """
    Dict敏感字段解密，仅支持字符串
    """
    for key, val in dic.items():
        if not sensitive_pattern.search(key):
            if isinstance(val, dict):
                dic[key] = decrypt_dic(val)
            else:
                dic[key] = val
            continue
        if isinstance(val, str):
            dic[key] = crypto.decrypt(val)
        elif isinstance(val, dict):
            dic[key] = decrypt_dic(val)
        else:
            dic[key] = val
    return dic
