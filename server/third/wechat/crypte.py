import json
import base64
from Crypto.Cipher import AES
from server.third.wechat.action import as_cfg


class WXBizDataCrypt(object):
    def __init__(self, session_key: str, iv: str):
        self.app_id = as_cfg.appid
        self.skey = base64.b64decode(session_key)
        self.iv = base64.b64decode(iv)

    @property
    def cryptor(self):
        aes = AES.new(self.skey, AES.MODE_CBC, self.iv)
        return aes

    def decrypt(self, encrypted_data):
        encrypted_data = base64.b64decode(encrypted_data)
        decrypted = json.loads(self._unpad(self.cryptor.decrypt(encrypted_data)))
        assert decrypted['watermark']['appid'] == self.app_id, f'Invalid AppID'
        return decrypted

    @staticmethod
    def _unpad(s):
        return s[:-ord(s[len(s)-1:])]


def wx_data_decrypt(encrypted_data, skey, iv):
    data = WXBizDataCrypt(skey, iv).decrypt(encrypted_data)
    return data
