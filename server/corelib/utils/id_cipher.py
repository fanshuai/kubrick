import struct
from Crypto.Cipher import ARC4


# 用户ID加密解密
class IdCipher(object):
    secret_key = b'LikeARollingStone'
    MAX = 4294967295

    def encrypt(self, eid):
        obj = ARC4.new(self.secret_key)
        ciph = obj.encrypt(struct.pack('I', eid))
        return struct.unpack('I', ciph)[0]

    def decrypt(self, ciph):
        obj = ARC4.new(self.secret_key)
        did = obj.decrypt(struct.pack('I', ciph))
        return struct.unpack('I', did)[0]


id_cipher = IdCipher()
id_encrypt = id_cipher.encrypt
id_decrypt = id_cipher.decrypt
