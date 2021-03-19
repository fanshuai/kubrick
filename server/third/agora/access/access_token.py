import time
import hmac
import base64
import struct
import random
import logging
from zlib import crc32
from hashlib import sha256
from collections import OrderedDict

from kubrick.initialize import AGORA_APPID, AGORA_CERTIFICATE

kJoinChannel = 1
kPublishAudioStream = 2
kPublishVideoStream = 3
kPublishDataStream = 4
kPublishAudiocdn = 5
kPublishVideoCdn = 6
kRequestPublishAudioStream = 7
kRequestPublishVideoStream = 8
kRequestPublishDataStream = 9
kInvitePublishAudioStream = 10
kInvitePublishVideoStream = 11
kInvitePublishDataStream = 12
kAdministrateChannel = 101
kRtmLogin = 1000

VERSION_LENGTH = 3
APP_ID_LENGTH = 32

logger = logging.getLogger('kubrick.debug')


def get_version():
    return '006'


def pack_uint16(x):
    return struct.pack('<H', int(x))


def pack_uint32(x):
    return struct.pack('<I', int(x))


def pack_int32(x):
    return struct.pack('<i', int(x))


def pack_string(string):
    return pack_uint16(len(string)) + string


def pack_map(m):
    ret = pack_uint16(len(list(m.items())))
    for k, v in list(m.items()):
        ret += pack_uint16(k) + pack_string(v)
    return ret


def pack_map_uint32(m):
    ret = pack_uint16(len(list(m.items())))
    for k, v in list(m.items()):
        ret += pack_uint16(k) + pack_uint32(v)
    return ret


class ReadByteBuffer(object):

    def __init__(self, buffer):
        self.buffer = buffer
        self.position = 0

    def un_pack_uint16(self):
        len_h = struct.calcsize('H')
        buff = self.buffer[self.position: self.position + len_h]
        ret = struct.unpack('<H', buff)[0]
        self.position += len_h
        return ret

    def un_pack_uint32(self):
        len_h = struct.calcsize('I')
        buff = self.buffer[self.position: self.position + len_h]
        ret = struct.unpack('<I', buff)[0]
        self.position += len_h
        return ret

    def un_pack_string(self):
        strlen = self.un_pack_uint16()
        buff = self.buffer[self.position: self.position + strlen]
        ret = struct.unpack('<' + str(strlen) + 's', buff)[0]
        self.position += strlen
        return ret

    def un_pack_map_uint32(self):
        messages = {}
        maplen = self.un_pack_uint16()

        for index in range(maplen):
            key = self.un_pack_uint16()
            value = self.un_pack_uint32()
            messages[key] = value
        return messages


def un_pack_content(buff):
    readbuf = ReadByteBuffer(buff)
    signature = readbuf.un_pack_string()
    crc_channel_name = readbuf.un_pack_uint32()
    crc_uid = readbuf.un_pack_uint32()
    m = readbuf.un_pack_string()

    return signature, crc_channel_name, crc_uid, m


def un_pack_messages(buff):
    readbuf = ReadByteBuffer(buff)
    salt = readbuf.un_pack_uint32()
    ts = readbuf.un_pack_uint32()
    messages = readbuf.un_pack_map_uint32()

    return salt, ts, messages


class AccessToken(object):

    def __init__(self, channel='', uid=''):
        random.seed(time.time())
        self.appID = AGORA_APPID
        self.certificate = AGORA_CERTIFICATE
        self.channel = channel
        self.ts = int(time.time()) + 24 * 3600
        self.salt = random.randint(1, 99999999)
        self.messages = {}
        self.uidStr = str(uid)

    def add_privilege(self, privilege, expire_ts):
        self.messages[privilege] = expire_ts

    def from_string(self, origin_token):
        try:
            dk6version = get_version()
            origin_version = origin_token[:VERSION_LENGTH]
            if origin_version != dk6version:
                return False

            # origin_appid = origin_token[VERSION_LENGTH:(VERSION_LENGTH + APP_ID_LENGTH)]
            origin_content = origin_token[(VERSION_LENGTH + APP_ID_LENGTH):]
            origin_content_decoded = base64.b64decode(origin_content)

            signature, crc_channel_name, crc_uid, m = un_pack_content(origin_content_decoded)
            self.salt, self.ts, self.messages = un_pack_messages(m)

        except Exception as exc:
            logger.exception(str(exc))
            return False

        return True

    def build(self):

        self.messages = OrderedDict(sorted(iter(self.messages.items()), key=lambda x: int(x[0])))

        m = pack_uint32(self.salt) + pack_uint32(self.ts) \
            + pack_map_uint32(self.messages)

        val = self.appID.encode('utf-8') + self.channel.encode('utf-8') + self.uidStr.encode('utf-8') + m

        signature = hmac.new(self.certificate.encode('utf-8'), val, sha256).digest()
        crc_channel_name = crc32(self.channel.encode('utf-8')) & 0xffffffff
        crc_uid = crc32(self.uidStr.encode('utf-8')) & 0xffffffff

        content = pack_string(signature) + pack_uint32(crc_channel_name) + pack_uint32(crc_uid) + pack_string(m)

        version = get_version()
        ret = version + self.appID + base64.b64encode(content).decode('utf-8')
        return ret
