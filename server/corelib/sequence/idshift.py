import hmac
import uuid
import random
import hashlib


def fmt_bid(bid):
    """ BigInteger转16进制 """
    hexid = format(bid, 'x').upper()
    return hexid


def parse_tid(tid):
    """ 16进制转BigInteger """
    bid = int(tid, 16)
    return bid


def generate_uuid5():
    """
    根据[uuid4]生成[uuid5]
    """
    uid_hex = uuid.uuid4().hex
    uuid5 = uuid.uuid5(uuid.NAMESPACE_DNS, uid_hex)
    return uuid5


def generate_name_uuid(name):
    """
    根据[name]生成[uuid5]
    """
    assert isinstance(name, str) and name
    uuid5 = uuid.uuid5(uuid.NAMESPACE_DNS, name)
    return uuid5


def generate_captcha(n=6):
    """
    生成随机数字验证码
    """
    try:
        assert 1 < n < 9
    except (TypeError, AssertionError):
        n = 6
    seeds = '1234567890'
    listr = ''.join(random.sample(seeds, n - 1))
    first = random.choice(seeds[:-1])
    code = first + listr
    return code


def hmac_hash(key, msg):
    """
    HMAC 摘要签名，SHA1
    """
    if isinstance(key, bytes):
        pass
    elif isinstance(key, str):
        key = key.encode()
    else:
        key = str(key).encode()
    if isinstance(msg, bytes):
        pass
    elif isinstance(msg, str):
        msg = msg.encode()
    else:
        msg = str(msg).encode()
    hexdigest = hmac.new(key, msg, hashlib.sha1).hexdigest()
    return hexdigest


def hash_md5(msg):
    if isinstance(msg, bytes):
        pass
    elif isinstance(msg, str):
        msg = msg.encode()
    else:
        msg = str(msg).encode()
    hexdigest = hashlib.md5(msg).hexdigest()
    return hexdigest


def hash_sha1(msg):
    if isinstance(msg, bytes):
        pass
    elif isinstance(msg, str):
        msg = msg.encode()
    else:
        msg = str(msg).encode()
    hexdigest = hashlib.sha1(msg).hexdigest()
    return hexdigest


if __name__ == '__main__':
    print(generate_uuid5())
    dic = dict(a=1, sub=dict(b=2))
